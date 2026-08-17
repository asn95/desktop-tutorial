"""Pengujian web ujung-ke-ujung: menggerakkan peramban sungguhan terhadap aplikasi
yang berjalan, bukan memanggil API-nya langsung.

Tes di backend/tests/ membuktikan aturan ditegakkan di lapisan API. Berkas ini
membuktikan hal yang berbeda dan tidak tercakup di sana: bahwa antarmuka yang
benar-benar dilihat pengguna memang menampilkan, menyembunyikan, dan menolak hal
yang seharusnya — termasuk ketika seseorang mengetik alamat halaman secara langsung
alih-alih menekan menu.

Menjalankan:
    source .venv/bin/activate
    python -m pytest tests_web/ -v

Prasyarat: `frontend/dist` sudah di-build, dan Chromium Playwright terpasang
(`python -m playwright install chromium`). Server dijalankan otomatis oleh fixture
pada porta 8000 — porta itu dipatok karena `frontend/.env` menanam alamat API
`http://localhost:8000/api` ke dalam bundel saat build.
"""
import os
import socket
import subprocess
import sys
import tempfile
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8000
BASE = f"http://localhost:{PORT}"
SANDI = "ujiweb12345"


def _porta_dipakai(porta: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", porta)) == 0


def _siapkan_basis_data(path: str) -> None:
    """Isi basis data sementara: satu admin, satu manajer, satu petugas, dan target."""
    sys.path.insert(0, REPO)
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.database import Base
    from backend.models import DbTarget, DbUser, UserRole
    from backend.security import hash_password

    mesin = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=mesin)
    db = sessionmaker(bind=mesin)()
    petugas = DbUser(name="Petugas Uji", telegram_id="990001", role=UserRole.officer)
    db.add_all([
        DbUser(name="Manajer Uji", email="manajer@uji.id",
               password_hash=hash_password(SANDI), role=UserRole.manager),
        DbUser(name="Admin Uji", email="admin@uji.id",
               password_hash=hash_password(SANDI), role=UserRole.admin),
        petugas,
    ])
    db.commit()
    db.refresh(petugas)
    for i in range(3):
        db.add(DbTarget(customer_name=f"Nasabah Uji {i + 1}", address=f"Jl. Uji No. {i + 1}",
                        phone=f"08120000000{i}", amount_due=1_000_000 * (i + 1),
                        period="2026-08", assigned_officer=petugas.id))
    db.commit()
    db.close()


@pytest.fixture(scope="session")
def server():
    if _porta_dipakai(PORT):
        pytest.skip(f"porta {PORT} sedang dipakai proses lain")
    if not os.path.isdir(os.path.join(REPO, "frontend", "dist")):
        pytest.skip("frontend/dist belum ada — jalankan `npm run build` di frontend/")

    berkas_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    _siapkan_basis_data(berkas_db)

    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{berkas_db}",
        "JWT_SECRET": "kunci-uji-web-saja-minimal-32-karakter!",
        "DEBUG": "false",
        # Dikosongkan dengan sengaja: verifikasi Telegram harus gagal-tertutup,
        # dan salah satu tes di bawah membuktikan itu.
        "TELEGRAM_BOT_TOKEN": "",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=REPO, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        if _porta_dipakai(PORT):
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail("server tidak kunjung siap")

    yield BASE

    proc.terminate()
    proc.wait(timeout=10)
    os.unlink(berkas_db)


@pytest.fixture()
def halaman(server):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        peramban = p.chromium.launch()
        # Konteks baru tiap tes: localStorage tidak boleh terbawa antar peran,
        # kalau tidak tes berikutnya ikut login sebagai pengguna sebelumnya.
        ctx = peramban.new_context(viewport={"width": 1400, "height": 900})
        pg = ctx.new_page()
        yield pg
        ctx.close()
        peramban.close()


def masuk(pg, email: str) -> None:
    pg.goto(BASE, wait_until="networkidle", timeout=45_000)
    pg.locator("input").first.fill(email)
    pg.fill('input[type="password"]', SANDI)
    pg.keyboard.press("Enter")
    pg.wait_for_load_state("networkidle", timeout=30_000)
    time.sleep(2.5)


# ── Halaman masuk ────────────────────────────────────────────────────

def test_halaman_masuk_tampil(halaman):
    halaman.goto(BASE, wait_until="networkidle", timeout=45_000)
    isi = halaman.content()
    assert "C3MR" in isi
    assert halaman.locator('input[type="password"]').count() == 1


def test_kata_sandi_salah_ditolak(halaman):
    halaman.goto(BASE, wait_until="networkidle", timeout=45_000)
    halaman.locator("input").first.fill("manajer@uji.id")
    halaman.fill('input[type="password"]', "jelas-salah")
    halaman.keyboard.press("Enter")
    time.sleep(3)
    # Masih di halaman masuk: kolom kata sandi belum hilang.
    assert halaman.locator('input[type="password"]').count() == 1


def test_tautan_lupa_kata_sandi_ada(halaman):
    """Butir revisi: alur pemulihan kata sandi harus benar-benar ada, bukan tautan mati."""
    halaman.goto(BASE, wait_until="networkidle", timeout=45_000)
    assert halaman.get_by_text("Lupa kata sandi", exact=False).count() >= 1


# ── Pemisahan peran, dilihat dari antarmuka ──────────────────────────

def test_manajer_melihat_menu_operasional(halaman):
    masuk(halaman, "manajer@uji.id")
    isi = halaman.content()
    assert "Dashboard" in isi
    assert "Target" in isi
    # Menu khusus admin tidak boleh muncul untuk manajer.
    assert "Log Audit" not in isi


def test_admin_hanya_melihat_menu_admin(halaman):
    """Butir revisi 1: portal admin dipisahkan dari portal manajer."""
    masuk(halaman, "admin@uji.id")
    isi = halaman.content()
    assert "Log Audit" in isi
    assert "Manajemen Pengguna" in isi
    # Data operasional bukan urusan admin.
    assert "Dashboard" not in isi


def test_admin_mengetik_alamat_target_tetap_ditolak(halaman):
    """Menyembunyikan menu saja kosmetik. Mengetik alamatnya langsung harus tetap gagal."""
    masuk(halaman, "admin@uji.id")
    halaman.goto(f"{BASE}/targets", wait_until="networkidle", timeout=30_000)
    time.sleep(3)
    isi = halaman.content()
    # Tidak boleh ada satu pun baris target yang tampil.
    assert "Nasabah Uji 1" not in isi


def test_halaman_terlindungi_melempar_ke_masuk(halaman):
    """Tanpa sesi, alamat mana pun harus berakhir di halaman masuk."""
    halaman.goto(f"{BASE}/dashboard", wait_until="networkidle", timeout=30_000)
    time.sleep(2.5)
    assert halaman.locator('input[type="password"]').count() == 1


# ── Fitur hasil revisi, dilihat dari antarmuka ───────────────────────

def test_formulir_target_manual_tampil(halaman):
    """Butir revisi: input target manual, tanpa harus lewat berkas CSV."""
    masuk(halaman, "manajer@uji.id")
    halaman.goto(f"{BASE}/targets", wait_until="networkidle", timeout=30_000)
    time.sleep(3.5)
    isi = halaman.content()
    assert "Input Manual" in isi or "Tambah Target" in isi
    assert "Nasabah Uji 1" in isi          # tabelnya memang terisi


def test_pendaftaran_petugas_meminta_nomor_telepon(halaman):
    """Butir revisi: penambahan petugas cukup dengan nomor telepon."""
    masuk(halaman, "admin@uji.id")
    time.sleep(2)
    isi = halaman.content()
    # Labelnya ditulis "Nomor telepon" di kode; huruf besar pada tampilan berasal
    # dari CSS, jadi yang dicocokkan adalah teks aslinya.
    assert "Nomor telepon" in isi or "Phone number" in isi


# ── Mini App petugas ─────────────────────────────────────────────────

def test_mini_app_menolak_tanda_tangan_palsu(halaman):
    """Verifikasi Telegram gagal-tertutup: tanpa token bot, initData palsu ditolak.

    Dijalankan lewat peramban supaya yang diuji adalah jalur yang benar-benar
    dipakai Mini App, termasuk headernya.
    """
    hasil = halaman.request.get(
        f"{BASE}/api/officer/tasks",
        headers={"X-Telegram-Auth": 'user={"id":990001}&hash=palsu'},
    )
    assert hasil.status in (401, 403)


def test_mini_app_termuat(halaman):
    halaman.goto(f"{BASE}/officer-app/", wait_until="networkidle", timeout=45_000)
    time.sleep(2.5)
    assert "C3MR" in halaman.content()


def test_mini_app_punya_penyaring_dan_pencarian(halaman):
    """Butir revisi: penyaringan di Mini App, dan antrean urut terbaru.

    Daftar tugas hanya muncul setelah identitas Telegram sah, jadi jawaban
    endpoint-nya diganti di lapisan jaringan; yang diuji tetap kode Mini App
    yang sungguhan, termasuk cara ia menyaring dan mengurutkan.
    """
    import json

    tugas = [
        {"id": "t-lama", "customerName": "Nasabah Lama", "address": "Jl. Lama",
         "phone": "0812", "amountDue": 1_000_000, "status": "in_progress",
         "period": "2026-08", "created_at": "2026-08-01T00:00:00Z"},
        {"id": "t-baru", "customerName": "Nasabah Baru", "address": "Jl. Baru",
         "phone": "0813", "amountDue": 2_000_000, "status": "in_progress",
         "period": "2026-08", "created_at": "2026-08-09T00:00:00Z"},
    ]
    halaman.context.add_init_script("""
      window.Telegram = { WebApp: {
        initData: 'user=%7B%22id%22%3A990001%7D&auth_date=1&hash=x',
        initDataUnsafe: { user: { id: 990001, first_name: 'Uji' } },
        ready(){}, expand(){}, close(){},
        BackButton:{show(){},hide(){},onClick(){}},
        MainButton:{show(){},hide(){},setText(){},onClick(){},showProgress(){},hideProgress(){}},
        HapticFeedback:{impactOccurred(){},notificationOccurred(){}},
        themeParams:{}, colorScheme:'light'
      }};
    """)
    # Skrip asli Telegram akan menimpa stub di atas, jadi dicegah memuat.
    halaman.context.route("**/telegram-web-app.js*", lambda r: r.abort())
    halaman.context.route("**/officer/tasks*", lambda r: r.fulfill(
        status=200, content_type="application/json", body=json.dumps(tugas)))

    halaman.goto(f"{BASE}/officer-app/", wait_until="networkidle", timeout=45_000)
    time.sleep(3)
    isi = halaman.content()

    assert "Cari nama atau alamat" in isi, "kotak pencarian tidak ditemukan"
    assert "Periode" in isi, "penyaring periode tidak ditemukan"
    # Terbaru lebih dulu: 'Nasabah Baru' harus muncul sebelum 'Nasabah Lama'.
    assert isi.index("Nasabah Baru") < isi.index("Nasabah Lama"), "antrean tidak urut terbaru"
    # Nomor kasus harus diturunkan dari id tugas, bukan dari posisinya di daftar.
    # Kalau turun dari posisi, mengurutkan ulang antrean membuat nomor yang sama
    # menempel pada nasabah yang berbeda.
    assert "TBARU" in isi and "TLAMA" in isi, "nomor kasus tidak berasal dari id tugas"
