# Backup & Pemulihan — TRIRARA TUNGGAL PUTRA

_Semua waktu WITA (Asia/Makassar). Versi in-app: menu Bantuan & Backup._

## Prinsip
- Backup bersifat hanya-baca. Tidak ada fitur di aplikasi yang menghapus atau mereset database.
- Deploy dan deploy ulang tidak mereset data produksi.

## Backup dari aplikasi (disarankan)
- Menu Bantuan & Backup → tab Backup → Unduh Backup. File: backup-trirara-YYYYMMDD-HHMM-WITA.json.gz.
- Default tanpa gambar WhatsApp (ukuran kecil). Centang Sertakan gambar untuk backup lengkap.
- Sesi login tidak ikut dicadangkan. File berisi data keuangan & hash kata sandi — simpan di tempat aman (Google Drive/Flashdisk terenkripsi).

## Jadwal backup yang disarankan
- Harian: unduh backup setiap sore setelah verifikasi selesai, simpan 14 file terakhir.
- Mingguan: setiap Senin simpan 1 salinan di lokasi kedua (simpan 8 minggu).
- Bulanan: simpan backup akhir bulan selama 12 bulan (untuk laporan keuangan).

## Backup lewat server (teknis)
```
python /app/scripts/backup_db.py --out /app/backups --keep 14
```
- Atau bawaan MongoDB: mongodump --uri "$MONGO_URL" --db "$DB_NAME" --gzip --archive=backup.gz

## Pemulihan (restore)
- 1. Uji dulu ke database terpisah: python /app/scripts/restore_db.py FILE.json.gz --target-db trirara_restore_test
- 2. Lihat dampak tanpa menulis: python /app/scripts/restore_db.py FILE.json.gz --dry-run
- 3. Pulihkan dokumen yang hilang saja (aman, default): python /app/scripts/restore_db.py FILE.json.gz --mode merge
- 4. Mode replace (menimpa dokumen dengan ID sama) hanya bila benar-benar perlu: --mode replace --yes
- Script tidak pernah menghapus koleksi/database. Untuk database produksi Emergent, hubungi dukungan Emergent untuk akses restore.

## Uji pemulihan berkala
- Minimal sebulan sekali: restore ke database uji, cocokkan jumlah dokumen (Unit, Ops Report, Kas Masuk, Kas Keluar) dengan info di tab Backup.

