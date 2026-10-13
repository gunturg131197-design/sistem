"""Status Sistem (admin): versi commit yang tayang, waktu build/startup, status MariaDB, info runtime.

Tanpa rahasia: password/secret tidak pernah dikembalikan. Target DB ditampilkan sebagai user@host:port/db.
Sumber versi (urut prioritas):
  1. env SOURCE_COMMIT (Coolify, default "Runtime only") / APP_COMMIT / GIT_COMMIT / COOLIFY_SOURCE_COMMIT
  2. /app/build_info.json (ditulis Dockerfile saat build)
  3. `git rev-parse HEAD` (preview / pengembangan lokal)
"""
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Depends

ROOT_DIR = Path(__file__).parent
_VERSION_CACHE: dict = {}


def _git(*args) -> str:
    for cwd in (ROOT_DIR, ROOT_DIR.parent):
        try:
            out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=3)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except Exception:  # noqa: BLE001
            pass
    return ""


def version_info() -> dict:
    if _VERSION_CACHE:
        return _VERSION_CACHE
    build = {}
    try:
        build = json.loads((ROOT_DIR / "build_info.json").read_text())
    except Exception:  # noqa: BLE001
        pass
    commit, source = "", ""
    for k in ("SOURCE_COMMIT", "APP_COMMIT", "GIT_COMMIT", "COOLIFY_SOURCE_COMMIT"):
        v = (os.environ.get(k) or "").strip()
        if v:
            commit, source = v, f"env {k}"
            break
    if not commit and (build.get("commit") or "").strip():
        commit, source = build["commit"].strip(), "build_info.json"
    if not commit:
        commit = _git("rev-parse", "HEAD")
        source = "git" if commit else ""
    branch = (os.environ.get("COOLIFY_BRANCH") or "").strip() or _git("rev-parse", "--abbrev-ref", "HEAD")
    message = _git("log", "-1", "--format=%s") if source == "git" else ""
    committed_at = _git("log", "-1", "--format=%cI") if source == "git" else ""
    _VERSION_CACHE.update({
        "commit": commit or None,
        "commit_short": commit[:7] if commit else None,
        "commit_source": source or None,
        "branch": branch or None,
        "message": message or None,
        "committed_at": committed_at or None,
        "built_at": build.get("built_at") or None,
        "repo_url": "https://github.com/gunturg131197-design/sistem",
    })
    return _VERSION_CACHE


def build_system_status_router(db, require_admin: Callable, boot: dict) -> APIRouter:
    r = APIRouter()

    @r.get("/api/admin/system-status")
    async def system_status(admin=Depends(require_admin)):
        now = datetime.now(timezone.utc)
        started = boot.get("started_at")
        dbinfo = {"engine": "MariaDB", "name": db.name, "target": boot.get("target"), "ok": False,
                  "latency_ms": None, "server_version": None, "tables": None,
                  "error": None, "attempts": boot.get("db_attempts", 0)}
        t0 = time.perf_counter()
        try:
            await db.ping()
            dbinfo["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            dbinfo["ok"] = True
            try:
                rows = await db._fetch("SELECT VERSION()", {})
                dbinfo["server_version"] = str(rows[0][0]) if rows else None
                rows = await db._fetch("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()", {})
                dbinfo["tables"] = int(rows[0][0]) if rows else None
            except Exception:  # noqa: BLE001
                pass
        except Exception as e:  # noqa: BLE001
            dbinfo["error"] = boot.get("db_error") or f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"
        on_coolify = bool(os.environ.get("COOLIFY_RESOURCE_UUID") or os.environ.get("COOLIFY_FQDN"))
        return {
            "checked_at": now.isoformat(),
            "version": version_info(),
            "startup": {
                "started_at": started.isoformat() if started else None,
                "ready_at": boot["ready_at"].isoformat() if boot.get("ready_at") else None,
                "ready": bool(boot.get("ready")),
                "startup_seconds": round((boot["ready_at"] - started).total_seconds(), 1) if boot.get("ready_at") and started else None,
                "uptime_seconds": int((now - started).total_seconds()) if started else None,
            },
            "database": dbinfo,
            "runtime": {
                "platform": "Coolify" if on_coolify else "Preview / lokal",
                "domain": (os.environ.get("COOLIFY_FQDN") or "").split(",")[0] or None,
                "python": platform.python_version(),
                "timezone": os.environ.get("TZ") or "Asia/Makassar",
                "port": os.environ.get("PORT") or "8000",
                "extra_ports": os.environ.get("EXTRA_PORTS", ""),
            },
        }

    return r
