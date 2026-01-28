from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import RateLimiter
from app.db.session import get_db
from app.schemas.auth import (
    LoginIn,
    LogoutIn,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    RefreshIn,
    RegisterIn,
    TokenPair,
    VerifyEmailIn,
)
from app.schemas.user import UserPublic
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = RateLimiter()


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)) -> UserPublic:
    ip = request.client.host if request.client else "unknown"
    limiter.hit(f"rl:register:ip:{ip}", settings.rate_limit_register, settings.rate_limit_window_seconds)
    user = auth_service.register_user(db, payload.email, payload.password)
    return user


@router.post("/verify-email")
def verify_email(payload: VerifyEmailIn, db: Session = Depends(get_db)) -> dict:
    auth_service.verify_email(db, payload.token)
    return {"message": "Email verified"}


@router.post("/login", response_model=TokenPair)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    ip = request.client.host if request.client else "unknown"
    limiter.hit(f"rl:login:ip:{ip}", settings.rate_limit_login, settings.rate_limit_window_seconds)
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    access_token, refresh_token = auth_service.create_token_pair(db, user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)) -> TokenPair:
    access_token, refresh_token = auth_service.refresh_tokens(db, payload.refresh_token)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
def logout(payload: LogoutIn, db: Session = Depends(get_db)) -> dict:
    auth_service.logout(db, payload.refresh_token)
    return {"message": "Logged out"}


@router.post("/password-reset/request")
def password_reset_request(payload: PasswordResetRequestIn, db: Session = Depends(get_db)) -> dict:
    auth_service.request_password_reset(db, payload.email)
    return {"message": "If the email exists, a reset token was sent"}


@router.post("/password-reset/confirm")
def password_reset_confirm(payload: PasswordResetConfirmIn, db: Session = Depends(get_db)) -> dict:
    auth_service.confirm_password_reset(db, payload.token, payload.new_password)
    return {"message": "Password updated"}
