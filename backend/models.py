from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text, Integer
import uuid
from datetime import datetime, timezone
from .database import Base, SQLALCHEMY_DATABASE_URL
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional, Any
from enum import Enum

_is_pg = SQLALCHEMY_DATABASE_URL.startswith("postgresql")

# --- SQLAlchemy Models ---

class UserRole(str, Enum):
    manager = "manager"
    officer = "officer"

class TargetStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class PaymentStatus(str, Enum):
    promise_to_pay = "Promise to Pay"
    paid = "Paid"
    refused = "Refused"
    not_home = "Not Home"
    partial_payment = "Partial Payment"

def _enum_col(enum_cls, pg_name, **kwargs):
    if _is_pg:
        return Column(SQLEnum(enum_cls, name=pg_name, create_type=False), **kwargs)
    return Column(SQLEnum(enum_cls), **kwargs)

class DbUser(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    telegram_id = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    role = _enum_col(UserRole, "user_role", default=UserRole.officer)
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DbTarget(Base):
    __tablename__ = "targets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    amount_due = Column(Float, nullable=False)
    assigned_officer = Column(String, ForeignKey("users.id"), nullable=True)
    status = _enum_col(TargetStatus, "target_status", default=TargetStatus.pending)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DbReport(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    target_id = Column(String, ForeignKey("targets.id"), nullable=False)
    officer_id = Column(String, ForeignKey("users.id"), nullable=False)
    payment_status = _enum_col(PaymentStatus, "payment_status_enum", nullable=False)
    notes = Column(Text, nullable=True)
    photo_url = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DbAuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)  # e.g. "assign", "edit_user", "delete_user", "upload", "change_password"
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DbNotificationLog(Base):
    __tablename__ = "notification_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = Column(String, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    success = Column(String, default="true")  # "true" or "false"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DbComment(Base):
    __tablename__ = "comments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    target_id = Column(String, ForeignKey("targets.id"), nullable=False)
    officer_id = Column(String, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    tag = Column(String, nullable=True)  # e.g. "wrong_address", "not_found"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# --- Pydantic Schemas ---

class UserBase(BaseModel):
    name: str
    telegram_id: Optional[str] = None
    role: UserRole = UserRole.officer

class User(UserBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_validator('id', mode='before')
    @classmethod
    def coerce_id(cls, v: Any) -> str:
        return str(v)

class TargetBase(BaseModel):
    customerName: str = Field(..., alias="customer_name", validation_alias="customer_name", serialization_alias="customerName")
    address: str
    phone: str
    amountDue: float = Field(..., alias="amount_due", validation_alias="amount_due", serialization_alias="amountDue")
    assignedOfficer: Optional[str] = Field(None, alias="assigned_officer", validation_alias="assigned_officer", serialization_alias="assignedOfficer")
    status: TargetStatus = TargetStatus.pending

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @field_validator('assignedOfficer', mode='before')
    @classmethod
    def coerce_officer(cls, v: Any) -> Optional[str]:
        return str(v) if v is not None else None

class Target(TargetBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @field_validator('id', mode='before')
    @classmethod
    def coerce_id(cls, v: Any) -> str:
        return str(v)

class DashboardStats(BaseModel):
    totalTargets: int
    completed: int
    inProgress: int
    pending: int

class TargetCreate(TargetBase):
    pass
