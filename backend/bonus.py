"""Rekap Bonus Admin per unit: setiap kelipatan jam kerja (default 300 jam) -> bonus (default Rp500.000).

Aturan:
- Jam = total_jam Ops Report per unit (HM akhir - HM awal), kumulatif sejak tanggal mulai (opsional).
- Sisa jam di bawah kelipatan DIBAWA ke bonus berikutnya (tidak hangus).
- Tanggal tercapai = tanggal laporan HM yang membuat kumulatif melewati kelipatan.
- Penerima: admin per unit (diatur di pengaturan bonus), fallback admin default.
- Admin menandai "Dibayar" -> otomatis 1 baris Kas Keluar (KK); "Batalkan" menghapus Kas Keluar tsb. Semua tercatat di audit.
- Bila kelipatan/nominal diubah, bonus yang sudah dibayar tetap tercatat dengan aturan saat dibayar.
- Bila jam unit berkurang (laporan dihapus/diubah) sehingga bonus yang sudah dibayar tidak lagi tercapai,
  pembayaran tetap tampil dengan tanda peringatan (tidak dihapus otomatis).
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


def _rp(v: float) -> str:
    return f"Rp{v:,.0f}".replace(",", ".")


def build_bonus_router(db, require_admin: Callable, next_bukti: Callable) -> APIRouter:
    r = APIRouter()

    async def cfg() -> dict:
        doc = await db.app_settings.find_one({"key": "bonus_admin"}, {"_id": 0}) or {}
        out = {**BONUS_DEFAULT, **{k: v for k, v in doc.items() if k in BONUS_DEFAULT}}
        out["updated_by"] = doc.get("updated_by", "")
        out["updated_at"] = doc.get("updated_at", "")
        return out

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
        by_unit: dict = {}
        for o in ops:
            by_unit.setdefault(o.get("unit_id"), []).append(o)
        rows, tot = [], {"jam": 0.0, "bonus": 0, "earned": 0.0, "paid": 0.0, "unpaid": 0.0, "unit_bonus": 0}
        for u in sorted(units, key=lambda x: _label(x).lower()):
            my = sorted(by_unit.get(u["id"], []), key=lambda o: (o.get("tanggal") or "", o.get("hour_meter_awal") or 0))
            cum, k, ms = 0.0, 0, []
            for o in my:
                cum += float(o.get("total_jam") or 0)
                while step > 0 and cum >= step * (k + 1) - 1e-9:
                    k += 1
                    ms.append({"milestone": k, "jam_target": step * k, "tanggal_tercapai": o.get("tanggal"), "jam_berkurang": False})
            total = round(cum, 2)
            admin = (c["unit_admins"] or {}).get(u["id"]) or c["default_admin"] or ""
            my_paid = {p["milestone"]: p for p in paid if p.get("unit_id") == u["id"] and float(p.get("jam_per_bonus") or 0) == step}
            # pembayaran untuk kelipatan yang (kini) belum tercapai karena jam berkurang -> tetap tampil + peringatan
            for mk in sorted(m for m in my_paid if m > k):
                p = my_paid[mk]
                ms.append({"milestone": mk, "jam_target": step * mk, "tanggal_tercapai": p.get("tanggal_tercapai"), "jam_berkurang": True})
            items = []
            for m in ms:
                p = my_paid.get(m["milestone"])
                items.append({**m, "nominal": float(p["nominal"]) if p else nominal, "status": "dibayar" if p else "belum",
                              "admin": (p or {}).get("admin") or admin, "paid_at": (p or {}).get("paid_at"), "paid_by": (p or {}).get("paid_by"),
                              "no_bukti": (p or {}).get("no_bukti", ""), "bonus_id": (p or {}).get("id", "")})
            items_y = [i for i in items if (i["tanggal_tercapai"] or "").startswith(str(year))] if year else items
            earned = sum(i["nominal"] for i in items_y)
            pd = sum(i["nominal"] for i in items_y if i["status"] == "dibayar")
            sisa = round(total - step * k, 2) if step > 0 else 0.0
            jam_y = round(sum(float(o.get("total_jam") or 0) for o in my if (o.get("tanggal") or "").startswith(str(year))), 2) if year else total
            rows.append({"unit_id": u["id"], "unit": _label(u), "unit_name": u.get("unit_name", ""), "nomor_lambung": u.get("nomor_lambung", ""),
                         "pengurus": u.get("pengurus", ""), "admin": admin, "admin_khusus": bool((c["unit_admins"] or {}).get(u["id"])),
                         "total_jam": total, "jam_periode": jam_y, "jumlah_laporan": len(my),
                         "jumlah_bonus": len(items_y), "jumlah_bonus_total": k, "sisa_jam": sisa,
                         "kurang_jam": round(step - sisa, 2) if step > 0 else 0.0,
                         "progress": round(sisa / step * 100, 1) if step > 0 else 0.0, "bonus_earned": earned, "bonus_paid": pd,
                         "bonus_unpaid": earned - pd, "items": items_y})
            tot["jam"] += jam_y
            tot["bonus"] += len(items_y)
            tot["earned"] += earned
            tot["paid"] += pd
            tot["unpaid"] += earned - pd
            tot["unit_bonus"] += 1 if items_y else 0
        # bonus yang sudah dibayar dengan aturan lama (kelipatan berbeda) tetap ditampilkan terpisah
        legacy = [p for p in paid if float(p.get("jam_per_bonus") or 0) != step]
        if year:
            legacy = [p for p in legacy if (p.get("tanggal_tercapai") or "").startswith(str(year))]
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
        await audit("bonus_settings", admin.name, f"Pengaturan bonus admin diubah: {new['jam_per_bonus']:g} jam = {_rp(new['nominal'])}",
                    {"sebelum": {k: before.get(k) for k in BONUS_DEFAULT}, "sesudah": new})
        return await cfg()

    @r.post("/api/bonus-admin/pay")
    async def pay(body: PayIn, admin=Depends(require_admin)):
        data = await compute()
        if not data["settings"].get("enabled", True):
            raise HTTPException(400, "Fitur bonus admin sedang dinonaktifkan di pengaturan")
        row = next((x for x in data["rows"] if x["unit_id"] == body.unit_id), None)
        item = next((i for i in (row or {}).get("items", []) if i["milestone"] == body.milestone), None)
        if not row or not item:
            raise HTTPException(404, "Bonus belum tercapai untuk unit / kelipatan ini")
        if item["status"] == "dibayar":
            raise HTTPException(400, f"Bonus ini sudah dibayar ({item['no_bukti']})")
        penerima = (body.admin or row["admin"] or "").strip()[:80]
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
        return {"ok": True, "bonus_id": bid, "no_bukti": no, "nominal": doc["nominal"], "admin": penerima}

    @r.delete("/api/bonus-admin/pay/{bid}")
    async def unpay(bid: str, admin=Depends(require_admin)):
        doc = await db.bonus_admin.find_one({"id": bid}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Data pembayaran bonus tidak ditemukan")
        await db.kas_keluar.delete_many({"source": "bonus_admin", "source_id": bid})
        await db.bonus_admin.delete_one({"id": bid})
        await audit("bonus_unpaid", admin.name, f"Pembayaran bonus {doc.get('admin')} {doc.get('unit')} ke-{doc.get('milestone')} dibatalkan ({doc.get('no_bukti')})", doc)
        return {"ok": True}

    @r.get("/api/bonus-admin/history")
    async def history(admin=Depends(require_admin)):
        return await db.wa_audit.find({"action": {"$in": ["bonus_settings", "bonus_paid", "bonus_unpaid"]}}, {"_id": 0, "data": 0}).sort("at", -1).to_list(100)

    return r


async def ensure_bonus_indexes(db):
    await db.bonus_admin.create_index([("unit_id", 1), ("milestone", 1), ("jam_per_bonus", 1)], unique=True)
