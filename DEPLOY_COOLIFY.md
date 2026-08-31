# Deploy EXCAVA.OPS di Coolify v4 (>= 4.3.14)

Aplikasi ini di-deploy sebagai **Docker Compose** (3 service: MongoDB, Backend FastAPI, Frontend React+nginx).
Hanya **frontend** yang diekspos ke domain publik; nginx di frontend otomatis mem-proxy `/api` ke backend,
sehingga login (cookie) berjalan aman dalam satu domain.

---

## Langkah Deploy

### 1. Siapkan kode
Pastikan seluruh repo (folder `backend/`, `frontend/`, dan `docker-compose.yml`) sudah ter-push ke
Git (GitHub/GitLab) yang bisa diakses Coolify. Gunakan fitur **"Save to Github"** di Emergent bila perlu.

### 2. Buat Resource di Coolify
1. Buka Coolify -> pilih Project/Server -> **+ New Resource**.
2. Pilih **Docker Compose** (Application) berbasis Git repository.
3. Arahkan ke repo kamu dan branch yang benar.
4. Coolify akan mendeteksi `docker-compose.yml` di root repo. Jika file compose ada di subfolder,
   set **Base Directory** / **Docker Compose Location** sesuai lokasinya (di sini: root `/`).

### 3. Set Environment Variables
Di tab **Environment Variables**, isi minimal (lihat `.env.example`):

```
DB_NAME=excava_ops
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ganti_dengan_password_kuat
ADMIN_NAME=Administrator
```

> `ADMIN_USERNAME` + `ADMIN_PASSWORD` dipakai untuk **membuat admin pertama otomatis** saat database
> masih kosong. Setelah admin ada, Anda bisa menambah operator/admin lain dari menu **Users** di aplikasi.

### 4. Atur Domain
1. Di daftar service, pilih service **frontend**.
2. Set **Domain** (FQDN) kamu, mis. `https://excava.domainku.com`.
3. Pastikan **Port** yang di-expose = **80** (nginx). Coolify akan menangani HTTPS (Let's Encrypt) otomatis.
4. Service `backend` dan `mongo` **TIDAK** perlu domain (internal saja).

### 5. Deploy
Klik **Deploy**. Coolify akan build image backend & frontend lalu menjalankan ketiga service.

### 6. Login pertama
Buka domain kamu -> halaman **/login** -> tab **Username/Password** -> masuk dengan
`ADMIN_USERNAME` / `ADMIN_PASSWORD` yang tadi di-set.

---

## Catatan Penting

- **Persistensi data**: MongoDB memakai named volume `mongo_data`. Jangan hapus volume ini agar data tidak hilang saat re-deploy.
- **Backend URL**: Tidak perlu di-set. Frontend memakai path relatif `/api` (di-proxy nginx ke backend). Karena itu tidak ada masalah cookie lintas-domain.
- **CPU tanpa AVX**: `mongo:7` butuh CPU yang mendukung AVX. Bila server VPS lama gagal menjalankan Mongo,
  ganti baris image di `docker-compose.yml` menjadi `image: mongo:4.4` (masih kompatibel).
- **Ganti password admin**: Setelah login pertama, buat admin baru berpassword kuat atau ganti password melalui menu Users, lalu hapus/nonaktifkan default bila perlu.
- **Google OAuth (opsional)**: Login via Google akan menjadikan email di `ADMIN_EMAILS` sebagai admin. Login manual (username/password) tidak butuh ini.
- **Rebuild frontend**: Bila mengubah kode frontend, Coolify otomatis build ulang saat deploy. Env `REACT_APP_BACKEND_URL` dibiarkan kosong (same-origin).

---

## Ringkasan Arsitektur

```
            (HTTPS, domain kamu)
Browser  ->  Coolify Traefik  ->  frontend (nginx :80)
                                     |-- serve React build (static)
                                     |-- /api/*  ->  backend (FastAPI :8001)
                                                        |-- mongo (:27017)
```
