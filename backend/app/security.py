from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_context.verify(password, hashed_password)


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    expires_at = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_expiry_minutes)
    )
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
