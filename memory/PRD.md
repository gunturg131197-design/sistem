# Excavator Operations Reporting System (EXCAVA.OPS)

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
- Semua PDF memakai kop surat TRIRARA TUNGGAL PUTRA (portrait A4, header+footer tiap halaman) via src/lib/letterhead.js + exporters.js

## Backlog (P1)
- Photo attachment on nota sparepart
- Filter/search on tables
- Monthly aggregated payslip PDF per operator
- Fuel consumption tracking
