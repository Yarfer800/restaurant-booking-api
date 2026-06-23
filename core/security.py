import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from config import config


def hash_password(password: str) -> str:
    """Хеширует пароль (PBKDF2-HMAC-SHA256, соль сохраняется в строке)."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, hashed: str) -> bool:
    salt, _, digest = hashed.partition("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(candidate, digest)


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    role: str,
    jti: str | None = None,
) -> tuple[str, str | None]:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
    }
    if jti is not None:
        payload["jti"] = jti

    token = jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)
    return token, payload.get("jti")


def create_access_token(user_id: int, role: str) -> tuple[str, str]:
    """Access-токен с jti для blacklist."""
    jti = secrets.token_hex(8)
    token, _ = _create_token(
        str(user_id),
        "access",
        timedelta(minutes=config.access_token_expire_minutes),
        role,
        jti,
    )
    return token, jti


def create_refresh_token(user_id: int, role: str) -> tuple[str, str]:
    """Refresh-токен с jti для черенкования при logout/rotate."""
    jti = secrets.token_hex(8)
    token, _ = _create_token(
        str(user_id),
        "refresh",
        timedelta(days=config.refresh_token_expire_days),
        role,
        jti,
    )
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    """Декодирует и валидирует JWT. Бросает jwt.PyJWTError при проблемах."""
    return jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
