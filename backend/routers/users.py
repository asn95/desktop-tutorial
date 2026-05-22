from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from ..database import get_db
from ..models import DbUser, DbTarget, DbReport, DbComment, DbAuditLog, User, UserBase, UserRole
from ..security import require_manager

router = APIRouter()

@router.get("/", response_model=List[User])
async def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    return db.query(DbUser).order_by(DbUser.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/", response_model=User)
async def create_user(user: UserBase, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    # Check if telegram_id already exists if provided
    if user.telegram_id:
        existing = db.query(DbUser).filter(DbUser.telegram_id == user.telegram_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Telegram ID already registered")
    
    db_user = DbUser(
        name=user.name,
        telegram_id=user.telegram_id,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

class UserUpdate(BaseModel):
    name: Optional[str] = None
    telegram_id: Optional[str] = None

@router.patch("/{user_id}", response_model=User)
async def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    db_user = db.query(DbUser).filter(DbUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.telegram_id is not None:
        existing = db.query(DbUser).filter(DbUser.telegram_id == payload.telegram_id, DbUser.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Telegram ID already registered to another user")
        db_user.telegram_id = payload.telegram_id
    if payload.name is not None:
        db_user.name = payload.name
    db.add(DbAuditLog(user_id=_auth["sub"], action="edit_user", detail=f"Edited user '{db_user.name}'"))
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    db_user = db.query(DbUser).filter(DbUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for FK dependencies before deleting
    has_targets = db.query(DbTarget).filter(DbTarget.assigned_officer == user_id).first()
    has_reports = db.query(DbReport).filter(DbReport.officer_id == user_id).first()
    has_comments = db.query(DbComment).filter(DbComment.officer_id == user_id).first()
    if has_targets or has_reports or has_comments:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete user with assigned targets, reports, or comments. Reassign them first."
        )

    user_name = db_user.name
    db.delete(db_user)
    db.add(DbAuditLog(user_id=_auth["sub"], action="delete_user", detail=f"Removed user '{user_name}'"))
    db.commit()
    return {"message": "User successfully removed"}
