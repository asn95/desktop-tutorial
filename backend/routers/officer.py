from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os
import uuid
import json
from urllib.parse import parse_qsl
from ..database import get_db
from ..models import DbTarget, DbUser, DbReport, DbComment, Target, TargetStatus, PaymentStatus
from ..security import validate_telegram_data

router = APIRouter()

UPLOAD_DIR = "backend/uploads"

def get_current_officer(x_telegram_auth: str = Header(None), db: Session = Depends(get_db)):
    """Dependency to extract and validate officer from Telegram header"""
    if not x_telegram_auth:
        raise HTTPException(status_code=401, detail="Missing Telegram Auth Header")
        
    # 1. Validasi Kriptografi (Anti-Spoofing)
    is_valid = validate_telegram_data(x_telegram_auth)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid Telegram Signature. Potential Spoofing Attack.")

    # 2. Ekstrak Data User setelah dipastikan valid
    parsed_data = dict(parse_qsl(x_telegram_auth))
    user_data_str = parsed_data.get("user")
    
    if not user_data_str:
        raise HTTPException(status_code=400, detail="User data not found in Telegram payload")
        
    try:
        user_data = json.loads(user_data_str)
        telegram_id = str(user_data.get("id"))
    except (json.JSONDecodeError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="Gagal membaca data pengguna Telegram")

    # 3. Cari Officer di Database
    officer = db.query(DbUser).filter(DbUser.telegram_id == telegram_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not registered in C3MR system")
        
    return officer

@router.get("/tasks", response_model=List[Target])
async def get_officer_tasks(officer: DbUser = Depends(get_current_officer), db: Session = Depends(get_db)):
    # Return targets assigned to the validated officer
    return db.query(DbTarget).filter(DbTarget.assigned_officer == officer.id).all()

@router.post("/report")
async def submit_report(
    target_id: str = Form(...),
    payment_status: str = Form(...),
    notes: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    officer: DbUser = Depends(get_current_officer),
    db: Session = Depends(get_db)
):
    target = db.query(DbTarget).filter(DbTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
        
    if target.assigned_officer != officer.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this target")

    # 2. Save Photo locally
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    contents = await photo.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")
    await photo.seek(0)

    ALLOWED_EXT = {"jpg", "jpeg", "png"}
    file_ext = (photo.filename or "").rsplit(".", 1)[-1].lower()
    if file_ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Use: {', '.join(ALLOWED_EXT)}")
    file_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)
    
    # 3. Create Report Record
    db_report = DbReport(
        target_id=target_id,
        officer_id=officer.id,
        payment_status=payment_status,
        notes=notes,
        photo_url=f"/uploads/{file_name}" # Local URL
    )
    db.add(db_report)

    # 4. Update Target Status — finalized report means collection is complete
    target.status = TargetStatus.completed
        
    db.commit()
    
    return {"message": "Report submitted successfully", "report_id": db_report.id}

@router.post("/comment")
async def submit_comment(
    target_id: str = Form(...),
    message: str = Form(...),
    tag: Optional[str] = Form(None),
    officer: DbUser = Depends(get_current_officer),
    db: Session = Depends(get_db)
):
    target = db.query(DbTarget).filter(DbTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if target.assigned_officer != officer.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this target")

    comment = DbComment(
        target_id=target_id,
        officer_id=officer.id,
        message=message,
        tag=tag
    )
    db.add(comment)
    db.commit()

    return {"message": "Comment submitted", "comment_id": comment.id}

@router.get("/comments/{target_id}")
async def get_comments(
    target_id: str,
    officer: DbUser = Depends(get_current_officer),
    db: Session = Depends(get_db)
):
    comments = (
        db.query(DbComment)
        .filter(DbComment.target_id == target_id)
        .order_by(DbComment.created_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "message": c.message,
            "tag": c.tag,
            "created_at": c.created_at.isoformat()
        }
        for c in comments
    ]
