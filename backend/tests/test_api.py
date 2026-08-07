"""Tests for C3MR API endpoints."""
import io
import time
import pytest
from backend.models import DbUser, DbTarget, DbComment, DbReport, UserRole, TargetStatus
from backend.security import hash_password


# ── Auth ─────────────────────────────────────────────────────────────

def test_seed_admin(client, monkeypatch):
    monkeypatch.setenv("SEED_TOKEN", "test-seed-token")
    res = client.post("/api/auth/seed-admin", json={"token": "test-seed-token", "password": "Str0ng!Passw0rd"})
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

def test_create_and_list_users(client, admin_headers):
    res = client.post("/api/users/", json={"name": "Officer A", "role": "officer"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Officer A"

    res = client.get("/api/users/", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_manager_can_still_list_users(client, auth_headers, admin_headers):
    """GET /users/ WAJIB tetap terbuka untuk manajer.

    Dropdown penugasan di TargetsTable, DashboardPage dan TargetsPage mengambil
    daftar petugas dari endpoint ini. Kalau ikut dijadikan admin-only, manajer
    kehilangan kemampuan menugaskan target sama sekali — dan gejalanya cuma
    dropdown kosong, bukan pesan galat.
    """
    client.post("/api/users/", json={"name": "Officer A", "role": "officer"}, headers=admin_headers)
    res = client.get("/api/users/", headers=auth_headers)
    assert res.status_code == 200
    assert any(u["name"] == "Officer A" for u in res.json())


def test_manager_cannot_manage_users(client, auth_headers):
    """Pemisahan portal: manajer tidak boleh membuat, mengubah, atau menghapus akun."""
    assert client.post("/api/users/", json={"name": "X", "role": "officer"}, headers=auth_headers).status_code == 403
    assert client.patch("/api/users/whatever", json={"name": "Y"}, headers=auth_headers).status_code == 403
    assert client.delete("/api/users/whatever", headers=auth_headers).status_code == 403


def test_create_manager_account_sets_password(client, admin_headers):
    """Admin bisa membuat akun portal kedua — sebelumnya tidak ada jalan sama sekali:
    POST /users/ tidak pernah menyetel kata sandi dan /seed-admin menolak berjalan
    begitu satu manajer sudah ada."""
    res = client.post("/api/users/", json={
        "name": "Manajer Baru", "role": "manager",
        "email": "mgr2@test.id", "password": "rahasia123",
    }, headers=admin_headers)
    assert res.status_code == 200

    login = client.post("/api/auth/login", json={"username": "mgr2@test.id", "password": "rahasia123"})
    assert login.status_code == 200
    assert login.json()["role"] == "manager"


def test_create_manager_without_password_rejected(client, admin_headers):
    res = client.post("/api/users/", json={"name": "Tanpa Sandi", "role": "manager"}, headers=admin_headers)
    assert res.status_code == 400


def test_last_admin_cannot_be_removed(client, db, admin_headers):
    """Menghapus admin terakhir mengunci semua orang keluar dari Manajemen Pengguna,
    dan karena membuat akun butuh peran admin, tidak ada jalan kembali dari aplikasi."""
    from backend.models import DbUser, UserRole
    admin = db.query(DbUser).filter(DbUser.role == UserRole.admin).first()

    assert client.delete(f"/api/users/{admin.id}", headers=admin_headers).status_code == 409
    assert client.patch(f"/api/users/{admin.id}", json={"role": "manager"}, headers=admin_headers).status_code == 409
    assert client.patch(f"/api/users/{admin.id}", json={"active": False}, headers=admin_headers).status_code == 409


def test_create_user_duplicate_telegram(client, admin_headers):
    client.post("/api/users/", json={"name": "A", "telegram_id": "111", "role": "officer"}, headers=admin_headers)
    res = client.post("/api/users/", json={"name": "B", "telegram_id": "111", "role": "officer"}, headers=admin_headers)
    assert res.status_code == 400


def test_create_user_duplicate_phone(client, admin_headers):
    """Nomor dibandingkan setelah dinormalisasi — tanda hubung tidak boleh jadi
    celah membuat dua akun bernomor sama, karena penautan Telegram lewat nomor
    jadi ambigu."""
    client.post("/api/users/", json={"name": "A", "phone": "081234567890", "role": "officer"}, headers=admin_headers)
    res = client.post("/api/users/", json={"name": "B", "phone": "+62 812-3456-7890", "role": "officer"}, headers=admin_headers)
    assert res.status_code == 400


def test_delete_user(client, admin_headers):
    res = client.post("/api/users/", json={"name": "Temp", "role": "officer"}, headers=admin_headers)
    uid = res.json()["id"]

    res = client.delete(f"/api/users/{uid}", headers=admin_headers)
    assert res.status_code == 200

    res = client.get("/api/users/", headers=admin_headers)
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

def test_delete_user_with_targets_blocked(client, db, admin_headers):
    officer = DbUser(name="Busy Officer", role=UserRole.officer)
    db.add(officer)
    db.commit()
    db.refresh(officer)

    target = DbTarget(customer_name="T1", address="A", phone="0", amount_due=100, assigned_officer=officer.id)
    db.add(target)
    db.commit()

    res = client.delete(f"/api/users/{officer.id}", headers=admin_headers)
    assert res.status_code == 409


# ── Ganti kata sandi membatalkan token lama ──────────────────────────

def test_password_change_forces_relogin(client, db):
    """Setelah kata sandi diubah, token lama harus ditolak (wajib login ulang),
    sedangkan login dengan kata sandi baru menghasilkan token yang valid."""
    import time

    user = DbUser(
        name="Pw Manager",
        email="pwmgr@c3mr.id",
        password_hash=hash_password("oldpass123"),
        role=UserRole.manager,
    )
    db.add(user)
    db.commit()

    # Login → token lama, dan token itu valid untuk endpoint terproteksi.
    res = client.post("/api/auth/login", json={"username": "pwmgr@c3mr.id", "password": "oldpass123"})
    assert res.status_code == 200
    old_headers = {"Authorization": f"Bearer {res.json()['token']}"}
    assert client.get("/api/dashboard/", headers=old_headers).status_code == 200

    # iat JWT presisi detik — lewati batas detik agar iat token lama < password_changed_at.
    time.sleep(1.1)

    # Ganti kata sandi (pakai token lama yang masih berlaku).
    res = client.post(
        "/api/auth/change-password",
        json={"current_password": "oldpass123", "new_password": "newpass456"},
        headers=old_headers,
    )
    assert res.status_code == 200

    # Token lama kini DITOLAK.
    assert client.get("/api/dashboard/", headers=old_headers).status_code == 401

    # Login dengan kata sandi baru → token baru valid.
    res = client.post("/api/auth/login", json={"username": "pwmgr@c3mr.id", "password": "newpass456"})
    assert res.status_code == 200
    new_headers = {"Authorization": f"Bearer {res.json()['token']}"}
    assert client.get("/api/dashboard/", headers=new_headers).status_code == 200


def test_token_ditolak_setelah_akun_dihapus(client, db):
    """Token yang sah tidak boleh berlaku lagi begitu akunnya dihapus.

    Dulu require_auth menulis `if user and ...`, sehingga pengguna terhapus JUSTRU
    lolos: user bernilai None, syaratnya salah, requestnya diteruskan. Endpoint
    dashboard/targets/analytics memakai require_auth, jadi celahnya nyata di sana.
    """
    from backend.models import DbUser, UserRole
    from backend.security import hash_password

    user = DbUser(
        name="Segera Dihapus",
        email="hapus@c3mr.id",
        password_hash=hash_password("pass123"),
        role=UserRole.manager,
    )
    db.add(user)
    db.commit()

    res = client.post("/api/auth/login", json={"username": "hapus@c3mr.id", "password": "pass123"})
    assert res.status_code == 200
    headers = {"Authorization": f"Bearer {res.json()['token']}"}
    assert client.get("/api/dashboard/", headers=headers).status_code == 200

    db.delete(db.query(DbUser).filter(DbUser.email == "hapus@c3mr.id").first())
    db.commit()

    # Token masih sah secara kriptografis dan belum kedaluwarsa — tetap harus ditolak.
    assert client.get("/api/dashboard/", headers=headers).status_code == 401
    assert client.get("/api/targets/", headers=headers).status_code == 401


# ── Normalisasi nomor telepon (A7) ───────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("081234567890", "6281234567890"),
    ("+62 812-3456-7890", "6281234567890"),
    ("6281234567890", "6281234567890"),
    ("81234567890", "6281234567890"),
    ("0062 812 3456 7890", "6281234567890"),
    ("", None),
    (None, None),
    ("bukan nomor", None),
])
def test_normalize_phone(raw, expected):
    """Telegram mengirim '62…' lewat kartu kontak sementara manajer mengetik '08…'.
    Kalau keduanya tidak diseragamkan, pencocokan nomor saat petugas menautkan
    Telegram-nya tidak akan pernah kena."""
    from backend.lib.format import normalize_phone
    assert normalize_phone(raw) == expected


# ── Validasi target masuk (A4) ───────────────────────────────────────

def test_upload_rejects_blank_and_negative(client, auth_headers):
    """Batas kepercayaan input manual: alamat kosong berarti target yang tidak bisa
    didatangi siapa pun, dan tagihan negatif merusak rekap."""
    assert client.post("/api/targets/upload", json=[
        {"customer_name": "A", "address": "   ", "phone": "0812", "amount_due": 100},
    ], headers=auth_headers).status_code == 422

    assert client.post("/api/targets/upload", json=[
        {"customer_name": "A", "address": "Jl. Satu", "phone": "0812", "amount_due": -5},
    ], headers=auth_headers).status_code == 422


def test_manual_single_target_upload(client, auth_headers):
    """Input manual memakai endpoint unggah yang sama dengan CSV, cukup satu elemen —
    jadi ia otomatis ikut tercatat di audit log dan ikut diantre geocoding."""
    res = client.post("/api/targets/upload", json=[
        {"customer_name": "  Budi  ", "address": " Jl. Merdeka 1 ", "phone": "0812", "amount_due": "50000"},
    ], headers=auth_headers)
    assert res.status_code == 200

    listed = client.get("/api/targets/", headers=auth_headers).json()
    assert any(t["customerName"] == "Budi" and t["address"] == "Jl. Merdeka 1" for t in listed)


# ── Reset kata sandi lewat Telegram (A2) ─────────────────────────────

def _seed_resettable_user(db, telegram_id="99001"):
    from backend.models import DbUser, UserRole
    from backend.security import hash_password
    user = DbUser(
        name="Lupa Sandi", email="lupa@test.id", telegram_id=telegram_id,
        password_hash=hash_password("sandilama"), role=UserRole.manager,
    )
    db.add(user)
    db.commit()
    return user


def test_forgot_password_does_not_leak_account_existence(client, db, monkeypatch):
    """Jawaban untuk akun yang ada dan yang tidak ada harus IDENTIK — kalau berbeda,
    halaman ini berubah jadi alat pencacah nama pengguna yang valid."""
    monkeypatch.setattr("backend.notifications.send_telegram_notification", lambda *a, **k: True)
    _seed_resettable_user(db)

    ada = client.post("/api/auth/forgot-password", json={"username": "lupa@test.id"})
    tidak_ada = client.post("/api/auth/forgot-password", json={"username": "tidakada@test.id"})
    assert ada.status_code == tidak_ada.status_code == 200
    assert ada.json() == tidak_ada.json()


def test_reset_password_end_to_end(client, db, monkeypatch):
    monkeypatch.setattr("backend.notifications.send_telegram_notification", lambda *a, **k: True)
    _seed_resettable_user(db)
    client.post("/api/auth/forgot-password", json={"username": "lupa@test.id"})

    from backend.routers.auth import _reset_codes
    code = _reset_codes["lupa@test.id"][0]

    res = client.post("/api/auth/reset-password", json={
        "username": "lupa@test.id", "code": code, "new_password": "sandibaru123",
    })
    assert res.status_code == 200
    assert client.post("/api/auth/login", json={"username": "lupa@test.id", "password": "sandibaru123"}).status_code == 200
    # Sekali pakai: kode yang sama tidak boleh berlaku lagi.
    assert client.post("/api/auth/reset-password", json={
        "username": "lupa@test.id", "code": code, "new_password": "sandilain123",
    }).status_code == 400


def test_reset_password_wrong_code_burns_attempts(client, db, monkeypatch):
    monkeypatch.setattr("backend.notifications.send_telegram_notification", lambda *a, **k: True)
    _seed_resettable_user(db)
    client.post("/api/auth/forgot-password", json={"username": "lupa@test.id"})

    from backend.routers.auth import _reset_codes, RESET_MAX_ATTEMPTS
    code = _reset_codes["lupa@test.id"][0]
    salah = "000000" if code != "000000" else "111111"

    for _ in range(RESET_MAX_ATTEMPTS):
        assert client.post("/api/auth/reset-password", json={
            "username": "lupa@test.id", "code": salah, "new_password": "sandibaru123",
        }).status_code == 400

    # Jatah habis: kode yang BENAR pun harus ditolak, kalau tidak menebak 6 digit
    # cuma soal mencoba berulang kali.
    assert client.post("/api/auth/reset-password", json={
        "username": "lupa@test.id", "code": code, "new_password": "sandibaru123",
    }).status_code == 400
    assert client.post("/api/auth/login", json={"username": "lupa@test.id", "password": "sandilama"}).status_code == 200


def test_reset_password_expired_code_rejected(client, db, monkeypatch):
    monkeypatch.setattr("backend.notifications.send_telegram_notification", lambda *a, **k: True)
    _seed_resettable_user(db)
    client.post("/api/auth/forgot-password", json={"username": "lupa@test.id"})

    from backend.routers import auth as auth_module
    code, _expires, attempts = auth_module._reset_codes["lupa@test.id"]
    auth_module._reset_codes["lupa@test.id"] = (code, time.time() - 1, attempts)

    assert client.post("/api/auth/reset-password", json={
        "username": "lupa@test.id", "code": code, "new_password": "sandibaru123",
    }).status_code == 400


# ── Notifikasi manajer saat kunjungan selesai (A6) ───────────────────

def test_visit_notification_reaches_admin_when_no_manager_exists(db, monkeypatch):
    """Penerima disaring `role != officer`, BUKAN `== manager`.

    Setelah peran admin dipisah, sebuah organisasi bisa saja hanya punya akun admin.
    Filter `== manager` akan mengirim NOL notifikasi tanpa satu pun galat — gagal
    diam-diam, jenis kegagalan yang tidak akan ketahuan sampai ada yang mengeluh.
    """
    from backend.models import DbNotificationLog, DbReport, PaymentStatus
    from backend.tests.conftest import TestSession

    monkeypatch.setattr("backend.database.SessionLocal", TestSession)
    terkirim = []
    monkeypatch.setattr(
        "backend.notifications.send_telegram_notification",
        lambda tid, msg, **k: terkirim.append((tid, msg)) or True,
    )

    admin = DbUser(name="Admin Saja", telegram_id="777", role=UserRole.admin)
    officer = DbUser(name="Petugas", telegram_id="888", role=UserRole.officer)
    db.add_all([admin, officer])
    db.commit()

    target = DbTarget(customer_name="Nasabah X", address="Jl. Uji 9", phone="0812", amount_due=250000)
    db.add(target)
    db.commit()
    report = DbReport(
        target_id=target.id, officer_id=officer.id,
        payment_status=PaymentStatus.paid, notes="Sudah dibayar tunai",
    )
    db.add(report)
    db.commit()

    from backend.routers.officer import notify_managers_of_report
    notify_managers_of_report(report.id)

    penerima = [tid for tid, _ in terkirim]
    assert "777" in penerima, "admin harus menerima notifikasi meski tidak ada akun manager"
    assert "888" not in penerima, "petugas pelapor tidak perlu dikabari soal laporannya sendiri"
    assert "Nasabah X" in terkirim[0][1] and "Lunas" in terkirim[0][1]
    assert db.query(DbNotificationLog).filter(DbNotificationLog.recipient_id == admin.id).count() == 1
