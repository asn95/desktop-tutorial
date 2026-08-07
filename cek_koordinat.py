#!/usr/bin/env python3
"""Periksa sebaran koordinat hasil geocoding per periode di produksi.

Tujuannya mendeteksi dua hal yang tidak terlihat dari tabel: target yang gagal
di-geocode, dan alamat berbeda yang menumpuk di satu titik yang sama — tanda
Nominatim jatuh ke fallback nama area, bukan menemukan jalannya.
"""
import subprocess
import sys
from collections import Counter

from sqlalchemy import create_engine, text


def url():
    out = subprocess.run(["railway", "variables", "--service", "Postgres", "--kv"],
                         capture_output=True, text=True, timeout=90).stdout
    for b in out.splitlines():
        if b.startswith("DATABASE_PUBLIC_URL="):
            return b.split("=", 1)[1].strip().replace("postgres://", "postgresql://", 1)
    sys.exit("DATABASE_PUBLIC_URL tidak ada.")


eng = create_engine(url(), connect_args={"sslmode": "require", "connect_timeout": 60})
with eng.connect() as c:
    rows = c.execute(text(
        "select period, address, latitude, longitude from targets order by period, address"
    )).all()

for p in sorted({r[0] for r in rows}):
    sub = [r for r in rows if r[0] == p]
    kosong = [r for r in sub if r[2] is None]
    titik = Counter((round(r[2], 4), round(r[3], 4)) for r in sub if r[2] is not None)
    print(f"\n=== periode {p} — {len(sub)} target, {len(kosong)} tanpa koordinat, "
          f"{len(titik)} titik unik ===")
    for (la, lo), n in titik.most_common(6):
        contoh = next(r[1] for r in sub if r[2] is not None
                      and round(r[2], 4) == la and round(r[3], 4) == lo)
        tanda = "  <-- MENUMPUK" if n > 3 else ""
        print(f"  {la:>9.4f}, {lo:>9.4f}  {n:>3} target   {contoh[:44]}{tanda}")
    for r in kosong[:3]:
        print(f"  (tanpa koordinat) {r[1][:60]}")
