# Deploy TRIRARA / EXCAVA.OPS di Coolify v4 (>= 4.3.14) — Database MariaDB

Arsitektur:

```
Frontend : React + nginx (port 80)
Backend  : FastAPI/uvicorn (port 8000)
Database : MariaDB 11.4 (tabel relasional, satu kolom per field — skema di backend/db_schema.py)
```

Tabel & kolom dibuat **otomatis** oleh backend saat start (tidak perlu import SQL manual).
Struktur bisa dibuka dengan phpMyAdmin / DBeaver / HeidiSQL untuk laporan SQL.

> Cookie login (`SameSite=None; Secure`) butuh HTTPS. Coolify menyediakan HTTPS via Let's Encrypt.

---

## 0. CARA UTAMA — Dockerfile tunggal (React + FastAPI dalam 1 container)

`/Dockerfile` (root) membangun React lalu FastAPI menyajikannya: `/api/*` = API, path lain = SPA
(refresh di `/dashboard` dsb tetap aman → index.html). Satu domain, tanpa CORS.

1. Coolify → **+ New → Database → MariaDB** (11.x). Catat *Internal host* (nama container), user, password, database.
2. Coolify → **+ New → Application → GitHub** `gunturg131197-design/sistem`, branch `main`.
   - Build Pack: **Dockerfile** · Base Directory: `/` · Dockerfile Location: `/Dockerfile`
   - Ports Exposes: **8000** · Domain: `https://trirara.my.id`
   - Pastikan app & database di **network/project yang sama** (atau aktifkan "Connect to Predefined Network").
3. Isi Environment Variables sesuai `.env.example` (DB_HOST = internal host MariaDB dari langkah 1).
4. Deploy → cek `https://trirara.my.id/api/health` → `{"status":"ok","database":"mariadb"}`.
5. Login `ADMIN_USERNAME` / `ADMIN_PASSWORD` (admin dibuat otomatis saat database masih kosong).

Build arg opsional: `INSTALL_AI=0` (lewati library AI baca-gambar WA, image lebih kecil).
Pindah data dari MongoDB lama: isi `MIGRATE_FROM_MONGO_URL` + `MIGRATE_FROM_MONGO_DB` sekali, deploy, lalu hapus.

Opsi docker-compose di bawah ini tetap tersedia sebagai alternatif.

---


## 1. Pilih cara deploy

| Opsi | File | Domain | Cocok bila |
|---|---|---|---|
| **F – Satu domain (DISARANKAN)** | `docker-compose.singledomain.yml` | 1 domain (`/api` di-proxy nginx) | Paling sederhana, tanpa CORS |
| **E – Gabungan 2 subdomain** | `docker-compose.yml` | frontend + `api.` subdomain | Ingin subdomain API terpisah |
| **B – App terpisah** | `backend/Dockerfile`, `frontend/Dockerfile`, `mariadb/docker-compose.yml` | bebas | Resource terpisah per service |

Pada opsi E & F, MariaDB berjalan sebagai service internal `mariadb` (tanpa domain).

---

## 2. Environment Variables (Coolify → resource → Environment Variables)

```
MARIADB_ROOT_PASSWORD=ganti_password_root_kuat
MARIADB_PASSWORD=ganti_password_app_kuat
MARIADB_DATABASE=trirara            # opsional (default trirara)
MARIADB_USER=trirara                # opsional (default trirara)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ganti_password_admin
CORS_ORIGINS=https://trirara.my.id   # opsi E saja (origin frontend PERSIS)

# Hanya selama migrasi dari versi MongoDB lama (lihat bagian 3):
MONGO_ROOT_USERNAME=root            # sama dengan nilai lama
MONGO_ROOT_PASSWORD=...             # sama dengan nilai lama
DB_NAME=ttp_ops                     # nama database Mongo lama (default ttp_ops)
```

Backend membaca koneksi dari `MARIADB_URL` **atau** `MARIADB_HOST/PORT/USER/PASSWORD/DATABASE`
(di compose sudah diisi otomatis: host `mariadb`, port `3306`). Contoh URL lengkap bila memakai MariaDB eksternal:
`MARIADB_URL=mysql+asyncmy://USER:PASSWORD@HOST:3306/trirara?charset=utf8mb4`

---

## 3. Migrasi data lama MongoDB → MariaDB (sekali jalan, aman)

Compose baru **masih menyertakan service `mongo` lama** dengan volume yang **sama** (`mongo_data`), hanya sebagai
**sumber baca**. Backend punya variabel `MIGRATE_FROM_MONGO_URL` & `MIGRATE_FROM_MONGO_DB` (sudah terisi di compose).

1. **Backup dulu dari aplikasi lama**: Bantuan & Backup → *Unduh Backup* (centang *Sertakan gambar WhatsApp*). Simpan file-nya.
2. Pastikan env `MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD`, `DB_NAME` **sama** dengan yang dipakai versi lama.
3. Tambahkan env MariaDB (bagian 2) → **Deploy**.
4. Saat backend start, data disalin otomatis (mode *merge*: MongoDB hanya dibaca, data yang sudah ada di MariaDB tidak ditimpa).
   Cek hasilnya di **Bantuan & Backup → panel Isi Database**: muncul **"Migrasi MongoDB → MariaDB selesai"** dan jumlah baris per tabel.
   Log backend juga menampilkan baris `[migrasi] OK <tabel> mongo=N -> mariadb=N`.
5. Cocokkan jumlah Unit, Ops Report, Kas Masuk, Kas Keluar dengan aplikasi lama.
6. Setelah yakin: hapus service `mongo`, baris `MIGRATE_FROM_MONGO_URL` / `MIGRATE_FROM_MONGO_DB`, dan `depends_on: mongo`
   dari compose → Deploy ulang. (Volume `mongo_data` boleh disimpan sementara sebagai cadangan.)

**Migrasi manual** (Coolify → backend → *Terminal*):
```
python scripts/migrate_mongo_to_mariadb.py --dry-run      # lihat jumlah tanpa menulis
python scripts/migrate_mongo_to_mariadb.py                 # jalankan (merge, aman diulang)
python scripts/migrate_mongo_to_mariadb.py --mongo-url "mongodb://root:PASS@HOST:27017/?authSource=admin" --mongo-db ttp_ops
```
**Tanpa akses Mongo** (mis. Mongo Atlas sudah mati): unggah file backup `.json.gz` lama ke container lalu
`python scripts/restore_db.py backup-lama.json.gz` — format backup lama didukung.

Sesi login tidak dimigrasi: semua pengguna cukup login ulang. Username, password, PIN, dan peran tetap sama.

---

## 4. Deploy opsi F (satu domain) — langkah ringkas

1. Coolify → **+ New Resource → Docker Compose** → repo ini → file `docker-compose.singledomain.yml`.
2. Isi Environment Variables (bagian 2).
3. Domain: **hanya** service `frontend` → `https://trirara.my.id` (port 80). `backend`, `mariadb`, `mongo` tanpa domain.
4. Deploy. Buka `https://trirara.my.id/login`.

## 5. Deploy opsi E (dua subdomain)

1. `frontend/.env.production` → `REACT_APP_BACKEND_URL=https://api.trirara.my.id` (tanpa `/api`), commit.
2. Docker Compose → `docker-compose.yml`. Domain: `frontend` → `https://trirara.my.id` (port 80),
   `backend` → `https://api.trirara.my.id` (port 8000). `mariadb` & `mongo` internal.
3. `CORS_ORIGINS` = origin frontend persis. Deploy.

## 6. Opsi B (resource terpisah)

- Database: Coolify → **+ New → Database → MariaDB** (atau compose `mariadb/docker-compose.yml`). Catat host internal, user, password.
- Backend: Application → Dockerfile, Base Directory `/backend`, port 8000, env `MARIADB_HOST`, `MARIADB_PORT`,
  `MARIADB_USER`, `MARIADB_PASSWORD`, `MARIADB_DATABASE` (atau `MARIADB_URL`). Pastikan backend & database di
  jaringan Docker yang sama ("Connect to Predefined Network").
- Frontend: Application → Dockerfile root `/Dockerfile`, port 80, domain frontend.

---

## 7. Login pertama

`/login` → tab **Username/Password** → `ADMIN_USERNAME` / `ADMIN_PASSWORD`. Admin awal hanya dibuat bila
belum ada admin di database (setelah migrasi, akun-akun lama langsung bisa dipakai).

## 8. Backup & pemulihan

- Aplikasi: **Bantuan & Backup → Unduh Backup** (.json.gz, semua tabel).
- Server: `python scripts/backup_db.py --out /app/backups --keep 14`
- SQL bawaan: `mariadb-dump -h mariadb -u trirara -p trirara | gzip > backup.sql.gz` (dari container mariadb).
- Restore: `python scripts/restore_db.py FILE.json.gz --dry-run` lalu `--mode merge` (default, tidak menimpa).
  Uji ke database terpisah: `--target-db trirara_restore_test`.

## Catatan & Troubleshooting

- **Backend log `[mariadb] belum siap ...`**: backend menunggu hingga 60 detik. Periksa service `mariadb` sehat dan
  `MARIADB_PASSWORD` sama di service mariadb & backend. Mengganti password **setelah** volume dibuat tidak
  mengubah password di database — ubah via `ALTER USER` atau buat volume baru.
- **`Access denied for user`**: user/password salah atau database belum dibuat (image MariaDB membuatnya otomatis
  dari `MARIADB_DATABASE` hanya saat volume pertama kali kosong).
- **Login gagal / 401 (opsi E)**: `CORS_ORIGINS` harus sama persis dengan origin frontend & keduanya HTTPS.
- **`.env.production` frontend** dibaca saat build — ubah URL backend → rebuild frontend.
- **`requirements.txt`** sengaja ramping & aman untuk `python:3.11-slim` (tanpa paket yang perlu compiler).
  Driver database: `SQLAlchemy[asyncio]` + `asyncmy` (wheel tersedia untuk x86_64 & ARM). `pymongo` tetap ada hanya
  untuk script migrasi & format backup JSON.
