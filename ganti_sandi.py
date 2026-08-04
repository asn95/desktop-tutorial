#!/usr/bin/env python3
"""Ganti kata sandi manajer C3MR di produksi.

Jalankan:  python3 ganti_sandi.py

Kata sandi diketik langsung ke skrip ini dan tidak ditampilkan di layar.
Skrip memakai endpoint resmi /api/auth/change-password, jadi perilakunya persis
sama dengan menekan tombol "Ubah Kata Sandi" di portal — termasuk stempel
password_changed_at yang mengakhiri semua sesi lama di semua perangkat.
"""
import getpass
import json
import sys
import urllib.error
import urllib.request

API = "https://c3mr-app-production-b353.up.railway.app/api"


def panggil(path, body, token=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"detail": f"Tidak bisa menghubungi server: {e}"}


def main():
    print("\nGanti kata sandi manajer C3MR")
    print("Server:", API.replace("/api", ""))
    print("Ketikan kata sandi tidak akan terlihat di layar — itu normal.\n")

    user = input("Nama pengguna [admin]: ").strip() or "admin"
    lama = getpass.getpass("Kata sandi SEKARANG : ")
    if not lama:
        sys.exit("Dibatalkan: kata sandi lama kosong.")

    baru = getpass.getpass("Kata sandi BARU     : ")
    ulang = getpass.getpass("Ketik ulang yang BARU: ")
    if baru != ulang:
        sys.exit("Dibatalkan: dua kata sandi baru tidak sama.")
    if len(baru) < 6:
        sys.exit("Dibatalkan: server menolak kata sandi di bawah 6 karakter.")
    if len(baru) < 12:
        print(f"\n  Catatan: {len(baru)} karakter. Sistem menerimanya, tapi portal ini "
              "terbuka di internet — makin panjang makin baik.")
        if input("  Lanjutkan? [y/N]: ").strip().lower() != "y":
            sys.exit("Dibatalkan.")

    print("\n1/3  Memverifikasi kata sandi lama…")
    st, d = panggil("/auth/login", {"username": user, "password": lama})
    if st != 200 or not isinstance(d, dict) or not d.get("token"):
        sys.exit(f"  GAGAL ({st}): {d.get('detail', d)}\n"
                 "  Kata sandi lama salah, atau akun terkunci sementara "
                 "(5 percobaan gagal per 60 detik). Tunggu satu menit lalu ulangi.")
    token = d["token"]
    print(f"  OK — masuk sebagai {d.get('name')} ({d.get('role')})")

    print("2/3  Mengganti kata sandi…")
    st, d = panggil("/auth/change-password",
                    {"current_password": lama, "new_password": baru}, token)
    if st != 200:
        sys.exit(f"  GAGAL ({st}): {d.get('detail', d)}")
    print(f"  OK — {d.get('message', 'kata sandi diubah')}")

    print("3/3  Menguji kata sandi baru…")
    st, d = panggil("/auth/login", {"username": user, "password": baru})
    if st != 200:
        sys.exit(f"  PERINGATAN ({st}): kata sandi sudah diganti tapi login uji gagal: "
                 f"{d.get('detail', d)}")
    print("  OK — kata sandi baru berhasil dipakai login.\n")

    print("Selesai. Semua sesi lama di semua perangkat sudah berakhir,")
    print("jadi browser yang masih terbuka akan diminta login ulang.")
    print("Simpan kata sandi barunya sekarang, dan beri tahu Rashad.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nDibatalkan.")
