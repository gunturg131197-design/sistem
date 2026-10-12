"""Modul Keuangan & Administrasi (admin only):
Kas Masuk, Kas Keluar (BK = belanja sparepart/barang, KK = gaji/kasbon/biaya lain),
Invoice, Surat Masuk, Surat Keluar, Rekap Bulanan + Dashboard.
Nota sparepart & payroll otomatis tercatat di Kas Keluar."""
import uuid
from datetime import datetime, timezone
from typing import Optional, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from mariadb_store import ReturnDocument

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
SURAT_BASE = 200      # nomor surat keluar pertama = 201 (SP/TTP/201/..)
INVOICE_BASE = 0


def _now():
    return datetime.now(timezone.utc).isoformat()


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------- Models ----------
class KasMasukIn(BaseModel):
    tanggal: str
    uraian: str
    tujuan_dana: Optional[str] = ""
    debit: float = 0
    pic: Optional[str] = ""
    pengurus: Optional[str] = ""
    no_ref: Optional[str] = ""


class KasKeluarIn(BaseModel):
    tanggal: str
    uraian: str
    penerima: Optional[str] = ""
    jenis: str = "KK"  # BK | KK
    kredit: float = 0
    keterangan: Optional[str] = ""


class InvoiceIn(BaseModel):
    tanggal: str
    nama_client: str
    deskripsi: Optional[str] = ""
    jumlah: float = 0
    status: str = "Belum Dibayar"  # Belum Dibayar | Sebagian | Lunas


class SuratMasukIn(BaseModel):
    tanggal_surat: str
    nomor_surat: str
    pengirim: str
    perihal: str
    tanggal_terima: Optional[str] = ""
    keterangan: Optional[str] = ""


class SuratKeluarIn(BaseModel):
    tanggal_surat: str
    tujuan_surat: str
    perihal: str
    pengirim: Optional[str] = ""
    keterangan: Optional[str] = ""


async def _next_seq(db, key: str) -> int:
    doc = await db.app_counters.find_one_and_update(
        {"key": key}, {"$inc": {"value": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return int(doc.get("value", 1))


async def next_bukti(db, prefix: str) -> str:
    seq = await _next_seq(db, f"bukti_{prefix}")
    return f"{prefix}-TTP-{seq:03d}"


# ---------- Sinkron otomatis dari modul lain ----------
async def sync_kas_sparepart(db, sp: dict):
    """Nota sparepart -> 1 baris Kas Keluar jenis BK."""
    await db.kas_keluar.delete_many({"source": "sparepart", "source_id": sp["id"]})
    if float(sp.get("biaya") or 0) <= 0:
        return
    items = ", ".join(i.get("nama_sparepart", "") for i in (sp.get("items") or []) if i.get("nama_sparepart")) or sp.get("nama_sparepart", "")
    await db.kas_keluar.insert_one({
        "id": str(uuid.uuid4()),
        "tanggal": sp.get("tanggal") or _today(),
        "uraian": f"Sparepart {sp.get('unit_label', '')}: {items}".strip(),
        "penerima": "",
        "jenis": "BK",
        "no_bukti": await next_bukti(db, "BK"),
        "kredit": float(sp.get("biaya") or 0),
        "keterangan": f"Nota {sp.get('nomor_nota', '')}",
        "source": "sparepart",
        "source_id": sp["id"],
        "created_at": _now(),
    })


async def sync_kas_payroll(db, p: dict):
    """Payroll -> Kas Keluar KK: kasbon (bila ada) + gaji bersih."""
    await db.kas_keluar.delete_many({"source": "payroll", "source_id": p["id"]})
    tgl = (p.get("created_at") or _now())[:10] if isinstance(p.get("created_at"), str) else _today()
    rows = []
    if float(p.get("kasbon") or 0) > 0:
        rows.append((f"Kasbon {p.get('operator_name', '')}", float(p["kasbon"]), f"Payroll {p.get('periode', '')} · {p.get('unit_label', '')}"))
    if float(p.get("gaji_bersih") or 0) > 0:
        rows.append((f"Gaji Op {p.get('operator_name', '')} ({p.get('unit_label', '')}) · {p.get('jam_dibayar', 0)} Jam",
                     float(p["gaji_bersih"]), f"Payroll {p.get('periode', '')}"))
    for uraian, kredit, ket in rows:
        await db.kas_keluar.insert_one({
            "id": str(uuid.uuid4()), "tanggal": tgl, "uraian": uraian, "penerima": p.get("operator_name", ""),
            "jenis": "KK", "no_bukti": await next_bukti(db, "KK"), "kredit": kredit, "keterangan": ket,
            "source": "payroll", "source_id": p["id"], "created_at": _now(),
        })


async def unsync_kas(db, source: str, source_id: str):
    await db.kas_keluar.delete_many({"source": source, "source_id": source_id})


def _renumber(nomor: str, tanggal: str) -> str:
    """Pertahankan nomor urut, perbarui bulan romawi & tahun sesuai tanggal baru."""
    try:
        parts = nomor.split("/")
        d = datetime.strptime(tanggal[:10], "%Y-%m-%d")
        parts[-2], parts[-1] = ROMAN[d.month], str(d.year)
        return "/".join(parts)
    except Exception:
        return nomor


def build_finance_router(db, require_admin: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/finance")

    def by_date(field):
        return [(field, 1), ("created_at", 1)]

    # ----- Kas Masuk -----
    @r.get("/kas-masuk")
    async def list_km(periode: Optional[str] = None, admin=Depends(require_admin)):
        q = {"tanggal": {"$regex": f"^{periode}"}} if periode else {}
        return await db.kas_masuk.find(q, {"_id": 0}).sort(by_date("tanggal")).to_list(10000)

    @r.post("/kas-masuk")
    async def create_km(body: KasMasukIn, admin=Depends(require_admin)):
        doc = {"id": str(uuid.uuid4()), **body.model_dump(), "no_bukti": await next_bukti(db, "KM"), "created_at": _now(), "created_by": admin.name}
        await db.kas_masuk.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @r.patch("/kas-masuk/{kid}")
    async def update_km(kid: str, body: KasMasukIn, admin=Depends(require_admin)):
        res = await db.kas_masuk.update_one({"id": kid}, {"$set": body.model_dump()})
        if res.matched_count == 0:
            raise HTTPException(404, "Not found")
        return await db.kas_masuk.find_one({"id": kid}, {"_id": 0})

    @r.delete("/kas-masuk/{kid}")
    async def delete_km(kid: str, admin=Depends(require_admin)):
        await db.kas_masuk.delete_one({"id": kid})
        return {"ok": True}

    # ----- Kas Keluar -----
    @r.get("/kas-keluar")
    async def list_kk(periode: Optional[str] = None, admin=Depends(require_admin)):
        q = {"tanggal": {"$regex": f"^{periode}"}} if periode else {}
        return await db.kas_keluar.find(q, {"_id": 0}).sort(by_date("tanggal")).to_list(10000)

    @r.post("/kas-keluar")
    async def create_kk(body: KasKeluarIn, admin=Depends(require_admin)):
        jenis = body.jenis if body.jenis in ("BK", "KK") else "KK"
        doc = {"id": str(uuid.uuid4()), **body.model_dump(), "jenis": jenis, "no_bukti": await next_bukti(db, jenis),
               "source": "manual", "source_id": "", "created_at": _now(), "created_by": admin.name}
        await db.kas_keluar.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @r.patch("/kas-keluar/{kid}")
    async def update_kk(kid: str, body: KasKeluarIn, admin=Depends(require_admin)):
        cur = await db.kas_keluar.find_one({"id": kid}, {"_id": 0})
        if not cur:
            raise HTTPException(404, "Not found")
        if cur.get("source") not in (None, "", "manual"):
            raise HTTPException(400, "Transaksi otomatis — ubah dari menu Sparepart/Payroll")
        upd = body.model_dump()
        upd["jenis"] = cur.get("jenis")  # nomor bukti terikat jenis
        await db.kas_keluar.update_one({"id": kid}, {"$set": upd})
        return await db.kas_keluar.find_one({"id": kid}, {"_id": 0})

    @r.delete("/kas-keluar/{kid}")
    async def delete_kk(kid: str, admin=Depends(require_admin)):
        cur = await db.kas_keluar.find_one({"id": kid}, {"_id": 0})
        if cur and cur.get("source") not in (None, "", "manual"):
            raise HTTPException(400, "Transaksi otomatis — hapus dari menu Sparepart/Payroll")
        await db.kas_keluar.delete_one({"id": kid})
        return {"ok": True}

    # ----- Invoice -----
    @r.get("/invoices")
    async def list_inv(admin=Depends(require_admin)):
        return await db.invoices.find({}, {"_id": 0}).sort(by_date("tanggal")).to_list(5000)

    @r.post("/invoices")
    async def create_inv(body: InvoiceIn, admin=Depends(require_admin)):
        d = datetime.strptime(body.tanggal[:10], "%Y-%m-%d") if body.tanggal else datetime.now(timezone.utc)
        seq = INVOICE_BASE + await _next_seq(db, "invoice_no")
        doc = {"id": str(uuid.uuid4()), **body.model_dump(), "no_invoice": f"INV/TTP/{seq:03d}/{ROMAN[d.month]}/{d.year}", "created_at": _now()}
        await db.invoices.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @r.patch("/invoices/{iid}")
    async def update_inv(iid: str, body: InvoiceIn, admin=Depends(require_admin)):
        cur = await db.invoices.find_one({"id": iid}, {"_id": 0})
        if not cur:
            raise HTTPException(404, "Not found")
        upd = body.model_dump()
        upd["no_invoice"] = _renumber(cur.get("no_invoice", ""), body.tanggal)
        await db.invoices.update_one({"id": iid}, {"$set": upd})
        return await db.invoices.find_one({"id": iid}, {"_id": 0})

    @r.delete("/invoices/{iid}")
    async def delete_inv(iid: str, admin=Depends(require_admin)):
        await db.invoices.delete_one({"id": iid})
        return {"ok": True}

    # ----- Surat Masuk -----
    @r.get("/surat-masuk")
    async def list_sm(admin=Depends(require_admin)):
        return await db.surat_masuk.find({}, {"_id": 0}).sort(by_date("tanggal_surat")).to_list(5000)

    @r.post("/surat-masuk")
    async def create_sm(body: SuratMasukIn, admin=Depends(require_admin)):
        doc = {"id": str(uuid.uuid4()), **body.model_dump(), "created_at": _now()}
        await db.surat_masuk.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @r.patch("/surat-masuk/{sid}")
    async def update_sm(sid: str, body: SuratMasukIn, admin=Depends(require_admin)):
        await db.surat_masuk.update_one({"id": sid}, {"$set": body.model_dump()})
        return await db.surat_masuk.find_one({"id": sid}, {"_id": 0})

    @r.delete("/surat-masuk/{sid}")
    async def delete_sm(sid: str, admin=Depends(require_admin)):
        await db.surat_masuk.delete_one({"id": sid})
        return {"ok": True}

    # ----- Surat Keluar (nomor otomatis SP/TTP/{seq}/{romawi}/{tahun}) -----
    @r.get("/surat-keluar")
    async def list_sk(admin=Depends(require_admin)):
        return await db.surat_keluar.find({}, {"_id": 0}).sort(by_date("tanggal_surat")).to_list(5000)

    @r.post("/surat-keluar")
    async def create_sk(body: SuratKeluarIn, admin=Depends(require_admin)):
        d = datetime.strptime(body.tanggal_surat[:10], "%Y-%m-%d") if body.tanggal_surat else datetime.now(timezone.utc)
        seq = SURAT_BASE + await _next_seq(db, "surat_keluar_no")
        doc = {"id": str(uuid.uuid4()), **body.model_dump(), "nomor_surat": f"SP/TTP/{seq}/{ROMAN[d.month]}/{d.year}", "created_at": _now()}
        await db.surat_keluar.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @r.patch("/surat-keluar/{sid}")
    async def update_sk(sid: str, body: SuratKeluarIn, admin=Depends(require_admin)):
        cur = await db.surat_keluar.find_one({"id": sid}, {"_id": 0})
        if not cur:
            raise HTTPException(404, "Not found")
        upd = body.model_dump()
        upd["nomor_surat"] = _renumber(cur.get("nomor_surat", ""), body.tanggal_surat)
        await db.surat_keluar.update_one({"id": sid}, {"$set": upd})
        return await db.surat_keluar.find_one({"id": sid}, {"_id": 0})

    @r.delete("/surat-keluar/{sid}")
    async def delete_sk(sid: str, admin=Depends(require_admin)):
        await db.surat_keluar.delete_one({"id": sid})
        return {"ok": True}

    # ----- Dashboard + Rekap Bulanan -----
    @r.get("/summary")
    async def summary(year: Optional[int] = None, admin=Depends(require_admin)):
        y = year or datetime.now(timezone.utc).year
        km = await db.kas_masuk.find({}, {"_id": 0, "tanggal": 1, "debit": 1}).to_list(50000)
        kk = await db.kas_keluar.find({}, {"_id": 0, "tanggal": 1, "kredit": 1, "jenis": 1, "source": 1}).to_list(50000)
        inv = await db.invoices.find({}, {"_id": 0, "jumlah": 1, "status": 1}).to_list(10000)
        total_in = sum(float(x.get("debit") or 0) for x in km)
        total_out = sum(float(x.get("kredit") or 0) for x in kk)
        months = []
        saldo = 0.0
        # saldo awal tahun = transaksi sebelum tahun y
        saldo += sum(float(x.get("debit") or 0) for x in km if (x.get("tanggal") or "")[:4] and int((x.get("tanggal") or "0")[:4] or 0) < y)
        saldo -= sum(float(x.get("kredit") or 0) for x in kk if (x.get("tanggal") or "")[:4] and int((x.get("tanggal") or "0")[:4] or 0) < y)
        saldo_awal = saldo
        for m in range(1, 13):
            key = f"{y}-{m:02d}"
            mi = sum(float(x.get("debit") or 0) for x in km if (x.get("tanggal") or "").startswith(key))
            mo = sum(float(x.get("kredit") or 0) for x in kk if (x.get("tanggal") or "").startswith(key))
            saldo += mi - mo
            months.append({"bulan": BULAN[m - 1], "periode": key, "total_masuk": mi, "total_keluar": mo, "selisih": mi - mo, "saldo": saldo})
        return {
            "year": y,
            "total_kas_masuk": total_in,
            "total_kas_keluar": total_out,
            "saldo_akhir": total_in - total_out,
            "saldo_awal_tahun": saldo_awal,
            "keluar_bk": sum(float(x.get("kredit") or 0) for x in kk if x.get("jenis") == "BK"),
            "keluar_kk": sum(float(x.get("kredit") or 0) for x in kk if x.get("jenis") == "KK"),
            "invoice_outstanding": sum(float(x.get("jumlah") or 0) for x in inv if x.get("status") != "Lunas"),
            "invoice_count": len(inv),
            "months": months,
        }

    return r
