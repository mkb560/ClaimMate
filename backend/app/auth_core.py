from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from ai.config import ai_config

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain, password_hash)


def create_access_token(*, subject_user_id: str, expires_minutes: int | None = None) -> str:
    secret = ai_config.jwt_secret_key.strip()
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")
    now = datetime.now(UTC)
    exp_m = expires_minutes if expires_minutes is not None else ai_config.jwt_expires_minutes
    payload: dict[str, Any] = {
        "sub": subject_user_id,
        "iat": now,
        "exp": now + timedelta(minutes=exp_m),
    }
    return jwt.encode(payload, secret, algorithm=ai_config.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    secret = ai_config.jwt_secret_key.strip()
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")
    return jwt.decode(token, secret, algorithms=[ai_config.jwt_algorithm])
