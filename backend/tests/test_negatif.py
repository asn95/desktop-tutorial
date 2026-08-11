"""Skenario negatif: yang TIDAK boleh terjadi.

Tes di test_api.py sebagian besar membuktikan jalur yang benar berhasil. Berkas ini
membuktikan jalur yang salah GAGAL — penyalahgunaan wewenang, akun yang sudah
dicabut, penugasan yang tidak masuk akal, dan data yang mustahil di lapangan.
"""
import io
import json
from urllib.parse import urlencode

from backend.models import DbComment, DbReport, DbTarget, DbUser, PaymentStatus, TargetStatus, UserRole
from backend.security import hash_password


def _login(client, email, password):
    res = client.post("/api/auth/login", json={"username": email, "password": password})
    return {"Authorization": f"Bearer {res.json()['token']}"}


def _telegram_headers(telegram_id):
    """Header Mini App. Tanda tangannya di-monkeypatch, isinya tetap dibaca sungguhan."""
    return {"X-Telegram-Auth": urlencode({"user": json.dumps({"id": telegram_id})})}


def _lewati_verifikasi_telegram(monkeypatch):
    monkeypatch.setattr("backend.routers.officer.validate_telegram_data", lambda _: True)


def _foto():
    # PNG 1×1 asli — ekstensi saja tidak cukup kalau suatu saat isinya divalidasi.
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000a49444154789c6300010000050001"
        "0d0a2db40000000049454e44ae426082"
    )
    return {"photo": ("bukti.png", io.BytesIO(png), "image/png")}


# ── Manajer mencoba mengubah data yang bukan haknya ──────────────────

def test_manajer_tidak_bisa_menaikkan_perannya_sendiri(client, db, auth_headers):
    """Eskalasi hak paling langsung: manajer menulis 'admin' ke akunnya sendiri.

    Kalau ini lolos, seluruh pemisahan peran dari butir revisi 1 tidak ada artinya —
    siapa pun yang bisa login sebagai manajer bisa jadi admin dalam satu request.
    """
    manajer = db.query(DbUser).filter(DbUser.email == "mgr@test.id").first()
    res = client.patch(f"/api/users/{manajer.id}", json={"role": "admin"}, headers=auth_headers)
    assert res.status_code == 403
    db.refresh(manajer)
    assert manajer.role == UserRole.manager


def test_manajer_tidak_bisa_membajak_telegram_akun_lain(client, db, auth_headers):
    """Telegram ID adalah identitas petugas di Mini App. Menulisinya ke akun sendiri
    berarti membaca dan mengirim laporan atas nama orang lain."""
    petugas = DbUser(name="Petugas Sah", telegram_id="900001", role=UserRole.officer)
    db.add(petugas)
    db.commit()
    db.refresh(petugas)

    res = client.patch(f"/api/users/{petugas.id}", json={"telegram_id": "666"}, headers=auth_headers)
    assert res.status_code == 403
    db.refresh(petugas)
    assert petugas.telegram_id == "900001"


def test_manajer_tidak_bisa_menyalakan_mode_pemeliharaan(client, auth_headers):
    """Mode pemeliharaan mengunci seluruh API. Itu tombol admin, bukan tombol manajer."""
    res = client.post("/api/admin/maintenance", json={"enabled": True}, headers=auth_headers)
    assert res.status_code == 403

    from backend.maintenance import maintenance_state
    assert maintenance_state.enabled is False


# ── Akun yang sudah dicabut ──────────────────────────────────────────

def test_akun_nonaktif_tidak_bisa_login(client, db):
    """Menonaktifkan akun harus mencabut aksesnya. Kalau hanya menyembunyikannya dari
    daftar penugasan, tombol 'nonaktifkan' membohongi orang yang menekannya."""
    user = DbUser(
        name="Manajer Keluar", email="keluar@test.id",
        password_hash=hash_password("pass123"), role=UserRole.manager, active=False,
    )
    db.add(user)
    db.commit()

    res = client.post("/api/auth/login", json={"username": "keluar@test.id", "password": "pass123"})
    assert res.status_code == 401


def test_token_lama_ditolak_setelah_akun_dinonaktifkan(client, db, admin_headers):
    """Kasus nyata: manajer resign, admin menonaktifkan akunnya. Kalau token yang
    terlanjur terbit tetap sah, orang itu masih bisa mengekspor seluruh data nasabah
    sampai tokennya kedaluwarsa."""
    manajer = DbUser(
        name="Manajer Resign", email="resign@test.id",
        password_hash=hash_password("pass123"), role=UserRole.manager,
    )
    db.add(manajer)
    db.commit()
    db.refresh(manajer)
    headers = _login(client, "resign@test.id", "pass123")
    assert client.get("/api/targets/", headers=headers).status_code == 200

    assert client.patch(f"/api/users/{manajer.id}", json={"active": False},
                        headers=admin_headers).status_code == 200

    assert client.get("/api/targets/", headers=headers).status_code == 401
    assert client.get("/api/targets/export/csv", headers=headers).status_code == 401


# ── Penugasan yang tidak masuk akal ──────────────────────────────────

def test_target_tidak_bisa_ditugaskan_ke_akun_portal(client, db, auth_headers):
    """Penugasan hanya mencari pengguna berdasarkan id, tanpa memeriksa perannya.
    Target yang jatuh ke akun manajer tidak akan pernah muncul di Mini App mana pun —
    ia hilang dari lapangan tapi berstatus 'sedang dikerjakan' di dashboard."""
    target = DbTarget(customer_name="Nasabah A", address="Jl. A", phone="0812", amount_due=100000)
    admin = DbUser(name="Admin Sistem", email="adm2@test.id",
                   password_hash=hash_password("pass1234"), role=UserRole.admin)
    db.add_all([target, admin])
    db.commit()
    db.refresh(target)
    db.refresh(admin)

    res = client.patch(f"/api/targets/{target.id}/assign?officer_id={admin.id}", headers=auth_headers)
    assert res.status_code == 400
    db.refresh(target)
    assert target.assigned_officer is None
    assert target.status == TargetStatus.pending


def test_target_tidak_bisa_ditugaskan_ke_petugas_nonaktif(client, db, auth_headers):
    """Petugas nonaktif = sudah tidak bekerja. Target yang ditugaskan padanya tidak
    akan pernah dikunjungi, dan tidak ada yang tahu karena statusnya bukan lagi
    'menunggu'."""
    target = DbTarget(customer_name="Nasabah B", address="Jl. B", phone="0813", amount_due=200000)
    petugas = DbUser(name="Petugas Nonaktif", telegram_id="900002",
                     role=UserRole.officer, active=False)
    db.add_all([target, petugas])
    db.commit()
    db.refresh(target)
    db.refresh(petugas)

    res = client.patch(f"/api/targets/{target.id}/assign?officer_id={petugas.id}", headers=auth_headers)
    assert res.status_code == 400
    db.refresh(target)
    assert target.assigned_officer is None


def test_bulk_assign_menolak_penerima_bukan_petugas(client, db, auth_headers):
    """Jalur massal harus dijaga sama ketatnya dengan jalur satuan — kalau tidak,
    penjaganya cuma menggeser masalah satu endpoint ke sebelahnya."""
    targets = [DbTarget(customer_name=f"N{i}", address="Jl. C", phone="0814", amount_due=50000)
               for i in range(3)]
    manajer_lain = DbUser(name="Manajer Lain", email="mgr2@test.id",
                          password_hash=hash_password("pass123"), role=UserRole.manager)
    db.add_all(targets + [manajer_lain])
    db.commit()
    for t in targets:
        db.refresh(t)
    db.refresh(manajer_lain)

    res = client.post("/api/targets/bulk-assign",
                      json={"target_ids": [t.id for t in targets], "officer_id": manajer_lain.id},
                      headers=auth_headers)
    assert res.status_code == 400
    for t in targets:
        db.refresh(t)
        assert t.assigned_officer is None


# ── Petugas lapangan menjangkau data petugas lain ────────────────────

def test_petugas_tidak_bisa_melapor_untuk_target_petugas_lain(client, db, monkeypatch):
    """Penjaga yang sudah ada di kode — ditegakkan di sini supaya tidak hilang diam-diam
    saat endpoint laporan disentuh lagi."""
    _lewati_verifikasi_telegram(monkeypatch)
    a = DbUser(name="Petugas A", telegram_id="900010", role=UserRole.officer)
    b = DbUser(name="Petugas B", telegram_id="900011", role=UserRole.officer)
    db.add_all([a, b])
    db.commit()
    db.refresh(a)
    target = DbTarget(customer_name="Milik A", address="Jl. D", phone="0815",
                      amount_due=300000, assigned_officer=a.id)
    db.add(target)
    db.commit()
    db.refresh(target)

    res = client.post("/api/officer/report",
                      data={"target_id": target.id, "payment_status": "Paid"},
                      files=_foto(), headers=_telegram_headers("900011"))
    assert res.status_code == 403
    assert db.query(DbReport).count() == 0


def test_petugas_tidak_bisa_baca_komentar_target_petugas_lain(client, db, monkeypatch):
    """Komentar memuat catatan lapangan tentang nasabah. Endpoint bacanya menyaring
    berdasarkan target_id saja — tanpa memeriksa target itu memang ditugaskan kepada
    si pembaca, siapa pun yang punya id target bisa membacanya."""
    _lewati_verifikasi_telegram(monkeypatch)
    a = DbUser(name="Petugas A2", telegram_id="900020", role=UserRole.officer)
    b = DbUser(name="Petugas B2", telegram_id="900021", role=UserRole.officer)
    db.add_all([a, b])
    db.commit()
    db.refresh(a)
    target = DbTarget(customer_name="Milik A2", address="Jl. E", phone="0816",
                      amount_due=400000, assigned_officer=a.id)
    db.add(target)
    db.commit()
    db.refresh(target)
    db.add(DbComment(target_id=target.id, officer_id=a.id,
                     message="Nasabah minta ditagih setelah gajian"))
    db.commit()

    res = client.get(f"/api/officer/comments/{target.id}", headers=_telegram_headers("900021"))
    assert res.status_code == 403


def test_laporan_kedua_untuk_target_selesai_ditolak(client, db, monkeypatch):
    """Satu kunjungan, satu laporan. Tanpa penjaga ini satu target bisa dilaporkan
    berkali-kali — tiap kali mengirim notifikasi baru ke manajer dan menggandakan
    angka kunjungan di analitik."""
    _lewati_verifikasi_telegram(monkeypatch)
    monkeypatch.setattr("backend.notifications.send_telegram_notification", lambda *a, **k: True)
    petugas = DbUser(name="Petugas C", telegram_id="900030", role=UserRole.officer)
    db.add(petugas)
    db.commit()
    db.refresh(petugas)
    target = DbTarget(customer_name="Nasabah C", address="Jl. F", phone="0817",
                      amount_due=500000, assigned_officer=petugas.id)
    db.add(target)
    db.commit()
    db.refresh(target)

    kirim = lambda: client.post(
        "/api/officer/report",
        data={"target_id": target.id, "payment_status": "Paid"},
        files=_foto(), headers=_telegram_headers("900030"),
    )
    assert kirim().status_code == 200
    assert kirim().status_code == 409
    assert db.query(DbReport).count() == 1


# ── Data yang mustahil di lapangan ───────────────────────────────────

def test_status_pembayaran_di_luar_daftar_ditolak(client, db, monkeypatch):
    """payment_status masuk sebagai teks bebas dari form. Nilai di luar enum harus
    ditolak di pintu masuk, bukan diselipkan ke kolom lalu meledak saat analitik
    membacanya kembali."""
    _lewati_verifikasi_telegram(monkeypatch)
    petugas = DbUser(name="Petugas D", telegram_id="900040", role=UserRole.officer)
    db.add(petugas)
    db.commit()
    db.refresh(petugas)
    target = DbTarget(customer_name="Nasabah D", address="Jl. G", phone="0818",
                      amount_due=600000, assigned_officer=petugas.id)
    db.add(target)
    db.commit()
    db.refresh(target)

    res = client.post("/api/officer/report",
                      data={"target_id": target.id, "payment_status": "Kabur"},
                      files=_foto(), headers=_telegram_headers("900040"))
    assert res.status_code in (400, 422)
    assert db.query(DbReport).count() == 0
