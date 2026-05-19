from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import DbUser, UserRole
from ..security import verify_password, create_access_token, hash_password

router = APIRouter()

def _role_str(role) -> str:
    return role.value if hasattr(role, "value") else role

class LoginPayload(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    token: str

@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginPayload, db: Session = Depends(get_db)):
    user = db.query(DbUser).filter(DbUser.email == payload.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    role = _role_str(user.role)
    token = create_access_token(user.id, role)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": role,
        "token": token,
    }

class SeedPayload(BaseModel):
    token: str
    password: str = "password123"

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
        email="admin@c3mr.id",
        password_hash=hash_password(payload.password),
        role=UserRole.manager,
    )
    db.add(admin)
    db.commit()
    return {"message": "Admin created with email admin@c3mr.id"}
