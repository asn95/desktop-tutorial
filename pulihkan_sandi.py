#!/usr/bin/env python3
"""Pemulihan kata sandi manajer C3MR — langsung ke database produksi.

Dipakai hanya bila kata sandi hilang dan tidak ada cara masuk lewat aplikasi.

Jalankan:  python3 pulihkan_sandi.py

Kata sandi baru diketik langsung ke skrip ini, tidak terlihat di layar, dan
tidak masuk riwayat shell. Skrip menulis hash bcrypt dan menstempel
password_changed_at, sehingga seluruh sesi lama ikut berakhir — sama persis
dengan efek mengganti kata sandi lewat portal.
"""
import getpass
import subprocess
import sys


def _tty():
    """Terminal sungguhan, kalau ada. Dibaca langsung supaya skrip tetap jalan
    walau stdin dialihkan — itu yang bikin versi sebelumnya kena EOFError."""
    try:
        return open("/dev/tty", "r+")
    except OSError:
        return None


def tanya(prompt: str) -> str:
    t = _tty()
    if t is None:
        sys.exit(BUTUH_TERMINAL)
    with t:
        t.write(prompt)
        t.flush()
        return (t.readline() or "").strip()


def sandi(prompt: str) -> str:
    """getpass membaca /dev/tty sendiri; kalau tidak ada, ia diam-diam jatuh ke
    stdin tanpa menyembunyikan ketikan. Itu bahaya, jadi dicegat lebih dulu."""
    if _tty() is None:
        sys.exit(BUTUH_TERMINAL)
    return getpass.getpass(prompt)


BUTUH_TERMINAL = """
Skrip ini butuh terminal sungguhan karena kata sandinya diketik langsung ke sini
dan tidak boleh terlihat di layar.

Buka Terminal, lalu jalankan:

    cd ~/capstone1 && source .venv/bin/activate && python3 pulihkan_sandi.py
"""


def ambil_url():
    """Ambil DATABASE_PUBLIC_URL dari Railway tanpa menampilkannya."""
    try:
        out = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--kv"],
            capture_output=True, text=True, timeout=90,
        ).stdout
    except FileNotFoundError:
        sys.exit("Railway CLI tidak ditemukan. Jalankan dari mesin yang sudah 'railway login'.")
    for line in out.splitlines():
        if line.startswith("DATABASE_PUBLIC_URL="):
            return line.split("=", 1)[1].strip()
    sys.exit("DATABASE_PUBLIC_URL tidak ada. Pastikan sudah 'railway link' ke proyek c3mr.")


def main():
    print("\nPemulihan kata sandi manajer C3MR")
    print("Hanya untuk keadaan terkunci. Semua sesi aktif akan berakhir.\n")

    try:
        import bcrypt
        from sqlalchemy import create_engine, text
    except ImportError:
        sys.exit("Jalankan dulu:  cd ~/capstone1 && source .venv/bin/activate")

    url = ambil_url().replace("postgres://", "postgresql://", 1)
    eng = create_engine(url, connect_args={"sslmode": "require"})

    with eng.connect() as c:
        rows = list(c.execute(text(
            "select id, name, email from users where role='manager' order by name")))
    if not rows:
        sys.exit("Tidak ada akun manajer di database.")

    print("Akun manajer yang ada:")
    for i, r in enumerate(rows, 1):
        print(f"  {i}. {r[1]}  (nama pengguna: {r[2]})")

    if len(rows) == 1:
        target = rows[0]          # tidak ada yang perlu dipilih
    else:
        pilih = tanya("\nPilih nomor [1]: ") or "1"
        try:
            target = rows[int(pilih) - 1]
        except (ValueError, IndexError):
            sys.exit("Pilihan tidak sah.")

    print(f"\nMengatur ulang kata sandi untuk: {target[1]}")
    print("Ketikan tidak akan terlihat di layar — itu normal.\n")

    baru = sandi("Kata sandi BARU      : ")
    ulang = sandi("Ketik ulang yang BARU: ")
    if baru != ulang:
        sys.exit("Dibatalkan: dua kata sandi tidak sama.")
    if len(baru) < 6:
        sys.exit("Dibatalkan: minimal 6 karakter.")
    if len(baru) < 12:
        print(f"\n  Catatan: {len(baru)} karakter, dan portal ini terbuka di internet.")
        if tanya("  Lanjutkan? [y/N]: ").lower() != "y":
            sys.exit("Dibatalkan.")

    hashed = bcrypt.hashpw(baru.encode(), bcrypt.gensalt()).decode()

    with eng.begin() as c:
        c.execute(
            text("update users set password_hash=:h, password_changed_at=now() where id=:i"),
            {"h": hashed, "i": target[0]},
        )

    # Buktikan hasilnya, jangan sekadar mengklaim berhasil.
    with eng.connect() as c:
        stored = c.execute(text("select password_hash, password_changed_at from users where id=:i"),
                           {"i": target[0]}).one()
    ok = bcrypt.checkpw(baru.encode(), stored[0].encode())
    print(f"\n  hash tertulis     : {'ya' if ok else 'TIDAK — hubungi bantuan'}")
    print(f"  sesi lama berakhir: ya (password_changed_at = {stored[1]})")
    print(f"\nSelesai. Login di portal dengan nama pengguna '{target[2]}' dan kata sandi baru.")
    print("Simpan kata sandinya sekarang, dan beri tahu Rashad.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nDibatalkan.")
