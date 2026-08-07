from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from ..database import get_db
from ..models import DbUser, DbTarget, DbReport, DbComment, DbAuditLog, User, UserBase, UserRole
from ..lib.format import normalize_phone
from ..security import require_manager, require_admin, hash_password, MIN_PASSWORD_LENGTH

router = APIRouter()


def _role_str(role) -> str:
    return role.value if hasattr(role, "value") else role


def _assert_not_last_admin(db: Session, user: DbUser):
    """Tolak aksi yang menghapus admin terakhir dari sistem.

    Tanpa penjaga ini satu klik bisa membuat organisasi kehilangan seluruh akses
    ke Manajemen Pengguna — dan karena pembuatan akun sendiri butuh peran admin,
    tidak ada jalan kembali dari dalam aplikasi; pemulihannya harus lewat SQL
    langsung ke basis data produksi.
    """
    if _role_str(user.role) != "admin":
        return
    others = (
        db.query(DbUser)
        .filter(DbUser.role == UserRole.admin, DbUser.id != user.id)
        .count()
    )
    if others == 0:
        raise HTTPException(status_code=409, detail="Ini admin terakhir. Angkat admin lain lebih dulu.")


def _assert_phone_free(db: Session, phone: str, exclude_id: Optional[str] = None):
    """Keunikan nomor dijaga di sini, bukan lewat batasan kolom.

    SQLite tidak bisa menambahkan kolom unik lewat ALTER TABLE, jadi menaruh UNIQUE
    hanya di PostgreSQL akan membuat dev dan produksi berperilaku berbeda tepat pada
    jalur yang paling sensitif: pencocokan nomor saat petugas menautkan Telegram.
    Dua akun bernomor sama membuat penautan itu ambigu.
    """
    q = db.query(DbUser).filter(DbUser.phone == phone)
    if exclude_id:
        q = q.filter(DbUser.id != exclude_id)
    if q.first():
        raise HTTPException(status_code=400, detail="Nomor telepon sudah terdaftar untuk pengguna lain")


class UserCreate(UserBase):
    """Pembuatan akun. Untuk peran portal (admin/manajer) email dan kata sandi wajib —
    tanpa keduanya akun terbuat tapi tidak bisa dipakai login, dan sebelum ini memang
    TIDAK ADA cara membuat akun portal kedua sama sekali: POST /users/ tidak pernah
    menyetel kata sandi, dan /seed-admin menolak berjalan begitu satu manajer ada."""
    email: Optional[str] = None
    password: Optional[str] = None


@router.get("/", response_model=List[User])
async def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    # Sengaja require_manager, bukan require_admin: dropdown penugasan di
    # TargetsTable/DashboardPage/TargetsPage mengambil daftar petugas dari sini.
    # Dijadikan admin-only berarti manajer tidak bisa menugaskan target lagi.
    return db.query(DbUser).order_by(DbUser.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=User)
async def create_user(user: UserCreate, db: Session = Depends(get_db), _auth: dict = Depends(require_admin)):
    if user.telegram_id:
        existing = db.query(DbUser).filter(DbUser.telegram_id == user.telegram_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Telegram ID already registered")

    phone = normalize_phone(user.phone)
    if phone:
        _assert_phone_free(db, phone)

    role = _role_str(user.role)
    email = (user.email or "").strip() or None
    password = user.password or ""

    if role in ("admin", "manager"):
        if not email or not password:
            raise HTTPException(status_code=400, detail="Akun admin/manajer wajib punya nama pengguna dan kata sandi")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise HTTPException(status_code=400, detail=f"Kata sandi minimal {MIN_PASSWORD_LENGTH} karakter")
        if db.query(DbUser).filter(DbUser.email == email).first():
            raise HTTPException(status_code=400, detail="Nama pengguna sudah dipakai")
    elif password:
        # Petugas bekerja lewat Mini App Telegram yang diautentikasi HMAC initData;
        # memberi mereka kata sandi portal hanya memperluas permukaan serangan.
        raise HTTPException(status_code=400, detail="Petugas tidak memakai kata sandi; aksesnya lewat Telegram")

    db_user = DbUser(
        name=user.name,
        telegram_id=user.telegram_id,
        phone=phone,
        email=email if role in ("admin", "manager") else None,
        password_hash=hash_password(password) if role in ("admin", "manager") else None,
        role=user.role,
    )
    db.add(db_user)
    db.add(DbAuditLog(user_id=_auth["sub"], action="create_user", detail=f"Membuat pengguna '{user.name}' ({role})"))
    db.commit()
    db.refresh(db_user)
    return db_user


class UserUpdate(BaseModel):
    name: Optional[str] = None
    telegram_id: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    active: Optional[bool] = None


@router.patch("/{user_id}", response_model=User)
async def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db), _auth: dict = Depends(require_admin)):
    db_user = db.query(DbUser).filter(DbUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.telegram_id is not None:
        existing = db.query(DbUser).filter(DbUser.telegram_id == payload.telegram_id, DbUser.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Telegram ID already registered to another user")
        db_user.telegram_id = payload.telegram_id
    if payload.phone is not None:
        phone = normalize_phone(payload.phone)
        if phone:
            _assert_phone_free(db, phone, exclude_id=user_id)
        db_user.phone = phone
    if payload.role is not None and _role_str(payload.role) != _role_str(db_user.role):
        new_role = _role_str(payload.role)
        # Menurunkan admin terakhir mengunci semua orang keluar dari Manajemen Pengguna.
        _assert_not_last_admin(db, db_user)
        if new_role in ("admin", "manager") and not db_user.password_hash:
            raise HTTPException(
                status_code=400,
                detail="Pengguna ini belum punya kredensial portal. Buat akun baru dengan peran tersebut.",
            )
        db.add(DbAuditLog(
            user_id=_auth["sub"], action="change_role",
            detail=f"Peran '{db_user.name}': {_role_str(db_user.role)} → {new_role}",
        ))
        db_user.role = payload.role
    if payload.name is not None:
        db_user.name = payload.name
    if payload.active is not None:
        if not payload.active:
            _assert_not_last_admin(db, db_user)
        db_user.active = payload.active
        action = "activate user" if payload.active else "deactivate user"
        db.add(DbAuditLog(user_id=_auth["sub"], action=action, detail=f"{action.title()} '{db_user.name}'"))
    else:
        db.add(DbAuditLog(user_id=_auth["sub"], action="edit_user", detail=f"Edited user '{db_user.name}'"))
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db), _auth: dict = Depends(require_admin)):
    db_user = db.query(DbUser).filter(DbUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    _assert_not_last_admin(db, db_user)

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
