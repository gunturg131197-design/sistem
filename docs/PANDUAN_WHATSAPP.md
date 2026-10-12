# Panduan WhatsApp Cloud API — TRIRARA TUNGGAL PUTRA

Semua waktu dalam WITA (Asia/Makassar). Panduan ini juga tampil di aplikasi: Kotak Masuk WA → tab **Koneksi WhatsApp**.

## Status saat ini
- **DITUNDA atas instruksi pemilik** — jangan konfigurasi Meta/webhook/nomor asli sebelum ada persetujuan eksplisit.
- Kode integrasi sudah siap. **WhatsApp BELUM terhubung**: kredensial Meta belum diisi dan uji kirim-terima dengan nomor asli belum dilakukan.
- Sampai Secrets diisi, semua pesan keluar disimpan sebagai **simulasi** (tab Pesan Keluar).

## 1. Business Portfolio (status user: BELUM ADA)
1. business.facebook.com → Buat akun → nama usaha, nama, email kantor.
2. Verifikasi bisnis tidak wajib di awal (tanpa verifikasi: ±250 penerima unik / 24 jam untuk pesan yang dimulai bisnis).
3. Bila portfolio dibatasi, selesaikan dulu via Account Quality.

## 2. Developer App
developers.facebook.com → My Apps → Create App → tipe Business → pilih portfolio → Add product **WhatsApp** → Set up.

## 3. Nomor perusahaan (status user: nomor masih aktif di aplikasi WA/WA Business)
- Cloud API langsung tidak bisa memakai nomor yang masih aktif di aplikasi HP. Coexistence hanya tersedia lewat Tech Provider/BSP (Embedded Signup) — tidak dipakai di aplikasi ini.
- Pilihan A: cadangkan chat → WhatsApp di HP → Setelan → Akun → **Hapus akun saya** → tunggu ±3 menit → daftarkan nomor di WhatsApp Manager. Nomor tidak bisa dipakai lagi di aplikasi HP.
- Pilihan B: pakai nomor baru khusus.
- WhatsApp Manager → Phone numbers → Add → Display Name → verifikasi SMS/telepon (Display Name perlu disetujui Meta).

## 4. Token & ID
- Business Settings → System users → Add (Admin) → Assign assets: App + WhatsApp account (Full control) → Generate token (Never expire) dengan izin `whatsapp_business_messaging`, `whatsapp_business_management`.
- Catat: Phone Number ID, WABA ID (API Setup), App Secret (App settings → Basic), buat Verify Token acak sendiri.

## 5. Deploy & Secrets
Deploy di Emergent (data preview disalin saat deploy pertama; deploy ulang tidak mereset database produksi).
Manage Publishes → Secrets:
| Variabel | Isi |
|---|---|
| WHATSAPP_ACCESS_TOKEN | token System User |
| WHATSAPP_PHONE_NUMBER_ID | Phone Number ID |
| WHATSAPP_WABA_ID | WhatsApp Business Account ID |
| WHATSAPP_APP_SECRET | App Secret |
| WHATSAPP_VERIFY_TOKEN | kata sandi acak buatan sendiri |
| WHATSAPP_API_VERSION | v25.0 |
| WEBHOOK_CRON_SECRET | sudah ada (penjadwal) |
Lalu **Re-publish changes**. Jangan kirim token lewat chat.

## 6. Webhook
App → WhatsApp → Configuration → Callback URL `https://<domain>/api/whatsapp/webhook`, Verify token = WHATSAPP_VERIFY_TOKEN → Verify and save → subscribe field **messages**.
Di aplikasi: **Tes Koneksi** → **Daftarkan Nomor** (PIN 6 digit, tidak disimpan) → **Langganan Webhook WABA**.

## 7. Live, pembayaran, template
- App settings → Basic → Privacy Policy URL `https://<domain>/kebijakan-privasi` → App Mode **Live**.
- WhatsApp Manager → Payment settings → metode pembayaran.
- Template Utility `ringkasan_harian` (bahasa Indonesian) — teks di tab Ringkasan Harian; isi nama template setelah disetujui.

## 8. Uji end-to-end (wajib sebelum dinyatakan Terhubung)
1. Kirim "halo" dari HP pengurus ke nomor perusahaan → checklist "Pesan masuk asli diterima" ✔.
2. Kirim Pesan Uji (teks) ke nomor itu → tab Pesan Keluar: Terkirim → Diterima → status **Terhubung · Terverifikasi**.
3. Kirim foto bukti transfer + caption `Sdlg 10` → Kotak Masuk → Setujui → pengirim menerima konfirmasi.
4. Kirim foto layar HM + caption kode unit → cek Ops Report.
5. Ringkasan Harian → Kirim Sekarang → pengurus menerima.

## Keamanan & keandalan (yang sudah dibangun)
- Token/App Secret hanya di env/Secrets; disaring dari semua log, audit, dan pesan error.
- Webhook POST wajib tanda tangan `X-Hub-Signature-256` (HMAC App Secret); webhook berulang dari Meta diabaikan (idempoten per message id).
- Outbox `wa_outbox`: `dedupe_key` unik → tidak ada kirim ganda; retry hanya untuk gagal koneksi/429/5xx (otomatis tiap 30 menit, maks 6 percobaan); timeout = status tidak pasti → tidak diulang otomatis.
- Status delivered/read/failed dari Meta diperbarui per pesan.
- Status **Terhubung** hanya setelah pesan masuk asli + pesan keluar delivered; reset otomatis bila nomor/token diganti.
