from fastapi import Header, HTTPException, status
from jose import jwt, JWTError
from supabase import Client, create_client
from datetime import datetime, timezone
from models.auth import CurrentUser
from typing import Optional
from uuid import UUID
import os

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
JWT_ALGO = "HS256"


def verify_jwt(token: str) -> dict:
    """
    Validates and decodes a Supabase JWT token.

    Parameters:
      - token: The raw JWT string (without "Bearer " prefix)

    Returns:
      - Decoded payload dict containing:
        - sub: str (user_id / UUID matching auth.uid())
        - email: str
        - exp: int (expiration timestamp)
        - aud: str (audience)

    Raises:
      - HTTPException 401 if token is expired, invalid, or malformed
    """
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured"
        )

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[JWT_ALGO],
            audience="authenticated"
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(
    authorization: str = Header(..., alias="Authorization")
) -> CurrentUser:
    """
    FastAPI dependency that extracts and validates the JWT from the
    Authorization header, then returns the current user.

    Implements lazy profile creation - if the user doesn't exist in the
    database, a profile is automatically created on first authenticated request.
    """
    # 1. Extract token from "Bearer <token>" header
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    # 2. Validate and decode JWT
    payload = verify_jwt(token)

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim"
        )

    # 3. Query user table by user_id (matches auth.uid())
    result = supabase.table("user").select("*").eq("user_id", user_id).execute()

    if result.data:
        # User exists - return CurrentUser
        user_data = result.data[0]
        return CurrentUser(
            user_id=UUID(str(user_data["user_id"])),
            email=user_data.get("email", email),
            user_name=user_data["user_name"],
            created_at=user_data.get("created_at")
        )

    # 4. User doesn't exist - create profile (lazy creation)
    try:
        new_user = {
            "user_id": user_id,  # Use auth UUID as user_id
            "email": email,
            "user_name": email.split("@")[0] if email else f"user_{user_id[:8]}",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        result = supabase.table("user").insert(new_user).execute()

        if result.data:
            user_data = result.data[0]
            return CurrentUser(
                user_id=UUID(str(user_data["user_id"])),
                email=user_data.get("email", email),
                user_name=user_data["user_name"],
                created_at=user_data.get("created_at")
            )

    except Exception as e:
        # 5. Handle race condition - another request may have created the profile
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            result = supabase.table("user").select("*").eq("user_id", user_id).execute()
            if result.data:
                user_data = result.data[0]
                return CurrentUser(
                    user_id=UUID(str(user_data["user_id"])),
                    email=user_data.get("email", email),
                    user_name=user_data["user_name"],
                    created_at=user_data.get("created_at")
                )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user profile"
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create user profile"
    )


def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Optional[CurrentUser]:
    """
    Optional auth dependency for endpoints that work with or without auth.
    Returns None if no Authorization header provided.
    """
    if not authorization:
        return None

    return get_current_user(authorization)