"""Authentication: salted PBKDF2 password hashing + JWT identity tokens.

Users are stored through the same persistence layer as sessions (local
filesystem or Supabase), so test isolation and deployments behave identically.
The JWT `sub` is a server-generated user id — the verified identity used for
session-ownership checks.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Request

from ..core.config import settings

_PBKDF2_ITERATIONS = 240_000


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS
    )
    return f"pbkdf2${_PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _scheme, iterations, salt, expected = stored.split("$", 3)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def create_token(user_id: str, email: str | None = None) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    """The user shape exposed by the API — never includes the password hash."""
    return {
        "id": row.get("id"),
        "email": row.get("email"),
        "name": row.get("name"),
        "guest": bool(row.get("guest")),
    }


class AuthService:
    """Signup / login / guest identities on top of the shared persistence."""

    def _store(self):
        # Late import so tests that monkeypatch session_service.local isolate
        # user rows exactly like session rows.
        from .session_service import session_service

        return session_service

    async def find_by_email(self, email: str) -> dict[str, Any] | None:
        store = self._store()
        rows = await store._all_rows("users")
        target = email.strip().lower()
        for row in rows:
            if str(row.get("email") or "").lower() == target:
                return row
        return None

    async def signup(self, email: str, password: str, name: str | None = None) -> dict[str, Any]:
        email = email.strip().lower()
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        if await self.find_by_email(email):
            raise FileExistsError("An account with this email already exists")
        store = self._store()
        row = await store._insert("users", {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": (name or email.split("@")[0]).strip(),
            "password_hash": hash_password(password),
            "guest": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"token": create_token(row["id"], email), "user": public_user(row)}

    async def login(self, email: str, password: str) -> dict[str, Any]:
        row = await self.find_by_email(email)
        if not row or not verify_password(password, str(row.get("password_hash") or "")):
            raise PermissionError("Invalid email or password")
        return {"token": create_token(row["id"], row.get("email")), "user": public_user(row)}

    async def guest(self) -> dict[str, Any]:
        store = self._store()
        row = await store._insert("users", {
            "id": str(uuid.uuid4()),
            "email": None,
            "name": "Guest Analyst",
            "password_hash": None,
            "guest": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"token": create_token(row["id"]), "user": public_user(row)}

    async def me(self, token: str) -> dict[str, Any]:
        payload = decode_token(token)
        if not payload or not payload.get("sub"):
            raise PermissionError("Invalid or expired token")
        store = self._store()
        row = await store._get_by_id("users", str(payload["sub"]))
        if not row:
            raise PermissionError("Unknown user")
        return public_user(row)


auth_service = AuthService()


def resolve_identity(request: Request) -> str | None:
    """The caller's identity: a verified JWT subject, else the legacy header.

    A verified Bearer token always wins. The plain X-Dataverse-User header is
    kept for anonymous/legacy clients; it can only ever match sessions created
    with that same client-generated id.
    """
    auth = request.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        payload = decode_token(auth[7:].strip())
        if payload and payload.get("sub"):
            return str(payload["sub"])
        return None  # an invalid token never falls back to the spoofable header
    header = request.headers.get("X-Dataverse-User")
    return str(header) if header else None
