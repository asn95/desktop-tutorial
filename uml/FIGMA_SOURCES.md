# Sumber diagram UML — Figma

Sejak revisi mayor Agustus 2026, seluruh diagram di `uml/images/` **dirancang di
Figma (FigJam)**, bukan digambar oleh skrip PIL. `generate_diagrams.py` sudah tidak
lagi menghasilkan diagram-diagram ini; jangan menjalankannya untuk memperbaruinya,
karena hasilnya akan menimpa ekspor Figma dengan gambar PIL versi lama.

| Berkas | Board Figma |
|---|---|
| `01_system_architecture.png` | https://www.figma.com/board/DsJ5A6mMCClPa7BwaLc7SC |
| `04_component_diagram.png`   | https://www.figma.com/board/3TyZaP03EeNMlCr02jGq69 |
| `05_sequence_diagram.png`    | https://www.figma.com/board/2UydRoLKcxsAQn4qcdLGB4 |
| `07_usecase_diagram.png`     | https://www.figma.com/board/KKDL2BOEQBacJ7K5Dg9ay3 |
| `08_activity_diagram.png`    | https://www.figma.com/board/wNd03DkWGvah1oam78GNpw |
| `09_erd_diagram.png`         | https://www.figma.com/board/2rrXo0SH1dqTMov0PUvq4F |
| `10_dfd_level0.png`          | https://www.figma.com/board/fOy4kijezSJ6js15Tu9t9z |

## Koreksi fakta yang ikut dikerjakan

Pemindahan ini bukan sekadar ganti alat gambar. Versi lama memuat beberapa
pernyataan yang tidak sesuai sistem sebenarnya:

- **Supabase.** Diagram arsitektur, komponen, dan DFD menyebut Supabase PostgreSQL
  dan Supabase Storage. Produksi memakai PostgreSQL terkelola di Railway, dan foto
  bukti disimpan di filesystem kontainer API (`backend/uploads`, disajikan lewat
  `/api/uploads`). Supabase tidak pernah dipakai.
- **Tabel `upload_batches` tidak ada.** ERD lama menampilkannya sebagai entitas
  dengan PK dan FK. Tidak ada tabel itu di `models.py`. ERD lama juga hanya
  menampilkan empat tabel; yang sebenarnya ada enam — `users`, `targets`,
  `reports`, `comments`, `audit_logs`, `notification_logs`.
- **Endpoint laporan.** Sequence lama menulis `POST /api/reports`. Endpoint yang
  ada adalah `POST /api/officer/report` (multipart, diautentikasi HMAC initData).
- **Peran Administrator belum ada** di use case, DFD, dan activity — peran ketiga
  ini baru dipisah dari manajer pada revisi mayor.

## Catatan bentuk

**Activity.** Alurnya linear empat belas langkah, jadi keluaran Figma-nya 1100x7347
(rasio 1:6,7) — mustahil muat di halaman potret tanpa mengecilkan teks sampai tak
terbaca. `08_activity_diagram.png` yang tersimpan di sini adalah versi **tiga kolom**
(3548x2710, rasio 1,31): gambar tinggi itu dipotong di celah antar-simpul terdekat
dengan sepertiga dan dua-pertiga tinggi, lalu disusun bersebelahan dengan pemisah
dan judul kolom. Titik potong WAJIB di celah — memotong di tengah kotak memenggal
teksnya. Group Report memakai varian **dua kolom** karena slot gambar di sana
berasio tegak (0,71); tiga kolom yang melebar akan terlalu banyak bermargin di situ.

**Judul lapisan.** Subgraph Mermaid ter-render sebagai pita bergaris tanpa judul —
nama lapisannya hanya ada sebagai id grup di dalam SVG dan tidak pernah digambar.
Judul "Client Tier", "Application Tier", dan seterusnya disisipkan sebagai elemen
`<text>` ke dalam SVG lalu di-render ulang, bukan dicap ke PNG, supaya tetap tajam.

## Sinkron dengan kode

Diagram dan dokumen ikut diperbarui setiap kali skema atau permukaan API berubah.
Terakhir (10 Agu 2026): `reports` mendapat `officer_lat`, `officer_lon`, dan
`distance_m` untuk verifikasi lokasi kunjungan, dan jumlah endpoint router naik
25 → 28. ERD, Table 3.1, Table 4.1, serta listing kode di lampiran laporan Rashad
dan Auza sudah disesuaikan.

Board ERD lama (`bmJL8pkuyCv9hcjSLzNS0U`) sudah usang — pakai yang tercantum di
tabel di atas.

## Yang masih perlu dikerjakan

- **Dua pasang label bertumpuk di diagram arsitektur**: "HTTPS + JWT" menimpa
  "HTTPS + initData HMAC", dan "SQL" menimpa "writes photos". Labelnya tidak bisa
  digeser dari SVG karena satu grup dengan garis konektornya — geser labelnya,
  garisnya ikut pindah. Perbaikannya di Figma: perpendek teks label atau geser
  simpulnya. Tertunda karena kuota panggilan Figma MCP paket Starter habis.
- **Teks badan Group Report masih menyebut Supabase** ("Supabase Auth for admin",
  "photo upload to object storage") di bagian Level 1 - Major Processes. Gambarnya
  sudah diganti, teksnya belum — menyunting teks di dalam PDF berisiko merusak
  penyematan font. Perlu dokumen sumbernya (Google Docs/Word), yang tidak ada di
  folder SUBMISSION.

## Cara memperbarui

Buka board-nya di Figma, ubah, lalu ekspor PNG dan timpa berkas di `uml/images/`.
Diagram di FigJam dibuat lewat Figma MCP (`generate_diagram` untuk kerangka
Mermaid, `use_figma` untuk penataan manual).
