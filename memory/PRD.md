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
