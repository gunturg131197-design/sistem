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
    main_port = int(os.environ.get("PORT") or 8000)
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
    config = uvicorn.Config("server:app", proxy_headers=True, forwarded_allow_ips="*",
                            timeout_keep_alive=30, log_level="info")
    asyncio.run(uvicorn.Server(config).serve(sockets=socks))


if __name__ == "__main__":
    main()
