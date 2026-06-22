"""Tests for C3MR API endpoints."""
import io
from backend.models import DbUser, DbTarget, DbComment, DbReport, UserRole, TargetStatus
from backend.security import hash_password


# ── Auth ─────────────────────────────────────────────────────────────

def test_seed_admin(client, monkeypatch):
    monkeypatch.setenv("SEED_TOKEN", "test-seed-token")
    res = client.post("/api/auth/seed-admin", json={"token": "test-seed-token", "password": "Str0ng!Pass"})
    assert res.status_code == 200
    assert "admin" in res.json()["message"].lower()

def test_seed_admin_wrong_token(client, monkeypatch):
    monkeypatch.setenv("SEED_TOKEN", "real-token")
    res = client.post("/api/auth/seed-admin", json={"token": "wrong-token", "password": "x"})
    assert res.status_code == 403


def test_login_valid(client, db):
    user = DbUser(
        name="Test Manager",
        email="test@c3mr.id",
        password_hash=hash_password("password123"),
        role=UserRole.manager,
    )
    db.add(user)
    db.commit()

    res = client.post("/api/auth/login", json={"username": "test@c3mr.id", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "test@c3mr.id"
    assert "token" in data
    assert len(data["token"]) > 10


def test_login_wrong_password(client, db):
    user = DbUser(
        name="Test", email="t@c3mr.id",
        password_hash=hash_password("correct"),
        role=UserRole.manager,
    )
    db.add(user)
    db.commit()

    res = client.post("/api/auth/login", json={"username": "t@c3mr.id", "password": "wrong"})
    assert res.status_code == 401


def test_login_nonexistent_user(client):
    res = client.post("/api/auth/login", json={"username": "nobody@c3mr.id", "password": "pass"})
    assert res.status_code == 401


def test_login_rate_limit(client):
    """Server-side rate limiting: 5 failures from same IP -> 429 Too Many Requests."""
    from backend.routers.auth import _login_attempts
    _login_attempts.clear()  # reset state between tests
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "brute@force", "password": "wrong"})
    res = client.post("/api/auth/login", json={"username": "brute@force", "password": "wrong"})
    assert res.status_code == 429
    assert "Terlalu banyak" in res.json()["detail"]


# ── Users ────────────────────────────────────────────────────────────

def test_create_and_list_users(client, auth_headers):
    res = client.post("/api/users/", json={"name": "Officer A", "role": "officer"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Officer A"

    res = client.get("/api/users/", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_create_user_duplicate_telegram(client, auth_headers):
    client.post("/api/users/", json={"name": "A", "telegram_id": "111", "role": "officer"}, headers=auth_headers)
    res = client.post("/api/users/", json={"name": "B", "telegram_id": "111", "role": "officer"}, headers=auth_headers)
    assert res.status_code == 400


def test_delete_user(client, auth_headers):
    res = client.post("/api/users/", json={"name": "Temp", "role": "officer"}, headers=auth_headers)
    uid = res.json()["id"]

    res = client.delete(f"/api/users/{uid}", headers=auth_headers)
    assert res.status_code == 200

    res = client.get("/api/users/", headers=auth_headers)
    ids = [u["id"] for u in res.json()]
    assert uid not in ids


# ── Targets ──────────────────────────────────────────────────────────

def test_upload_and_list_targets(client, db, auth_headers):
    db.add(DbTarget(customer_name="Budi", address="Jl. Test 1", phone="081111", amount_due=500000))
    db.add(DbTarget(customer_name="Siti", address="Jl. Test 2", phone="082222", amount_due=750000))
    db.commit()

    res = client.get("/api/targets/", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_targets_pagination(client, db, auth_headers):
    for i in range(5):
        db.add(DbTarget(customer_name=f"Customer {i}", address=f"Addr {i}", phone=f"08{i}", amount_due=1000 * i))
    db.commit()

    res = client.get("/api/targets/?skip=0&limit=2", headers=auth_headers)
    assert len(res.json()) == 2

    res = client.get("/api/targets/?skip=2&limit=2", headers=auth_headers)
    assert len(res.json()) == 2


def test_assign_target(client, db, auth_headers):
    officer = DbUser(name="Field Officer", role=UserRole.officer)
    db.add(officer)
    db.commit()
    db.refresh(officer)

    target = DbTarget(customer_name="Target X", address="Addr", phone="08", amount_due=100000)
    db.add(target)
    db.commit()
    db.refresh(target)

    res = client.patch(f"/api/targets/{target.id}/assign?officer_id={officer.id}", headers=auth_headers)
    assert res.status_code == 200

    res = client.get("/api/targets/?status=in_progress", headers=auth_headers)
    assert len(res.json()) == 1


# ── Dashboard ────────────────────────────────────────────────────────

def test_dashboard_snapshot(client, db, auth_headers):
    db.add(DbTarget(customer_name="A", address="X", phone="0", amount_due=100, status=TargetStatus.pending))
    db.add(DbTarget(customer_name="B", address="Y", phone="1", amount_due=200, status=TargetStatus.completed))
    db.commit()

    res = client.get("/api/dashboard/", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["stats"]["totalTargets"] == 2
    assert data["stats"]["completed"] == 1
    assert data["stats"]["pending"] == 1


def test_dashboard_recent_comments(client, db, auth_headers):
    officer = DbUser(name="Off1", role=UserRole.officer)
    db.add(officer)
    db.commit()
    db.refresh(officer)

    target = DbTarget(customer_name="Cust1", address="A", phone="0", amount_due=100, assigned_officer=officer.id)
    db.add(target)
    db.commit()
    db.refresh(target)

    comment = DbComment(target_id=target.id, officer_id=officer.id, message="Wrong address", tag="wrong_address")
    db.add(comment)
    db.commit()

    res = client.get("/api/dashboard/recent-comments?limit=5", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["officerName"] == "Off1"
    assert data[0]["customerName"] == "Cust1"


# ── Analytics ────────────────────────────────────────────────────────

def test_analytics_summary(client, db, auth_headers):
    officer = DbUser(name="Analyst", role=UserRole.officer)
    db.add(officer)
    db.commit()
    db.refresh(officer)

    db.add(DbTarget(customer_name="T1", address="A", phone="0", amount_due=1000000, status=TargetStatus.completed, assigned_officer=officer.id))
    db.add(DbTarget(customer_name="T2", address="B", phone="1", amount_due=500000, status=TargetStatus.pending))
    db.commit()

    res = client.get("/api/analytics/summary", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_targets"] == 2
    assert data["revenue"]["total_due"] == 1500000
    assert data["revenue"]["collected"] == 1000000
    assert len(data["distribution"]) == 3


# ── Target Comments ──────────────────────────────────────────────────

def test_target_comments(client, db, auth_headers):
    officer = DbUser(name="Commenter", role=UserRole.officer)
    db.add(officer)
    db.commit()
    db.refresh(officer)

    target = DbTarget(customer_name="C1", address="A", phone="0", amount_due=100)
    db.add(target)
    db.commit()
    db.refresh(target)

    db.add(DbComment(target_id=target.id, officer_id=officer.id, message="Bad address", tag="wrong_address"))
    db.add(DbComment(target_id=target.id, officer_id=officer.id, message="Phone unreachable"))
    db.commit()

    res = client.get(f"/api/targets/{target.id}/comments", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2
    assert res.json()[0]["officerName"] == "Commenter"


# ── Officer Endpoints (Telegram Mini App) ────────────────────────────

def test_officer_tasks_no_auth(client):
    res = client.get("/api/officer/tasks")
    assert res.status_code == 401


def test_officer_report_no_auth(client):
    res = client.post("/api/officer/report")
    assert res.status_code == 401


def test_officer_comment_no_auth(client):
    res = client.post("/api/officer/comment")
    assert res.status_code == 401


# ── Role-Based Access ────────────────────────────────────────────────

def test_officer_cannot_access_users(client, db):
    officer = DbUser(
        name="Field Officer",
        email="officer@c3mr.id",
        password_hash=hash_password("pass123"),
        role=UserRole.officer,
    )
    db.add(officer)
    db.commit()

    res = client.post("/api/auth/login", json={"username": "officer@c3mr.id", "password": "pass123"})
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/users/", headers=headers)
    assert res.status_code == 403


# ── Delete User FK Protection ────────────────────────────────────────

def test_delete_user_with_targets_blocked(client, db, auth_headers):
    officer = DbUser(name="Busy Officer", role=UserRole.officer)
    db.add(officer)
    db.commit()
    db.refresh(officer)

    target = DbTarget(customer_name="T1", address="A", phone="0", amount_due=100, assigned_officer=officer.id)
    db.add(target)
    db.commit()

    res = client.delete(f"/api/users/{officer.id}", headers=auth_headers)
    assert res.status_code == 409
