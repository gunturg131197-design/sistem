"""Backup database MariaDB (admin) — unduh arsip .json.gz berisi semua tabel (format trirara-backup-v1, JSON).

Aman: hanya-baca, tidak pernah menghapus / mereset data. Koleksi sesi login (token) tidak ikut dicadangkan.
Gambar WhatsApp (wa_media) opsional karena ukurannya besar.
Pemulihan dilakukan dengan scripts/restore_db.py (mode default: hanya menambah dokumen yang belum ada).
"""
import gzip
import io
import uuid
from datetime import datetime, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from bson import json_util
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

EXCLUDE = {"user_sessions"}  # token sesi tidak pernah dicadangkan
MEDIA = {"wa_media"}


def build_backup_router(db, require_admin: Callable) -> APIRouter:
    r = APIRouter()

    @r.get("/api/admin/backup/info")
    async def info(admin=Depends(require_admin)):
        names = sorted(n for n in await db.list_collection_names() if n not in EXCLUDE and not n.startswith("system."))
        counts = {n: await db[n].estimated_document_count() for n in names}
        last = await db.app_settings.find_one({"key": "last_backup"}, {"_id": 0})
        mig = await db.app_settings.find_one({"key": "mongo_migration"}, {"_id": 0, "tables": 0})
        return {"collections": counts, "excluded": sorted(EXCLUDE), "media_collections": sorted(MEDIA), "last_backup": last,
                "database": {"engine": "MariaDB", "name": db.name}, "migration": mig}

    @r.get("/api/admin/backup")
    async def download(include_media: bool = False, admin=Depends(require_admin)):
        names = sorted(n for n in await db.list_collection_names() if n not in EXCLUDE and not n.startswith("system.")
                       and (include_media or n not in MEDIA))
        buf = io.BytesIO()
        counts = {}
        now = datetime.now(timezone.utc)
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            meta = {"app": "TRIRARA TUNGGAL PUTRA", "format": "trirara-backup-v1", "created_at": now.isoformat(),
                    "created_by": admin.name, "db": db.name, "engine": "mariadb", "include_media": include_media}
            gz.write(b'{"meta": ' + json_util.dumps(meta).encode() + b', "collections": {')
            for i, n in enumerate(names):
                gz.write(("," if i else "").encode() + json_util.dumps(n).encode() + b": [")
                c = 0
                async for d in db[n].find({}):
                    gz.write((b"," if c else b"") + json_util.dumps(d).encode())
                    c += 1
                gz.write(b"]")
                counts[n] = c
            gz.write(b"}}")
        await db.app_settings.update_one({"key": "last_backup"}, {"$set": {"key": "last_backup", "at": now.isoformat(), "by": admin.name,
                                                                          "counts": counts, "include_media": include_media}}, upsert=True)
        await db.wa_audit.insert_one({"id": str(uuid.uuid4()), "at": now.isoformat(), "action": "backup_downloaded", "actor": admin.name,
                                      "inbox_id": "", "detail": f"Backup database diunduh ({sum(counts.values())} dokumen, {len(counts)} koleksi"
                                                                 f"{', termasuk gambar' if include_media else ''})", "data": {"counts": counts}})
        stamp = now.astimezone(ZoneInfo("Asia/Makassar")).strftime("%Y%m%d-%H%M")
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/gzip",
                                 headers={"Content-Disposition": f'attachment; filename="backup-trirara-{stamp}-WITA.json.gz"',
                                          "Cache-Control": "no-store"})

    return r
