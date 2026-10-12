#!/usr/bin/env python3
"""Pulihkan database (MariaDB) dari file backup .json.gz (tombol Backup di aplikasi, backup_db.py,
atau backup LAMA dari versi MongoDB — formatnya sama: trirara-backup-v1).

KEAMANAN — default TIDAK menghapus dan TIDAK menimpa data:
  --mode merge    (default) hanya menambahkan baris yang belum ada (berdasarkan kunci alami: id / key / user_id ...).
  --mode replace  menimpa baris dengan kunci sama memakai versi backup (baris lain tetap ada). Wajib --yes.
  --target-db     pulihkan ke database MariaDB LAIN (disarankan untuk uji restore), mis. trirara_restore_test
                  (user MariaDB perlu hak CREATE DATABASE, atau buat database-nya dulu).
  --dry-run       hanya hitung, tidak menulis apa pun
Tidak ada opsi drop/reset database.

Contoh:
  python scripts/restore_db.py backup.json.gz --dry-run
  python scripts/restore_db.py backup.json.gz --target-db trirara_restore_test
  python scripts/restore_db.py backup.json.gz --mode merge
"""
import argparse
import asyncio
import gzip
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

BACKEND = Path(__file__).resolve().parent.parent  # folder berisi server.py / db_schema.py
sys.path.insert(0, str(BACKEND))

from bson import json_util  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from db_schema import TABLES  # noqa: E402
from mariadb_store import DuplicateKeyError, Store, build_url_from_env  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from migrate_mongo_to_mariadb import clean, natural_key  # noqa: E402


def with_db(url: str, name: str) -> str:
    u = urlparse(url)
    return urlunparse(u._replace(path="/" + name))


async def run(a):
    url = build_url_from_env(dict(os.environ))
    if a.target_db:
        from sqlalchemy import text
        admin = Store(url)
        try:
            async with admin.engine.begin() as c:
                await c.execute(text(f"CREATE DATABASE IF NOT EXISTS `{a.target_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        except Exception as e:  # noqa: BLE001
            print(f"(info) tidak bisa membuat database {a.target_db}: {str(e)[:120]} — pastikan sudah dibuat")
        await admin.close()
        url = with_db(url, a.target_db)
    with gzip.open(a.file, "rb") as f:
        data = json_util.loads(f.read().decode())
    meta = data.get("meta") or {}
    if meta.get("format") != "trirara-backup-v1":
        sys.exit("File bukan backup TRIRARA yang valid")
    db = Store(url)
    await db.init_schema()
    print(f"Backup {meta.get('created_at')} oleh {meta.get('created_by')} (db asal {meta.get('db')}, {meta.get('engine', 'mongodb')})"
          f" -> MariaDB '{db.name}' mode {a.mode}" + (" [DRY RUN]" if a.dry_run else ""))
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    for name, docs in (data.get("collections") or {}).items():
        if only and name not in only:
            continue
        coll = db[name]
        keys = (TABLES.get(name) or {}).get("key") or []
        existing = set()
        if keys and docs:
            for d in await coll.find({}, {k: 1 for k in keys}).to_list(None):
                k = natural_key(name, d)
                if k is not None:
                    existing.add(k)
        added = replaced = same = skipped = 0
        for raw in docs:
            doc = clean(raw)
            k = natural_key(name, doc)
            if k is not None and k in existing:
                same += 1
                if a.mode == "replace" and not a.dry_run:
                    await coll.replace_one(dict(zip(keys, k)), doc)
                    replaced += 1
                continue
            if a.dry_run:
                added += 1
                continue
            try:
                await coll.insert_one(doc)
                added += 1
                if k is not None:
                    existing.add(k)
            except DuplicateKeyError:
                skipped += 1
        if a.dry_run:
            print(f"  {name}: {len(docs)} di backup · {added} baru · {same} sudah ada")
        else:
            print(f"  {name}: +{added} ditambahkan" + (f", {replaced} ditimpa" if a.mode == "replace" else f", {same} sudah ada (dibiarkan)")
                  + (f", {skipped} dilewati (konflik indeks unik)" if skipped else ""))
    await db.close()
    print("Selesai.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--mode", choices=["merge", "replace"], default="merge")
    ap.add_argument("--target-db", default="")
    ap.add_argument("--only", default="", help="tabel tertentu, pisahkan koma")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    load_dotenv(BACKEND / ".env")
    if a.mode == "replace" and not a.yes and not a.dry_run:
        sys.exit("Mode replace menimpa baris dengan kunci sama. Jalankan ulang dengan --yes bila yakin.")
    asyncio.run(run(a))


if __name__ == "__main__":
    main()
