"""
Password hashing and JWT issuance/verification for CryptCare (Phase 1 & 5).
"""

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

import jwt as _pyjwt
from jwt.exceptions import InvalidTokenError as JWTError  # noqa: F401 — re-exported for callers
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def _create_token(subject: str, role: str, permissions: list[str], expires_delta: timedelta, token_type: str, purpose: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "permissions": permissions,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if purpose:
        payload["purpose"] = purpose
    if token_type in ("preauth", "refresh"):
        payload["jti"] = str(uuid.uuid4())
    return _pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str, permissions: list[str]) -> str:
    return _create_token(
        subject=user_id,
        role=role,
        permissions=permissions,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(user_id: str, role: str, permissions: list[str]) -> str:
    return _create_token(
        subject=user_id,
        role=role,
        permissions=permissions,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def create_preauth_token(user_id: str, role: str, permissions: list[str], purpose: str) -> str:
    return _create_token(
        subject=user_id,
        role=role,
        permissions=permissions,
        expires_delta=timedelta(minutes=5),
        token_type="preauth",
        purpose=purpose,
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode + verify a JWT. Raises JWTError (caught by caller) on:
    - invalid signature
    - expired token
    - malformed token
    """
    return _pyjwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat", "type"]},
    )


class TokenError(Exception):
    pass


def verify_access_token(token: str) -> dict[str, Any]:
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise TokenError(str(exc)) from exc

    if payload.get("type") != "access":
        raise TokenError("Wrong token type — expected access token")
    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise TokenError(str(exc)) from exc

    if payload.get("type") != "refresh":
        raise TokenError("Wrong token type — expected refresh token")
    return payload


def verify_preauth_token(token: str, expected_purpose: str) -> dict[str, Any]:
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise TokenError(str(exc)) from exc

    if payload.get("type") != "preauth":
        raise TokenError("Wrong token type — expected preauth token")
    if not payload.get("jti"):
        raise TokenError("Missing jti in preauth token")
    if payload.get("purpose") != expected_purpose:
        raise TokenError(f"Wrong preauth purpose — expected {expected_purpose}")
    return payload
