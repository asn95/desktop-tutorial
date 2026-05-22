from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import DbAuditLog, DbUser, DbNotificationLog
from ..security import require_manager

router = APIRouter()

@router.get("/logs")
async def get_audit_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    logs = (
        db.query(DbAuditLog, DbUser.name)
        .join(DbUser, DbAuditLog.user_id == DbUser.id)
        .order_by(DbAuditLog.created_at.desc())
        .offset(skip).limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "action": log.action,
            "detail": log.detail,
            "userName": name,
            "created_at": log.created_at.isoformat(),
        }
        for log, name in logs
    ]

@router.get("/notifications")
async def get_notification_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    logs = (
        db.query(DbNotificationLog, DbUser.name)
        .join(DbUser, DbNotificationLog.recipient_id == DbUser.id)
        .order_by(DbNotificationLog.created_at.desc())
        .offset(skip).limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "recipientName": name,
            "message": log.message,
            "success": log.success == "true",
            "created_at": log.created_at.isoformat(),
        }
        for log, name in logs
    ]
