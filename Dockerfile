# syntax=docker/dockerfile:1.6
# ============================================================================
# TRIRARA / EXCAVA.OPS — Dockerfile TUNGGAL (root) untuk Coolify
# Build Pack: Dockerfile   |   Base Directory: /   |   Dockerfile Location: /Dockerfile
#
# Stack  : React (CRA + craco) frontend  +  FastAPI (Python 3.11) backend  +  MariaDB (eksternal)
# Hasil  : SATU container. FastAPI melayani API di /api/* dan file React hasil build
#          di path lainnya (same-origin → tanpa CORS, cookie login aman).
# Port   : env PORT (default 8000)  → isi "Ports Exposes" di Coolify = 8000
#
# Stage 1  frontend-build : node:20-alpine  → yarn build (static files)
# Stage 2  backend-build  : python:3.11-slim → venv berisi dependency runtime saja
# Stage 3  production     : python:3.11-slim → venv + kode backend + build frontend, user non-root
# ============================================================================

# ---------------------------------------------------------------------------
# Stage 1: build frontend React
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend-build
WORKDIR /build

# Kosong = frontend memanggil API di origin yang sama (/api). Isi hanya bila backend di domain lain.
ARG REACT_APP_BACKEND_URL=""
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL} \
    GENERATE_SOURCEMAP=false \
    DISABLE_ESLINT_PLUGIN=true \
    CI=false \
    NODE_OPTIONS=--max-old-space-size=3072

# Layer dependency terpisah agar cache build dipakai ulang bila hanya kode yang berubah
COPY frontend/package.json frontend/yarn.lock* ./
RUN yarn install --frozen-lockfile --ignore-engines --network-timeout 600000 \
    || yarn install --ignore-engines --network-timeout 600000

COPY frontend/ ./
RUN rm -f .env .env.* && yarn build

# ---------------------------------------------------------------------------
# Stage 2: install dependency Python ke virtualenv
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS backend-build
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY backend/requirements.prod.txt /tmp/requirements.prod.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.prod.txt
# Opsional: AI pembaca gambar WA (bukti transfer / foto HM) via EMERGENT_LLM_KEY.
# Build arg INSTALL_AI=0 untuk melewati (image lebih kecil, fitur AI nonaktif). Gagal install tidak menggagalkan build.
ARG INSTALL_AI=1
RUN if [ "$INSTALL_AI" = "1" ]; then \
      pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
      || echo "WARN: emergentintegrations gagal dipasang - fitur AI baca-gambar nonaktif"; \
    fi

# ---------------------------------------------------------------------------
# Stage 3: image produksi (kecil: tanpa node, tanpa build tools, tanpa dev deps)
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS production

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Makassar \
    PORT=8000 \
    EXTRA_PORTS=3000 \
    STATIC_DIR=/app/static

# curl & wget: dibutuhkan "Health Check" bawaan Coolify (dijalankan di dalam container)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl wget ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home /app app
WORKDIR /app

COPY --from=backend-build /opt/venv /opt/venv
COPY --chown=app:app backend/ /app/
COPY --from=frontend-build --chown=app:app /build/build /app/static
RUN rm -f /app/.env /app/requirements.txt && mkdir -p /app/backups && chown app:app /app /app/backups

USER app
# 8000 = port utama (isi "Ports Exposes" Coolify = 8000). 3000 = cadangan bila Ports Exposes masih bawaan Coolify.
EXPOSE 8000 3000

# Liveness: proses hidup (selalu 200 meski DB belum siap) agar Traefik tetap meneruskan trafik.
# Status database lengkap: buka https://DOMAIN/api/health
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/health/live" >/dev/null || exit 1

# 1 proses uvicorn (tugas startup & penjadwal internal berjalan tunggal), listen di PORT + EXTRA_PORTS
CMD ["python", "run.py"]
