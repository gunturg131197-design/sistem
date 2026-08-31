# ============================================================
# Dockerfile ROOT untuk FRONTEND (EXCAVA.OPS)
# Coolify: Base Directory = /   |   Dockerfile = /Dockerfile
# Build context = root repo, jadi path COPY relatif dari root repo.
#
# CATATAN STRUKTUR REPO:
#   Repo ini menaruh folder "frontend/" & "backend/" LANGSUNG di root.
#   Karena itu COPY memakai "frontend/...".
#   Jika repo Anda menaruhnya di dalam subfolder (mis. sistem-ttp-cpanel/),
#   ganti "frontend/" -> "sistem-ttp-cpanel/frontend/" pada baris COPY di bawah.
# ============================================================

FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package*.json ./

RUN npm install

COPY frontend/ ./

RUN npm run build


FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html

# Wajib untuk React Router (deep-link/refresh tidak 404)
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
