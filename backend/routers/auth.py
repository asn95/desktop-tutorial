import time
import hmac
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import DbUser, DbAuditLog, UserRole
from ..security import verify_password, create_access_token, hash_password, require_manager

router = APIRouter()

# Server-side rate limiting for login.
# NOTE: in-memory only — fine for a single instance. For multi-instance prod a shared
# store (e.g. Redis) is the production-grade fix so limits are enforced cluster-wide.
_login_attempts: dict[str, list[float]] = defaultdict(list)        # keyed by client IP
_login_attempts_user: dict[str, list[float]] = defaultdict(list)   # keyed by username
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60


def _client_ip(request: Request) -> str:
    """Resolve the real client IP.

    Behind Railway's reverse proxy request.client.host is always the proxy, so per-IP
    limiting is useless. Prefer the left-most (original client) entry of X-Forwarded-For
    when present, falling back to the direct peer.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def _prune(bucket: list[float], now: float) -> list[float]:
    return [t for t in bucket if now - t < LOGIN_WINDOW_SECONDS]


def _check_rate_limit(client_ip: str, username: str):
    """Block login if either the client IP or the username exceeded the attempt limit."""
    now = time.time()
    _login_attempts[client_ip] = _prune(_login_attempts[client_ip], now)
    _login_attempts_user[username] = _prune(_login_attempts_user[username], now)
    if (
        len(_login_attempts[client_ip]) >= LOGIN_MAX_ATTEMPTS
        or len(_login_attempts_user[username]) >= LOGIN_MAX_ATTEMPTS
    ):
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak percobaan login. Coba lagi dalam {LOGIN_WINDOW_SECONDS} detik.",
        )


def _record_attempt(client_ip: str, username: str):
    now = time.time()
    _login_attempts[client_ip].append(now)
    _login_attempts_user[username].append(now)

def _role_str(role) -> str:
    return role.value if hasattr(role, "value") else role

class LoginPayload(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    id: str
    name: str
    username: str
    role: str
    token: str

@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginPayload, request: Request, db: Session = Depends(get_db)):
    client_ip = _client_ip(request)
    _check_rate_limit(client_ip, payload.username)

    user = db.query(DbUser).filter(DbUser.email == payload.username).first()
    if not user or not user.password_hash:
        _record_attempt(client_ip, payload.username)
        raise HTTPException(status_code=401, detail="Nama pengguna atau kata sandi tidak valid")
    if not verify_password(payload.password, user.password_hash):
        _record_attempt(client_ip, payload.username)
        raise HTTPException(status_code=401, detail="Nama pengguna atau kata sandi tidak valid")

    role = _role_str(user.role)
    token = create_access_token(user.id, role)
    return {
        "id": user.id,
        "name": user.name,
        "username": user.email,
        "role": role,
        "token": token,
    }

class VerifyPasswordPayload(BaseModel):
    password: str

@router.post("/verify-password")
async def verify_manager_password(payload: VerifyPasswordPayload, db: Session = Depends(get_db), auth: dict = Depends(require_manager)):
    user = db.query(DbUser).filter(DbUser.id == auth["sub"]).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Kata sandi tidak valid")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Kata sandi tidak valid")
    return {"verified": True}

class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
async def change_password(payload: ChangePasswordPayload, db: Session = Depends(get_db), auth: dict = Depends(require_manager)):
    user = db.query(DbUser).filter(DbUser.id == auth["sub"]).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Pengguna tidak ditemukan")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Kata sandi saat ini salah")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Kata sandi baru minimal 6 karakter")
    user.password_hash = hash_password(payload.new_password)
    db.add(DbAuditLog(user_id=auth["sub"], action="change_password", detail="Kata sandi diubah"))
    db.commit()
    return {"message": "Kata sandi berhasil diubah"}

class SeedPayload(BaseModel):
    token: str
    password: str

@router.post("/seed-admin")
async def seed_admin(payload: SeedPayload, db: Session = Depends(get_db)):
    """Create default admin only if no managers exist at all. Requires SEED_TOKEN env var."""
    import os
    seed_token = os.environ.get("SEED_TOKEN")
    # Constant-time comparison to avoid leaking the token via timing side-channels.
    if not seed_token or not hmac.compare_digest(payload.token, seed_token):
        raise HTTPException(status_code=403, detail="Seed token tidak valid atau belum diatur.")

    # Enforce a minimum admin password policy on seed.
    if len(payload.password) < 12:
        raise HTTPException(status_code=400, detail="Kata sandi admin minimal 12 karakter.")

    any_manager = db.query(DbUser).filter(DbUser.role == UserRole.manager).first()
    if any_manager:
        raise HTTPException(status_code=403, detail="Admin sudah ada. Seed dinonaktifkan.")

    admin = DbUser(
        name="C3MR Administrator",
        email="admin",
        password_hash=hash_password(payload.password),
        role=UserRole.manager,
    )
    db.add(admin)
    db.commit()
    return {"message": "Admin dibuat dengan nama pengguna: admin"}
