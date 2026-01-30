# Authentication Implementation Plan for Riftventory

## Overview
Implement user authentication using Supabase Auth with JWT-based token validation. This replaces the current insecure `x_user_id` header approach with proper authentication.

### Requirements
- **Auth methods**: Email/Password + OAuth (Google, Apple)
- **Email verification**: Not required (immediate access after signup)
- **Password reset**: Not needed for initial implementation

## Current State
- **Database**: Minimal user table (`user_id` UUID, `user_name`, `created_at`) - no auth columns
- **Backend**: Uses spoofable `x_user_id` header, no JWT validation
- **Frontend**: Supabase client exists but no auth implementation, all routes unprotected

---

## Phase 1: Database Changes

### New Migration File
**Create**: `supabase/migrations/20260130000000_auth_integration.sql`

---

### Step 1.1: Add auth columns to user table

```sql
-- Add auth_id column for linking to Supabase auth (no foreign key to avoid coupling)
ALTER TABLE "public"."user"
ADD COLUMN "auth_id" UUID UNIQUE;

-- Add email column for user lookup
ALTER TABLE "public"."user"
ADD COLUMN "email" TEXT UNIQUE;
```

**Note**: No foreign key reference to `auth.users` - this keeps the schema decoupled from Supabase internals. The `UNIQUE` constraint automatically creates an index for fast lookups.

---

### Step 1.2: Lazy Profile Creation (Backend)

Instead of using database triggers on `auth.users`, user profiles are created lazily on first authenticated API request. This approach:
- Avoids coupling to Supabase's internal schema
- Is self-healing (handles edge cases automatically)
- Works with any auth provider

See **Phase 2, Step 2.2** for implementation details.

---

### Step 1.3: Add RLS policies for all tables

#### 1.3a: User table policies

```sql
-- Users can view their own profile
CREATE POLICY "Users can view own profile"
  ON "public"."user" FOR SELECT
  USING (auth.uid() = auth_id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
  ON "public"."user" FOR UPDATE
  USING (auth.uid() = auth_id);
```

#### 1.3b: Card and Set tables (public read)

```sql
-- Cards are publicly readable (no auth required)
CREATE POLICY "Cards are publicly readable"
  ON "public"."card" FOR SELECT
  USING (true);

-- Sets are publicly readable
CREATE POLICY "Sets are publicly readable"
  ON "public"."set" FOR SELECT
  USING (true);
```

#### 1.3c: Inventory table policies

```sql
-- Users can view their own inventories OR any non-private inventory
CREATE POLICY "Users can view accessible inventories"
  ON "public"."inventory" FOR SELECT
  USING (auth.uid() = user_id OR is_private = false);

-- Users can create inventories for themselves
CREATE POLICY "Users can create own inventories"
  ON "public"."inventory" FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own inventories
CREATE POLICY "Users can update own inventories"
  ON "public"."inventory" FOR UPDATE
  USING (auth.uid() = user_id);

-- Users can delete their own inventories
CREATE POLICY "Users can delete own inventories"
  ON "public"."inventory" FOR DELETE
  USING (auth.uid() = user_id);
```

#### 1.3d: Inventory_card table policies

```sql
-- Users can view cards in their own inventories OR in non-private inventories
CREATE POLICY "Users can view accessible inventory cards"
  ON "public"."inventory_card" FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM "public"."inventory"
      WHERE inventory.inventory_id = inventory_card.inventory_id
      AND (inventory.user_id = auth.uid() OR inventory.is_private = false)
    )
  );

CREATE POLICY "Users can insert own inventory cards"
  ON "public"."inventory_card" FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM "public"."inventory"
      WHERE inventory.inventory_id = inventory_card.inventory_id
      AND inventory.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update own inventory cards"
  ON "public"."inventory_card" FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM "public"."inventory"
      WHERE inventory.inventory_id = inventory_card.inventory_id
      AND inventory.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete own inventory cards"
  ON "public"."inventory_card" FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM "public"."inventory"
      WHERE inventory.inventory_id = inventory_card.inventory_id
      AND inventory.user_id = auth.uid()
    )
  );
```

#### 1.3e: Trade table policies

```sql
-- Trade participants can view their trades
CREATE POLICY "Trade participants can view trades"
  ON "public"."trade" FOR SELECT
  USING (
    auth.uid() = initiator_user_id OR
    auth.uid() = recipient_user_id
  );

-- Users can create trades they initiate
CREATE POLICY "Users can create trades"
  ON "public"."trade" FOR INSERT
  WITH CHECK (auth.uid() = initiator_user_id);

-- Trade participants can update trades
CREATE POLICY "Trade participants can update trades"
  ON "public"."trade" FOR UPDATE
  USING (
    auth.uid() = initiator_user_id OR
    auth.uid() = recipient_user_id
  );
```

#### 1.3f: Trade escrow table policies

```sql
-- Trade participants can view escrow items
CREATE POLICY "Trade participants can view escrow"
  ON "public"."trade_escrow" FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM "public"."trade"
      WHERE trade.trade_id = trade_escrow.trade_id
      AND (trade.initiator_user_id = auth.uid()
           OR trade.recipient_user_id = auth.uid())
    )
  );

-- Trade initiators can manage escrow items
CREATE POLICY "Initiators can manage escrow"
  ON "public"."trade_escrow" FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM "public"."trade"
      WHERE trade.trade_id = trade_escrow.trade_id
      AND trade.initiator_user_id = auth.uid()
    )
  );
```

#### 1.3g: Trade recipient table policies

```sql
-- Trade participants can view requested items
CREATE POLICY "Trade participants can view recipient items"
  ON "public"."trade_recipient" FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM "public"."trade"
      WHERE trade.trade_id = trade_recipient.trade_id
      AND (trade.initiator_user_id = auth.uid()
           OR trade.recipient_user_id = auth.uid())
    )
  );

-- Trade initiators can manage requested items
CREATE POLICY "Initiators can manage recipient items"
  ON "public"."trade_recipient" FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM "public"."trade"
      WHERE trade.trade_id = trade_recipient.trade_id
      AND trade.initiator_user_id = auth.uid()
    )
  );
```

#### 1.3h: Trade history table policies

```sql
-- Trade participants can view trade history
CREATE POLICY "Trade participants can view history"
  ON "public"."trade_history" FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM "public"."trade"
      WHERE trade.trade_id = trade_history.trade_id
      AND (trade.initiator_user_id = auth.uid()
           OR trade.recipient_user_id = auth.uid())
    )
  );

-- System inserts history (via service role), users cannot directly insert
```

---

## Phase 2: Backend Changes

### Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| `backend/auth.py` | CREATE | JWT validation, `get_current_user` dependency with lazy profile creation |
| `backend/main.py` | MODIFY | Add auth endpoints, protect existing endpoints |
| `backend/requirements.txt` | MODIFY | Add `python-jose[cryptography]` |
| `backend/models/auth.py` | CREATE | Auth Pydantic models |

---

### Step 2.1: New Auth Endpoints

- `POST /auth/register` - Email/password registration
- `POST /auth/login` - Email/password login, returns JWT
- `POST /auth/logout` - Sign out
- `GET /auth/me` - Get current user profile

**Note**: OAuth flows (Google, Apple) are handled client-side via Supabase SDK - no backend endpoints needed.

---

### Step 2.2: Lazy Profile Creation in `get_current_user`

The `get_current_user` dependency validates the JWT and ensures a user profile exists, creating one if needed.

```python
async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    supabase: Client = Depends(get_supabase)
) -> CurrentUser:
    # 1. Extract and validate JWT
    token = authorization.replace("Bearer ", "")
    payload = verify_jwt(token)  # Raises 401 if invalid

    auth_id = payload.get("sub")  # Supabase user ID
    email = payload.get("email")

    # 2. Try to get existing profile
    result = supabase.table("user").select("*").eq("auth_id", auth_id).execute()

    if result.data:
        return CurrentUser(**result.data[0])

    # 3. Profile doesn't exist - create it (lazy creation)
    try:
        new_user = {
            "user_id": auth_id,  # Use auth UUID as user_id
            "auth_id": auth_id,
            "email": email,
            "user_name": email.split("@")[0],  # Default username from email
            "created_at": datetime.utcnow().isoformat()
        }
        result = supabase.table("user").insert(new_user).execute()
        return CurrentUser(**result.data[0])

    except Exception as e:
        # 4. Handle race condition - another request created the profile
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            result = supabase.table("user").select("*").eq("auth_id", auth_id).execute()
            if result.data:
                return CurrentUser(**result.data[0])
        raise HTTPException(status_code=500, detail="Failed to create user profile")
```

**Race condition handling**: If two requests arrive simultaneously for a new user, both may try to INSERT. The unique constraint on `auth_id` causes one to fail, which then falls back to SELECT.

---

### Step 2.3: Endpoint Protection

Replace `x_user_id: str = Header(...)` with `current_user: CurrentUser = Depends(get_current_user)` in:

**Trade endpoints** (7 instances):
- `POST /trades` (line ~825)
- `POST /trades/{id}/accept` (line ~997)
- `POST /trades/{id}/reject` (line ~1065)
- `POST /trades/{id}/cancel` (line ~1114)
- `POST /trades/{id}/counter-offer` (line ~1170)
- `POST /trades/{id}/confirm` (line ~1289)
- `POST /trades/{id}/unconfirm` (line ~1358)

**Inventory endpoints** (add auth):
- `POST /inventories`
- `PATCH /inventories/{id}`
- `DELETE /inventories/{id}`
- `POST /inventories/{id}/cards`
- `POST /inventories/{id}/cards/bulk`
- `PATCH /inventories/{id}/cards/{card_id}`
- `DELETE /inventories/{id}/cards/{card_id}`

### CORS Update
Restrict `allow_origins` from `["*"]` to specific frontend URLs.

---

## Phase 3: Frontend Changes

### Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| `app/config/supabase.ts` | MODIFY | Add AsyncStorage for session persistence |
| `app/context/AuthContext.tsx` | CREATE | Auth state management, signIn/signUp/signOut |
| `app/hooks/useAuthenticatedFetch.ts` | CREATE | Axios instance with auth header |
| `app/app/(auth)/_layout.tsx` | CREATE | Auth routes stack layout |
| `app/app/(auth)/login.tsx` | CREATE | Login screen (email + OAuth buttons) |
| `app/app/(auth)/signup.tsx` | CREATE | Signup screen (email + OAuth buttons) |
| `app/app/_layout.tsx` | MODIFY | Wrap with AuthProvider, add route protection |
| `app/package.json` | MODIFY | Add `@react-native-async-storage/async-storage` |

### Route Protection Logic
In root `_layout.tsx`:
- If not authenticated and not on auth screen → redirect to login
- If authenticated and on auth screen → redirect to tabs

---

## Phase 4: OAuth Configuration

### Supabase Dashboard Setup (Manual)
1. Enable Google provider in Authentication → Providers
2. Enable Apple provider in Authentication → Providers
3. Configure OAuth credentials from Google Cloud Console / Apple Developer

### Frontend OAuth Dependencies
Add to `app/package.json`:
- `expo-auth-session` - OAuth flow handling
- `expo-web-browser` - Browser-based OAuth redirects

### OAuth Flow in Login/Signup Screens
- Google Sign-In button → `supabase.auth.signInWithOAuth({ provider: 'google' })`
- Apple Sign-In button → `supabase.auth.signInWithOAuth({ provider: 'apple' })`

---

## Phase 5: Environment Variables

### Backend `.env`
```
SUPABASE_JWT_SECRET=<from-supabase-dashboard>
ALLOWED_ORIGINS=http://localhost:8081,http://localhost:19006
```

### Frontend `.env`
```
EXPO_PUBLIC_API_URL=http://localhost:8000
```

---

## Implementation Order

1. **Database**: Create and apply auth migration (add `auth_id` and `email` columns)
2. **Backend**: Create auth module (`auth.py`) with JWT validation and lazy profile creation
3. **Backend**: Add auth endpoints (`/auth/register`, `/auth/login`, etc.)
4. **Backend**: Update protected endpoints (keep hybrid auth temporarily)
5. **Supabase**: Enable OAuth providers in dashboard (Google, Apple)
6. **Frontend**: Add dependencies (`async-storage`, `expo-auth-session`, `expo-web-browser`)
7. **Frontend**: Create AuthContext and authenticated fetch hook
8. **Frontend**: Create login/signup screens with email + OAuth buttons
9. **Frontend**: Update root layout with AuthProvider and route protection
10. **Frontend**: Update existing API calls to use authenticated fetch
11. **Testing**: Verify full auth flow (email + OAuth)
12. **Cleanup**: Remove deprecated `x_user_id` header support

---

## Verification

1. **Registration**: Create account → redirects to app
2. **Lazy profile creation**: First API request after signup → profile auto-created in `user` table
3. **Login**: Enter credentials → receives JWT → can access protected routes
4. **Protected endpoints**: Requests without valid JWT return 401
5. **Race condition**: Concurrent first requests → only one profile created (no duplicates)
6. **Session persistence**: Close app → reopen → still logged in
7. **Logout**: Sign out → redirects to login → cannot access protected routes