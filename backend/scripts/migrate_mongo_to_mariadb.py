#!/usr/bin/env python3
"""Migrasi SELURUH data TRIRARA dari MongoDB lama -> MariaDB (tabel relasional, lihat db_schema.py).

AMAN:
  - MongoDB hanya DIBACA (tidak pernah diubah / dihapus).
  - Default mode `merge`: baris yang sudah ada di MariaDB (berdasarkan kunci alami: id / key / user_id / run_id ...)
    DIBIARKAN, hanya data yang belum ada yang ditambahkan -> boleh dijalankan berulang kali.
  - `--mode replace --yes`: baris dengan kunci sama ditimpa versi MongoDB.
  - `--dry-run`: hanya menghitung, tidak menulis apa pun.
  - Di akhir ditampilkan verifikasi jumlah data MongoDB vs MariaDB per tabel.

Koneksi:
  MongoDB : --mongo-url (default env MIGRATE_FROM_MONGO_URL / MONGO_URL) & --mongo-db (default env MIGRATE_FROM_MONGO_DB / DB_NAME)
  MariaDB : env MARIADB_URL / DATABASE_URL, atau MARIADB_HOST/PORT/USER/PASSWORD/DATABASE (atau --mariadb-url)

Di Coolify (Terminal container backend):
  python scripts/migrate_mongo_to_mariadb.py --dry-run
  python scripts/migrate_mongo_to_mariadb.py
"""
import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent  # folder berisi server.py / db_schema.py
sys.path.insert(0, str(BACKEND))

from bson import Binary, Decimal128, ObjectId  # noqa: E402

from db_schema import TABLES  # noqa: E402
from mariadb_store import DuplicateKeyError, Store, build_url_from_env  # noqa: E402

SKIP = {"user_sessions"}  # sesi login tidak dimigrasi (pengguna cukup login ulang)


def clean(v):
    """Konversi tipe khusus MongoDB ke tipe yang dipakai aplikasi."""
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items() if k != "_id"}
    if isinstance(v, list):
        return [clean(x) for x in v]
    if isinstance(v, datetime):
        return (v if v.tzinfo else v.replace(tzinfo=timezone.utc)).isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, Binary):
        return bytes(v)
    if isinstance(v, Decimal128):
        return float(v.to_decimal())
    return v


def natural_key(name: str, doc: dict):
    keys = (TABLES.get(name) or {}).get("key") or []
    if not keys:
        return None
    vals = tuple(doc.get(k) for k in keys)
    return None if any(v is None for v in vals) else vals


async def migrate_all(mongo_url: str, mongo_db: str, store: Store, mode: str = "merge", dry_run: bool = False,
                      only: set | None = None, with_sessions: bool = False, log=print) -> dict:
    """Salin semua koleksi Mongo -> MariaDB. Mengembalikan ringkasan {tabel: {...}} + ok."""
    from pymongo import MongoClient
    mongo = MongoClient(mongo_url, serverSelectionTimeoutMS=8000)[mongo_db]
    await store.init_schema()
    names = sorted(n for n in await asyncio.to_thread(mongo.list_collection_names) if not n.startswith("system."))
    skip = set() if with_sessions else SKIP
    log(f"MongoDB '{mongo_db}' -> MariaDB '{store.name}'  mode={mode}" + ("  [DRY RUN]" if dry_run else ""))
    summary, ok = {}, True
    for n in names:
        if (only and n not in only) or n in skip:
            continue
        if n not in TABLES:
            log(f"  ! koleksi '{n}' tidak ada di skema -> tetap dimigrasi (field disimpan di kolom _extra)")
        coll = store[n]
        keys = (TABLES.get(n) or {}).get("key") or []
        existing = set()
        if keys:
            for d in await coll.find({}, {k: 1 for k in keys}).to_list(None):
                k = natural_key(n, d)
                if k is not None:
                    existing.add(k)
        raws = await asyncio.to_thread(lambda: list(mongo[n].find({})))
        added = replaced = skipped = failed = 0
        for raw in raws:
            doc = clean(raw)
            k = natural_key(n, doc)
            if k is not None and k in existing:
                if mode == "replace":
                    if not dry_run:
                        await coll.replace_one(dict(zip(keys, k)), doc)
                    replaced += 1
                else:
                    skipped += 1
                continue
            if dry_run:
                added += 1
                continue
            try:
                await coll.insert_one(doc)
                added += 1
                if k is not None:
                    existing.add(k)
            except DuplicateKeyError as e:
                failed += 1
                log(f"    {n}: dilewati (duplikat indeks unik): {str(e)[:120]}")
        dst = await coll.count_documents({})
        good = dry_run or dst >= len(raws)
        ok = ok and good
        summary[n] = {"mongo": len(raws), "mariadb": dst, "ditambah": added, "ditimpa": replaced, "sudah_ada": skipped, "gagal": failed, "ok": good}
        log(f"  {'OK    ' if good else 'KURANG'} {n:<20} mongo={len(raws):<6} +{added}"
            + (f" ditimpa={replaced}" if mode == "replace" else f" sudah_ada={skipped}") + (f" gagal={failed}" if failed else "") + f"  -> mariadb={dst}")
    log("Selesai." + ("" if ok else "  Ada tabel yang jumlahnya kurang — periksa pesan di atas."))
    return {"ok": ok, "tables": summary, "mode": mode, "dry_run": dry_run, "mongo_db": mongo_db, "mariadb": store.name}


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(BACKEND / ".env")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mongo-url", default=os.environ.get("MIGRATE_FROM_MONGO_URL") or os.environ.get("MONGO_URL", ""))
    ap.add_argument("--mongo-db", default=os.environ.get("MIGRATE_FROM_MONGO_DB") or os.environ.get("DB_NAME", ""))
    ap.add_argument("--mariadb-url", default="")
    ap.add_argument("--mode", choices=["merge", "replace"], default="merge")
    ap.add_argument("--only", default="", help="tabel tertentu, pisahkan koma")
    ap.add_argument("--with-sessions", action="store_true", help="ikut pindahkan sesi login aktif")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    if not a.mongo_url or not a.mongo_db:
        sys.exit("Isi --mongo-url dan --mongo-db (atau env MIGRATE_FROM_MONGO_URL & MIGRATE_FROM_MONGO_DB)")
    if a.mode == "replace" and not a.yes and not a.dry_run:
        sys.exit("Mode replace menimpa baris dengan kunci sama. Jalankan ulang dengan --yes bila yakin.")

    async def run():
        store = Store(a.mariadb_url or build_url_from_env(dict(os.environ)))
        try:
            res = await migrate_all(a.mongo_url, a.mongo_db, store, a.mode, a.dry_run,
                                    {x.strip() for x in a.only.split(",") if x.strip()}, a.with_sessions)
        finally:
            await store.close()
        return 0 if res["ok"] else 1
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
