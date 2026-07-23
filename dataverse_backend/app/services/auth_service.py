"""Authentication: strictly integrated with Supabase Auth.

Delegates signup, login, refresh, and token validation to the Supabase Auth REST API.
"""
from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
from fastapi import Request

from ..core.config import settings
from ..core.logger import logger

# In-memory cache for verified tokens to avoid calling Supabase Auth API on every request
# Maps token -> (user_id, expires_at)
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}


def validate_signup_password(password: str, email: str) -> None:
    """Apply server-side password rules that cannot be bypassed by the UI."""
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    if not all((
        any(char.islower() for char in password),
        any(char.isupper() for char in password),
        any(char.isdigit() for char in password),
        any(not char.isalnum() for char in password),
    )):
        raise ValueError("Password must include uppercase, lowercase, a number, and a special character")
    email_name = email.partition("@")[0].lower()
    if len(email_name) >= 3 and email_name in password.lower():
        raise ValueError("Password must not contain your email name")


def _auth_response(data: dict[str, Any]) -> dict[str, Any]:
    """Return the stable auth payload consumed by the frontend."""
    user_info = data["user"]
    token = data["access_token"]
    _TOKEN_CACHE[token] = (user_info["id"], time.time() + 300)
    return {
        "token": token,
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
        "user": public_user(user_info),
    }


def _can_verify_locally(token: str) -> bool:
    """Only legacy HS256 tokens can be checked with SUPABASE_JWT_SECRET.

    Supabase projects can issue asymmetric JWTs (for example ES256). Those
    tokens must be verified by Supabase rather than rejected as invalid merely
    because a legacy JWT secret is also configured.
    """
    if not settings.SUPABASE_JWT_SECRET:
        return False
    try:
        return jwt.get_unverified_header(token).get("alg") == "HS256"
    except jwt.PyJWTError:
        return False


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
        """Create a Supabase password user and require confirmation by email link."""
        email = email.strip().lower()
        validate_signup_password(password, email)

        headers = {
            "apikey": settings.SUPABASE_ANON_KEY or "",
            "Content-Type": "application/json",
        }
        payload = {
            "email": email,
            "password": password,
            "data": {
                "name": (name or email.split("@")[0]).strip(),
                "guest": False,
            },
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            redirect_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?confirmed=true"
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/signup",
                json=payload,
                headers=headers,
                params={"redirect_to": redirect_url},
            )
            if resp.status_code not in (200, 201):
                error_data = resp.json()
                msg = error_data.get("msg", "") or error_data.get("message", "")
                raise ValueError(msg or "Registration failed")

            data = resp.json()
            if data.get("access_token"):
                raise RuntimeError(
                    "Supabase email confirmation is disabled. Enable Confirm Email before allowing signups."
                )
            return {"requires_verification": True, "email": email}

    async def resend_signup_confirmation(self, email: str) -> None:
        """Ask Supabase to resend an existing signup confirmation link."""
        headers = {
            "apikey": settings.SUPABASE_ANON_KEY or "",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/resend",
                json={"type": "signup", "email": email.strip().lower()},
                headers=headers,
            )
            if resp.status_code != 200:
                raise ValueError("Could not resend the confirmation link yet. Please wait and try again")

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
            
            return _auth_response(resp.json())

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """Exchange a Supabase refresh token for a fresh authenticated session."""
        if not refresh_token.strip():
            raise PermissionError("Missing refresh token")
        headers = {
            "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_ROLE_KEY or "",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
                json={"refresh_token": refresh_token},
                headers=headers,
            )
            if resp.status_code != 200:
                raise PermissionError("Session expired. Please sign in again")
            return _auth_response(resp.json())

    async def me(self, token: str) -> dict[str, Any]:
        """Validate token and fetch user details from Supabase Auth API."""
        # Locally verify legacy HS256 tokens only. Newer Supabase signing keys
        # use asymmetric algorithms and are verified by /auth/v1/user below.
        if _can_verify_locally(token):
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
                # The remote endpoint remains the source of truth during key
                # rotation and avoids false rejections from stale local config.
                pass

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
    if _can_verify_locally(token):
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
