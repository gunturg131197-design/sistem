"""Uji paritas: operasi yang sama dijalankan di MongoDB (referensi lama) dan MariaDB Store -> hasil harus identik.
Jalankan:  cd /app/backend && python ../tests/test_store_parity.py
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from pymongo import ReturnDocument as MRD  # noqa: E402

from mariadb_store import DuplicateKeyError, ReturnDocument, Store, build_url_from_env  # noqa: E402

FAIL = []


def same(label, a, b):
    if a != b:
        FAIL.append(label)
        print(f"  FAIL {label}\n     mongo  = {a}\n     maria  = {b}")
    else:
        print(f"  ok   {label}")


async def main():
    tag = uuid.uuid4().hex[:6]
    mdb = AsyncIOMotorClient(os.environ["MONGO_URL"])[f"parity_{tag}"]
    sdb = Store(build_url_from_env(dict(os.environ)))
    await sdb.init_schema()
    T = "operations"
    await sdb[T].delete_many({"unit_id": {"$regex": "^PAR-"}})
    docs = [
        {"id": f"o{i}", "unit_id": f"PAR-{i % 3}", "tanggal": f"2026-0{1 + i % 4}-1{i}", "hour_meter_awal": 100.0 + i, "hour_meter_akhir": 110.5 + i,
         "total_jam": 10.5, "jumlah_cars": i, "pengurus": ["Rudi", "budi", None, "Budi"][i % 4], "kondisi_alat": {"mesin": {"status": "baik"}},
         "auto_approved": i % 2 == 0, "created_at": f"2026-10-0{i}T10:00:00+00:00", "custom_field": [i, "x"]}
        for i in range(1, 9)
    ]
    docs[2].pop("auto_approved")
    docs[3]["keterangan"] = None
    docs[4]["tanggal"] = "tanggal-salah"  # tidak valid -> disimpan di _extra, tetap terbaca utuh
    for d in docs:
        await mdb[T].insert_one(dict(d))
        await sdb[T].insert_one(dict(d))
    P = {"_id": 0}

    async def both(label, fn):
        a = await fn(mdb)
        b = await fn(sdb)
        same(label, a, b)

    base = {"unit_id": {"$regex": "^PAR-"}}
    await both("find all sort tanggal desc", lambda db: db[T].find(base, P).sort("tanggal", -1).to_list(100))
    await both("find_one id", lambda db: db[T].find_one({"id": "o3"}, P))
    await both("eq + range", lambda db: db[T].find({"unit_id": "PAR-1", "tanggal": {"$gte": "2026-02-01"}}, P).sort("id", 1).to_list(50))
    await both("regex prefix", lambda db: db[T].find({"tanggal": {"$regex": "^2026-03"}, **base}, P).sort("id", 1).to_list(50))
    await both("regex i exact", lambda db: db[T].find({"pengurus": {"$regex": "^budi$", "$options": "i"}}, P).sort("id", 1).to_list(50))
    await both("$in", lambda db: db[T].find({"id": {"$in": ["o1", "o5", "zz"]}}, P).sort("id", 1).to_list(50))
    await both("$ne None-aware", lambda db: db[T].find({"pengurus": {"$ne": "Rudi"}, **base}, P).sort("id", 1).to_list(50))
    await both("eq None (null/missing)", lambda db: db[T].find({"auto_approved": None, **base}, P).sort("id", 1).to_list(50))
    await both("bool eq", lambda db: db[T].find({"auto_approved": True, **base}, P).sort("id", 1).to_list(50))
    await both("$or", lambda db: db[T].find({"$or": [{"id": "o1"}, {"jumlah_cars": {"$gt": 6}}], **base}, P).sort("id", 1).to_list(50))
    await both("multi sort + limit", lambda db: db[T].find(base, P).sort([("unit_id", 1), ("tanggal", -1)]).to_list(4))
    await both("projection include", lambda db: db[T].find({"id": "o2"}, {"_id": 0, "id": 1, "kondisi_alat": 1}).to_list(5))
    await both("projection exclude", lambda db: db[T].find({"id": "o2"}, {"_id": 0, "kondisi_alat": 0, "custom_field": 0}).to_list(5))
    await both("count eq", lambda db: db[T].count_documents({"unit_id": "PAR-0"}))
    await both("count regex", lambda db: db[T].count_documents({"pengurus": {"$regex": "udi"}}))
    await both("distinct", lambda db: db[T].distinct("pengurus", base))
    await both("array contains", lambda db: db[T].find({"custom_field": "x", "id": "o1"}, P).to_list(5))

    async def upd(db):
        r = await db[T].update_one({"id": "o1"}, {"$set": {"pengurus": "Andi", "kondisi_alat.mesin.status": "rusak"}, "$inc": {"jumlah_cars": 2}, "$unset": {"custom_field": ""}})
        return [r.matched_count, r.modified_count, r.upserted_id, await db[T].find_one({"id": "o1"}, P)]
    await both("update_one set/inc/unset/dotted", upd)

    async def upd_none(db):
        r = await db[T].update_one({"id": "nope"}, {"$set": {"x": 1}})
        return [r.matched_count, r.modified_count, r.upserted_id]
    await both("update_one tanpa match", upd_none)

    async def upd_many(db):
        r = await db[T].update_many({"unit_id": "PAR-2"}, {"$set": {"status": "ok"}})
        return [r.matched_count, r.modified_count]
    await both("update_many", upd_many)

    C = "app_counters"
    async def counter(db):
        out = []
        for _ in range(3):
            d = await db[C].find_one_and_update({"key": f"par_{tag}"}, {"$inc": {"value": 1}}, upsert=True,
                                                return_document=MRD.AFTER if db is mdb else ReturnDocument.AFTER)
            out.append(d["value"])
        return out
    await both("counter $inc upsert AFTER", counter)

    R = "cron_runs"
    async def lock(db):
        a = await db[R].update_one({"run_id": f"lock:{tag}"}, {"$setOnInsert": {"run_id": f"lock:{tag}", "job": "x"}}, upsert=True)
        b = await db[R].update_one({"run_id": f"lock:{tag}"}, {"$setOnInsert": {"run_id": f"lock:{tag}", "job": "y"}}, upsert=True)
        doc = await db[R].find_one({"run_id": f"lock:{tag}"}, P)
        return [a.upserted_id is None, b.upserted_id is None, b.matched_count, doc]
    await both("setOnInsert lock", lock)

    async def delete(db):
        r1 = await db[T].delete_one({"id": "o8"})
        r2 = await db[T].delete_many({"unit_id": "PAR-0"})
        return [r1.deleted_count, r2.deleted_count, await db[T].count_documents(base)]
    await both("delete", delete)

    # concurrency: 40 increments paralel harus menghasilkan nilai unik 1..40 (penomoran bukti)
    vals = await asyncio.gather(*[sdb[C].find_one_and_update({"key": f"conc_{tag}"}, {"$inc": {"value": 1}}, upsert=True,
                                                             return_document=ReturnDocument.AFTER) for _ in range(40)])
    same("concurrent counter unique", sorted(v["value"] for v in vals), list(range(1, 41)))
    # concurrency lock: 20 upsert setOnInsert bersamaan -> tepat 1 yang upserted
    res = await asyncio.gather(*[sdb[R].update_one({"run_id": f"conc:{tag}"}, {"$setOnInsert": {"run_id": f"conc:{tag}"}}, upsert=True) for _ in range(20)])
    same("concurrent lock single winner", sum(1 for r in res if r.upserted_id is not None), 1)
    # unique dedupe -> DuplicateKeyError
    await sdb.wa_outbox.insert_one({"id": f"a{tag}", "dedupe_key": f"k{tag}"})
    try:
        await sdb.wa_outbox.insert_one({"id": f"b{tag}", "dedupe_key": f"k{tag}"})
        same("duplicate key raises", False, True)
    except DuplicateKeyError:
        same("duplicate key raises", True, True)
    # blob
    await sdb.wa_media.insert_one({"id": f"m{tag}", "data": b"\xff\xd8binary", "mime": "image/jpeg"})
    same("blob roundtrip", (await sdb.wa_media.find_one({"id": f"m{tag}"}, P))["data"], b"\xff\xd8binary")

    # cleanup
    await sdb[T].delete_many(base)
    await sdb[C].delete_many({"key": {"$in": [f"par_{tag}", f"conc_{tag}"]}})
    await sdb[R].delete_many({"run_id": {"$in": [f"lock:{tag}", f"conc:{tag}"]}})
    await sdb.wa_outbox.delete_many({"dedupe_key": f"k{tag}"})
    await sdb.wa_media.delete_many({"id": f"m{tag}"})
    await mdb.client.drop_database(f"parity_{tag}")
    await sdb.close()
    print(f"\n{'SEMUA LULUS' if not FAIL else 'GAGAL: ' + ', '.join(FAIL)}")
    sys.exit(1 if FAIL else 0)


asyncio.run(main())
