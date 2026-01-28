from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.db.models.user import UserRole


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    is_verified: bool
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    email: EmailStr | None = None
