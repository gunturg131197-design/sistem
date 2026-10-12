# plan.md — TRIRARA TUNGGAL PUTRA Ops System (Tema + Hour Meter Report)

## 1) Objectives
- Ubah identitas aplikasi: **EXCAVA.OPS → TRIRARA TUNGGAL PUTRA** + gunakan **Logo.jpg**.
- Retheme ke **dark navy** dengan aksen **kuning + merah** (selaras logo & kop surat).
- Tambahkan field yang dibutuhkan format **Hour Meter.docx** ke sistem (Unit & Ops Report) agar laporan terisi otomatis.
- Buat eksport laporan **Hour Meter** dengan **layout sama** untuk **PDF + Excel + Word**.
- Pastikan fitur existing (Dashboard, Units, Ops, Payroll, Sparepart, Laporan/nomor LP/TTP + arsip, Pengurus, Users) tetap berjalan.
- Otomasi WhatsApp (dalam mode simulasi dulu):
  - Pesan masuk (gambar bukti transfer & foto HM) dapat diuji masuk ke **Kotak Masuk WA**.
  - Balasan konfirmasi, Ringkasan Harian, Pengingat Piutang, dan Laporan Mingguan dapat diuji **tanpa mengirim pesan sungguhan**.
  - **Auto-approve** tetap: AI confidence **≥ 90%**, unit dikenali, angka jelas, **no_ref tidak duplikat**, tanpa warning; selain itu **manual**.
  - **HM janggal** (turun/lonjakan tidak wajar/tidak terbaca) **selalu masuk verifikasi manual** dan **tidak boleh auto-approve**.
  - **Audit log** lengkap untuk setiap aksi dan setiap “pengiriman” (simulasi/outbox).
- Semua otomasi berjalan di zona waktu **Asia/Makassar (WITA)**.
- Deployment harus aman dan **tidak menghapus / mereset database**.
- Integrasi WhatsApp Cloud API resmi Meta (kredensial nyata, webhook nyata, nomor nyata) **DITUNDA** sampai user memberi persetujuan eksplisit.

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

## 3) Next Actions (revisi)
**Prinsip:** pertahankan fitur/data yang stabil; tidak ada perubahan kecuali diperlukan untuk integrasi/perbaikan.

### Phase 8 — (A) WhatsApp Automation Hardening + Simulasi (TANPA integrasi Meta) — Status: COMPLETED
**Tujuan:** semua fitur otomasi WA bisa diuji aman di lingkungan simulasi, tanpa kredensial Meta.

**Yang sudah ada (teruji iteration_6 & iteration_7):**
- Inbox WA + upload manual + AI parsing (Gemini).
- Auto-approve (≥90% + unit match + no_ref unik + no warning).
- Audit log aksi inbox + summary.
- Ringkasan harian 20:00 WITA (cron → `/api/cron/daily-summary`).
- Outbox WA (`wa_outbox.py`): dedupe anti dobel kirim, retry aman untuk error sementara, status delivered/read/failed dari webhook bila tersedia.
- UI:
  - Tab Otomasi & Ringkasan (existing)
  - Tab Koneksi WhatsApp (status bertingkat + panduan) dan tab Pesan Keluar
  - Halaman publik `/kebijakan-privasi`

**Catatan penting:** integrasi Meta asli DITUNDA; semua pengiriman akan berstatus **simulated** selama kredensial tidak diisi.

### Phase 9 — Stabilitas Aplikasi + Pengujian Menyeluruh (tanpa perubahan fitur stabil) — Status: TODO
**Tujuan:** memastikan seluruh modul berjalan stabil, aman, konsisten, dan terdokumentasi, tanpa mengubah fitur yang sudah stabil kecuali perbaikan bug/keamanan.

**Scope pengujian**
- Backend:
  - Validasi input, error handling, idempotensi, timezone WITA, audit logging.
  - Keamanan: role-based access admin/operator, CORS, tidak ada kebocoran secrets, rate-limit ringan untuk endpoint publik (opsional).
  - Konsistensi data: transaksi approve WA menghasilkan record finance/ops yang benar.
- Frontend:
  - Tidak ada console error.
  - State management tab Kotak Masuk WA stabil (refresh, filter, pagination).
  - UI audit log, summary preview, outbox render stabil.
- Database:
  - Pastikan indexes penting ada (no_ref unik untuk kas masuk, dedupe_key unik outbox, dedupe inbound message id).
  - Pastikan tidak ada migration yang mereset data.

**Deliverables**
- Laporan pengujian komprehensif (backend + frontend + security) + daftar temuan dan tindakan.

### Phase 10 — (C2) Peringatan HM Janggal — Status: TODO (PRIORITAS 2)
**Tujuan:** HM mencurigakan tidak boleh lolos auto-approve.

**Rule minimum (wajib):**
- HM turun dibanding HM terakhir unit → selalu manual (auto-block).
- HM melonjak tidak wajar → selalu manual (auto-block).
- Foto/angka tidak terbaca jelas atau confidence < ambang → selalu manual.

**Backend**
- Tambah deteksi anomali HM dalam pipeline WA (sebelum auto-approve):
  - HM turun vs HM terakhir unit.
  - HM lonjakan: ambang configurable (mis. `max_hm_delta_per_day` jam/hari) + opsi tambahan berbasis rata-rata 7 hari.
  - “Tidak terbaca”: berdasarkan `warnings`/field kosong/AI confidence.
- Jika anomaly terdeteksi → `eligible=false` auto-approve + status tetap pending.
- Audit: `auto_blocked` harus menyimpan alasan anomali.
- Tambah setting di WA Automation (toggle + threshold lonjakan) default aman.

**Frontend**
- Tampilkan badge/peringatan jelas di Kotak Masuk WA (item HM) bila terdeteksi anomali.
- Panel setting untuk ambang lonjakan (on/off, max jam/hari) + tooltip.

**Testing**
- Backend unit tests: HM turun, HM lonjak, HM tidak terbaca.
- UI tests: item masuk manual queue, badge tampil.

### Phase 11 — (C3) Pengingat Piutang (Simulasi WhatsApp) — Status: TODO (PRIORITAS 3)
**Tujuan:** pengingat otomatis berdasar umur piutang & ambang nominal, bisa dikonfigurasi, tidak spam, tercatat. Semua pengiriman masih simulasi sampai Meta disetujui.

**Backend**
- Setting (admin):
  - enable/disable
  - jam kirim WITA (mis. 08:00)
  - threshold nominal
  - umur piutang minimal (hari)
  - cooldown/dedupe (mis. tidak kirim ulang sebelum N hari)
  - penerima: pengurus (default) + opsi cc pemilik
  - pesan template (teks) untuk simulasi
- Perhitungan piutang:
  - Pastikan piutang yang dihitung adalah “benar-benar belum dibayar” dari data tervalidasi.
  - Pastikan perubahan pembayaran hari ini langsung menurunkan piutang dan memblok pengingat.
- Anti spam:
  - dedupe per pengurus per hari/minggu; kirim ulang hanya jika piutang naik/melewati ambang lagi.
  - catat log pengiriman (audit + outbox simulated).
- Cron:
  - Gunakan 1 cron harian tetap (mis. tiap 10 menit atau 1 jam) yang memeriksa apakah **sudah waktunya** (WITA) untuk mengirim (menghindari penambahan cron terlalu banyak), atau gabungkan dengan cron existing bila perlu.

**Frontend**
- Halaman pengaturan pengingat piutang + preview daftar penerima yang memenuhi syarat.
- Riwayat/log pengiriman.

**Testing**
- Backend: perhitungan, dedupe, cooldown, tidak mengirim jika sudah lunas.
- UI: preview benar, toggle on/off bekerja.

### Phase 12 — (C4) Laporan Mingguan Pemilik (Simulasi WhatsApp) — Status: TODO (PRIORITAS 4)
**Tujuan:** laporan otomatis setiap Senin 08:00 WITA ke pemilik.

**Spesifikasi isi:**
- total HM per unit (mingguan)
- total pemasukan (kas masuk)
- pembayaran diterima
- piutang berjalan
- daftar transaksi masih perlu verifikasi

**Backend**
- Pengaturan:
  - enabled
  - penerima (default pemilik: **6282343070023**)
  - jam kirim (default Senin 08:00 WITA)
- Generator laporan mingguan + endpoint preview/run-now/history.
- Cron:
  - Gunakan 1 cron tetap (mis. tiap 1 jam) yang mengecek “apakah sekarang Senin 08:00 WITA” dan idempoten per minggu; atau tambahkan cron khusus jika slot cron masih tersedia.
- Audit + outbox simulated.

**Frontend**
- Pengaturan laporan mingguan + preview + history.

**Testing**
- Backend: generator, idempotensi, rentang minggu WITA (Senin–Minggu).
- UI: preview dan log.

### Phase 13 — Simulasi Pesan Masuk WhatsApp (untuk uji end-to-end tanpa Meta) — Status: TODO
**Tujuan:** seluruh alur inbound dapat diuji (termasuk dedupe, auto-reply help/ack, pemrosesan AI) tanpa webhook Meta.

**Backend**
- Endpoint admin-only `POST /api/wa/simulate/inbound` untuk memasukkan payload yang meniru webhook (teks/gambar) dan melewati pipeline yang sama.
- Pastikan:
  - tidak membutuhkan signature
  - tetap idempoten berdasarkan message_id
  - membuat record inbox dan audit sama seperti webhook asli.

**Frontend**
- Tombol “Simulasi Pesan Masuk” (opsional) di tab Koneksi WhatsApp untuk QA internal.

**Testing**
- Backend: simulasi text -> help (dedupe per hari), simulasi image -> inbox item -> process.

### Phase 14 — Dokumentasi Penggunaan + Backup/Restore DB — Status: TODO
**Tujuan:** memudahkan operasional harian dan menjaga keselamatan data.

**Dokumentasi yang disiapkan**
- Panduan pengguna:
  - alur Kotak Masuk WA (upload, verifikasi manual, auto-approve, audit)
  - alur Ringkasan Harian (preview/run-now/history)
  - alur Outbox (status, retry, arti “tidak pasti”)
  - setting otomasi (threshold confidence, HM janggal, reminder, weekly)
- Backup & pemulihan database:
  - prosedur `mongodump`/`mongorestore` (untuk server produksi)
  - kebijakan retensi backup (harian/mingguan)
  - uji restore di lingkungan terpisah
- Panduan integrasi WhatsApp Meta (sudah ada): `/app/memory/PANDUAN_WHATSAPP.md` — **untuk digunakan nanti setelah user setuju**.

## 4) Success Criteria
- App UI berbranding **TRIRARA TUNGGAL PUTRA** + logo, dark navy theme konsisten.
- Data tambahan dapat disimpan & dibaca kembali (Unit & Ops) tanpa breaking changes.
- Export **Hour Meter** berhasil untuk **PDF + Excel + Word** dengan struktur section sesuai docx.
- Nomor laporan LP/TTP otomatis tercantum pada export dan arsip nomor tetap berjalan.
- WhatsApp (mode simulasi saat ini):
  - pesan masuk dan pesan keluar dapat diuji end-to-end tanpa Meta (upload manual + simulasi inbound).
  - tidak ada pengiriman ganda, retry aman tercatat (outbox) meskipun simulated.
  - audit log lengkap untuk setiap aksi.
- HM janggal selalu masuk verifikasi manual dan tidak auto-approve.
- Pengingat piutang dan laporan mingguan dapat diaktif/nonaktifkan, terjadwal WITA, anti-spam, dan tercatat (simulasi).
- Deployment aman: **database tidak dihapus/di-reset**.
- Integrasi WhatsApp Cloud API resmi Meta **tidak diaktifkan** sampai user memberi persetujuan eksplisit.

---
## Phase 4 — Keuangan & Rekap Bulanan Excavator (Status: COMPLETED)
User choices: (a) Keuangan dulu, (b) Rekap Bulanan di halaman Laporan (tab), (c) Surat Keluar dibuat sekarang.
- [x] Route `/finance` (admin only) + menu sidebar "Keuangan"
- [x] FinancePage: Dashboard, Kas Masuk (KM-TTP-xxx), Kas Keluar (BK/KK-TTP-xxx, auto dari Sparepart & Payroll), Invoice (INV/TTP/xxx/romawi/tahun), Surat Masuk, Surat Keluar (SP/TTP/xxx/romawi/tahun mulai 201), Rekap Bulanan + export Excel/PDF
- [x] Edit tanggal Surat Keluar/Invoice -> bulan romawi & tahun nomor ikut diperbarui (urut tetap)
- [x] Laporan: tab "Rekap Bulanan Excavator" (tabel 12 kolom sesuai form PDF) + export PDF A3/Excel/Word
- [x] Testing agent iteration_3: backend 36/36, frontend 100%

## Phase 5 — Rekap Penghasilan per Pengurus (Status: COMPLETED)
User choices: pendapatan = jam HM × tarif sewa/jam (tarif unit; fallback tarif pengurus); pengeluaran = gaji operator + sparepart; tampil di halaman Pengurus; tabel pengurus × Jan–Des + total; export Excel/PDF berkop.
- [x] Field `tarif_sewa_per_jam` di Unit & Pengurus
- [x] GET /api/pengurus-rekap?year= (admin)
- [x] Komponen PengurusRekap (stat, toggle tampilan, tabel bulanan + detail expand, peringatan tarif kosong)
- [x] Export PDF (A4 landscape berkop) & Excel berkop + nomor laporan otomatis
- [x] Testing iteration_4: 100%

## Phase 6 — Integrasi WhatsApp + AI pembaca gambar (Status: COMPLETED — mode simulasi)
User choices: WhatsApp Business Cloud API resmi (kredensial menyusul), data diverifikasi admin dulu (Kotak Masuk WA), AI Gemini (gemini-3-flash-preview) via Emergent LLM Key.
- [x] backend/wa_ai.py: OCR bukti transfer & foto layar HM, pencocokan keterangan unit
- [x] backend/whatsapp.py: webhook Meta (verify + HMAC; aktif bila Secrets diisi), upload manual, inbox (approve/reject/reprocess/delete), kontak WA, balasan via outbox (simulasi bila belum dikonfigurasi)
- [x] Approve transfer -> Kas Masuk (no_ref anti-duplikat); approve HM -> Ops Report
- [x] Unit: field kode_wa; Kas Masuk: pengurus & no_ref
- [x] Rekap Pengurus: metrik Transfer Diterima & Piutang (+ export)
- [x] Testing iteration_5: backend 16/16, frontend OK

## Phase 7 — Setujui Otomatis + Ringkasan Harian WA (Status: COMPLETED)
- [x] Auto-approve (confidence >= 90%, unit dikenali, nilai jelas, no_ref tidak duplikat, tanpa peringatan) — sisanya ke verifikasi manual
- [x] Audit log semua aksi
- [x] Ringkasan Harian WA per pengurus 20:00 WITA (cron → POST /api/cron/daily-summary, idempoten)
- [x] UI tab Otomasi & Ringkasan di Kotak Masuk WA
- [x] Testing iteration_6: backend 100%, frontend 100%
- Catatan: pengiriman WA saat ini **simulasi** sampai user menyetujui integrasi Meta.
