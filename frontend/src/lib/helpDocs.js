// Dokumentasi in-app (juga diekspor ke /app/docs/*.md). Semua waktu WITA (Asia/Makassar).
export const HELP_DOCS = [
  {
    id: "penggunaan",
    title: "Panduan Penggunaan",
    sections: [
      { h: "Peran pengguna", p: ["Admin: akses semua menu (Keuangan, Kotak Masuk WA, Operators, Backup).", "Operator: Dashboard, Unit, Ops Report, Payroll, Sparepart, Laporan, Pengurus sesuai hak akses."] },
      { h: "Alur harian", p: ["1. Operator/pengurus mengirim foto layar HM dan bukti transfer (via WhatsApp setelah tersambung, atau admin Upload Gambar di Kotak Masuk WA).", "2. AI membaca gambar, mencocokkan unit dari keterangan (mis. Sdlg 10) atau kontak WA.", "3. Item yang lolos semua syarat disimpan otomatis (bila diaktifkan); sisanya menunggu verifikasi admin.", "4. Admin membuka item, mengoreksi bila perlu, lalu Setujui & Simpan → tercatat di Kas Masuk (transfer) atau Ops Report (HM).", "5. Pukul 20:00 WITA Ringkasan Harian dibuat untuk tiap pengurus."] },
      { h: "Kotak Masuk WA", p: ["Filter: Menunggu, HM Janggal, Duplikat, Diproses, Disetujui, Ditolak, Gagal, Semua.", "Badge merah HM JANGGAL = HM turun / melonjak / tidak terbaca / tanggal tidak wajar. Wajib dicek; centang konfirmasi sebelum menyimpan.", "Duplikat = No. Ref transfer sudah pernah tercatat — jangan disetujui ulang.", "Baca Ulang AI untuk memproses ulang gambar; Tolak untuk menandai tidak valid; Hapus menghapus pesan & gambar (tercatat di audit)."] },
      { h: "Bonus Admin", p: ["Menu Bonus Admin (admin): setiap unit yang mencapai kelipatan 300 jam kerja (total jam Ops Report, HM akhir − HM awal) memberi bonus Rp500.000 ke admin unit. Kelipatan, nominal, admin default/per unit, dan tanggal mulai hitung dapat diubah di Pengaturan.", "Sisa jam di bawah kelipatan dibawa ke bonus berikutnya. Tanggal tercapai = tanggal laporan HM yang melewati kelipatan.", "Tandai Dibayar → otomatis tercatat di Kas Keluar (KK-TTP); Batalkan → bukti Kas Keluar dihapus. Semua tercatat di Riwayat."] },
      { h: "Kontak WA", p: ["Daftarkan nomor operator & pengurus beserta unit/pengurusnya. Pengurus wajib bertipe Pengurus agar menerima Ringkasan Harian dan Pengingat Piutang."] },
      { h: "Pesan Keluar", p: ["Semua pesan keluar (balasan, ringkasan, pengingat, laporan mingguan, pesan uji) tercatat di sini.", "Status: Simulasi (belum terhubung ke Meta), Terkirim ke Meta, Diterima, Dibaca, Gagal.", "Kirim Ulang hanya untuk status Gagal. Status \"tidak pasti\" berarti pesan mungkin sudah sampai — cek WhatsApp penerima dulu."] },
      { h: "Riwayat Audit", p: ["Tab Otomatisasi & Audit mencatat setiap aksi: diterima, dibaca AI, disimpan otomatis/manual, HM janggal, ditolak, dihapus, perubahan pengaturan, ringkasan, pengingat, laporan, backup.", "Gunakan filter aktivitas untuk menelusuri."] },
      { h: "Simulasi WhatsApp", p: ["Selama Meta belum disetujui, gunakan Koneksi WhatsApp → Simulasi Pesan Masuk untuk meniru pesan teks/gambar dari HP. Alurnya sama dengan pesan asli, tetapi tidak ada pesan sungguhan yang dikirim dan status koneksi tidak berubah."] },
    ],
  },
  {
    id: "otomatisasi",
    title: "Pengaturan Otomatisasi",
    sections: [
      { h: "Persetujuan otomatis (Otomatisasi & Audit)", p: ["Aktif/nonaktif terpisah untuk Bukti Transfer dan Foto HM (default nonaktif).", "Batas keyakinan AI minimal 90% (tidak bisa di bawah 90%).", "Syarat disimpan otomatis: keyakinan ≥ batas, unit dikenali, nominal/angka HM terbaca, No. Ref terbaca & belum pernah tercatat, tanpa peringatan, HM tidak janggal. Selain itu → verifikasi manual."] },
      { h: "Peringatan HM Janggal", p: ["Selalu aktif: HM turun dari laporan sebelumnya, HM melebihi laporan tanggal sesudahnya, angka/foto tidak terbaca (keyakinan < batas), tanggal di masa depan.", "Dapat diatur: deteksi lonjakan (on/off) dan batas jam kerja per hari (1–24, default 20). Lonjakan = kenaikan HM > batas × jumlah hari sejak laporan terakhir.", "Item janggal tidak pernah disimpan otomatis; persetujuan manual wajib mencentang konfirmasi dan tercatat di audit."] },
      { h: "Ringkasan Harian", p: ["Setiap hari 20:00 WITA per pengurus: HM per unit (awal, akhir, total), transfer hari ini, total diterima, piutang berjalan bulan ini, item menunggu verifikasi.", "Aktif/nonaktif, nama template Meta (nanti). Pratinjau & Jalankan Sekarang tersedia. Tidak dikirim ganda untuk tanggal yang sama."] },
      { h: "Pengingat Piutang", p: ["Default NONAKTIF. Atur jam kirim (WITA), hari kirim, batas nominal, umur minimal piutang (hari), masa jeda antar-pengingat, tembusan pemilik, pengurus yang dikecualikan.", "Dikirim hanya bila: piutang ≥ batas nominal, umur tagihan tertua ≥ batas hari, tidak ada bukti transfer menunggu verifikasi (opsional), di luar masa jeda. Maksimal 1x per hari.", "Piutang = tagihan (jam × tarif) − pembayaran tervalidasi. Umur dihitung FIFO (pembayaran melunasi tagihan tertua dulu). Yang lunas tidak pernah diingatkan.", "Kirim Paksa mengabaikan masa jeda & batas, tetapi tetap tidak mengirim ke yang lunas, tanpa nomor, atau yang transfernya menunggu verifikasi."] },
      { h: "Laporan Mingguan Pemilik", p: ["Setiap Senin 08:00 WITA untuk minggu sebelumnya (Senin–Minggu) ke penerima (default Pemilik 6282343070023).", "Isi: jam kerja per unit (HM awal/akhir, total, hari kerja), total pemasukan Kas Masuk, pembayaran sewa per pengurus, piutang berjalan per pengurus, daftar menunggu verifikasi.", "Maks. 1x per minggu per penerima; Kirim Ulang Paksa bila perlu."] },
      { h: "Jadwal (cron platform, zona WITA)", p: ["wa-daily-summary 20:00 setiap hari · wa-piutang-reminder tiap jam (mengecek jam & hari yang diatur) · wa-weekly-owner-report Senin 08:00 · wa-outbox-retry tiap 30 menit.", "Semua endpoint jadwal dilindungi WEBHOOK_CRON_SECRET dan idempoten (tidak berjalan ganda)."] },
    ],
  },
  {
    id: "backup",
    title: "Backup & Pemulihan",
    sections: [
      { h: "Prinsip", p: ["Backup bersifat hanya-baca. Tidak ada fitur di aplikasi yang menghapus atau mereset database.", "Deploy dan deploy ulang tidak mereset data produksi."] },
      { h: "Backup dari aplikasi (disarankan)", p: ["Menu Bantuan & Backup → tab Backup → Unduh Backup. File: backup-trirara-YYYYMMDD-HHMM-WITA.json.gz.", "Default tanpa gambar WhatsApp (ukuran kecil). Centang Sertakan gambar untuk backup lengkap.", "Sesi login tidak ikut dicadangkan. File berisi data keuangan & hash kata sandi — simpan di tempat aman (Google Drive/Flashdisk terenkripsi)."] },
      { h: "Jadwal backup yang disarankan", p: ["Harian: unduh backup setiap sore setelah verifikasi selesai, simpan 14 file terakhir.", "Mingguan: setiap Senin simpan 1 salinan di lokasi kedua (simpan 8 minggu).", "Bulanan: simpan backup akhir bulan selama 12 bulan (untuk laporan keuangan)."] },
      { h: "Backup lewat server (teknis)", p: ["python /app/scripts/backup_db.py --out /app/backups --keep 14", "Atau bawaan MongoDB: mongodump --uri \"$MONGO_URL\" --db \"$DB_NAME\" --gzip --archive=backup.gz"] },
      { h: "Pemulihan (restore)", p: ["1. Uji dulu ke database terpisah: python /app/scripts/restore_db.py FILE.json.gz --target-db trirara_restore_test", "2. Lihat dampak tanpa menulis: python /app/scripts/restore_db.py FILE.json.gz --dry-run", "3. Pulihkan dokumen yang hilang saja (aman, default): python /app/scripts/restore_db.py FILE.json.gz --mode merge", "4. Mode replace (menimpa dokumen dengan ID sama) hanya bila benar-benar perlu: --mode replace --yes", "Script tidak pernah menghapus koleksi/database. Untuk database produksi Emergent, hubungi dukungan Emergent untuk akses restore."] },
      { h: "Uji pemulihan berkala", p: ["Minimal sebulan sekali: restore ke database uji, cocokkan jumlah dokumen (Unit, Ops Report, Kas Masuk, Kas Keluar) dengan info di tab Backup."] },
    ],
  },
  {
    id: "whatsapp",
    title: "Integrasi WhatsApp (nanti)",
    sections: [
      { h: "Status", p: ["Integrasi WhatsApp Cloud API resmi DITUNDA sampai ada persetujuan pemilik. Saat ini semua pesan berjalan dalam mode simulasi.", "Panduan langkah demi langkah tersedia di Kotak Masuk WA → Koneksi WhatsApp (8 langkah) dan /app/memory/PANDUAN_WHATSAPP.md."] },
      { h: "Ringkas", p: ["Buat Meta Business Portfolio & Developer App (Business) + produk WhatsApp.", "Nomor perusahaan yang masih aktif di aplikasi WA harus dihapus akunnya dulu, atau gunakan nomor baru.", "Isi Secrets di Emergent (WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_WABA_ID, WHATSAPP_APP_SECRET, WHATSAPP_VERIFY_TOKEN, WHATSAPP_API_VERSION) lalu Re-publish.", "Pasang webhook https://<domain>/api/whatsapp/webhook (field messages), App mode Live dengan Privacy Policy https://<domain>/kebijakan-privasi.", "Daftarkan template Utility: ringkasan_harian, pengingat_piutang, laporan_mingguan (teks tersedia di tab masing-masing).", "Status Terhubung hanya muncul setelah pesan masuk asli DAN pesan keluar terkonfirmasi delivered."] },
    ],
  },
];
