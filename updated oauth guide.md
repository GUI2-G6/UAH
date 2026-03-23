# Updated Google OAuth Integration Guide

> **Revised against the actual UAH codebase.**  
> This guide corrects several mismatches with the real DB schema, ORM layer, route prefixes, and existing dependencies that were present in the original draft.  
> **Do not alter any existing code** until you have read through all sections — the order matters.

---

## What Changed vs. the Original Guide

| Topic | Original Guide | This Revision |
|---|---|---|
| DB library | `asyncpg` + raw SQL (`$1/$2`, `fetchrow`) | SQLAlchemy ORM (`Session = Depends(get_db)`) |
| `name` column | Single `name` column | `first_name` + `last_name` (existing schema) |
| `avatar_url` column | Referenced as already existing | Must be added via `ALTER TABLE` |
| `google_id` column | Referenced as already existing | Must be added via `ALTER TABLE` |
| `hashed_password` | Not addressed | NOT NULL in current schema — must be made nullable for OAuth users |
| `username` | Not addressed | NOT NULL UNIQUE in current schema — must be generated for OAuth users |
| Route prefix | `/auth/google` | `/api/auth/google` (matches existing `/api/auth` prefix) |
| Redirect URI | `…/auth/google/callback` | `…/api/auth/google/callback` |
| Dependencies | Install `asyncpg` + others | `httpx`, `python-jose`, `python-dotenv` are **already in requirements.txt** |
| Token response | Raw `{"access_token": …}` dict | Use existing `TokenResponse` schema (includes `user` object) |

---

## Step 1 — Dependencies

`httpx`, `python-jose[cryptography]`, and `python-dotenv` are **already listed in `backend/requirements.txt`** — no new installs are required for the OAuth flow itself.

The only new package needed is `starlette`'s `SessionMiddleware` for CSRF state verification, but **Starlette is already a transitive dependency of FastAPI**, so nothing extra needs to be installed.

> **Do not add `asyncpg`** — the project uses SQLAlchemy + `psycopg2-binary`, not asyncpg.

If you ever need to rebuild the Docker image after touching `requirements.txt`, run:

```bash
docker compose build backend
```

---

## Step 2 — Environment Variables

Add these to `backend/.env` (alongside the existing Postgres and secret-key vars):

```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=https://uahapp.com/api/auth/google/callback
SESSION_SECRET=some_long_random_string_min_32_chars
```

> Note the `/api/auth/` prefix in `GOOGLE_REDIRECT_URI` — this matches the existing auth router's `prefix="/api/auth"`.

Also expose these in `app/core/config.py` so they are accessible as `settings.*`:

```python
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")
SESSION_SECRET: str = os.getenv("SESSION_SECRET", "change-me-in-production")
```

---

## Step 3 — Database Migration

The current `users` table (defined in `backend/app/models/user.py`) needs four changes before OAuth can work:

```sql
-- 1. Add google_id for stable, provider-issued user identity
ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE;

-- 2. Add avatar_url for the profile picture returned by Google
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);

-- 3. Allow hashed_password to be NULL
--    OAuth-only users have no password, but the column is currently NOT NULL.
ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;

-- 4. Allow username to be NULL
--    Google does not return a username; it must be derived or left null initially.
--    Alternatively you may keep NOT NULL and always derive a value — see Step 5.
ALTER TABLE users ALTER COLUMN username DROP NOT NULL;
```

> Run these statements against your dev DB directly (e.g., `psql`) or wrap them in an initialisation script.  
> Once applied, update `backend/app/models/user.py` to match: mark `hashed_password` and `username` as `nullable=True`, and add the two new columns.

---

## Step 4 — Session Middleware (CSRF State Check)

Open `backend/app/main.py` and add the `SessionMiddleware` import and registration **before** the routers are mounted:

```python
import os
from starlette.middleware.sessions import SessionMiddleware

# add immediately after the app = FastAPI(...) block
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "change-me"))
```

---

## Step 5 — The Two OAuth Endpoints

Add these endpoints to `backend/app/api/auth.py`, alongside the existing `/login` and `/register` routes.

The existing router already carries `prefix="/api/auth"`, so these become:
- `GET /api/auth/google` — redirect to Google
- `GET /api/auth/google/callback` — handle Google's response

```python
import os, secrets, httpx
from fastapi import Request
from fastapi.responses import RedirectResponse
from app.core.config import settings

# ── Step 1: Redirect user to Google ──────────────────────────────────────────
@router.get("/google")
async def google_login(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state  # requires SessionMiddleware

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
    )


# ── Step 2: Google redirects back here ───────────────────────────────────────
@router.get("/google/callback", response_model=TokenResponse)
async def google_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db),
):
    # Verify state to prevent CSRF
    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    async with httpx.AsyncClient() as client:
        # Exchange authorisation code for tokens
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        tokens = token_res.json()

        # Fetch user profile from Google
        profile_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        profile = profile_res.json()

    google_id  = profile["sub"]          # stable, unique Google user ID
    email      = profile["email"]
    given_name = profile.get("given_name")   # maps to first_name
    family_name = profile.get("family_name") # maps to last_name
    avatar_url = profile.get("picture")

    # Upsert the user into the DB using SQLAlchemy ORM
    user = upsert_google_user(db, google_id, email, given_name, family_name, avatar_url)

    # Reuse the existing create_access_token — no changes needed there
    token = create_access_token(data={"sub": str(user.id)})

    # Return the existing TokenResponse schema (includes the user object)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
```

---

## Step 6 — DB Upsert Helper (SQLAlchemy ORM)

The original guide used raw asyncpg SQL with `$1/$2` placeholders and `db.fetchrow()`. The project uses **SQLAlchemy ORM** — use this pattern instead and place it in `backend/app/api/auth.py` (or extract to a `backend/app/crud/user.py` helper):

```python
from sqlalchemy.orm import Session
from app.models.user import User


def upsert_google_user(
    db: Session,
    google_id: str,
    email: str,
    first_name: str | None,
    last_name: str | None,
    avatar_url: str | None,
) -> User:
    """
    Look up a user by google_id; create one if they don't exist yet.
    Also handles the case where an existing email account has no google_id
    (i.e. the user registered with a password before using Google sign-in).
    """
    # 1. Try to find by google_id first (returning user)
    user = db.query(User).filter(User.google_id == google_id).first()
    if user:
        # Update mutable fields in case they changed on Google's end
        user.avatar_url  = avatar_url
        user.first_name  = first_name
        user.last_name   = last_name
        db.commit()
        db.refresh(user)
        return user

    # 2. No google_id match — check if the email already exists (password user)
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Link the existing account to this Google identity
        user.google_id  = google_id
        user.avatar_url = avatar_url
        if not user.first_name:
            user.first_name = first_name
        if not user.last_name:
            user.last_name = last_name
        db.commit()
        db.refresh(user)
        return user

    # 3. Brand-new user — create a record
    #    username is derived from the email prefix; adjust to taste.
    #    hashed_password is None because this user authenticates via Google only.
    new_user = User(
        email=email,
        google_id=google_id,
        first_name=first_name,
        last_name=last_name,
        avatar_url=avatar_url,
        username=email.split("@")[0],  # derive a default username
        hashed_password=None,           # no password for OAuth-only users
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
```

> **Derived username collisions:** if two users share an email prefix (unlikely but possible), the `UNIQUE` constraint on `username` will raise an `IntegrityError`. Add a collision-handling strategy (e.g. append a short random suffix) before going to production.

---

## Step 7 — Update the Pydantic Schemas

`UserResponse` (in `backend/app/schemas/user.py`) does not currently include `avatar_url`.  
Add the field so it is returned in the token response:

```python
class UserResponse(BaseModel):
    id: int
    email: str
    username: str | None          # now nullable (see Step 3)
    first_name: str | None
    last_name: str | None
    avatar_url: str | None        # new field
    is_active: bool

    class Config:
        from_attributes = True
```

---

## Quick Checklist

- [ ] Add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, and `SESSION_SECRET` to `backend/.env`
- [ ] Expose those four settings in `app/core/config.py`
- [ ] Run the four `ALTER TABLE` statements from Step 3 against your dev database
- [ ] Update `backend/app/models/user.py` to reflect the schema changes (`google_id`, `avatar_url`, nullable `hashed_password` and `username`)
- [ ] Add `SessionMiddleware` to `main.py` (Step 4)
- [ ] Add the two OAuth endpoints to `backend/app/api/auth.py` (Step 5)
- [ ] Add the `upsert_google_user` helper (Step 6)
- [ ] Update `UserResponse` schema to include `avatar_url` (Step 7)
- [ ] Register `https://uahapp.com/api/auth/google/callback` as an authorised redirect URI in Google Cloud Console (note the `/api/auth/` prefix)
- [ ] Rebuild the Docker image if any dependency changes were made (`docker compose build backend`)

---

## Notes on Existing Code That Requires No Changes

- **`create_access_token`** in `app/core/security.py` — works as-is; just import and call it.
- **`get_db`** in `app/db/session.py` — use as-is via `Depends(get_db)`.
- **`TokenResponse`** schema — already handles both `access_token` and the `user` object; the Google callback can return the same shape as the password login endpoint.
- **`GET /api/auth/me`** — no changes needed; it already validates any valid JWT regardless of how it was issued.
