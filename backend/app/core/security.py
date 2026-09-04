from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import bcrypt
import jwt

from app.core.config import settings


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plaintext password matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    subject: Union[str, int],
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed JWT access token for authentication."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
    }
    if role:
        payload["role"] = role

    encoded_jwt = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a signed JWT access token.
    
    Raises:
        jwt.PyJWTError: If token is expired or invalid.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
