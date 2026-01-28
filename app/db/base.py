from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Alembic can detect them.
from app.db.models.user import User  # noqa: E402,F401
from app.db.models.token import (  # noqa: E402,F401
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
)
