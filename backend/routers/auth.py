import time
import hmac
import secrets
from datetime import datetime, timezone
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import DbUser, DbAuditLog, DbNotificationLog, UserRole
from ..security import (
    verify_password, create_access_token, hash_password, require_manager,
    MIN_PASSWORD_LENGTH,
)

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
    if len(payload.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Kata sandi baru minimal {MIN_PASSWORD_LENGTH} karakter")
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = datetime.now(timezone.utc)  # batalkan token lama → wajib login ulang
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


# --- Lupa kata sandi lewat Telegram ---
#
# Disimpan di memori proses, tanpa tabel dan tanpa migrasi — sama seperti penghitung
# rate limit di atas. Kodenya hidup 15 menit; kehilangan seluruhnya saat kontainer
# restart hanya berarti pengguna meminta kode baru.
# ponytail: dict per-proses; pindah ke Redis kalau API pernah dijalankan >1 instance,
# karena kode yang terbit di instance A tidak akan dikenali instance B.
_reset_codes: dict[str, tuple[str, float, int]] = {}  # username -> (kode, kedaluwarsa, sisa_percobaan)
RESET_TTL_SECONDS = 900
RESET_MAX_ATTEMPTS = 5

# Jawaban yang SAMA persis dipakai baik akun ada maupun tidak. Membedakannya akan
# mengubah halaman lupa-sandi menjadi alat pencacah nama pengguna yang valid.
_RESET_SENT_MESSAGE = (
    "Jika akun tersebut terdaftar dan tertaut ke Telegram, kode verifikasi sudah dikirim ke Telegram-nya."
)


class ForgotPasswordPayload(BaseModel):
    username: str


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordPayload, request: Request, db: Session = Depends(get_db)):
    username = payload.username.strip()
    # Rate limit memakai ember yang sama dengan login: tanpa itu endpoint ini jadi
    # cara gratis membanjiri Telegram seorang manajer dengan kode yang tak ia minta.
    _check_rate_limit(_client_ip(request), username)
    _record_attempt(_client_ip(request), username)

    user = db.query(DbUser).filter(DbUser.email == username).first()
    if user and user.telegram_id and user.password_hash:
        code = f"{secrets.randbelow(1_000_000):06d}"
        _reset_codes[username] = (code, time.time() + RESET_TTL_SECONDS, RESET_MAX_ATTEMPTS)
        message = (
            f"Kode reset kata sandi C3MR Anda: {code}\n\n"
            f"Berlaku {RESET_TTL_SECONDS // 60} menit dan hanya bisa dipakai sekali.\n"
            "Abaikan pesan ini jika Anda tidak meminta reset."
        )
        from ..notifications import send_telegram_notification
        # parse_mode=None: kodenya angka polos, tidak perlu Markdown, dan Markdown
        # yang gagal diurai membuat Telegram menolak seluruh pesan.
        ok = send_telegram_notification(user.telegram_id, message, parse_mode=None)
        db.add(DbNotificationLog(recipient_id=user.id, message="Kode reset kata sandi dikirim", success="true" if ok else "false"))
        db.add(DbAuditLog(user_id=user.id, action="request_password_reset", detail="Kode reset diminta lewat halaman login"))
        db.commit()

    return {"message": _RESET_SENT_MESSAGE}


class ResetPasswordPayload(BaseModel):
    username: str
    code: str
    new_password: str


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordPayload, db: Session = Depends(get_db)):
    username = payload.username.strip()
    entry = _reset_codes.get(username)
    if not entry:
        raise HTTPException(status_code=400, detail="Kode tidak valid atau sudah kedaluwarsa")

    code, expires_at, attempts_left = entry
    if time.time() > expires_at or attempts_left <= 0:
        _reset_codes.pop(username, None)
        raise HTTPException(status_code=400, detail="Kode tidak valid atau sudah kedaluwarsa")

    if not hmac.compare_digest(code, payload.code.strip()):
        # Sisa percobaan dikurangi lebih dulu supaya menebak 6 digit dengan cara
        # mencoba berulang kali habis jatahnya jauh sebelum ruang kodenya terjelajahi.
        _reset_codes[username] = (code, expires_at, attempts_left - 1)
        raise HTTPException(status_code=400, detail="Kode tidak valid atau sudah kedaluwarsa")

    if len(payload.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Kata sandi baru minimal {MIN_PASSWORD_LENGTH} karakter")

    user = db.query(DbUser).filter(DbUser.email == username).first()
    if not user:
        _reset_codes.pop(username, None)
        raise HTTPException(status_code=400, detail="Kode tidak valid atau sudah kedaluwarsa")

    user.password_hash = hash_password(payload.new_password)
    # Membatalkan seluruh token lama (lihat security.py): kalau akunnya memang
    # sedang dibajak, sesi penyerang mati begitu pemiliknya reset.
    user.password_changed_at = datetime.now(timezone.utc)
    db.add(DbAuditLog(user_id=user.id, action="reset_password", detail="Kata sandi direset lewat kode Telegram"))
    # Sekali pakai: dibuang SEBELUM membalas, jadi kode yang sama tidak bisa
    # dipakai ulang bahkan oleh permintaan yang berjalan bersamaan.
    _reset_codes.pop(username, None)
    db.commit()
    return {"message": "Kata sandi berhasil diubah. Silakan masuk dengan kata sandi baru."}
