"""Authentication routes: email-confirmed signup, login, refresh, and current user."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, EmailStr

from ..services.auth_service import auth_service

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ResendConfirmationRequest(BaseModel):
    email: EmailStr


@router.post("/auth/signup")
async def signup(request: SignupRequest) -> dict[str, Any]:
    try:
        return await auth_service.signup(request.email, request.password, request.name)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/auth/login")
async def login(request: LoginRequest) -> dict[str, Any]:
    try:
        return await auth_service.login(request.email, request.password)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/auth/resend-signup")
async def resend_signup(request: ResendConfirmationRequest) -> dict[str, bool]:
    try:
        await auth_service.resend_signup_confirmation(request.email)
        return {"sent": True}
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@router.post("/auth/refresh")
async def refresh(request: RefreshRequest) -> dict[str, Any]:
    try:
        return await auth_service.refresh(request.refresh_token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/auth/me")
async def me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return await auth_service.me(authorization[7:].strip())
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
