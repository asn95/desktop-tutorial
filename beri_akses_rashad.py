#!/usr/bin/env python3
"""Buat akun database read-only untuk Rashad di PostgreSQL produksi.

    python3 beri_akses_rashad.py           # buat / ganti sandi
    python3 beri_akses_rashad.py --cabut   # hapus aksesnya lagi

Kenapa role terpisah dan bukan DATABASE_PUBLIC_URL apa adanya: URL itu memakai
user 'postgres' yang superuser — bisa DROP TABLE, bisa ganti sandi manajer, dan
tidak bisa dicabut tanpa mengganti sandi seluruh sistem. Role di bawah hanya bisa
SELECT, dan bisa dihapus satu perintah tanpa mengganggu aplikasi.
"""
import argparse
import subprocess
import sys
from urllib.parse import urlsplit

from pulihkan_sandi import sandi          # prompt tanpa gema, sudah teruji

NAMA = "rashad"


def url_admin():
    try:
        out = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--kv"],
            capture_output=True, text=True, timeout=90,
        ).stdout
    except FileNotFoundError:
        sys.exit("Railway CLI tidak ada. Jalankan dari mesin yang sudah 'railway login'.")
    for baris in out.splitlines():
        if baris.startswith("DATABASE_PUBLIC_URL="):
            return baris.split("=", 1)[1].strip().replace("postgres://", "postgresql://", 1)
    sys.exit("DATABASE_PUBLIC_URL tidak ada. Jalankan 'railway link' ke proyek c3mr dulu.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cabut", action="store_true", help="hapus akses Rashad")
    a = ap.parse_args()

    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        sys.exit("Jalankan dulu:  cd ~/capstone1 && source .venv/bin/activate")

    url = url_admin()
    bagian = urlsplit(url)
    basis = bagian.path.lstrip("/")
    eng = create_engine(url, connect_args={"sslmode": "require"}, isolation_level="AUTOCOMMIT")

    if a.cabut:
        with eng.connect() as c:
            # Hak akses harus dilepas sebelum role bisa dihapus.
            c.execute(text(f"REASSIGN OWNED BY {NAMA} TO postgres"))
            c.execute(text(f"DROP OWNED BY {NAMA}"))
            c.execute(text(f"DROP ROLE IF EXISTS {NAMA}"))
        print(f"Akses '{NAMA}' dicabut. Sambungan dia yang sedang jalan ikut mati.")
        return

    print(f"\nMembuat akses read-only untuk '{NAMA}' di database produksi.")
    print("Ketikan sandi tidak akan terlihat di layar — itu normal.\n")
    pw = sandi("Sandi untuk Rashad   : ")
    if pw != sandi("Ketik ulang          : "):
        sys.exit("Dibatalkan: dua sandi tidak sama.")
    if len(pw) < 12:
        sys.exit("Dibatalkan: minimal 12 karakter — port ini terbuka di internet.")

    with eng.connect() as c:
        ada = c.execute(text("select 1 from pg_roles where rolname=:n"), {"n": NAMA}).first()
        if ada:
            c.execute(text(f"ALTER ROLE {NAMA} WITH LOGIN PASSWORD :p"), {"p": pw})
            print(f"\n  role '{NAMA}' sudah ada — sandinya diganti")
        else:
            c.execute(text(f"CREATE ROLE {NAMA} LOGIN PASSWORD :p"), {"p": pw})
            print(f"\n  role '{NAMA}' dibuat")
        c.execute(text(f'GRANT CONNECT ON DATABASE "{basis}" TO {NAMA}'))
        c.execute(text(f"GRANT USAGE ON SCHEMA public TO {NAMA}"))
        c.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {NAMA}"))
        # Tabel yang dibuat SETELAH ini (migrasi baru) juga ikut terbaca.
        c.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {NAMA}"))

    # Buktikan batasnya, jangan sekadar mengklaim read-only.
    url_r = f"postgresql://{NAMA}:{pw}@{bagian.hostname}:{bagian.port}/{basis}"
    eng_r = create_engine(url_r, connect_args={"sslmode": "require"})
    with eng_r.connect() as c:
        n = c.execute(text("select count(*) from targets")).scalar()
    print(f"  bisa membaca      : ya ({n} baris di tabel targets)")
    try:
        # 'where false' tidak menyentuh satu baris pun; izin diperiksa lebih dulu,
        # jadi ini aman dijalankan di produksi dan tetap menguji hak tulis.
        with eng_r.connect() as c:
            c.execute(text("delete from targets where false"))
        print("  BISA MENULIS      : GAGAL — role ini tidak read-only, jangan diberikan!")
        sys.exit(1)
    except Exception as e:
        if "permission denied" not in str(e).lower():
            sys.exit(f"  uji tulis tidak konklusif, periksa sendiri: {e}")
        print("  bisa menulis      : tidak (ditolak, seperti seharusnya)")

    print(f"""
Kirim ini ke Rashad — sandinya sampaikan lewat jalur terpisah, jangan satu pesan:

  Host     : {bagian.hostname}
  Port     : {bagian.port}
  Database : {basis}
  User     : {NAMA}
  Sandi    : (yang kamu ketik barusan)
  SSL      : require

  psql "postgresql://{NAMA}:SANDI@{bagian.hostname}:{bagian.port}/{basis}?sslmode=require"

Selesai sidang, cabut lagi:  python3 beri_akses_rashad.py --cabut
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nDibatalkan.")
