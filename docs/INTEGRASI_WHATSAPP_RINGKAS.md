# Integrasi WhatsApp (nanti) — TRIRARA TUNGGAL PUTRA

_Semua waktu WITA (Asia/Makassar). Versi in-app: menu Bantuan & Backup._

## Status
- Integrasi WhatsApp Cloud API resmi DITUNDA sampai ada persetujuan pemilik. Saat ini semua pesan berjalan dalam mode simulasi.
- Panduan langkah demi langkah tersedia di Kotak Masuk WA → Koneksi WhatsApp (8 langkah) dan /app/memory/PANDUAN_WHATSAPP.md.

## Ringkas
- Buat Meta Business Portfolio & Developer App (Business) + produk WhatsApp.
- Nomor perusahaan yang masih aktif di aplikasi WA harus dihapus akunnya dulu, atau gunakan nomor baru.
- Isi Secrets di Emergent (WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_WABA_ID, WHATSAPP_APP_SECRET, WHATSAPP_VERIFY_TOKEN, WHATSAPP_API_VERSION) lalu Re-publish.
- Pasang webhook https://<domain>/api/whatsapp/webhook (field messages), App mode Live dengan Privacy Policy https://<domain>/kebijakan-privasi.
- Daftarkan template Utility: ringkasan_harian, pengingat_piutang, laporan_mingguan (teks tersedia di tab masing-masing).
- Status Terhubung hanya muncul setelah pesan masuk asli DAN pesan keluar terkonfirmasi delivered.

