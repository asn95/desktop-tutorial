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
| `09_erd_diagram.png`         | https://www.figma.com/board/bmJL8pkuyCv9hcjSLzNS0U |
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

`08_activity_diagram.png` berukuran 1100x7347 karena alurnya linear empat belas
langkah. Lebarnya sengaja tidak dikecilkan supaya teksnya tetap terbaca saat
dicetak; kalau perlu muat satu halaman, potong di simpul keputusan
"Photo evidence attached?" dan sajikan sebagai dua gambar.

## Cara memperbarui

Buka board-nya di Figma, ubah, lalu ekspor PNG dan timpa berkas di `uml/images/`.
Diagram di FigJam dibuat lewat Figma MCP (`generate_diagram` untuk kerangka
Mermaid, `use_figma` untuk penataan manual).
