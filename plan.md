# plan.md — TRIRARA TUNGGAL PUTRA Ops System (Tema + Hour Meter Report)

## 1) Objectives
- Ubah identitas aplikasi: **EXCAVA.OPS → TRIRARA TUNGGAL PUTRA** + gunakan **Logo.jpg**.
- Retheme ke **dark navy** dengan aksen **kuning + merah** (selaras logo & kop surat).
- Tambahkan field yang dibutuhkan format **Hour Meter.docx** ke sistem (Unit & Ops Report) agar laporan terisi otomatis.
- Buat eksport laporan **Hour Meter** dengan **layout sama** untuk **PDF + Excel + Word**.
- Pastikan fitur existing (Dashboard, Units, Ops, Payroll, Sparepart, Laporan/nomor LP/TTP + arsip, Pengurus, Users) tetap berjalan.

## 2) Implementation Steps

### Phase 1 — Core POC (isolated) “Hour Meter Export Engine”
**Core workflow (paling riskan):** generate **PDF/Excel/Word** dengan layout mendekati docx (kop + tabel) dari 1 payload report.

**User stories (POC)**
1. Sebagai admin, saya bisa menghasilkan **PDF Hour Meter** berkop TRIRARA yang rapi dan konsisten.
2. Sebagai admin, saya bisa menghasilkan **Excel Hour Meter** dengan susunan section yang sama.
3. Sebagai admin, saya bisa menghasilkan **Word Hour Meter** yang bisa diedit bila perlu.
4. Sebagai admin, saya bisa menguji export dengan data dummy tanpa mengubah data produksi.
5. Sebagai admin, saya mendapat error message yang jelas jika export gagal.

**Steps**
- Web research singkat: best practice **docx generation** (library `docx`) dan **Excel styling** (`exceljs`) untuk layout form.
- Tambah dependencies frontend: `exceljs`, `docx`, `file-saver`.
- Buat **POC page/dev route** (sementara) yang:
  - memakai payload contoh (hardcoded JSON) yang mencakup semua section docx.
  - menghasilkan:
    - PDF via jsPDF + autoTable + existing letterhead (re-use header/footer images).
    - Excel via exceljs (worksheet dengan blok section + borders).
    - Word via docx (tables + borders).
- Checklist POC acceptance:
  - kop surat tampil benar;
  - struktur section sesuai urutan docx;
  - tabel rekap bulanan dan sparepart bisa memuat banyak baris;
  - file berhasil terunduh dan terbuka tanpa korup.

### Phase 2 — V1 App Development (tema + data model + laporan Hour Meter nyata)

**User stories (V1)**
1. Sebagai user, saya melihat branding **TRIRARA TUNGGAL PUTRA + logo** di login dan sidebar.
2. Sebagai admin, saya dapat mengisi **data proyek & data alat** pada Unit agar dipakai di laporan.
3. Sebagai operator/admin, saya dapat mengisi field tambahan di **Ops Report** (keterangan harian, downtime, solar, kondisi alat, catatan).
4. Sebagai admin, saya dapat mengekspor **Hour Meter** per unit/periode dalam PDF/Excel/Word dengan nomor LP/TTP otomatis.
5. Sebagai admin, saya dapat mengekspor **rekap semua unit** tetap seperti saat ini (tidak rusak oleh perubahan).

**Backend (FastAPI + Mongo)**
- Update model + CRUD:
  - `Unit`: tambah `nama_proyek`, `lokasi_proyek`, `pengawas_lapangan`, `merek_type`, `pemilik_alat`.
  - `Operation`: tambah `keterangan_harian`, `downtime_jam`, `pemakaian_solar_liter`, `catatan_operator`.
  - `Operation`: tambah `kondisi_alat` object:
    - items: `mesin`, `sistem_hidrolik`, `ban_track`, `lampu`, `rem`, `kelistrikan` (masing-masing: baik:boolean, keterangan:string).
- Tambah endpoint report “Hour Meter format”:
  - `GET /api/reports/hour-meter?unit_id=...&periode=YYYY-MM` mengembalikan payload lengkap untuk export (gabung unit+ops+payroll+spareparts, plus computed totals).
  - Sertakan: rekap bulanan rows (ops list), total pemakaian jam alat (total HM, hari operasional, downtime total, solar total), detail sparepart items, total biaya (sparepart + gaji + kasbon/komponen lain jika diperlukan).
- Pastikan filter `periode` konsisten (ops: tanggal startswith, spareparts: tanggal startswith, payroll: periode==).

**Frontend (React)**
- Branding/tema:
  - Ganti nama di `AppShell` & `Login` jadi **TRIRARA TUNGGAL PUTRA**.
  - Pakai **Logo.jpg** (simpan di `src/assets/logo.jpg` atau `public/logo.jpg`) + update favicon/title.
  - Sesuaikan warna chart/accents: navy background + primary yellow + accent red (tetap mengikuti design_guidelines).
- Forms:
  - UnitsPage: tambah input untuk field proyek + alat (merek/type, pemilik).
  - OperationsPage: tambah input downtime, solar, keterangan harian, catatan operator, kondisi alat (6 baris baik/tidak + keterangan).
- Reports:
  - Tambah tombol export **Hour Meter (PDF/Excel/Word)** per unit (menggunakan payload dari endpoint baru).
  - Nomor laporan: re-use `POST /api/reports/number` (jenis=unit/semua) dan simpan nomor ke metadata export.
- Export engine (promote from POC):
  - PDF: buat `exportHourMeterPDF(payload, meta)`.
  - Excel: `exportHourMeterExcel(payload, meta)` (exceljs styled, borders, column widths).
  - Word: `exportHourMeterDocx(payload, meta)` (docx tables).

**Testing (end of Phase 2)**
- Run backend tests + add new tests:
  - create unit with new fields; create ops with new fields; fetch hour-meter payload.
- E2E smoke:
  - login, create unit+ops, export 3 formats, open file validity (basic size/non-empty checks).

### Phase 3 — Hardening + parity with docx + regression

**User stories (Hardening)**
1. Sebagai admin, hasil export konsisten di berbagai jumlah baris (sedikit/banyak).
2. Sebagai admin, border & spacing tabel rapi (tidak “lompat halaman” di PDF).
3. Sebagai admin, Excel mudah di-print (page setup, scaling).
4. Sebagai admin, Word dapat diedit tanpa merusak tabel.
5. Sebagai admin, semua halaman lama (Payroll/Sparepart/Dashboard) tetap berfungsi.

**Tasks**
- PDF parity:
  - Tambahkan section “Petunjuk Pengisian” dan pastikan multi-page header/footer selalu muncul.
  - Pastikan table “Rekap Bulanan” bisa otomatis split halaman.
- Excel parity:
  - Formatting: merged cells untuk judul section, header row bold, borders, print area.
- Word parity:
  - Table widths, borders, heading style, bullet list.
- Regression:
  - Validasi endpoints lama tetap compatible.
  - Update exporter existing bila terdampak perubahan meta/nomor.

## STATUS (2026-10)
- Phase 1 (engine PDF/Excel/Word) — DONE, diverifikasi render via LibreOffice/pdftoppm
- Phase 2 (rebrand, tema navy, field baru Unit & Ops, PATCH ops, extras laporan, export Hour Meter per unit & semua unit) — DONE, testing_agent iteration_2: 100% pass
- Phase 3 hardening: smart padding baris kosong PDF, nomor halaman — DONE

## 3) Next Actions (lama)
1. Implement Phase 1 POC: add deps (`exceljs`, `docx`, `file-saver`) + build export functions for 1 dummy payload.
2. Review POC output: PDF/Excel/Word layout vs Hour Meter.docx (iterate until acceptable).
3. Implement backend schema updates + new report endpoint.
4. Update Units/Ops UI forms to capture new fields.
5. Integrate export buttons in Reports per Unit using real payload + nomor LP/TTP.

## 4) Success Criteria
- App UI berbranding **TRIRARA TUNGGAL PUTRA** + logo, dark navy theme konsisten.
- Data tambahan dapat disimpan & dibaca kembali (Unit & Ops) tanpa breaking changes.
- Export **Hour Meter** berhasil untuk **PDF + Excel + Word** dengan struktur section sesuai docx.
- Nomor laporan LP/TTP otomatis tercantum pada export dan arsip nomor tetap berjalan.
- Semua halaman existing lulus smoke test (CRUD + export lama + dashboard).
---
## Phase 4 — Keuangan & Rekap Bulanan Excavator (Status: COMPLETED)
User choices: (a) Keuangan dulu, (b) Rekap Bulanan di halaman Laporan (tab), (c) Surat Keluar dibuat sekarang.
- [x] Route `/finance` (admin only) + menu sidebar "Keuangan"
- [x] FinancePage: Dashboard, Kas Masuk (KM-TTP-xxx), Kas Keluar (BK/KK-TTP-xxx, auto dari Sparepart & Payroll), Invoice (INV/TTP/xxx/romawi/tahun), Surat Masuk, Surat Keluar (SP/TTP/xxx/romawi/tahun mulai 201), Rekap Bulanan + export Excel/PDF
- [x] Edit tanggal Surat Keluar/Invoice -> bulan romawi & tahun nomor ikut diperbarui (urut tetap)
- [x] Laporan: tab "Rekap Bulanan Excavator" (tabel 12 kolom sesuai form PDF) + export PDF A3/Excel/Word
- [x] Testing agent iteration_3: backend 36/36, frontend 100%
