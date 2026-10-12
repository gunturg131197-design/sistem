"""Rekap Bonus Admin per unit: setiap kelipatan jam kerja (default 300 jam) -> bonus (default Rp500.000).

Aturan (rekomendasi yang disetujui user):
- Jam = total_jam Ops Report tervalidasi per unit (HM akhir - HM awal), kumulatif sejak tanggal mulai (opsional).
- Sisa jam di bawah kelipatan DIBAWA ke bonus berikutnya (tidak hangus).
- Tanggal tercapai = tanggal laporan HM yang membuat kumulatif melewati kelipatan.
- Penerima: admin per unit (diatur di pengaturan bonus), fallback admin default.
- Admin menandai "Dibayar" -> otomatis 1 baris Kas Keluar (KK); "Batalkan" menghapus Kas Keluar tsb. Semua tercatat di audit.
- Bila kelipatan/nominal diubah, bonus yang sudah dibayar tetap tercatat dengan aturan saat dibayar.
"""
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

BONUS_DEFAULT = {"enabled": True, "jam_per_bonus": 300.0, "nominal": 500000.0, "default_admin": "", "start_date": "", "unit_admins": {}}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _label(u: dict) -> str:
    return f"{u.get('unit_name', '')} - {u.get('nomor_lambung', '')}".strip(" -")


def build_bonus_router(db, require_admin: Callable, next_bukti: Callable) -> APIRouter:
    r = APIRouter()

    async def cfg() -> dict:
        doc = await db.app_settings.find_one({"key": "bonus_admin"}, {"_id": 0}) or {}
        return {**BONUS_DEFAULT, **{k: v for k, v in doc.items() if k in BONUS_DEFAULT}}

    async def audit(action, actor, detail, data=None):
        await db.wa_audit.insert_one({"id": str(uuid.uuid4()), "at": _now(), "action": action, "actor": actor, "inbox_id": "",
                                      "detail": detail[:500], "data": data or {}})

    async def compute(year: Optional[int] = None) -> dict:
        c = await cfg()
        step, nominal = float(c["jam_per_bonus"]), float(c["nominal"])
        units = await db.units.find({}, {"_id": 0}).to_list(5000)
        q = {"tanggal": {"$gte": c["start_date"]}} if c["start_date"] else {}
        ops = await db.operations.find(q, {"_id": 0, "unit_id": 1, "tanggal": 1, "total_jam": 1, "hour_meter_awal": 1}).to_list(200000)
        paid = await db.bonus_admin.find({}, {"_id": 0}).to_list(100000)
        rows, tot = [], {"jam": 0.0, "bonus": 0, "earned": 0.0, "paid": 0.0, "unpaid": 0.0}
        for u in sorted(units, key=lambda x: _label(x).lower()):
            my = sorted([o for o in ops if o.get("unit_id") == u["id"]], key=lambda o: (o.get("tanggal") or "", o.get("hour_meter_awal") or 0))
            total, cum, k, ms = 0.0, 0.0, 0, []
            for o in my:
                cum += float(o.get("total_jam") or 0)
                while step > 0 and cum >= step * (k + 1) - 1e-9:
                    k += 1
                    ms.append({"milestone": k, "jam_target": step * k, "tanggal_tercapai": o.get("tanggal")})
            total = round(cum, 2)
            admin = (c["unit_admins"] or {}).get(u["id"]) or c["default_admin"] or ""
            my_paid = {p["milestone"]: p for p in paid if p.get("unit_id") == u["id"] and float(p.get("jam_per_bonus") or 0) == step}
            items = []
            for m in ms:
                p = my_paid.get(m["milestone"])
                items.append({**m, "nominal": float(p["nominal"]) if p else nominal, "status": "dibayar" if p else "belum",
                              "admin": (p or {}).get("admin") or admin, "paid_at": (p or {}).get("paid_at"), "paid_by": (p or {}).get("paid_by"),
                              "no_bukti": (p or {}).get("no_bukti", ""), "bonus_id": (p or {}).get("id", "")})
            if year:
                items_y = [i for i in items if (i["tanggal_tercapai"] or "").startswith(str(year))]
            else:
                items_y = items
            earned = sum(i["nominal"] for i in items_y)
            pd = sum(i["nominal"] for i in items_y if i["status"] == "dibayar")
            sisa = round(total - step * k, 2) if step > 0 else 0.0
            rows.append({"unit_id": u["id"], "unit": _label(u), "pengurus": u.get("pengurus", ""), "admin": admin, "total_jam": total,
                         "jumlah_bonus": len(items_y), "sisa_jam": sisa, "kurang_jam": round(step - sisa, 2) if step > 0 else 0.0,
                         "progress": round(sisa / step * 100, 1) if step > 0 else 0.0, "bonus_earned": earned, "bonus_paid": pd,
                         "bonus_unpaid": earned - pd, "items": items_y})
            tot["jam"] += total
            tot["bonus"] += len(items_y)
            tot["earned"] += earned
            tot["paid"] += pd
            tot["unpaid"] += earned - pd
        # bonus yang sudah dibayar dengan aturan lama (kelipatan berbeda) tetap ditampilkan terpisah
        legacy = [p for p in paid if float(p.get("jam_per_bonus") or 0) != step]
        return {"settings": c, "rows": rows, "total": {k: round(v, 2) for k, v in tot.items()}, "legacy_paid": legacy, "year": year}

    class BonusCfg(BaseModel):
        enabled: bool = True
        jam_per_bonus: float = 300
        nominal: float = 500000
        default_admin: str = ""
        start_date: str = ""
        unit_admins: dict = {}

    class PayIn(BaseModel):
        unit_id: str
        milestone: int
        tanggal: Optional[str] = None
        admin: Optional[str] = None

    @r.get("/api/bonus-admin")
    async def get_bonus(year: Optional[int] = None, admin=Depends(require_admin)):
        return await compute(year)

    @r.get("/api/bonus-admin/settings")
    async def get_cfg(admin=Depends(require_admin)):
        return await cfg()

    @r.put("/api/bonus-admin/settings")
    async def put_cfg(body: BonusCfg, admin=Depends(require_admin)):
        if not 1 <= body.jam_per_bonus <= 100000:
            raise HTTPException(400, "Kelipatan jam harus 1 – 100.000")
        if not 0 <= body.nominal <= 1_000_000_000:
            raise HTTPException(400, "Nominal bonus tidak valid")
        if body.start_date:
            try:
                datetime.strptime(body.start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(400, "Format tanggal mulai YYYY-MM-DD")
        ids = {u["id"] for u in await db.units.find({}, {"_id": 0, "id": 1}).to_list(5000)}
        ua = {k: str(v).strip()[:80] for k, v in (body.unit_admins or {}).items() if k in ids and str(v).strip()}
        before = await cfg()
        new = {**body.model_dump(), "default_admin": body.default_admin.strip()[:80], "unit_admins": ua}
        await db.app_settings.update_one({"key": "bonus_admin"}, {"$set": {"key": "bonus_admin", **new, "updated_by": admin.name, "updated_at": _now()}}, upsert=True)
        await audit("bonus_settings", admin.name, f"Pengaturan bonus admin diubah: {new['jam_per_bonus']:g} jam = Rp{new['nominal']:,.0f}".replace(",", "."),
                    {"sebelum": before, "sesudah": new})
        return await cfg()

    @r.post("/api/bonus-admin/pay")
    async def pay(body: PayIn, admin=Depends(require_admin)):
        data = await compute()
        row = next((x for x in data["rows"] if x["unit_id"] == body.unit_id), None)
        item = next((i for i in (row or {}).get("items", []) if i["milestone"] == body.milestone), None)
        if not row or not item:
            raise HTTPException(404, "Bonus belum tercapai untuk unit / kelipatan ini")
        if item["status"] == "dibayar":
            raise HTTPException(400, f"Bonus ini sudah dibayar ({item['no_bukti']})")
        penerima = (body.admin or row["admin"] or "").strip()
        if not penerima:
            raise HTTPException(400, "Isi nama admin penerima bonus (pengaturan bonus / per unit)")
        tgl = (body.tanggal or datetime.now(timezone.utc).date().isoformat())[:10]
        try:
            datetime.strptime(tgl, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "Format tanggal YYYY-MM-DD")
        step = float(data["settings"]["jam_per_bonus"])
        bid = str(uuid.uuid4())
        doc = {"id": bid, "unit_id": body.unit_id, "unit": row["unit"], "milestone": body.milestone, "jam_per_bonus": step,
               "jam_target": item["jam_target"], "tanggal_tercapai": item["tanggal_tercapai"], "nominal": float(data["settings"]["nominal"]),
               "admin": penerima, "paid_at": tgl, "paid_by": admin.name, "created_at": _now()}
        try:
            await db.bonus_admin.insert_one(doc)  # unique index mencegah pembayaran ganda
        except Exception:
            raise HTTPException(400, "Bonus ini sudah dibayar")
        no = await next_bukti(db, "KK")
        await db.kas_keluar.insert_one({
            "id": str(uuid.uuid4()), "tanggal": tgl, "uraian": f"Bonus Admin {penerima} · {row['unit']} · {item['jam_target']:g} jam (ke-{body.milestone})",
            "penerima": penerima, "jenis": "KK", "no_bukti": no, "kredit": doc["nominal"],
            "keterangan": f"Bonus per {step:g} jam kerja · tercapai {item['tanggal_tercapai']}", "source": "bonus_admin", "source_id": bid, "created_at": _now()})
        await db.bonus_admin.update_one({"id": bid}, {"$set": {"no_bukti": no}})
        await audit("bonus_paid", admin.name, f"Bonus admin {penerima} {row['unit']} ke-{body.milestone} ({item['jam_target']:g} jam) dibayar · {no}",
                    {"bonus_id": bid, "no_bukti": no, "nominal": doc["nominal"]})
        return {"ok": True, "bonus_id": bid, "no_bukti": no}

    @r.delete("/api/bonus-admin/pay/{bid}")
    async def unpay(bid: str, admin=Depends(require_admin)):
        doc = await db.bonus_admin.find_one({"id": bid}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Data pembayaran bonus tidak ditemukan")
        await db.kas_keluar.delete_many({"source": "bonus_admin", "source_id": bid})
        await db.bonus_admin.delete_one({"id": bid})
        await audit("bonus_unpaid", admin.name, f"Pembayaran bonus {doc.get('admin')} {doc.get('unit')} ke-{doc.get('milestone')} dibatalkan ({doc.get('no_bukti')})", doc)
        return {"ok": True}

    @r.on_event("startup")
    async def _idx():
        await db.bonus_admin.create_index([("unit_id", 1), ("milestone", 1), ("jam_per_bonus", 1)], unique=True)

    return r
