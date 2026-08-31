# Deploy EXCAVA.OPS di Coolify v4 (>= 4.3.14) — Dua Subdomain

Arsitektur: **Frontend** dan **Backend** di-deploy sebagai **dua Application terpisah** (berbasis Dockerfile),
plus **MongoDB** (disarankan MongoDB Atlas / atau container Mongo tersendiri).

```
Frontend : https://sistem.domainanda.com        (React + nginx, port 80)
Backend  : https://api.sistem.domainanda.com     (FastAPI/uvicorn, port 8000)
Database : MongoDB Atlas (mongodb+srv://...)      atau Mongo container
```

> Keduanya berada di bawah satu domain induk (`domainanda.com`) sehingga cookie login
> (`SameSite=None; Secure`) tetap valid antar-subdomain. HTTPS wajib (Coolify menyediakan via Let's Encrypt).

---

## A. Deploy BACKEND (FastAPI)

1. Coolify → **+ New Resource → Application → Dockerfile / Git**.
2. Pilih repo Anda.
3. **Base Directory**: arahkan ke folder backend, mis. `/sistem-ttp-cpanel/backend`
   (sesuaikan dengan struktur repo GitHub Anda). **Dockerfile**: `/Dockerfile` (relatif thd Base Directory).
4. **Port**: `8000` (sesuai `EXPOSE 8000` di Dockerfile).
5. **Domain**: `https://api.sistem.domainanda.com`.
6. **Environment Variables** (JANGAN commit ke GitHub):
   ```
   MONGO_URL=mongodb+srv://USERNAME:PASSWORD@CLUSTER.mongodb.net/?retryWrites=true&w=majority
   DB_NAME=ttp_ops
   CORS_ORIGINS=https://sistem.domainanda.com

   # Bootstrap admin pertama (DB kosong) — GANTI passwordnya!
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=ganti_password_kuat
   ADMIN_NAME=Administrator
   # Opsional: email Google yang otomatis jadi admin (pisah koma)
   ADMIN_EMAILS=
   ```
   > **PENTING**: `CORS_ORIGINS` harus **persis** origin frontend (bukan `*`), karena login memakai
   > cookie berkredensial. Kalau salah, login akan gagal (CORS blok).
7. **Start Command**: kosongkan (CMD sudah ada di Dockerfile). Jangan pakai `npm start`/lainnya.
8. Deploy.

Cek sehat: buka `https://api.sistem.domainanda.com/docs` → harus muncul Swagger UI.

---

## B. Deploy FRONTEND (React + nginx)

1. **Edit `frontend/.env.production`** → ganti nilai `REACT_APP_BACKEND_URL` ke subdomain backend Anda
   (TANPA `/api` di akhir), lalu commit:
   ```
   REACT_APP_BACKEND_URL=https://api.sistem.domainanda.com
   ```
   Kode `src/lib/api.js` menambahkan `/api` otomatis → `https://api.sistem.domainanda.com/api`.
2. Coolify → **+ New Resource → Application → Dockerfile / Git** (repo yang sama).
3. **Base Directory**: `/sistem-ttp-cpanel/frontend` (sesuaikan repo Anda). **Dockerfile**: `/Dockerfile`.
4. **Port**: `80`.
5. **Domain**: `https://sistem.domainanda.com`.
6. **Start Command**: kosongkan (Dockerfile sudah `CMD ["nginx","-g","daemon off;"]`). Hapus `npm start`.
7. Deploy.

---

## C. Login pertama

Buka `https://sistem.domainanda.com/login` → tab **Username/Password** →
masuk dengan `ADMIN_USERNAME` / `ADMIN_PASSWORD` yang di-set di backend.
Setelah masuk, tambah operator/admin lain dari menu **Users**.

---

## Catatan & Troubleshooting

- **`.env.production` frontend**: nilainya dibaca saat BUILD (`npm run build`). Jika mengubah URL backend,
  Anda harus **redeploy/rebuild** frontend agar berubah.
- **Lama muncul `.../api-dev/api`?** Itu karena nilai lama `REACT_APP_BACKEND_URL` mengandung path.
  Pastikan hanya origin murni: `https://api.sistem.domainanda.com` (tanpa `/api`, tanpa `/api-dev`).
- **Login gagal / 401 setelah login**: hampir selalu karena `CORS_ORIGINS` di backend tidak sama persis
  dengan origin frontend, atau salah satu sisi belum HTTPS. Cookie butuh HTTPS (Secure) + origin eksak.
- **`requirements.txt`**: sudah dibersihkan agar aman di `python:3.11-slim`
  (menghapus `emergentintegrations` yang tidak ada di PyPI & `jq` yang butuh compiler; menambahkan `httpx`
  yang dipakai kode). Jangan menambah lagi paket yang butuh kompilasi tanpa menyiapkan build tools.
- **MongoDB Atlas**: whitelist IP server Coolify Anda (atau `0.0.0.0/0` untuk uji) di Atlas Network Access.
- **Alternatif Mongo tanpa Atlas**: buat satu lagi resource **Database → MongoDB** di Coolify, lalu pakai
  connection string internalnya sebagai `MONGO_URL` (mis. `mongodb://user:pass@host:27017`).
- **Google OAuth (opsional)**: hanya relevan bila memakai login Google; email pada `ADMIN_EMAILS`
  otomatis menjadi admin. Login manual (username/password) tidak membutuhkannya.
