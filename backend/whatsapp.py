"""Integrasi WhatsApp (Meta Cloud API) + Kotak Masuk WA.

Alur: gambar masuk (webhook WhatsApp atau upload manual) -> AI membaca (bukti transfer / foto HM)
-> dicocokkan ke unit & pengurus (keterangan mis. "Sdlg 10") -> status "Menunggu Verifikasi"
-> admin menyetujui -> tercatat ke Kas Masuk (KM-TTP-xxx) atau Ops Report (HM).
Webhook non-aktif (graceful) sampai kredensial WHATSAPP_* diisi di backend/.env.
"""
import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import httpx
from bson import Binary
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from wa_ai import AI_MODEL, extract_image, match_unit, normalize_image

MAX_BYTES = 12 * 1024 * 1024


def _now():
    return datetime.now(timezone.utc).isoformat()


def _env(k):
    return (os.environ.get(k) or "").strip()


def wa_configured() -> bool:
    return all(_env(k) for k in ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN"))


def _graph(path: str) -> str:
    return f"https://graph.facebook.com/{_env('WHATSAPP_API_VERSION') or 'v25.0'}/{path}"


async def wa_download_media(media_id: str) -> tuple[bytes, str]:
    hdr = {"Authorization": f"Bearer {_env('WHATSAPP_ACCESS_TOKEN')}"}
    async with httpx.AsyncClient(timeout=60) as c:
        meta = await c.get(_graph(media_id), headers=hdr)
        meta.raise_for_status()
        r = await c.get(meta.json()["url"], headers=hdr)
        r.raise_for_status()
    if len(r.content) > MAX_BYTES:
        raise ValueError("Gambar terlalu besar")
    return r.content, r.headers.get("content-type", "image/jpeg")


async def wa_send_text(to: str, body: str) -> bool:
    if not wa_configured() or not to:
        return False
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                _graph(f"{_env('WHATSAPP_PHONE_NUMBER_ID')}/messages"),
                headers={"Authorization": f"Bearer {_env('WHATSAPP_ACCESS_TOKEN')}"},
                json={"messaging_product": "whatsapp", "recipient_type": "individual", "to": to, "type": "text",
                      "text": {"preview_url": False, "body": body[:4096]}},
            )
        return r.status_code < 300
    except Exception:
        return False


def norm_phone(p: str) -> str:
    d = "".join(ch for ch in (p or "") if ch.isdigit())
    if d.startswith("0"):
        d = "62" + d[1:]
    return d


def _idr(n) -> str:
    return "Rp" + f"{float(n or 0):,.0f}".replace(",", ".")


# ---------- Models ----------
class ContactIn(BaseModel):
    phone: str
    nama: str
    tipe: str = "operator"  # operator | pengurus | klien | lainnya
    user_id: Optional[str] = ""
    unit_id: Optional[str] = ""
    pengurus: Optional[str] = ""


class DraftIn(BaseModel):
    jenis: Optional[str] = None  # transfer | hour_meter | lainnya
    draft: dict = {}


def build_whatsapp_router(db, require_admin: Callable, hooks: dict) -> APIRouter:
    """hooks: {'next_bukti': async fn(db, prefix) -> str}"""
    r = APIRouter()

    AUTO_DEFAULT = {"transfer_enabled": False, "hm_enabled": False, "min_confidence": 0.9}

    async def get_auto_settings() -> dict:
        doc = await db.app_settings.find_one({"key": "wa_auto"}, {"_id": 0}) or {}
        return {**AUTO_DEFAULT, **{k: v for k, v in doc.items() if k in AUTO_DEFAULT}}

    async def audit(action: str, actor: str, inbox_id: str = "", detail: str = "", data: Optional[dict] = None):
        await db.wa_audit.insert_one({"id": str(uuid.uuid4()), "at": _now(), "action": action, "actor": actor,
                                      "inbox_id": inbox_id, "detail": detail[:500], "data": data or {}})

    async def _units():
        return await db.units.find({}, {"_id": 0}).to_list(2000)

    def _label(u):
        return f"{u.get('unit_name', '')} - {u.get('nomor_lambung', '')}" if u else ""

    async def _prev_hm(unit_id: str, tanggal: str) -> Optional[float]:
        q = {"unit_id": unit_id}
        if tanggal:
            q["tanggal"] = {"$lt": tanggal}
        prev = await db.operations.find(q, {"_id": 0}).sort([("tanggal", -1), ("hour_meter_akhir", -1)]).to_list(1)
        return float(prev[0].get("hour_meter_akhir") or 0) if prev else None

    # ---------- inti pemrosesan ----------
    async def process_item(item_id: str):
        item = await db.wa_inbox.find_one({"id": item_id}, {"_id": 0})
        if not item:
            return
        media = await db.wa_media.find_one({"id": item.get("media_id")}, {"_id": 0})
        if not media:
            await db.wa_inbox.update_one({"id": item_id}, {"$set": {"status": "error", "error": "Gambar tidak ditemukan"}})
            return
        try:
            ai = await extract_image(bytes(media["data"]), item.get("caption", ""))
        except Exception as e:  # noqa: BLE001
            await db.wa_inbox.update_one({"id": item_id}, {"$set": {"status": "error", "error": f"AI gagal membaca gambar: {str(e)[:200]}"}})
            await audit("ai_error", f"AI ({AI_MODEL})", item_id, str(e)[:200])
            return

        units = await _units()
        contact = await db.wa_contacts.find_one({"phone": item.get("from_phone")}, {"_id": 0}) if item.get("from_phone") else None
        unit = match_unit(item.get("caption", ""), units)
        how = "keterangan" if unit else ""
        if not unit and contact and contact.get("unit_id"):
            unit = next((u for u in units if u["id"] == contact["unit_id"]), None)
            how = "kontak" if unit else ""
        if not unit and contact and contact.get("user_id"):
            unit = next((u for u in units if u.get("operator_id") == contact["user_id"]), None)
            how = "operator unit" if unit else ""

        jenis = ai.get("jenis") or "lainnya"
        pengurus = (unit or {}).get("pengurus") or ((contact or {}).get("pengurus")) or ((contact or {}).get("nama") if (contact or {}).get("tipe") == "pengurus" else "") or ""
        draft: dict[str, Any] = {"unit_id": (unit or {}).get("id", ""), "pengurus": pengurus}
        warnings = []
        status = "pending"

        if jenis == "transfer":
            t = ai.get("transfer") or {}
            nominal = t.get("nominal") or t.get("total") or 0
            pengirim = " · ".join([x for x in [t.get("nama_pengirim"), t.get("bank_pengirim")] if x])
            draft.update({
                "tanggal": t.get("tanggal") or (item.get("received_at") or _now())[:10],
                "debit": float(nominal or 0),
                "no_ref": str(t.get("no_ref") or ""),
                "uraian": f"Pembayaran {item.get('caption') or _label(unit) or ''}".strip() + (f" dari {t.get('nama_pengirim')}" if t.get("nama_pengirim") else ""),
                "tujuan_dana": _label(unit) or (item.get("caption") or ""),
                "pic": pengirim,
            })
            if draft["no_ref"]:
                dup = await db.kas_masuk.find_one({"no_ref": draft["no_ref"]}, {"_id": 0, "no_bukti": 1})
                dup_inbox = await db.wa_inbox.find_one({"id": {"$ne": item_id}, "draft.no_ref": draft["no_ref"], "status": {"$in": ["pending", "approved"]}}, {"_id": 0, "id": 1})
                if dup or dup_inbox:
                    status = "duplicate"
                    warnings.append(f"No. Ref {draft['no_ref']} sudah pernah tercatat" + (f" ({dup['no_bukti']})" if dup else ""))
            if not draft["debit"]:
                warnings.append("Nominal tidak terbaca")
        elif jenis == "hour_meter":
            h = ai.get("hour_meter") or {}
            tgl = h.get("tanggal") or (item.get("received_at") or _now())[:10]
            hm = float(h.get("hm") or 0)
            draft.update({"tanggal": tgl, "hm_reading": hm, "hm_awal": None, "hm_akhir": hm, "jam_foto": h.get("jam") or "",
                          "operator_id": (contact or {}).get("user_id") or (unit or {}).get("operator_id") or "", "jumlah_cars": 0})
            if unit:
                same = await db.operations.find_one({"unit_id": unit["id"], "tanggal": tgl}, {"_id": 0})
                if same:
                    draft["existing_op_id"] = same["id"]
                    lo = min(float(same.get("hour_meter_awal") or hm), hm)
                    hi = max(float(same.get("hour_meter_akhir") or hm), hm)
                    draft["hm_awal"], draft["hm_akhir"] = lo, hi
                    warnings.append("Ops Report tanggal ini sudah ada — HM akan digabung (awal = terkecil, akhir = terbesar)")
                else:
                    prev = await _prev_hm(unit["id"], tgl)
                    draft["hm_awal"] = prev if prev is not None else hm
                    if prev is None:
                        warnings.append("Belum ada HM sebelumnya — HM Awal disamakan, silakan koreksi bila perlu")
                    elif prev > hm:
                        draft["hm_awal"] = hm
                        warnings.append(f"HM terbaca ({hm}) lebih kecil dari HM terakhir ({prev}) — periksa unit / angka HM")
            if not hm:
                warnings.append("Angka HM tidak terbaca")
            if not draft["operator_id"]:
                warnings.append("Operator belum dikenali — pilih operator")
        else:
            warnings.append("Gambar bukan bukti transfer atau foto HM")
        if not unit and jenis in ("transfer", "hour_meter"):
            warnings.append(f"Unit untuk keterangan \"{item.get('caption') or '-'}\" belum dikenali — pilih unit")

        # ---- evaluasi persetujuan otomatis ----
        cfg = await get_auto_settings()
        try:
            conf = float(ai.get("keyakinan") or 0)
        except (TypeError, ValueError):
            conf = 0.0
        reasons = []
        if jenis not in ("transfer", "hour_meter"):
            reasons.append("Jenis gambar tidak dikenali")
        elif not cfg["transfer_enabled" if jenis == "transfer" else "hm_enabled"]:
            reasons.append("Persetujuan otomatis untuk jenis ini nonaktif")
        if conf < float(cfg["min_confidence"]):
            reasons.append(f"Keyakinan AI {conf:.0%} di bawah batas {float(cfg['min_confidence']):.0%}")
        if not unit:
            reasons.append("Unit tidak dikenali")
        if jenis == "transfer":
            if not draft.get("debit"):
                reasons.append("Nominal tidak terbaca")
            if not draft.get("no_ref"):
                reasons.append("No. Ref tidak terbaca — duplikasi tidak bisa dipastikan")
        if jenis == "hour_meter" and not draft.get("hm_akhir"):
            reasons.append("Angka HM tidak terbaca")
        if status == "duplicate":
            reasons.append("Terindikasi duplikat")
        reasons.extend(f"Peringatan: {w}" for w in warnings)
        auto_check = {"eligible": not reasons, "confidence": conf, "threshold": float(cfg["min_confidence"]), "reasons": reasons, "at": _now()}

        await db.wa_inbox.update_one({"id": item_id}, {"$set": {
            "status": status, "jenis": jenis, "ai": ai, "draft": draft, "warnings": warnings,
            "match": {"unit_label": _label(unit), "via": how, "contact": (contact or {}).get("nama", "")},
            "processed_at": _now(), "error": "", "auto_check": auto_check,
        }})
        await audit("ai_processed", f"AI ({AI_MODEL})", item_id, f"{jenis} · keyakinan {conf:.0%} · unit {_label(unit) or '-'}",
                    {"warnings": warnings, "status": status})
        if not reasons:
            fresh = await db.wa_inbox.find_one({"id": item_id}, {"_id": 0})
            try:
                res = await do_approve(fresh, jenis, {}, actor="Sistem (otomatis)", auto=True)
                await audit("auto_approved", "Sistem (otomatis)", item_id, f"Tersimpan otomatis: {res['result'].get('no')}", res["result"])
            except HTTPException as e:
                await db.wa_inbox.update_one({"id": item_id}, {"$set": {"auto_check.eligible": False, "auto_check.reasons": [f"Validasi akhir gagal: {e.detail}"]}})
                await audit("auto_blocked", "Sistem (otomatis)", item_id, f"Validasi akhir gagal: {e.detail}")
        elif jenis in ("transfer", "hour_meter"):
            await audit("auto_blocked", "Sistem (otomatis)", item_id, "; ".join(reasons))

    async def create_item(data: bytes, mime: str, caption: str, source: str, from_phone: str = "", from_name: str = "",
                          message_id: str = "", created_by: str = "") -> dict:
        try:
            jpeg = normalize_image(data)
        except Exception:
            raise HTTPException(400, "File bukan gambar yang valid (gunakan JPG/PNG/WEBP)")
        media_id = str(uuid.uuid4())
        await db.wa_media.insert_one({"id": media_id, "data": Binary(jpeg), "mime": "image/jpeg", "orig_mime": mime, "created_at": _now()})
        doc = {
            "id": str(uuid.uuid4()), "source": source, "message_id": message_id, "from_phone": norm_phone(from_phone),
            "from_name": from_name, "caption": (caption or "").strip(), "media_id": media_id, "status": "processing",
            "jenis": "", "ai": {}, "draft": {}, "warnings": [], "match": {}, "received_at": _now(), "created_by": created_by,
        }
        await db.wa_inbox.insert_one(doc)
        doc.pop("_id", None)
        return doc

    # ---------- Status ----------
    @r.get("/api/wa/status")
    async def wa_status(admin=Depends(require_admin)):
        return {
            "configured": wa_configured(),
            "webhook_path": "/api/whatsapp/webhook",
            "missing": [k for k in ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN") if not _env(k)],
            "ai_model": AI_MODEL,
            "counts": {s: await db.wa_inbox.count_documents({"status": s}) for s in ("processing", "pending", "duplicate", "approved", "rejected", "error")},
        }

    # ---------- Inbox ----------
    @r.get("/api/wa/inbox")
    async def list_inbox(status: Optional[str] = None, admin=Depends(require_admin)):
        sts = [x for x in (status or "").split(",") if x and x != "all"]
        q = {"status": {"$in": sts}} if sts else {}
        return await db.wa_inbox.find(q, {"_id": 0}).sort("received_at", -1).to_list(500)

    @r.post("/api/wa/upload")
    async def upload(background: BackgroundTasks, file: UploadFile = File(...), caption: str = Form(""), phone: str = Form(""),
                     admin=Depends(require_admin)):
        data = await file.read()
        if not data:
            raise HTTPException(400, "File kosong")
        if len(data) > MAX_BYTES:
            raise HTTPException(400, "Ukuran gambar maksimal 12 MB")
        doc = await create_item(data, file.content_type or "", caption, "upload", from_phone=phone, created_by=admin.name)
        await audit("received", admin.name, doc["id"], f"Upload manual · ket {caption or '-'}")
        background.add_task(process_item, doc["id"])
        return doc

    @r.get("/api/wa/inbox/{iid}/media")
    async def media(iid: str, admin=Depends(require_admin)):
        item = await db.wa_inbox.find_one({"id": iid}, {"_id": 0, "media_id": 1})
        m = await db.wa_media.find_one({"id": (item or {}).get("media_id")}, {"_id": 0}) if item else None
        if not m:
            raise HTTPException(404, "Gambar tidak ditemukan")
        return Response(content=bytes(m["data"]), media_type=m.get("mime", "image/jpeg"), headers={"Cache-Control": "private, max-age=3600"})

    @r.patch("/api/wa/inbox/{iid}")
    async def update_draft(iid: str, body: DraftIn, admin=Depends(require_admin)):
        item = await db.wa_inbox.find_one({"id": iid}, {"_id": 0})
        if not item:
            raise HTTPException(404, "Not found")
        if item["status"] == "approved":
            raise HTTPException(400, "Sudah disetujui")
        upd = {"draft": {**(item.get("draft") or {}), **(body.draft or {})}}
        if body.jenis:
            upd["jenis"] = body.jenis
        await db.wa_inbox.update_one({"id": iid}, {"$set": upd})
        await audit("edited", admin.name, iid, "Draft diubah", {"draft": body.draft or {}})
        return await db.wa_inbox.find_one({"id": iid}, {"_id": 0})

    @r.post("/api/wa/inbox/{iid}/reprocess")
    async def reprocess(iid: str, background: BackgroundTasks, admin=Depends(require_admin)):
        res = await db.wa_inbox.update_one({"id": iid, "status": {"$ne": "approved"}}, {"$set": {"status": "processing", "error": ""}})
        if res.matched_count == 0:
            raise HTTPException(400, "Tidak bisa diproses ulang")
        await audit("reprocessed", admin.name, iid, "Dibaca ulang oleh AI")
        background.add_task(process_item, iid)
        return {"ok": True}

    @r.post("/api/wa/inbox/{iid}/reject")
    async def reject(iid: str, admin=Depends(require_admin)):
        res = await db.wa_inbox.update_one({"id": iid, "status": {"$ne": "approved"}},
                                           {"$set": {"status": "rejected", "reviewed_by": admin.name, "reviewed_at": _now()}})
        if res.matched_count == 0:
            raise HTTPException(400, "Tidak bisa ditolak")
        await audit("rejected", admin.name, iid, "Ditolak admin")
        return {"ok": True}

    @r.delete("/api/wa/inbox/{iid}")
    async def delete_item(iid: str, admin=Depends(require_admin)):
        item = await db.wa_inbox.find_one({"id": iid}, {"_id": 0})
        if not item:
            raise HTTPException(404, "Not found")
        await db.wa_media.delete_one({"id": item.get("media_id")})
        await db.wa_inbox.delete_one({"id": iid})
        await audit("deleted", admin.name, iid, f"Pesan dihapus (status {item.get('status')}, ket {item.get('caption') or '-'})")
        return {"ok": True}

    @r.post("/api/wa/inbox/{iid}/approve")
    async def approve(iid: str, body: DraftIn, admin=Depends(require_admin)):
        item = await db.wa_inbox.find_one({"id": iid}, {"_id": 0})
        if not item:
            raise HTTPException(404, "Not found")
        if item["status"] == "processing":
            raise HTTPException(400, "Masih diproses AI")
        before = item.get("draft") or {}
        changed = {k: v for k, v in (body.draft or {}).items() if before.get(k) != v}
        res = await do_approve(item, body.jenis or item.get("jenis"), body.draft or {}, actor=admin.name, admin=admin)
        await audit("approved", admin.name, iid, f"Disetujui manual: {res['result'].get('no')}", {"koreksi": changed, **res["result"]})
        return res

    async def do_approve(item: dict, jenis: str, override: dict, actor: str, admin=None, auto: bool = False):
        iid = item["id"]
        if item["status"] == "approved":
            raise HTTPException(400, "Sudah disetujui")
        d = {**(item.get("draft") or {}), **(override or {})}
        actor_id = getattr(admin, "user_id", "") if admin else ""
        unit = await db.units.find_one({"id": d.get("unit_id")}, {"_id": 0}) if d.get("unit_id") else None
        result: dict[str, Any] = {}

        if jenis == "transfer":
            debit = float(d.get("debit") or 0)
            if debit <= 0:
                raise HTTPException(400, "Nominal wajib diisi")
            if not d.get("tanggal"):
                raise HTTPException(400, "Tanggal wajib diisi")
            if d.get("no_ref"):
                dup = await db.kas_masuk.find_one({"no_ref": str(d["no_ref"])}, {"_id": 0, "no_bukti": 1})
                if dup:
                    raise HTTPException(400, f"No. Ref sudah tercatat sebagai {dup['no_bukti']}")
            no = await hooks["next_bukti"](db, "KM")
            km = {
                "id": str(uuid.uuid4()), "tanggal": d["tanggal"][:10], "uraian": d.get("uraian") or "Pembayaran via WhatsApp",
                "tujuan_dana": d.get("tujuan_dana") or _label(unit), "debit": debit, "pic": d.get("pic") or "",
                "pengurus": d.get("pengurus") or (unit or {}).get("pengurus", ""), "unit_id": (unit or {}).get("id", ""),
                "unit_label": _label(unit), "no_ref": str(d.get("no_ref") or ""), "no_bukti": no,
                "source": "whatsapp" if item.get("source") == "whatsapp" else "upload", "inbox_id": iid,
                "created_at": _now(), "created_by": actor, "auto_approved": auto,
            }
            await db.kas_masuk.insert_one(km)
            result = {"type": "kas_masuk", "id": km["id"], "no": no}
            reply = f"Tercatat di Kas Masuk {no}\nNominal: {_idr(debit)}\nTanggal: {km['tanggal']}\nUnit: {km['unit_label'] or '-'}\nPengurus: {km['pengurus'] or '-'}"
        elif jenis == "hour_meter":
            if not unit:
                raise HTTPException(400, "Pilih unit terlebih dahulu")
            if not d.get("tanggal"):
                raise HTTPException(400, "Tanggal wajib diisi")
            hm_akhir = float(d.get("hm_akhir") or 0)
            hm_awal = float(d.get("hm_awal") if d.get("hm_awal") not in (None, "") else hm_akhir)
            if hm_akhir <= 0:
                raise HTTPException(400, "HM Akhir wajib diisi")
            if hm_awal > hm_akhir:
                raise HTTPException(400, "HM Awal tidak boleh lebih besar dari HM Akhir")
            op_user = None
            if d.get("operator_id"):
                op_user = await db.users.find_one({"user_id": d["operator_id"]}, {"_id": 0, "user_id": 1, "name": 1})
            existing = await db.operations.find_one({"unit_id": unit["id"], "tanggal": d["tanggal"][:10]}, {"_id": 0})
            total = round(max(0.0, hm_akhir - hm_awal), 2)
            if existing:
                await db.operations.update_one({"id": existing["id"]}, {"$set": {
                    "hour_meter_awal": hm_awal, "hour_meter_akhir": hm_akhir, "total_jam": total,
                    "keterangan": (existing.get("keterangan") or "") or "Laporan HM via WhatsApp",
                }})
                op_id = existing["id"]
            else:
                op_id = str(uuid.uuid4())
                await db.operations.insert_one({
                    "id": op_id, "unit_id": unit["id"], "unit_label": _label(unit),
                    "operator_id": (op_user or {}).get("user_id") or unit.get("operator_id") or actor_id or "wa-system",
                    "operator_name": (op_user or {}).get("name") or unit.get("operator_name") or actor,
                    "tanggal": d["tanggal"][:10], "hour_meter_awal": hm_awal, "hour_meter_akhir": hm_akhir,
                    "jumlah_cars": int(d.get("jumlah_cars") or 0), "pengurus": d.get("pengurus") or unit.get("pengurus", ""),
                    "keterangan": "Laporan HM via WhatsApp", "downtime_jam": 0.0, "solar_liter": 0.0, "catatan_operator": "",
                    "kondisi_alat": {}, "total_jam": total, "source": "whatsapp", "inbox_id": iid, "created_at": _now(),
                    "auto_approved": auto,
                })
            result = {"type": "operation", "id": op_id, "no": f"{_label(unit)} · {d['tanggal'][:10]}", "updated": bool(existing)}
            reply = f"Laporan HM tercatat\nUnit: {_label(unit)}\nTanggal: {d['tanggal'][:10]}\nHM: {hm_awal} -> {hm_akhir} ({total} jam)"
        else:
            raise HTTPException(400, "Jenis harus bukti transfer atau hour meter")

        await db.wa_inbox.update_one({"id": iid, "status": {"$ne": "approved"}}, {"$set": {
            "status": "approved", "jenis": jenis, "draft": d, "result": result, "reviewed_by": actor, "reviewed_at": _now(), "auto_approved": auto}})
        replied = False
        if item.get("source") == "whatsapp" and item.get("from_phone"):
            replied = await wa_send_text(item["from_phone"], reply + ("\n(Tercatat otomatis)" if auto else ""))
            await audit("reply_sent" if replied else "reply_failed", "Sistem", iid, "Balasan konfirmasi WA" + ("" if replied else " gagal terkirim"))
        return {"ok": True, "result": result, "replied": replied}

    # ---------- Pengaturan otomatis + audit ----------
    class AutoIn(BaseModel):
        transfer_enabled: bool = False
        hm_enabled: bool = False
        min_confidence: float = 0.9

    @r.get("/api/wa/auto-settings")
    async def get_auto(admin=Depends(require_admin)):
        cfg = await get_auto_settings()
        return {**cfg, "auto_count": await db.wa_inbox.count_documents({"auto_approved": True}),
                "manual_queue": await db.wa_inbox.count_documents({"status": {"$in": ["pending", "duplicate", "error"]}})}

    @r.put("/api/wa/auto-settings")
    async def put_auto(body: AutoIn, admin=Depends(require_admin)):
        if not 0.9 <= body.min_confidence <= 1.0:
            raise HTTPException(400, "Batas keyakinan minimal 90% (0.90 – 1.00)")
        before = await get_auto_settings()
        await db.app_settings.update_one({"key": "wa_auto"}, {"$set": {"key": "wa_auto", **body.model_dump(), "updated_by": admin.name, "updated_at": _now()}}, upsert=True)
        await audit("settings_changed", admin.name, "", "Pengaturan persetujuan otomatis diubah", {"sebelum": before, "sesudah": body.model_dump()})
        return await get_auto_settings()

    @r.get("/api/wa/audit")
    async def list_audit(inbox_id: Optional[str] = None, action: Optional[str] = None, limit: int = 300, admin=Depends(require_admin)):
        q: dict[str, Any] = {}
        if inbox_id:
            q["inbox_id"] = inbox_id
        if action and action != "all":
            q["action"] = {"$in": action.split(",")}
        return await db.wa_audit.find(q, {"_id": 0}).sort("at", -1).to_list(min(max(limit, 1), 1000))

    # ---------- Kontak WA ----------
    @r.get("/api/wa/contacts")
    async def list_contacts(admin=Depends(require_admin)):
        return await db.wa_contacts.find({}, {"_id": 0}).sort("nama", 1).to_list(1000)

    @r.post("/api/wa/contacts")
    async def create_contact(body: ContactIn, admin=Depends(require_admin)):
        phone = norm_phone(body.phone)
        if len(phone) < 9:
            raise HTTPException(400, "Nomor WhatsApp tidak valid")
        if await db.wa_contacts.find_one({"phone": phone}):
            raise HTTPException(400, "Nomor sudah terdaftar")
        doc = {"id": str(uuid.uuid4()), **body.model_dump(), "phone": phone, "created_at": _now()}
        await db.wa_contacts.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @r.patch("/api/wa/contacts/{cid}")
    async def update_contact(cid: str, body: ContactIn, admin=Depends(require_admin)):
        phone = norm_phone(body.phone)
        if await db.wa_contacts.find_one({"phone": phone, "id": {"$ne": cid}}):
            raise HTTPException(400, "Nomor sudah terdaftar")
        res = await db.wa_contacts.update_one({"id": cid}, {"$set": {**body.model_dump(), "phone": phone}})
        if res.matched_count == 0:
            raise HTTPException(404, "Not found")
        return await db.wa_contacts.find_one({"id": cid}, {"_id": 0})

    @r.delete("/api/wa/contacts/{cid}")
    async def delete_contact(cid: str, admin=Depends(require_admin)):
        await db.wa_contacts.delete_one({"id": cid})
        return {"ok": True}

    # ---------- Webhook WhatsApp (publik) ----------
    @r.get("/api/whatsapp/webhook")
    async def verify(request: Request):
        if not wa_configured():
            return PlainTextResponse("WhatsApp belum dikonfigurasi", status_code=503)
        q = request.query_params
        if q.get("hub.mode") != "subscribe" or not hmac.compare_digest(q.get("hub.verify_token", ""), _env("WHATSAPP_VERIFY_TOKEN")):
            return PlainTextResponse("Forbidden", status_code=403)
        return PlainTextResponse(q.get("hub.challenge", ""))

    async def handle_payload(payload: dict):
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                names = {c.get("wa_id"): (c.get("profile") or {}).get("name", "") for c in value.get("contacts", [])}
                for m in value.get("messages", []):
                    mid, sender = m.get("id"), m.get("from")
                    if sender:
                        await db.wa_last_inbound.update_one({"phone": norm_phone(sender)}, {"$set": {"phone": norm_phone(sender), "at": _now()}}, upsert=True)
                    if not mid or not sender or await db.wa_inbox.find_one({"message_id": mid}):
                        continue
                    if m.get("type") == "image":
                        img = m.get("image") or {}
                        try:
                            data, mime = await wa_download_media(img["id"])
                            doc = await create_item(data, mime, img.get("caption", ""), "whatsapp", sender, names.get(sender, ""), mid)
                            await audit("received", f"WA {names.get(sender, '') or sender}", doc["id"], f"Pesan WhatsApp · ket {img.get('caption') or '-'}")
                            await wa_send_text(sender, "Gambar diterima, sedang diproses dan menunggu verifikasi admin.")
                            await process_item(doc["id"])
                        except Exception as e:  # noqa: BLE001
                            await db.wa_inbox.insert_one({"id": str(uuid.uuid4()), "source": "whatsapp", "message_id": mid, "from_phone": sender,
                                                          "from_name": names.get(sender, ""), "caption": img.get("caption", ""), "status": "error",
                                                          "error": f"Gagal mengunduh gambar: {str(e)[:150]}", "received_at": _now(), "draft": {}, "warnings": []})
                    elif m.get("type") == "text":
                        await wa_send_text(sender, "Kirim FOTO bukti transfer atau foto layar HM, dengan keterangan unit (contoh: Sdlg 10).")

    @r.post("/api/whatsapp/webhook")
    async def receive(request: Request, background: BackgroundTasks):
        if not wa_configured():
            return {"status": "disabled"}
        raw = await request.body()
        expected = "sha256=" + hmac.new(_env("WHATSAPP_APP_SECRET").encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(request.headers.get("x-hub-signature-256", ""), expected):
            return PlainTextResponse("Invalid signature", status_code=401)
        try:
            payload = await request.json()
        except ValueError:
            return PlainTextResponse("Invalid JSON", status_code=400)
        if payload.get("object") == "whatsapp_business_account":
            background.add_task(handle_payload, payload)
        return {"status": "accepted"}

    return r
