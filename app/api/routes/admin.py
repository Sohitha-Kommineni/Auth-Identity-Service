from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.user import UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserPublic])
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[UserPublic]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.patch("/users/{user_id}/role", response_model=UserPublic)
def update_user_role(
    user_id: str,
    role: UserRole,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserPublic:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = role
    db.commit()
    db.refresh(user)
    return user
