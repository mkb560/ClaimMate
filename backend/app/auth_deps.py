from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ai.config import ai_config
from app.auth_core import decode_access_token
from app.auth_service import get_user_by_id
from models.auth_orm import UserRow


@dataclass(frozen=True)
class AuthContext:
    """Request-scoped auth: mode mirrors AUTH_MODE; user is set when a valid Bearer token was sent."""

    mode: str
    user: UserRow | None


_bearer_scheme = HTTPBearer(auto_error=False)


def _normalize_mode() -> str:
    m = (ai_config.auth_mode or "off").strip().lower()
    if m not in ("off", "optional", "required"):
        return "off"
    return m


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> AuthContext:
    mode = _normalize_mode()
    if credentials is None or credentials.scheme.lower() != "bearer":
        return AuthContext(mode=mode, user=None)

    token = credentials.credentials.strip()
    if not token:
        return AuthContext(mode=mode, user=None)

    if not ai_config.jwt_secret_key.strip():
        raise HTTPException(status_code=503, detail="JWT_SECRET_KEY is not configured.")

    try:
        claims = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc

    sub = claims.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(status_code=401, detail="Invalid token subject.")

    try:
        uid = uuid.UUID(sub)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject.") from exc

    user = await get_user_by_id(uid)
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return AuthContext(mode=mode, user=user)
