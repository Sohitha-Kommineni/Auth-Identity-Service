from datetime import datetime, timedelta, timezone
import secrets
from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.token import EmailVerificationToken, PasswordResetToken, RefreshToken
from app.db.models.user import User
from app.services.email_service import send_password_reset_email, send_verification_email

REDIS_REFRESH_PREFIX = "refresh:"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def register_user(db: Session, email: str, password: str) -> User:
    existing = _get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        is_active=False,
        is_verified=False,
    )
    db.add(user)
    db.flush()

    token_value = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(minutes=settings.email_verification_minutes)
    verification = EmailVerificationToken(user_id=user.id, token=token_value, expires_at=expires_at)
    db.add(verification)
    db.commit()
    db.refresh(user)

    send_verification_email(user.email, token_value)
    return user


def verify_email(db: Session, token: str) -> None:
    record = db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token == token,
            EmailVerificationToken.used_at.is_(None),
        )
    )
    if not record or record.expires_at < _now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    record.used_at = _now()
    user = db.get(User, record.user_id)
    if user:
        user.is_verified = True
        user.is_active = True
    db.commit()


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = _get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_verified or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")
    return user


def _store_refresh_token(db: Session, user: User, refresh_token: str) -> None:
    payload = decode_token(refresh_token)
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    db.add(RefreshToken(user_id=user.id, token_jti=jti, expires_at=expires_at))
    db.commit()

    redis = get_redis()
    ttl = int(expires_at.timestamp() - _now().timestamp())
    redis.setex(f"{REDIS_REFRESH_PREFIX}{jti}", ttl, str(user.id))


def create_token_pair(db: Session, user: User) -> Tuple[str, str]:
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    _store_refresh_token(db, user, refresh_token)
    return access_token, refresh_token


def refresh_tokens(db: Session, refresh_token: str) -> Tuple[str, str]:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not jti or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    redis = get_redis()
    redis_key = f"{REDIS_REFRESH_PREFIX}{jti}"
    if not redis.get(redis_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    token_row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_jti == jti,
            RefreshToken.revoked_at.is_(None),
        )
    )
    if not token_row or token_row.expires_at < _now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    token_row.revoked_at = _now()
    redis.delete(redis_key)
    db.commit()

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return create_token_pair(db, user)


def logout(db: Session, refresh_token: str) -> None:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    token_row = db.scalar(select(RefreshToken).where(RefreshToken.token_jti == jti))
    if token_row and token_row.revoked_at is None:
        token_row.revoked_at = _now()
        db.commit()

    redis = get_redis()
    redis.delete(f"{REDIS_REFRESH_PREFIX}{jti}")


def request_password_reset(db: Session, email: str) -> None:
    user = _get_user_by_email(db, email)
    if not user:
        return

    token_value = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(minutes=settings.password_reset_minutes)
    reset = PasswordResetToken(user_id=user.id, token=token_value, expires_at=expires_at)
    db.add(reset)
    db.commit()
    send_password_reset_email(user.email, token_value)


def confirm_password_reset(db: Session, token: str, new_password: str) -> None:
    record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token,
            PasswordResetToken.used_at.is_(None),
        )
    )
    if not record or record.expires_at < _now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    record.used_at = _now()
    user = db.get(User, record.user_id)
    if user:
        user.password_hash = hash_password(new_password)

    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == record.user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    db.commit()

    redis = get_redis()
    tokens = db.scalars(select(RefreshToken.token_jti).where(RefreshToken.user_id == record.user_id))
    for jti in tokens:
        redis.delete(f"{REDIS_REFRESH_PREFIX}{jti}")
