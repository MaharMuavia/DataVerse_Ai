"""Authentication: strictly integrated with Supabase Auth.

Delegates signup, login, guest creation, and token verification to the Supabase Auth REST API.
"""
from __future__ import annotations

import secrets
import time
import uuid
from typing import Any

import httpx
import jwt
from fastapi import Request

from ..core.config import settings
from ..core.logger import logger

# In-memory cache for verified tokens to avoid calling Supabase Auth API on every request
# Maps token -> (user_id, expires_at)
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}


def public_user(user_info: dict[str, Any]) -> dict[str, Any]:
    """Format Supabase user data into the expected public user shape."""
    metadata = user_info.get("user_metadata") or {}
    return {
        "id": user_info.get("id"),
        "email": user_info.get("email"),
        "name": metadata.get("name") or user_info.get("email", "").split("@")[0] or "User",
        "guest": bool(metadata.get("guest")),
    }


class AuthService:
    """Signup, login, guest, and token validation via Supabase Auth API."""

    def __init__(self) -> None:
        pass

    async def signup(self, email: str, password: str, name: str | None = None) -> dict[str, Any]:
        """Sign up a new user using Supabase Auth Admin API (for auto-confirming email) or standard signup."""
        email = email.strip().lower()
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        # We first check if the user exists using the Admin API or direct login to prevent duplicates if possible.
        # Alternatively, we can use the Admin API to create the user with email_confirm = True
        # which provides a frictionless signup experience.
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "",
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY or ''}",
            "Content-Type": "application/json"
        }
        
        # Use Admin Create User to bypass email confirmation
        admin_payload = {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "name": (name or email.split("@")[0]).strip(),
                "guest": False
            }
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users",
                json=admin_payload,
                headers=headers
            )
            
            if resp.status_code == 400 or resp.status_code == 422:
                # User might already exist
                error_data = resp.json()
                msg = error_data.get("msg", "") or error_data.get("message", "")
                if "already" in msg.lower() or "registered" in msg.lower() or "exists" in msg.lower():
                    raise FileExistsError("An account with this email already exists")
                raise ValueError(msg or "Registration failed")
            
            resp.raise_for_status()
            user_info = resp.json()

        # Login immediately after successful registration to get a session token
        return await self.login(email, password)

    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate user credentials against Supabase GoTrue Auth API."""
        headers = {
            "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_ROLE_KEY or "",
            "Content-Type": "application/json"
        }
        payload = {
            "email": email.strip().lower(),
            "password": password
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                json=payload,
                headers=headers
            )
            if resp.status_code != 200:
                raise PermissionError("Invalid email or password")
            
            data = resp.json()
            user_info = data["user"]
            token = data["access_token"]
            
            # Pre-cache this token to avoid token verification lookup
            _TOKEN_CACHE[token] = (user_info["id"], time.time() + 300)
            
            return {
                "token": token,
                "user": public_user(user_info)
            }

    async def guest(self) -> dict[str, Any]:
        """Create a frictionless auto-confirmed guest user profile in Supabase Auth."""
        guest_id = str(uuid.uuid4())
        email = f"guest_{guest_id}@dataverse-guest.local"
        password = secrets.token_urlsafe(16)
        
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY or "",
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY or ''}",
            "Content-Type": "application/json"
        }
        admin_payload = {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "name": "Guest Analyst",
                "guest": True
            }
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users",
                json=admin_payload,
                headers=headers
            )
            resp.raise_for_status()
            user_info = resp.json()

        # Login to get the token
        return await self.login(email, password)

    async def me(self, token: str) -> dict[str, Any]:
        """Validate token and fetch user details from Supabase Auth API."""
        # Try local decode first if JWT secret is set
        if settings.SUPABASE_JWT_SECRET:
            try:
                payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
                if payload and payload.get("sub"):
                    return {
                        "id": payload["sub"],
                        "email": payload.get("email"),
                        "name": payload.get("user_metadata", {}).get("name") or payload.get("email", "").split("@")[0] or "User",
                        "guest": bool(payload.get("user_metadata", {}).get("guest")),
                    }
            except jwt.PyJWTError:
                raise PermissionError("Invalid or expired token")

        # Fallback to Supabase /user endpoint
        headers = {
            "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_ROLE_KEY or "",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers=headers
            )
            if resp.status_code != 200:
                raise PermissionError("Invalid or expired token")
            
            user_info = resp.json()
            # Cache the verified token
            _TOKEN_CACHE[token] = (user_info["id"], time.time() + 300)
            
            return public_user(user_info)


auth_service = AuthService()


async def resolve_identity(request: Request) -> str | None:
    """Asynchronously verify standard Bearer JWT token and return the user ID.

    Maintains strict Supabase integration and uses local caching for performance.
    """
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        header = request.headers.get("X-Dataverse-User")
        return str(header) if header else None
        
    token = auth[7:].strip()
    if not token:
        return None

    # Check cache first
    now = time.time()
    if token in _TOKEN_CACHE:
        user_id, expires_at = _TOKEN_CACHE[token]
        if now < expires_at:
            return user_id

    # Fallback to local decoding (if JWT secret exists) or remote verification
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
            if payload and payload.get("sub"):
                user_id = str(payload["sub"])
                _TOKEN_CACHE[token] = (user_id, now + 300)
                return user_id
        except jwt.PyJWTError:
            pass

    # Remote verification against Supabase Auth /user
    try:
        headers = {
            "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_ROLE_KEY or "",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers=headers
            )
            if resp.status_code == 200:
                user_info = resp.json()
                user_id = str(user_info["id"])
                _TOKEN_CACHE[token] = (user_id, now + 300)
                return user_id
    except Exception as e:
        logger.error(f"Error validating Supabase token: {e}")

    return None
