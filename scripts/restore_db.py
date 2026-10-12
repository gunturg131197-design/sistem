#!/usr/bin/env python3
"""Pulihkan database dari file backup .json.gz (buatan tombol Backup di aplikasi atau backup_db.py).

KEAMANAN — default TIDAK menghapus dan TIDAK menimpa data:
  --mode merge    (default) hanya menambahkan dokumen yang belum ada (berdasarkan _id). Data saat ini tetap utuh.
  --mode replace  menimpa dokumen dengan _id sama memakai versi backup (dokumen lain tetap ada). Wajib --yes.
  --target-db     pulihkan ke database LAIN (disarankan untuk uji restore), mis. trirara_restore_test
  --dry-run       hanya hitung, tidak menulis apa pun
Tidak ada opsi drop/reset database.

Contoh:
  python /app/scripts/restore_db.py backup.json.gz --dry-run
  python /app/scripts/restore_db.py backup.json.gz --target-db trirara_restore_test
  python /app/scripts/restore_db.py backup.json.gz --mode merge
"""
import argparse
import gzip
import os
import sys

from bson import json_util
from dotenv import load_dotenv
from pymongo import MongoClient, ReplaceOne
from pymongo.errors import BulkWriteError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--mode", choices=["merge", "replace"], default="merge")
    ap.add_argument("--target-db", default="")
    ap.add_argument("--only", default="", help="koleksi tertentu, pisahkan koma")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    load_dotenv("/app/backend/.env")
    url = os.environ.get("MONGO_URL")
    target = a.target_db or os.environ.get("DB_NAME")
    if not url or not target:
        sys.exit("MONGO_URL / DB_NAME tidak ditemukan")
    if a.mode == "replace" and not a.yes and not a.dry_run:
        sys.exit("Mode replace menimpa dokumen dengan _id sama. Jalankan ulang dengan --yes bila yakin.")
    with gzip.open(a.file, "rb") as f:
        data = json_util.loads(f.read().decode())
    meta = data.get("meta") or {}
    if meta.get("format") != "trirara-backup-v1":
        sys.exit("File bukan backup TRIRARA yang valid")
    print(f"Backup {meta.get('created_at')} oleh {meta.get('created_by')} (db asal {meta.get('db')}) -> target db '{target}' mode {a.mode}"
          + (" [DRY RUN]" if a.dry_run else ""))
    db = MongoClient(url)[target]
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    for name, docs in (data.get("collections") or {}).items():
        if only and name not in only:
            continue
        existing = set(d["_id"] for d in db[name].find({}, {"_id": 1})) if docs else set()
        new = [d for d in docs if d.get("_id") not in existing]
        same = len(docs) - len(new)
        if a.dry_run:
            print(f"  {name}: {len(docs)} di backup · {len(new)} baru · {same} sudah ada")
            continue
        added = replaced = 0
        if new:
            try:
                added = len(db[name].insert_many(new, ordered=False).inserted_ids)
            except BulkWriteError as e:
                added = e.details.get("nInserted", 0)
                print(f"  {name}: {len(e.details.get('writeErrors', []))} dokumen dilewati (konflik indeks unik)")
        if a.mode == "replace" and same:
            ops = [ReplaceOne({"_id": d["_id"]}, d) for d in docs if d.get("_id") in existing]
            replaced = db[name].bulk_write(ops, ordered=False).modified_count
        print(f"  {name}: +{added} ditambahkan" + (f", {replaced} ditimpa" if a.mode == "replace" else f", {same} sudah ada (dibiarkan)"))
    print("Selesai.")


if __name__ == "__main__":
    main()
