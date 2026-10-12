// Panduan konfigurasi WhatsApp Cloud API (Meta) — ditampilkan di tab Koneksi WhatsApp.
// Versi lengkap juga tersedia di /app/memory/PANDUAN_WHATSAPP.md
export const WA_GUIDE = [
  {
    id: "portfolio",
    title: "Buat Meta Business Portfolio",
    items: [
      "Buka business.facebook.com → Buat akun → isi nama usaha TRIRARA TUNGGAL PUTRA, nama Anda, dan email kantor.",
      "Verifikasi bisnis (Pengaturan Bisnis → Pusat Keamanan → Mulai Verifikasi; dokumen NIB/akta/NPWP) TIDAK wajib di awal. Tanpa verifikasi, pesan yang dimulai bisnis dibatasi ±250 penerima per 24 jam — cukup untuk pengurus & pemilik.",
      "Bila Business Portfolio dibatasi / ditolak, selesaikan dulu lewat Account Quality di business.facebook.com sebelum lanjut.",
    ],
  },
  {
    id: "app",
    title: "Buat Meta Developer App + produk WhatsApp",
    items: [
      "developers.facebook.com → My Apps → Create App → pilih use case lainnya → tipe Business → hubungkan ke Business Portfolio di atas.",
      "Di dashboard App: Add product → WhatsApp → Set up. Meta otomatis membuat WhatsApp Business Account (WABA) + nomor uji.",
    ],
  },
  {
    id: "number",
    title: "Siapkan nomor WhatsApp perusahaan",
    warn: "Nomor Anda saat ini aktif di aplikasi WhatsApp / WA Business. Cloud API langsung TIDAK bisa memakai nomor yang masih aktif di aplikasi HP (fitur coexistence hanya lewat Tech Provider/BSP).",
    items: [
      "Pilihan A (pindahkan nomor lama): cadangkan chat penting → di HP buka WhatsApp → Setelan → Akun → Hapus akun saya (bukan sekadar uninstall) → tunggu ±3 menit.",
      "Setelah dipindah, nomor tersebut TIDAK bisa lagi dipakai di aplikasi WhatsApp di HP; semua chat dikelola lewat aplikasi ini.",
      "Pilihan B (disarankan bila nomor lama masih dibutuhkan): gunakan nomor baru khusus (kartu SIM aktif, bisa menerima SMS/telepon).",
      "WhatsApp Manager → Phone numbers → Add phone number → isi Display Name (mis. TRIRARA TUNGGAL PUTRA) → verifikasi kode SMS/telepon. Display Name perlu disetujui Meta.",
    ],
  },
  {
    id: "token",
    title: "Buat token permanen & catat ID",
    items: [
      "Pengaturan Bisnis → Pengguna → System users → Tambah (peran Admin).",
      "Assign assets: App (Full control) dan WhatsApp account (Full control).",
      "Generate new token → pilih App → masa berlaku Never → izin whatsapp_business_messaging dan whatsapp_business_management. Simpan token di tempat aman — JANGAN kirim lewat chat.",
      "Catat dari App → WhatsApp → API Setup: Phone Number ID dan WhatsApp Business Account ID (WABA ID).",
      "Catat App Secret: App settings → Basic → App secret → Show.",
      "Buat Verify Token sendiri: kata sandi acak bebas (mis. 32 karakter).",
    ],
  },
  {
    id: "deploy",
    title: "Deploy & isi Secrets di Emergent",
    items: [
      "Tekan Deploy di Emergent. Deploy tidak menghapus data; deploy ulang mempertahankan database produksi.",
      "Manage Publishes → Secrets → tambahkan: WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_WABA_ID, WHATSAPP_APP_SECRET, WHATSAPP_VERIFY_TOKEN, WHATSAPP_API_VERSION (isi v25.0).",
      "Tekan Re-publish changes agar Secrets aktif. Token tidak pernah ditampilkan di aplikasi maupun log.",
    ],
  },
  {
    id: "webhook",
    title: "Pasang webhook di Meta",
    items: [
      "App → WhatsApp → Configuration → Webhook → Edit: Callback URL = URL webhook di atas (alamat aplikasi yang sudah di-deploy), Verify token = sama dengan WHATSAPP_VERIFY_TOKEN → Verify and save.",
      "Webhook fields → Subscribe kolom messages (berisi pesan masuk dan status pengiriman).",
      "Di tab ini: tekan Tes Koneksi → Daftarkan Nomor (PIN 6 digit, untuk nomor produksi) → Langganan Webhook WABA.",
    ],
  },
  {
    id: "live",
    title: "Aktifkan mode Live, pembayaran & template",
    items: [
      "App settings → Basic: isi Privacy Policy URL = https://<domain-anda>/kebijakan-privasi, kategori, ikon → ubah App Mode ke Live (tanpa Live, webhook produksi tidak terkirim).",
      "WhatsApp Manager → Payment settings: tambahkan metode pembayaran (pesan template ditagih per pesan oleh Meta; balasan dalam jendela 24 jam tidak ditagih).",
      "WhatsApp Manager → Message templates → Create → kategori Utility → nama ringkasan_harian, bahasa Indonesian, isi sesuai teks di tab Ringkasan Harian → Submit. Setelah disetujui, isi nama template di tab Ringkasan Harian.",
    ],
  },
  {
    id: "e2e",
    title: "Uji end-to-end dengan nomor asli",
    items: [
      "1. Dari HP pengurus/operator, kirim pesan \"halo\" ke nomor perusahaan → Riwayat Audit menampilkan \"Pesan MASUK asli pertama\" dan status Pesan Masuk terverifikasi.",
      "2. Tekan Kirim Pesan Uji (teks) ke nomor yang sama (dalam 24 jam) → di tab Pesan Keluar status berubah Terkirim → Diterima. Status koneksi menjadi Terhubung · Terverifikasi.",
      "3. Kirim foto bukti transfer dengan caption kode unit (mis. Sdlg 10) → muncul di Kotak Masuk → setujui → pengirim menerima balasan konfirmasi.",
      "4. Kirim foto layar HM dengan caption kode unit → periksa Ops Report.",
      "5. Tab Ringkasan Harian → Kirim Sekarang → pengurus menerima ringkasan. Periksa tab Pesan Keluar untuk status tiap pesan.",
    ],
  },
];
