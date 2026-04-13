from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ai.config import ai_config
from app.auth_deps import AuthContext, get_auth_context
from app.auth_service import authenticate_user, issue_token_for_user, register_user, user_to_public
from app.deps import ensure_db_ready
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(tags=["auth"])


class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=128)


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def _require_jwt_config() -> None:
    if not ai_config.jwt_secret_key.strip():
        raise HTTPException(status_code=503, detail="JWT_SECRET_KEY is not configured; auth endpoints are disabled.")


@router.post("/auth/register")
async def register(request: Request, body: RegisterBody) -> dict[str, object]:
    ensure_db_ready(request)
    _require_jwt_config()
    try:
        user = await register_user(
            email=str(body.email),
            password=body.password,
            display_name=body.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    token = issue_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": user_to_public(user)}


@router.post("/auth/login")
async def login(request: Request, body: LoginBody) -> dict[str, object]:
    ensure_db_ready(request)
    _require_jwt_config()
    user = await authenticate_user(email=str(body.email), password=body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = issue_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": user_to_public(user)}


@router.get("/auth/me")
async def me(request: Request, ctx: AuthContext = Depends(get_auth_context)) -> dict[str, object]:
    ensure_db_ready(request)
    _require_jwt_config()
    if ctx.user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user_to_public(ctx.user)
