# TRIRARA TUNGGAL PUTRA — Sistem Pelaporan Alat Berat (dulu EXCAVA.OPS)

## Problem Statement
Aplikasi sistem pelaporan untuk alat berat excavator. Fields: unit excavator, nomor lambung, serial number, hour meter awal/akhir, jumlah cars baru, tanggal cars, gaji operator, kasbon operator, nota penggantian sparepart, tanggal penggantian sparepart, total biaya penggantian sparepart per unit.

## User Choices
- Login: Google (Emergent Auth)
- Multi-role: Admin & Operator
- Reports: Dashboard + charts + tables + PDF/Excel export
- Auto calculations: total jam, gaji bersih, total sparepart per unit
- Theme: Industrial yellow/black (deep obsidian + safety yellow)

## Personas
- **Admin (owner: shanchidean@gmail.com)**: Full CRUD across units, ops, payroll, sparepart. Manages operator roles.
- **Operator**: Submits own operation reports. Views own payroll & ops only.

## Architecture
- Backend: FastAPI + Motor + MongoDB. Session-based auth via Emergent Google OAuth (httpOnly cookie).
- Frontend: React 19 + React Router + Shadcn UI + Recharts + Phosphor Icons + jsPDF + xlsx.
- Fonts: Chivo (heading), IBM Plex Sans/Mono (body).

## Implemented (2026-02)
- Emergent Google OAuth (login, callback, /auth/me, logout)
- Role-based routing & RBAC on backend endpoints
- Unit Registry CRUD (admin only)
- Operations Report (all roles; operator sees own)
- Payroll CRUD (admin only; operator views own)
- Sparepart CRUD + per-unit cost aggregation
- Dashboard with 4 stat cards, daily trend line chart, cost per unit bar chart, fleet summary table
- Export to PDF + Excel across every table
- Users/roles management (admin only)
- Industrial yellow/black theme, grid-bg, sharp corners, Phosphor icons, sonner toasts

## Update (2025-07)
- Nota Sparepart multi-item (nama, qty, harga satuan, total/item + total nota) + kolom HM service (info servis kelipatan 250 jam)
- Semua nilai keuangan format Rupiah (live CurrencyInput di common.jsx)
- Payroll per-jam: pilih unit, jam kerja auto dari Ops (HM akhir-awal), jam dibayar & sisa jam belum dibayar (GET /api/payroll/hours), tarif/jam → gaji = jam dibayar × tarif; 1 payroll = 1 unit
- Halaman Laporan per Unit (GET /api/reports/units) + download per unit & semua (PDF + Excel multi-sheet)
- Filter periode (bulan) di Laporan; Nomor laporan otomatis LP/TTP/{seq}/{romawi}/{tahun} (POST /api/reports/number, counter app_counters mulai 200)
- Arsip Nomor Laporan: setiap nomor terbit disimpan (db.report_archive) & bisa ditelusuri via GET /api/reports/archive + dialog "Arsip Nomor" di halaman Laporan
- Semua PDF memakai kop surat TRIRARA TUNGGAL PUTRA (portrait A4, header+footer tiap halaman) via src/lib/letterhead.js + exporters.js

## Update (2026-10) — Rebrand + Format Laporan Hour Meter
- Rebrand: EXCAVA.OPS -> TRIRARA TUNGGAL PUTRA; logo (mark transparan src/assets/logo-mark.png, logo penuh logo-full.jpg), favicon, title
- Tema gelap navy (#0B1E2D/#022D42) + kuning (#FEC202) + merah (#EF3B2D); shadcn accent hover -> secondary
- Data perusahaan permanen: src/lib/company.js (CV. TRIRARA TUNGGAL PUTRA)
- Unit: + merek_type, pemilik_alat, nama_proyek, lokasi_proyek, pengawas_lapangan
- Ops: + keterangan, downtime_jam, solar_liter, catatan_operator, kondisi_alat{mesin,sistem_hidrolik,ban_track,lampu,rem,kelistrikan:{status baik|tidak, keterangan}}; PATCH /api/operations/{id} (edit)
- Report extras per unit+periode: GET/PUT /api/reports/extras (pengembalian_jam, lain_lain, keterangan_tambahan) -> db.report_extras
- /api/reports/units menambah: data proyek/alat, total_downtime, total_solar, hari_operasional, kondisi_alat (terbaru), catatan_operator, extras
- Engine laporan src/lib/hourMeter.js: Form Hour Meter (sesuai Hour Meter.docx) -> PDF (jsPDF), Excel (exceljs), Word (docx), per unit & semua unit, kop surat dari template docx (src/lib/letterhead.js), TTD Operator/Pengawas/Pimpinan

## Backlog (P1)
- Photo attachment on nota sparepart
- Filter/search on tables
- Monthly aggregated payslip PDF per operator
- Fuel consumption tracking

## Update — Phase 2 (Keuangan & Rekap Bulanan Excavator) — COMPLETED
- Menu "Keuangan" (admin only, /finance): Dashboard arus kas, Kas Masuk (KM-TTP-xxx), Kas Keluar (BK-TTP-xxx dari nota sparepart otomatis, KK-TTP-xxx dari payroll otomatis / manual), Invoice (INV/TTP/xxx/romawi/tahun), Surat Masuk, Surat Keluar (SP/TTP/201.../romawi/tahun), Rekap Bulanan; export Excel & PDF per tab.
- Laporan: tab "Rekap Bulanan Excavator" (12 kolom sesuai form PDF) + export PDF A3 / Excel / Word.
- Tested: iteration_3 (100%).

## Update — Rekap Penghasilan per Pengurus — COMPLETED
- Tarif Sewa per Jam di Unit (prioritas) & Pengurus (default).
- Halaman Pengurus (admin): rekap per pengurus × bulan — Jam, Pendapatan (HM × tarif), Gaji Operator, Sparepart, Penghasilan Bersih; export PDF/Excel berkop.

## Update — Integrasi WhatsApp + AI (Kotak Masuk WA) — COMPLETED (WhatsApp belum terhubung)
- Menu "Kotak Masuk WA" (admin): upload / pesan WA berisi foto bukti transfer atau layar HM -> AI Gemini (gemini-3-flash-preview, Emergent LLM Key) membaca -> cocokkan keterangan (mis. "Sdlg 10") ke unit via nomor lambung / nama / Kode WhatsApp unit -> verifikasi admin -> Kas Masuk (KM-TTP, pengurus, no_ref anti-duplikat) atau Ops Report (HM).
- Kontak WA (nomor operator/pengurus -> unit default / pengurus), tab Koneksi WhatsApp (status + webhook URL + langkah Meta).
- Webhook /api/whatsapp/webhook siap (Meta Cloud API, verifikasi HMAC) — aktif setelah env WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_APP_SECRET, WHATSAPP_VERIFY_TOKEN diisi & app di-deploy.
- Rekap Pengurus: + Transfer Diterima & Piutang.

## Phase 7 — Setujui Otomatis & Ringkasan Harian WA (COMPLETED, iteration_6 100%)
- Auto-approve >= 90% confidence + cek unit, no_ref duplikat, peringatan; audit log lengkap
- Ringkasan harian 20:00 WITA per pengurus: HM per unit, transfer hari ini, total diterima, piutang berjalan bulan ini, verifikasi tertunda
- Pengiriman WA DISIMULASIKAN sampai kredensial Meta diisi (pasca-deploy)

## Phase 8 — WA Cloud API production hardening (COMPLETED, iteration_7)
- wa_outbox.py: semua pesan keluar via outbox (dedupe_key unik, retry aman 429/5xx/koneksi, timeout=tidak pasti tanpa auto-retry, redaksi token, status delivered/read/failed dari webhook)
- Status koneksi bertingkat; "Terhubung · Terverifikasi" hanya setelah pesan masuk asli + pesan keluar delivered
- Endpoint: /api/wa/connection, /api/wa/cloud/{check,send-test,register,subscribe}, /api/wa/outbox(+retry), cron /api/cron/wa-outbox-retry (*/30)
- UI: tab Koneksi WhatsApp (checklist, alat uji, panduan 8 langkah), tab Pesan Keluar; halaman publik /kebijakan-privasi
- Panduan: /app/memory/PANDUAN_WHATSAPP.md. User: Business Portfolio belum ada; nomor masih aktif di app WA (harus dihapus akun / nomor baru); nomor pemilik 6282343070023

## Update — Bonus Admin per 300 Jam (2026-10)
- Menu "Bonus Admin" (/bonus-admin, admin only): tiap unit mencapai kelipatan 300 jam kerja (total_jam Ops Report) → bonus Rp500.000 ke admin unit; sisa jam dibawa ke bonus berikutnya.
- Backend backend/bonus.py: GET /api/bonus-admin?year=, GET/PUT /api/bonus-admin/settings (enabled, jam_per_bonus, nominal, default_admin, start_date, unit_admins), POST /api/bonus-admin/pay (→ Kas Keluar KK-TTP otomatis, source=bonus_admin), DELETE /api/bonus-admin/pay/{id} (hapus KK), GET /api/bonus-admin/history (audit). Unique index cegah bayar ganda.
- UI: stat cards, progress bar ke bonus berikutnya, filter (Belum Dibayar / Hampir Tercapai), rincian per kelipatan + Tandai Dibayar / Batalkan, Pengaturan, Riwayat, export PDF berkop & Excel.

## Update — Migrasi Database MongoDB → MariaDB (2026-10)
- User choices: MariaDB di Coolify (service compose), migrasi data lama, tabel relasional penuh (kolom per field), deploy hanya Coolify, backup tetap JSON.
- backend/db_schema.py: 28 tabel (kolom bertipe: VARCHAR/DATE/DOUBLE/BIGINT/BOOLEAN/JSON/LONGBLOB, unique & index). Kolom `_extra` JSON = penampung field baru/nilai tak cocok tipe (tanpa kehilangan data). Kolom baru otomatis ALTER TABLE + backfill.
- backend/mariadb_store.py: lapisan akses data async (SQLAlchemy 2 + asyncmy). API find/find_one/insert/update/upsert/find_one_and_update/delete/count/distinct; filter → WHERE SQL + verifikasi Python; update dalam transaksi SELECT…FOR UPDATE (READ COMMITTED) → penomoran bukti & lock cron atomik; DuplicateKeyError; None vs field-tidak-ada dipertahankan.
- tests/test_store_parity.py: 27 uji paritas Mongo vs MariaDB (termasuk 40 increment paralel & 20 lock paralel) — LULUS. Test suite lama: hasil identik dengan baseline Mongo.
- Migrasi: backend/scripts/migrate_mongo_to_mariadb.py (CLI, merge/replace/dry-run, verifikasi jumlah) + otomatis saat startup bila MIGRATE_FROM_MONGO_URL & MIGRATE_FROM_MONGO_DB di-set (dijalankan sebelum bootstrap admin/backfill; status di app_settings 'mongo_migration' + panel Backup).
- backup_db.py / restore_db.py (backend/scripts, wrapper di /app/scripts) memakai MariaDB; format trirara-backup-v1 (backup lama Mongo bisa direstore).
- docker-compose(.singledomain).yml: service mariadb:11.4 (volume mariadb_data) + mongo lama (volume mongo_data, hanya sumber migrasi). mariadb/docker-compose.yml standalone. DEPLOY_COOLIFY.md ditulis ulang.
- requirements.txt: + SQLAlchemy[asyncio], asyncmy, greenlet, Pillow (bug lama: PIL di-import tanpa terdaftar); − motor. pymongo tetap (bson + migrasi).
- Preview Emergent: MariaDB lokal via scripts/preview_mariadb.sh (data di /app/.mariadb_data), auto-start oleh backend bila PREVIEW_MARIADB_AUTOSTART=1.
