# Pengaturan Otomatisasi — TRIRARA TUNGGAL PUTRA

_Semua waktu WITA (Asia/Makassar). Versi in-app: menu Bantuan & Backup._

## Persetujuan otomatis (Otomatisasi & Audit)
- Aktif/nonaktif terpisah untuk Bukti Transfer dan Foto HM (default nonaktif).
- Batas keyakinan AI minimal 90% (tidak bisa di bawah 90%).
- Syarat disimpan otomatis: keyakinan ≥ batas, unit dikenali, nominal/angka HM terbaca, No. Ref terbaca & belum pernah tercatat, tanpa peringatan, HM tidak janggal. Selain itu → verifikasi manual.

## Peringatan HM Janggal
- Selalu aktif: HM turun dari laporan sebelumnya, HM melebihi laporan tanggal sesudahnya, angka/foto tidak terbaca (keyakinan < batas), tanggal di masa depan.
- Dapat diatur: deteksi lonjakan (on/off) dan batas jam kerja per hari (1–24, default 20). Lonjakan = kenaikan HM > batas × jumlah hari sejak laporan terakhir.
- Item janggal tidak pernah disimpan otomatis; persetujuan manual wajib mencentang konfirmasi dan tercatat di audit.

## Ringkasan Harian
- Setiap hari 20:00 WITA per pengurus: HM per unit (awal, akhir, total), transfer hari ini, total diterima, piutang berjalan bulan ini, item menunggu verifikasi.
- Aktif/nonaktif, nama template Meta (nanti). Pratinjau & Jalankan Sekarang tersedia. Tidak dikirim ganda untuk tanggal yang sama.

## Pengingat Piutang
- Default NONAKTIF. Atur jam kirim (WITA), hari kirim, batas nominal, umur minimal piutang (hari), masa jeda antar-pengingat, tembusan pemilik, pengurus yang dikecualikan.
- Dikirim hanya bila: piutang ≥ batas nominal, umur tagihan tertua ≥ batas hari, tidak ada bukti transfer menunggu verifikasi (opsional), di luar masa jeda. Maksimal 1x per hari.
- Piutang = tagihan (jam × tarif) − pembayaran tervalidasi. Umur dihitung FIFO (pembayaran melunasi tagihan tertua dulu). Yang lunas tidak pernah diingatkan.
- Kirim Paksa mengabaikan masa jeda & batas, tetapi tetap tidak mengirim ke yang lunas, tanpa nomor, atau yang transfernya menunggu verifikasi.

## Laporan Mingguan Pemilik
- Setiap Senin 08:00 WITA untuk minggu sebelumnya (Senin–Minggu) ke penerima (default Pemilik 6282343070023).
- Isi: jam kerja per unit (HM awal/akhir, total, hari kerja), total pemasukan Kas Masuk, pembayaran sewa per pengurus, piutang berjalan per pengurus, daftar menunggu verifikasi.
- Maks. 1x per minggu per penerima; Kirim Ulang Paksa bila perlu.

## Jadwal (cron platform, zona WITA)
- wa-daily-summary 20:00 setiap hari · wa-piutang-reminder tiap jam (mengecek jam & hari yang diatur) · wa-weekly-owner-report Senin 08:00 · wa-outbox-retry tiap 30 menit.
- Semua endpoint jadwal dilindungi WEBHOOK_CRON_SECRET dan idempoten (tidak berjalan ganda).

