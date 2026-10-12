#!/usr/bin/env python3
"""Backup database TRIRARA ke file .json.gz (hanya-baca, aman dijalankan kapan saja).

Pemakaian:
  python /app/scripts/backup_db.py                      # pakai MONGO_URL & DB_NAME dari /app/backend/.env
  python /app/scripts/backup_db.py --out /backup/dir    # folder tujuan (default /app/backups)
  python /app/scripts/backup_db.py --include-media      # sertakan gambar WhatsApp (besar)
  python /app/scripts/backup_db.py --keep 14            # simpan 14 file terbaru, hapus file backup lama di folder tujuan
Alternatif bawaan MongoDB: mongodump --uri "$MONGO_URL" --db "$DB_NAME" --gzip --archive=backup.gz
"""
import argparse
import gzip
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bson import json_util
from dotenv import load_dotenv
from pymongo import MongoClient

EXCLUDE = {"user_sessions"}
MEDIA = {"wa_media"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/backups")
    ap.add_argument("--include-media", action="store_true")
    ap.add_argument("--keep", type=int, default=0, help="jumlah file backup terbaru yang disimpan (0 = semua)")
    a = ap.parse_args()
    load_dotenv("/app/backend/.env")
    url, name = os.environ.get("MONGO_URL"), os.environ.get("DB_NAME")
    if not url or not name:
        sys.exit("MONGO_URL / DB_NAME tidak ditemukan")
    db = MongoClient(url)[name]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo("Asia/Makassar")).strftime("%Y%m%d-%H%M%S")
    path = out / f"backup-trirara-{stamp}-WITA.json.gz"
    names = sorted(n for n in db.list_collection_names() if n not in EXCLUDE and not n.startswith("system.") and (a.include_media or n not in MEDIA))
    total = 0
    with gzip.open(path, "wb") as gz:
        meta = {"app": "TRIRARA TUNGGAL PUTRA", "format": "trirara-backup-v1", "created_at": datetime.utcnow().isoformat() + "Z",
                "created_by": "script", "db": name, "include_media": a.include_media}
        gz.write(b'{"meta": ' + json_util.dumps(meta).encode() + b', "collections": {')
        for i, n in enumerate(names):
            gz.write(("," if i else "").encode() + json_util.dumps(n).encode() + b": [")
            for j, d in enumerate(db[n].find({})):
                gz.write((b"," if j else b"") + json_util.dumps(d).encode())
                total += 1
            gz.write(b"]")
            print(f"  {n}: {db[n].estimated_document_count()} dokumen")
        gz.write(b"}}")
    print(f"OK  {path}  ({total} dokumen, {path.stat().st_size / 1024:.1f} KB)")
    if a.keep > 0:
        files = sorted(out.glob("backup-trirara-*.json.gz"))
        for f in files[:-a.keep]:
            f.unlink()
            print(f"hapus backup lama: {f.name}")


if __name__ == "__main__":
    main()
