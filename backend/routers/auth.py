import time
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import DbUser, UserRole
from ..security import verify_password, create_access_token, hash_password

router = APIRouter()

# Server-side rate limiting for login
_login_attempts: dict[str, list[float]] = defaultdict(list)
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60


def _check_rate_limit(client_ip: str):
    """Block login if client_ip exceeded LOGIN_MAX_ATTEMPTS within the window."""
    now = time.time()
    # Prune old entries
    _login_attempts[client_ip] = [
        t for t in _login_attempts[client_ip]
        if now - t < LOGIN_WINDOW_SECONDS
    ]
    if len(_login_attempts[client_ip]) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Try again in {LOGIN_WINDOW_SECONDS} seconds.",
        )


def _record_attempt(client_ip: str):
    _login_attempts[client_ip].append(time.time())

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
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = db.query(DbUser).filter(DbUser.email == payload.username).first()
    if not user or not user.password_hash:
        _record_attempt(client_ip)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not verify_password(payload.password, user.password_hash):
        _record_attempt(client_ip)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    role = _role_str(user.role)
    token = create_access_token(user.id, role)
    return {
        "id": user.id,
        "name": user.name,
        "username": user.email,
        "role": role,
        "token": token,
    }

class SeedPayload(BaseModel):
    token: str
    password: str

@router.post("/seed-admin")
async def seed_admin(payload: SeedPayload, db: Session = Depends(get_db)):
    """Create default admin only if no managers exist at all. Requires SEED_TOKEN env var."""
    import os
    seed_token = os.environ.get("SEED_TOKEN")
    if not seed_token or payload.token != seed_token:
        raise HTTPException(status_code=403, detail="Invalid or missing seed token.")

    any_manager = db.query(DbUser).filter(DbUser.role == UserRole.manager).first()
    if any_manager:
        raise HTTPException(status_code=403, detail="Admin already exists. Seed disabled.")

    admin = DbUser(
        name="C3MR Administrator",
        email="admin",
        password_hash=hash_password(payload.password),
        role=UserRole.manager,
    )
    db.add(admin)
    db.commit()
    return {"message": "Admin created with username: admin"}
