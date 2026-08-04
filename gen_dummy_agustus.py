#!/usr/bin/env python3
"""Batch target Agustus 2026 — Banda Aceh dan sekitarnya (Aceh Besar).

SETIAP alamat di sini sudah diuji ke Nominatim dan terbukti menghasilkan koordinat
tingkat jalan (koordinat hasil uji dicantumkan sebagai komentar). Ini penting karena:
  1. peta di dashboard butuh koordinat berbeda-beda, bukan pin menumpuk;
  2. komponen klaster 3 km di skor prioritas butuh jarak antar target yang nyata;
  3. extract_area() memakai segmen setelah koma TERAKHIR, jadi kecamatan ditaruh
     di posisi itu supaya filter area pada auto-assign benar-benar berguna.

Nomor rumah SENGAJA tidak dipakai: OSM tidak punya data nomor rumah di Aceh, dan
uji menunjukkan keberhasilan geocoding turun dari 8/8 menjadi 4/8 begitu nomor
rumah ditambahkan. Kalau nomor rumah wajib ada, konsekuensinya alamat jatuh ke
fallback area dan semua target satu kecamatan berbagi satu titik yang sama.

Deterministik lewat seed tetap, jadi hasilnya bisa diulang persis.
"""
import csv, random

random.seed(20260807)

# (alamat, kecamatan) — koordinat = hasil uji Nominatim 1 Agustus 2026
LOKASI = [
    # --- Kota Banda Aceh ---
    ("Jl. Teuku Umar, Baiturrahman",           "Banda Aceh"),  # 5.54692, 95.31676
    ("Jl. Diponegoro, Baiturrahman",           "Banda Aceh"),  # 5.55530, 95.31659
    ("Jl. Hasan Dek, Kuta Alam",               "Banda Aceh"),  # 5.55609, 95.33041
    ("Jl. Teuku Nyak Makam, Kuta Alam",        "Banda Aceh"),  # 5.56166, 95.34369
    ("Jl. Sri Ratu Safiatuddin, Kuta Alam",    "Banda Aceh"),  # 5.55689, 95.32036
    ("Jl. Pocut Baren, Kuta Alam",             "Banda Aceh"),  # 5.56156, 95.31999
    ("Jl. T. Nyak Arief, Syiah Kuala",         "Banda Aceh"),  # 5.57136, 95.37221
    ("Jl. Syiah Kuala, Syiah Kuala",           "Banda Aceh"),  # 5.57374, 95.36761
    ("Jl. Lamreung, Ulee Kareng",              "Banda Aceh"),  # 5.55524, 95.35937
    ("Jl. Lamlagang, Banda Raya",              "Banda Aceh"),  # 5.53556, 95.31306
    ("Jl. Sultan Malikussaleh, Banda Raya",    "Banda Aceh"),  # 5.54079, 95.31599
    ("Jl. Cut Nyak Dhien, Jaya Baru",          "Banda Aceh"),  # 5.52779, 95.29186
    ("Jl. Lamteumen Timur, Jaya Baru",         "Banda Aceh"),  # 5.53857, 95.30322
    ("Jl. Sultan Iskandar Muda, Meuraxa",      "Banda Aceh"),  # 5.55191, 95.30258
    ("Jl. Rama Setia, Kuta Raja",              "Banda Aceh"),  # 5.55787, 95.31185
    # --- Aceh Besar (sekitarnya) ---
    ("Jl. Lambaro, Ingin Jaya",                "Aceh Besar"),  # 5.50897, 95.35711
    ("Jl. Mata Ie, Darul Imarah",              "Aceh Besar"),  # 5.51779, 95.30345
    ("Jl. Krueng Raya, Mesjid Raya",           "Aceh Besar"),  # 5.55889, 95.53661
    ("Jl. Blang Bintang, Blang Bintang",       "Aceh Besar"),  # 5.50315, 95.45194
]

DEPAN_PRIA = ["Teuku", "Muhammad", "Zulfikar", "Fauzan", "Rahmat", "Munawar", "Syahrul",
              "Ridwan", "Iskandar", "Hendra", "Bustami", "Mahdi", "Zainal", "Nasruddin",
              "Saifullah", "Marzuki", "Yusran", "Khairul", "Fadhil", "Reza", "Arif",
              "Irwansyah", "Dedi", "Aulia", "Rizki", "Taufik", "Junaidi", "Sofyan"]
BELAKANG_PRIA = ["Rahman", "Hidayat", "Maulana", "Iqbal", "Abidin", "Syah", "Putra",
                 "Ramadhan", "Fadli", "Akbar", "Nugraha", "Alfata", "Ismail", "Yusuf"]
DEPAN_WANITA = ["Cut", "Nurul", "Rahmawati", "Siti", "Marlina", "Yulia", "Dewi",
                "Nurhayati", "Fitriani", "Zahara", "Maulida", "Rosmawar", "Nova",
                "Elly", "Herlina", "Safrida", "Rita", "Nanda", "Intan", "Putri"]
BELAKANG_WANITA = ["Fajri", "Aisyah", "Meutia", "Sari", "Yanti", "Suryani", "Sartika",
                   "Zahra", "Lestari", "Anggraini", "Wati", "Ulfa", "Rahmi", "Keumala"]

# Prefiks Telkomsel — kliennya IndiHome by Telkomsel, jadi ini konsisten
PREFIKS = ["0811", "0812", "0813", "0821", "0822", "0823", "0851", "0852", "0853"]


def nama(dipakai):
    for _ in range(400):
        if random.random() < 0.45:
            n = f"{random.choice(DEPAN_WANITA)} {random.choice(BELAKANG_WANITA)}"
        else:
            n = f"{random.choice(DEPAN_PRIA)} {random.choice(BELAKANG_PRIA)}"
        if n not in dipakai:
            dipakai.add(n)
            return n
    raise RuntimeError("kehabisan kombinasi nama")


def telepon(dipakai):
    for _ in range(500):
        p = f"{random.choice(PREFIKS)}{random.randint(10000000, 99999999)}"
        if p not in dipakai:
            dipakai.add(p)
            return p
    raise RuntimeError("kehabisan nomor")


def tunggakan():
    """Tagihan IndiHome ±300rb/bulan. Sebagian besar nunggak 1-3 bulan,
    sepertiga 4-8 bulan, sedikit yang berat. Kelipatan tagihan bulanan
    supaya angkanya terlihat seperti tunggakan, bukan angka acak."""
    r = random.random()
    if r < 0.55:
        bulan = random.randint(1, 3)
    elif r < 0.88:
        bulan = random.randint(4, 8)
    else:
        bulan = random.randint(9, 18)
    return bulan * random.choice([285000, 315000, 345000, 375000, 445000, 525000])


def bangun(n=50, hindari_nama=(), hindari_telepon=()):
    """hindari_* berisi nama/telepon yang SUDAH ada di basis data, supaya batch
    berikutnya tidak menghasilkan pelanggan ganda. Unggahan tidak memeriksa
    duplikat, jadi pencegahannya harus di sini."""
    kota = [l for l in LOKASI if l[1] == "Banda Aceh"]
    luar = [l for l in LOKASI if l[1] == "Aceh Besar"]
    n_kota = round(n * 0.75)   # mayoritas di kota, sisanya Aceh Besar

    pilihan = ([random.choice(kota) for _ in range(n_kota)] +
               [random.choice(luar) for _ in range(n - n_kota)])
    random.shuffle(pilihan)

    baris, nm, tp = [], set(hindari_nama), set(hindari_telepon)
    for alamat, _wilayah in pilihan:
        baris.append({
            "customer_name": nama(nm),
            "address": alamat,
            "phone": telepon(tp),
            "amount_due": tunggakan(),
        })
    return baris


if __name__ == "__main__":
    import argparse, json
    from collections import Counter
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("n", nargs="?", type=int, default=50)
    ap.add_argument("out", nargs="?", default="dummy_targets_agustus.csv")
    ap.add_argument("--seed", type=int, default=20260807,
                    help="ubah untuk batch berikutnya, supaya datanya bukan salinan")
    ap.add_argument("--exclude", metavar="FILE.json",
                    help='{"nama":[...], "telepon":[...]} yang sudah ada di basis data')
    a = ap.parse_args()
    n, out = a.n, a.out

    random.seed(a.seed)          # seed modul dipakai untuk batch 1; ini menimpanya
    hn = ht = ()
    if a.exclude:
        ex = json.load(open(a.exclude))
        hn, ht = ex.get("nama", []), ex.get("telepon", [])
        print(f"menghindari {len(hn)} nama dan {len(ht)} nomor yang sudah terpakai")
    rows = bangun(n, hn, ht)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["customer_name", "address", "phone", "amount_due"])
        w.writeheader()
        w.writerows(rows)

    tot = sum(r["amount_due"] for r in rows)
    area = Counter(r["address"].rsplit(",", 1)[1].strip() for r in rows)
    rupiah = lambda v: f"Rp {v:,}".replace(",", ".")
    print(f"{out}: {len(rows)} target")
    print(f"  total tunggakan {rupiah(tot)} · rata-rata {rupiah(tot // len(rows))}")
    print(f"  rentang {rupiah(min(r['amount_due'] for r in rows))} – "
          f"{rupiah(max(r['amount_due'] for r in rows))}")
    print(f"  nama unik {len({r['customer_name'] for r in rows})} · "
          f"telepon unik {len({r['phone'] for r in rows})} · "
          f"lokasi unik {len({r['address'] for r in rows})}")
    print(f"  area (hasil extract_area) — {len(area)} kelompok:")
    for a, c in area.most_common():
        print(f"     {a:<18} {c}")
