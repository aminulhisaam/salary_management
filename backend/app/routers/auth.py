from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession, get_current_user
from app.models import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> User:
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        created_at=datetime.now(UTC),
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        ) from None

    db.refresh(user)
    return user


@router.post("/login", response_model=AccessTokenResponse)
def login(payload: LoginRequest, db: DbSession) -> AccessTokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AccessTokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
