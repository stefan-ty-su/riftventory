# backend/models/auth.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional


class CurrentUser(BaseModel):
    user_id: UUID
    email: str
    user_name: str
    created_at: Optional[datetime] = None


class TokenPayload(BaseModel):
    sub: str          # user_id (matches auth.uid())
    email: str
    exp: int          # expiration timestamp
    aud: str          # audience ("authenticated")


# Request models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    user_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Response models
class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: CurrentUser


class UserResponse(BaseModel):
    user_id: UUID
    email: str
    user_name: str
    created_at: Optional[datetime] = None


class MessageResponse(BaseModel):
    message: str
