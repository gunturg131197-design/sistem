#!/usr/bin/env python3
"""Backup database TRIRARA (MariaDB) ke file .json.gz (hanya-baca, aman dijalankan kapan saja).

Format file sama dengan tombol Backup di aplikasi (trirara-backup-v1), dapat dipulihkan dengan restore_db.py.

Pemakaian:
  python scripts/backup_db.py                      # koneksi dari MARIADB_URL di /app/backend/.env / env server
  python scripts/backup_db.py --out /backup/dir    # folder tujuan (default /app/backups)
  python scripts/backup_db.py --include-media      # sertakan gambar WhatsApp (besar)
  python scripts/backup_db.py --keep 14            # simpan 14 file terbaru, hapus file backup lama di folder tujuan
Alternatif bawaan MariaDB (SQL): mariadb-dump -h HOST -u USER -p NAMA_DB | gzip > backup.sql.gz
"""
import argparse
import asyncio
import gzip
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BACKEND = Path(__file__).resolve().parent.parent  # folder berisi server.py / db_schema.py
sys.path.insert(0, str(BACKEND))

from bson import json_util  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from db_schema import TABLES  # noqa: E402
from mariadb_store import Store, build_url_from_env  # noqa: E402

EXCLUDE = {"user_sessions"}
MEDIA = {"wa_media"}


async def run(a):
    db = Store(build_url_from_env(dict(os.environ)))
    await db.init_schema()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo("Asia/Makassar")).strftime("%Y%m%d-%H%M%S")
    path = out / f"backup-trirara-{stamp}-WITA.json.gz"
    names = sorted(n for n in await db.list_collection_names() if n not in EXCLUDE and (a.include_media or n not in MEDIA))
    total = 0
    with gzip.open(path, "wb") as gz:
        meta = {"app": "TRIRARA TUNGGAL PUTRA", "format": "trirara-backup-v1", "engine": "mariadb",
                "created_at": datetime.now(timezone.utc).isoformat(), "created_by": "script", "db": db.name, "include_media": a.include_media}
        gz.write(b'{"meta": ' + json_util.dumps(meta).encode() + b', "collections": {')
        for i, n in enumerate(names):
            gz.write(("," if i else "").encode() + json_util.dumps(n).encode() + b": [")
            docs = await db[n].find({}).to_list(None)
            for j, d in enumerate(docs):
                gz.write((b"," if j else b"") + json_util.dumps(d).encode())
            total += len(docs)
            gz.write(b"]")
            print(f"  {n}: {len(docs)} baris")
        gz.write(b"}}")
    await db.close()
    print(f"OK  {path}  ({total} baris, {path.stat().st_size / 1024:.1f} KB)")
    if a.keep > 0:
        files = sorted(out.glob("backup-trirara-*.json.gz"))
        for f in files[:-a.keep]:
            f.unlink()
            print(f"hapus backup lama: {f.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/backups")
    ap.add_argument("--include-media", action="store_true")
    ap.add_argument("--keep", type=int, default=0, help="jumlah file backup terbaru yang disimpan (0 = semua)")
    a = ap.parse_args()
    load_dotenv(BACKEND / ".env")
    _ = TABLES
    asyncio.run(run(a))


if __name__ == "__main__":
    main()
