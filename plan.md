# plan.md — TRIRARA TUNGGAL PUTRA Ops System (Tema + Hour Meter Report)

## 1) Objectives
- Ubah identitas aplikasi: **EXCAVA.OPS → TRIRARA TUNGGAL PUTRA** + gunakan **Logo.jpg**.
- Retheme ke **dark navy** dengan aksen **kuning + merah** (selaras logo & kop surat).
- Tambahkan field yang dibutuhkan format **Hour Meter.docx** ke sistem (Unit & Ops Report) agar laporan terisi otomatis.
- Buat eksport laporan **Hour Meter** dengan **layout sama** untuk **PDF + Excel + Word**.
- Pastikan fitur existing (Dashboard, Units, Ops, Payroll, Sparepart, Laporan/nomor LP/TTP + arsip, Pengurus, Users) tetap berjalan.
- Integrasi WhatsApp end-to-end (produksi) via **Meta WhatsApp Cloud API**:
  - Pesan masuk (gambar bukti transfer & foto HM) benar-benar masuk ke **Kotak Masuk WA**.
  - Balasan konfirmasi & Ringkasan Harian benar-benar terkirim.
  - **Tidak pernah** menampilkan token/App Secret di log atau UI; hanya via env/secrets.
  - **Auto-approve** tetap: AI confidence **≥ 90%**, unit dikenali, angka jelas, **no_ref tidak duplikat**, tanpa warning; selain itu **manual**.
  - **Audit log** lengkap untuk setiap aksi dan setiap pengiriman WA.
- Semua otomasi berjalan di zona waktu **Asia/Makassar (WITA)**.
- Deployment harus aman dan **tidak menghapus / mereset database**.
- Tidak menyatakan WhatsApp “Terhubung” sebelum **uji kirim + terima** berhasil dengan nomor WhatsApp sungguhan.

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

### Phase 8 — (A) WhatsApp Cloud API Production Hardening (sebelum deploy) — Status: COMPLETED (iteration_7: backend 95%→fix PIN order, frontend 100%, security 100%)
**Tujuan:** memastikan integrasi WA aman/andal di produksi: tidak dobel kirim, ada retry aman, ada status delivery, audit lengkap, dan tidak mengklaim “Terhubung” sebelum E2E real berhasil.

**Catatan kondisi Meta dari user:**
- Business Portfolio: **BELUM ADA**.
- Nomor WA perusahaan: **masih aktif** di aplikasi WhatsApp/WA Business.
  - Untuk Cloud API “langsung” (tanpa program coexistence), nomor harus **dimigrasi** (hapus akun WA di nomor tsb) atau pakai **nomor baru**.
  - Coexistence (pakai nomor yang tetap aktif di WA Business App) umumnya memerlukan jalur **Embedded Signup/Tech Provider/BSP** → kemungkinan **tidak feasible** untuk app sendiri saat ini.
- Nomor pemilik untuk laporan mingguan: **082343070023** (normalisasi: **6282343070023**).

**Backend**
- Buat modul pengiriman terpusat (mis. `wa_outbox.py`) dan ubah semua pengiriman WA agar lewat satu jalur ini:
  - Reply konfirmasi approve (transfer/HM)
  - Balasan auto-help
  - Ringkasan harian
  - (Nanti) pengingat piutang dan laporan mingguan
- Desain outbox (Mongo):
  - koleksi `wa_outbox` berisi: `id`, `to`, `type` (text/template), `payload`, `dedupe_key`, `status` (queued/sending/sent/failed), `attempts`, `last_error`, `next_retry_at`, `created_at`, `sent_at`.
  - `dedupe_key` wajib unik (unique index) agar mencegah pengiriman ganda.
- Retry aman:
  - Retry hanya untuk error jaringan/timeout, HTTP **429/5xx**.
  - Tidak retry untuk **4xx** (kecuali 429).
  - Backoff bertahap + jitter.
  - Error message disimpan ter-redact (tanpa token / secret).
- Endpoint admin:
  - `POST /api/wa/outbox/retry` (manual retry by id / by status)
  - `GET /api/wa/outbox` (monitoring)
- Cron retry outbox:
  - Tambah cron max 5 total crons (ingat limit platform). Gunakan: setiap **30 menit** (>= 15 menit).
- Status koneksi WhatsApp di UI:
  - Level status:
    1) `not_configured` (env kosong)
    2) `configured_not_verified` (env terisi tapi belum ada inbound webhook valid dan belum sukses outbound)
    3) `connected_verified` (sudah terima inbound webhook signed + ada outbound berhasil/delivered)
  - Simpan “hasil uji koneksi” di DB (mis. `app_settings.key=wa_connection_state`) tanpa menyimpan token.
- Tambahkan endpoint uji:
  - `GET /api/wa/cloud/phone-number` untuk verifikasi kredensial (ambil display_phone_number/verified_name/status) via Graph API.
  - `POST /api/wa/cloud/send-test` untuk mengirim pesan uji (text atau `hello_world` template bila diperlukan).
- Webhook safety:
  - Pastikan signature validation tetap on saat `WHATSAPP_APP_SECRET` terisi.
  - Simpan event status message (sent/delivered/read/failed) untuk update outbox.
- Dokumen & halaman publik:
  - Halaman **Kebijakan Privasi** publik: `/kebijakan-privasi` (dibutuhkan untuk App Live).
  - Buat dokumentasi setup: `/app/memory/PANDUAN_WHATSAPP.md` berisi:
    - pembuatan Business Portfolio
    - pembuatan App Meta + penambahan produk WhatsApp
    - setup webhook (callback URL + verify token)
    - set Secrets di Emergent (prod)
    - daftar variabel env yang diperlukan
    - langkah pengujian end-to-end

**Frontend**
- Tambah/rapikan UI:
  - Tombol “Tes Koneksi” (menjalankan `/api/wa/cloud/phone-number`)
  - Tombol “Kirim Pesan Uji” (menjalankan `/api/wa/cloud/send-test`)
  - Halaman/panel status koneksi yang tidak misleading (tidak boleh “Terhubung” sebelum verified)
  - Panel monitoring Outbox (sent/failed/queued) + tombol retry
- Pastikan tidak ada token/secret tampil di UI.

**Testing (wajib sebelum Phase 9)**
- Backend tests (testing_agent_v3):
  - dedupe_key unique, retry logic, redaction, endpoint auth
  - webhook menerima status update tanpa crash
- Frontend tests:
  - status koneksi tampil sesuai state
  - outbox table render + retry action
- Security checks:
  - tidak ada token muncul di response/log/audit detail

### Phase 9 — (B) Deploy + E2E WhatsApp Cloud API dengan nomor nyata (user-driven) — Status: MENUNGGU USER (deploy + Secrets + nomor)
**Tujuan:** aplikasi benar-benar menerima pesan WA dan mengirim pesan ringkasan/konfirmasi.

**Langkah (dibantu panduan, dieksekusi oleh user):**
1. User membuat **Meta Business Portfolio**.
2. User membuat **Meta Developer App** (Business) + tambah produk WhatsApp.
3. User menyiapkan nomor WA perusahaan:
   - Opsi 1 (paling realistis untuk Cloud API): **nomor baru**.
   - Opsi 2 (migrasi nomor lama): **hapus akun WhatsApp** pada nomor itu sebelum registrasi Cloud API.
   - Opsi coexistence (nomor tetap aktif di WA Business App) kemungkinan perlu Tech Provider/BSP → bukan target awal.
4. User deploy app (HTTPS otomatis) dan isi Secrets (tanpa mengirim token di chat):
   - `WHATSAPP_ACCESS_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - `WHATSAPP_WABA_ID` (bila diperlukan untuk subscribe)
   - `WHATSAPP_APP_SECRET`
   - `WHATSAPP_VERIFY_TOKEN`
   - `WHATSAPP_API_VERSION`
   - `WEBHOOK_CRON_SECRET`
5. Set webhook callback ke `https://<domain>/api/whatsapp/webhook` dan verify token sesuai Secrets.
6. Uji E2E:
   - Kirim foto bukti transfer & foto HM dari nomor operator/pengurus → masuk Kotak Masuk WA.
   - Uji approve manual → balasan terkirim.
   - Uji auto-approve (≥90% dan tanpa warning) → record tercipta dan balasan terkirim.
   - Uji daily summary run-now → terkirim (mode text bila 24h window, atau template bila di luar window).
7. Setelah uji sukses barulah status UI berubah menjadi “Terhubung (Terverifikasi)”.

**Testing**
- Dokumentasikan hasil uji (tanggal, nomor uji, screenshot log/status).

### Phase 10 — (C2) Peringatan HM Janggal
**Tujuan:** HM mencurigakan tidak boleh lolos auto-approve.

**Rule minimum:**
- HM turun dibanding HM terakhir unit (sudah ada warning dasar, akan dipertegas menjadi auto-block).
- HM melonjak tidak wajar (threshold configurable, misal > X jam/hari atau > Y% dari rata-rata 7 hari).
- Foto tidak terbaca jelas / HM=0 → selalu manual.

**Backend**
- Tambah deteksi anomali HM:
  - simpan `hm_anomaly` pada `wa_inbox.auto_check.reasons` atau field khusus.
  - jika anomaly terdeteksi → `eligible=false` untuk auto-approve.
- Tambah pengaturan ambang anomali HM (di tab Otomasi).
- Audit: setiap auto-block karena anomali dicatat.

**Frontend**
- Tampilkan badge/peringatan jelas di Kotak Masuk WA.
- Pengaturan ambang: on/off, threshold lonjakan.

**Testing**
- Backend unit tests untuk kasus hm turun/lonjak.
- UI memastikan item masuk manual queue.

### Phase 11 — (C3) Pengingat Piutang (WhatsApp)
**Tujuan:** kirim pengingat otomatis berdasar umur piutang & ambang nominal, bisa dikonfigurasi, tidak spam, tercatat.

**Backend**
- Setting:
  - enable/disable
  - jam kirim (WITA)
  - threshold nominal
  - umur piutang minimal (hari)
  - penerima (pengurus dan/atau pemilik)
- Hitung piutang “benar-benar belum dibayar” dari data tervalidasi (ops + kas masuk) per pengurus.
- Mekanisme anti-spam:
  - dedupe per pengurus per hari/minggu
  - simpan log pengiriman dan status outbox
- Cron: minimal 1x/hari (memperhatikan limit 5 cron total; gabungkan bila perlu).

**Frontend**
- Halaman pengaturan pengingat piutang + preview penerima.
- Log pengiriman.

**Testing**
- Backend: perhitungan, dedupe, retry via outbox.
- UI: preview dan toggle.

### Phase 12 — (C4) Laporan Mingguan Pemilik (Senin 08:00 WITA)
**Tujuan:** laporan otomatis ke pemilik setiap Senin 08:00 WITA.

**Spesifikasi isi:**
- total HM per unit (mingguan)
- total pemasukan (kas masuk)
- piutang berjalan
- pembayaran diterima
- daftar transaksi masih perlu verifikasi

**Backend**
- Cron: `0 8 * * 1` timezone Asia/Makassar.
- Penerima: pemilik **6282343070023** (bisa diubah di Settings).
- Template Meta (Utility) untuk pengiriman di luar 24 jam window.
- Audit log + outbox.

**Frontend**
- Pengaturan laporan mingguan: enabled, penerima, template.
- Preview laporan.

**Testing**
- Backend: generator laporan + idempotensi.
- UI: preview + history.

## 4) Success Criteria
- App UI berbranding **TRIRARA TUNGGAL PUTRA** + logo, dark navy theme konsisten.
- Data tambahan dapat disimpan & dibaca kembali (Unit & Ops) tanpa breaking changes.
- Export **Hour Meter** berhasil untuk **PDF + Excel + Word** dengan struktur section sesuai docx.
- Nomor laporan LP/TTP otomatis tercantum pada export dan arsip nomor tetap berjalan.
- WhatsApp produksi:
  - webhook menerima pesan gambar nyata dan masuk Kotak Masuk WA.
  - balasan konfirmasi approve terkirim.
  - Ringkasan Harian 20:00 WITA terkirim (text atau template sesuai aturan 24 jam).
  - tidak ada pengiriman ganda, ada retry aman.
  - audit log lengkap untuk setiap aksi dan pengiriman.
- HM janggal selalu masuk verifikasi manual dan tidak auto-approve.
- Pengingat piutang dan laporan mingguan dapat diaktif/nonaktifkan, terjadwal WITA, anti-spam, dan tercatat.
- Deployment aman: **database tidak dihapus/di-reset**.

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

## Phase 6 — Integrasi WhatsApp + AI pembaca gambar (Status: COMPLETED — menunggu kredensial WhatsApp)
User choices: WhatsApp Business Cloud API resmi (kredensial menyusul), data diverifikasi admin dulu (Kotak Masuk WA), AI Gemini (gemini-3-flash-preview) via Emergent LLM Key.
- [x] backend/wa_ai.py: OCR bukti transfer & foto layar HM (antre 1 request + retry 429), pencocokan keterangan "Sdlg 10" -> unit (nomor lambung/nama/merek/kode_wa)
- [x] backend/whatsapp.py: webhook Meta (verify + HMAC, nonaktif sampai WHATSAPP_* diisi), upload manual, inbox (approve/reject/reprocess/delete), kontak WA, balasan WA otomatis
- [x] Approve transfer -> Kas Masuk KM-TTP-xxx (pengurus, unit, no_ref anti-duplikat); approve HM -> Ops Report (HM awal = HM terakhir / gabung bila tanggal sama)
- [x] Unit: field kode_wa; Kas Masuk: pengurus & no_ref
- [x] Rekap Pengurus: metrik Transfer Diterima & Piutang (+ export)
- [x] Testing iteration_5: backend 16/16, frontend OK
- Pending dari user: WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_APP_SECRET, WHATSAPP_VERIFY_TOKEN + deploy

## Phase 7 — Setujui Otomatis + Ringkasan Harian WA (Status: COMPLETED)
- [x] Auto-approve (confidence >= 90%, unit dikenali, nilai jelas, no_ref tidak duplikat, tanpa peringatan) — sisanya ke verifikasi manual
- [x] Audit log semua aksi (received, ai_processed, auto_approved, auto_blocked, approved, rejected, settings_changed, summary_run)
- [x] Ringkasan Harian WA per pengurus 20:00 WITA (/.emergent/crons.yml -> POST /api/cron/daily-summary, Bearer WEBHOOK_CRON_SECRET, idempoten)
- [x] UI tab Otomasi & Ringkasan di Kotak Masuk WA
- [x] Testing iteration_6: backend 100%, frontend 100%
- Pending: kredensial Meta WhatsApp setelah deploy (pengiriman saat ini disimulasikan/dilewati)
