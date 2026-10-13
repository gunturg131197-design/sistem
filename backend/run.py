"""Entrypoint produksi (Dockerfile): SATU proses uvicorn yang listen di beberapa port sekaligus.

- PORT        (default 8000) : port utama → isi "Ports Exposes" Coolify dengan ini
- EXTRA_PORTS (default 3000) : port cadangan (dipisah koma) agar tetap jalan bila "Ports Exposes"
                               Coolify masih bawaan (3000). Kosongkan untuk menonaktifkan.
Satu proses = tugas startup (migrasi/backfill/penjadwal) tetap berjalan sekali.
"""
import asyncio
import logging
import os
import socket

import uvicorn


def _bind(port: int):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(2048)
    s.set_inheritable(True)
    return s


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - run - %(levelname)s - %(message)s")
    lg = logging.getLogger("run")
    raw_port = (os.environ.get("PORT") or "").strip()
    if raw_port and not raw_port.isdigit():
        lg.error(f"PORT='{raw_port}' bukan angka — memakai 8000. Perbaiki env PORT di Coolify.")
    main_port = int(raw_port) if raw_port.isdigit() else 8000
    ports = [main_port]
    for p in (os.environ.get("EXTRA_PORTS", "3000") or "").split(","):
        p = p.strip()
        if p.isdigit() and int(p) not in ports:
            ports.append(int(p))
    socks = []
    for p in ports:
        try:
            socks.append(_bind(p))
        except OSError as e:
            if p == main_port:
                raise
            lg.warning(f"port cadangan {p} dilewati: {e}")
    lg.info(f"listen di port: {', '.join(str(s.getsockname()[1]) for s in socks)} (utama {main_port})")
    app = _load_app(lg)
    config = uvicorn.Config(app, proxy_headers=True, forwarded_allow_ips="*",
                            timeout_keep_alive=30, log_level="info")
    asyncio.run(uvicorn.Server(config).serve(sockets=socks))


_SECRET_HINTS = ("PASS", "SECRET", "TOKEN", "KEY", "URL")


def _mask(text: str) -> str:
    """Samarkan nilai env rahasia & URL berkredensial di pesan error."""
    import re
    for k, v in os.environ.items():
        if v and len(v) >= 4 and any(h in k.upper() for h in _SECRET_HINTS):
            text = text.replace(v, "***")
    return re.sub(r"([A-Za-z][A-Za-z0-9+.-]*://)[^\s@/'\"]*@", r"\1***@", text)


def _load_app(lg):
    """Import aplikasi utama. Bila gagal (bug/konfigurasi), JANGAN crash (crash = container Restarting = 503 Traefik):
    jalankan mode aman yang hidup di port yang sama & menampilkan penyebabnya di /api/health."""
    try:
        import server  # noqa: F401
        return server.app
    except Exception as e:  # noqa: BLE001
        import json
        import traceback
        tb = _mask(traceback.format_exc())
        reason = _mask(f"{type(e).__name__}: {str(e).splitlines()[0][:300] if str(e) else ''}")
        lg.error("APLIKASI GAGAL START — mode aman aktif (container tetap hidup). Penyebab: " + reason)
        lg.error(tb)
        last = [ln.strip() for ln in tb.strip().splitlines() if ln.strip().startswith("File ")][-1:]

        async def safe_app(scope, receive, send):
            if scope["type"] == "lifespan":
                while True:
                    msg = await receive()
                    if msg["type"] == "lifespan.startup":
                        await send({"type": "lifespan.startup.complete"})
                    elif msg["type"] == "lifespan.shutdown":
                        await send({"type": "lifespan.shutdown.complete"})
                        return
            if scope["type"] != "http":
                return
            path = scope.get("path", "")
            if path == "/api/health/live":
                code, body = 200, {"status": "degraded", "safe_mode": True, "error": reason}
            elif path.startswith("/api/"):
                code, body = 503, {"status": "error", "safe_mode": True, "detail": reason, "where": last,
                                   "hint": "Aplikasi gagal start. Perbaiki penyebab di atas (biasanya env), lalu Redeploy."}
            else:
                code, body = 503, None
            if body is None:
                payload = ("Aplikasi sedang dalam mode aman: gagal start.\nPenyebab: " + reason +
                           "\nDetail: /api/health").encode()
                ctype = b"text/plain; charset=utf-8"
            else:
                payload, ctype = json.dumps(body, ensure_ascii=False).encode(), b"application/json"
            await send({"type": "http.response.start", "status": code,
                        "headers": [(b"content-type", ctype), (b"content-length", str(len(payload)).encode())]})
            await send({"type": "http.response.body", "body": payload})

        return safe_app


if __name__ == "__main__":
    main()
