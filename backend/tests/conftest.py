import pytest
import sys
import os

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend.main import app

# Use in-memory SQLite for tests
from sqlalchemy.pool import StaticPool
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def auth_headers(client, db):
    """Create a manager user and return Authorization headers with a valid JWT."""
    from backend.models import DbUser, UserRole
    from backend.security import hash_password

    user = DbUser(
        name="Test Manager",
        email="mgr@test.id",
        password_hash=hash_password("pass123"),
        role=UserRole.manager,
    )
    db.add(user)
    db.commit()

    res = client.post("/api/auth/login", json={"email": "mgr@test.id", "password": "pass123"})
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}
