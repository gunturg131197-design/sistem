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
from zoneinfo import ZoneInfo
from typing import Any, Callable, Optional

import httpx
from bson import Binary
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from hm_check import HM_DEFAULT, hm_anomalies
from wa_ai import AI_MODEL, extract_image, match_unit, normalize_image
from wa_outbox import (Outbox, connection_state, graph_call, graph_url, mark_connection, norm_phone, redact,
                       save_phone_check, wa_configured)

MAX_BYTES = 12 * 1024 * 1024


def _now():
    return datetime.now(timezone.utc).isoformat()


def _env(k):
    return (os.environ.get(k) or "").strip()


def _graph(path: str) -> str:
    return graph_url(path)


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
    confirm_anomaly: bool = False  # admin sudah memeriksa peringatan HM janggal


def build_whatsapp_router(db, require_admin: Callable, hooks: dict) -> APIRouter:
    """hooks: {'next_bukti': async fn(db, prefix) -> str}"""
    r = APIRouter()
    outbox = Outbox(db)

    @r.on_event("startup")
    async def _wa_indexes():
        await outbox.ensure_indexes()

    async def send_text(to: str, body: str, kind: str, key: str, label: str, ref: Optional[dict] = None) -> dict:
        return await outbox.send(to, {"type": "text", "text": {"preview_url": False, "body": body[:4096]}}, kind, key,
                                 actor="Sistem", ref=ref or {}, label=label)

    AUTO_DEFAULT = {"transfer_enabled": False, "hm_enabled": False, "min_confidence": 0.9, **HM_DEFAULT}

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
        cfg = await get_auto_settings()
        try:
            conf = float(ai.get("keyakinan") or 0)
        except (TypeError, ValueError):
            conf = 0.0
        anomalies: list = []
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
            anomalies = await hm_anomalies(db, (unit or {}).get("id", ""), tgl, draft.get("hm_awal"), draft.get("hm_akhir"),
                                           conf, cfg, exclude_op_id=draft.get("existing_op_id"))
            if not draft["operator_id"]:
                warnings.append("Operator belum dikenali — pilih operator")
        else:
            warnings.append("Gambar bukan bukti transfer atau foto HM")
        if not unit and jenis in ("transfer", "hour_meter"):
            warnings.append(f"Unit untuk keterangan \"{item.get('caption') or '-'}\" belum dikenali — pilih unit")

        # ---- evaluasi persetujuan otomatis ----
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
        reasons.extend(f"HM janggal: {a['pesan']}" for a in anomalies)
        reasons.extend(f"Peringatan: {w}" for w in warnings)
        auto_check = {"eligible": not reasons, "confidence": conf, "threshold": float(cfg["min_confidence"]), "reasons": reasons, "at": _now()}

        await db.wa_inbox.update_one({"id": item_id}, {"$set": {
            "status": status, "jenis": jenis, "ai": ai, "draft": draft, "warnings": warnings,
            "match": {"unit_label": _label(unit), "via": how, "contact": (contact or {}).get("nama", "")},
            "processed_at": _now(), "error": "", "auto_check": auto_check, "hm_anomalies": anomalies, "hm_flag": bool(anomalies),
        }})
        if anomalies:
            await audit("hm_anomaly", "Sistem (pemeriksa HM)", item_id, "; ".join(a["pesan"] for a in anomalies),
                        {"anomalies": anomalies, "unit": _label(unit)})
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
            "connection": await connection_state(db),
            "counts": {**{s: await db.wa_inbox.count_documents({"status": s}) for s in ("processing", "pending", "duplicate", "approved", "rejected", "error")},
                       "hm_flag": await db.wa_inbox.count_documents({"hm_flag": True, "status": {"$in": ["pending", "duplicate"]}})},
        }

    # ---------- Inbox ----------
    @r.get("/api/wa/inbox")
    async def list_inbox(status: Optional[str] = None, flag: Optional[str] = None, admin=Depends(require_admin)):
        sts = [x for x in (status or "").split(",") if x and x != "all"]
        q: dict[str, Any] = {"status": {"$in": sts}} if sts else {}
        if flag == "hm":
            q["hm_flag"] = True
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
        res = await do_approve(item, body.jenis or item.get("jenis"), body.draft or {}, actor=admin.name, admin=admin,
                               confirm_anomaly=body.confirm_anomaly)
        if res.get("anomalies"):
            await audit("hm_anomaly_confirmed", admin.name, iid, "Admin menyetujui HM janggal setelah pemeriksaan: "
                        + "; ".join(a["pesan"] for a in res["anomalies"]), {"anomalies": res["anomalies"]})
        await audit("approved", admin.name, iid, f"Disetujui manual: {res['result'].get('no')}", {"koreksi": changed, **res["result"]})
        return res

    async def do_approve(item: dict, jenis: str, override: dict, actor: str, admin=None, auto: bool = False,
                         confirm_anomaly: bool = False):
        iid = item["id"]
        if item["status"] == "approved":
            raise HTTPException(400, "Sudah disetujui")
        d = {**(item.get("draft") or {}), **(override or {})}
        actor_id = getattr(admin, "user_id", "") if admin else ""
        unit = await db.units.find_one({"id": d.get("unit_id")}, {"_id": 0}) if d.get("unit_id") else None
        result: dict[str, Any] = {}
        anomalies: list = []

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
            # pemeriksaan HM janggal pada nilai FINAL (setelah koreksi admin)
            cfg = await get_auto_settings()
            orig = item.get("draft") or {}
            edited = any(str(override.get(k)) != str(orig.get(k)) for k in ("hm_akhir", "hm_awal", "tanggal", "unit_id") if k in (override or {}))
            try:
                conf_v = None if edited else float((item.get("ai") or {}).get("keyakinan") or 0)
            except (TypeError, ValueError):
                conf_v = 0.0
            same_day = await db.operations.find_one({"unit_id": unit["id"], "tanggal": d["tanggal"][:10]}, {"_id": 0, "id": 1})
            anomalies = await hm_anomalies(db, unit["id"], d["tanggal"][:10], hm_awal, hm_akhir, conf_v, cfg,
                                           exclude_op_id=(same_day or {}).get("id"))
            if anomalies and auto:
                raise HTTPException(400, "HM janggal: " + "; ".join(a["pesan"] for a in anomalies))
            if anomalies and not confirm_anomaly:
                raise HTTPException(409, "HM janggal — centang konfirmasi pemeriksaan sebelum menyetujui: " + "; ".join(a["pesan"] for a in anomalies))
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
        replied, reply_status = False, ""
        if item.get("source") == "whatsapp" and item.get("from_phone"):
            ob = await send_text(item["from_phone"], reply + ("\n(Tercatat otomatis)" if auto else ""), "reply",
                                 f"reply:{iid}", "Balasan konfirmasi", {"inbox_id": iid})
            reply_status = ob.get("status", "")
            replied = reply_status in ("sent", "delivered", "read")
        return {"ok": True, "result": result, "replied": replied, "reply_status": reply_status, "anomalies": anomalies}

    # ---------- Pengaturan otomatis + audit ----------
    class AutoIn(BaseModel):
        transfer_enabled: bool = False
        hm_enabled: bool = False
        min_confidence: float = 0.9
        hm_spike_check: Optional[bool] = None
        hm_max_per_day: Optional[float] = None

    @r.get("/api/wa/auto-settings")
    async def get_auto(admin=Depends(require_admin)):
        cfg = await get_auto_settings()
        return {**cfg, "auto_count": await db.wa_inbox.count_documents({"auto_approved": True}),
                "hm_flag_count": await db.wa_inbox.count_documents({"hm_flag": True, "status": {"$in": ["pending", "duplicate"]}}),
                "manual_queue": await db.wa_inbox.count_documents({"status": {"$in": ["pending", "duplicate", "error"]}})}

    @r.put("/api/wa/auto-settings")
    async def put_auto(body: AutoIn, admin=Depends(require_admin)):
        if not 0.9 <= body.min_confidence <= 1.0:
            raise HTTPException(400, "Batas keyakinan minimal 90% (0.90 – 1.00)")
        if body.hm_max_per_day is not None and not 1 <= body.hm_max_per_day <= 24:
            raise HTTPException(400, "Batas lonjakan HM harus 1 – 24 jam per hari")
        before = await get_auto_settings()
        new = {k: v for k, v in body.model_dump().items() if v is not None}
        await db.app_settings.update_one({"key": "wa_auto"}, {"$set": {"key": "wa_auto", **new, "updated_by": admin.name, "updated_at": _now()}}, upsert=True)
        await audit("settings_changed", admin.name, "", "Pengaturan persetujuan otomatis / HM janggal diubah", {"sebelum": before, "sesudah": {**before, **new}})
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

    # ---------- Koneksi Cloud API: uji, daftar nomor, outbox ----------
    class SendTestIn(BaseModel):
        to: str
        mode: str = "text"  # text | template
        text: str = ""
        template_name: str = "hello_world"
        template_lang: str = "en_US"

    class PinIn(BaseModel):
        pin: str

    def _need_config():
        if not wa_configured():
            raise HTTPException(400, "Kredensial WhatsApp belum lengkap di server (Secrets)")

    @r.get("/api/wa/connection")
    async def get_connection(admin=Depends(require_admin)):
        return await connection_state(db)

    @r.post("/api/wa/cloud/check")
    async def cloud_check(admin=Depends(require_admin)):
        _need_config()
        code, body = await graph_call("GET", _env("WHATSAPP_PHONE_NUMBER_ID"), params={
            "fields": "display_phone_number,verified_name,quality_rating,code_verification_status,platform_type,name_status"})
        ok = code == 200
        info = {"ok": ok, "http": code}
        if ok:
            info.update({k: body.get(k) for k in ("display_phone_number", "verified_name", "quality_rating",
                                                   "code_verification_status", "platform_type", "name_status")})
        else:
            info["error"] = redact(((body.get("error") or {}).get("message")) or "Gagal menghubungi Meta")
        await save_phone_check(db, info)
        await audit("wa_check", admin.name, "", ("Tes koneksi berhasil: " + str(info.get("display_phone_number") or "")) if ok
                    else f"Tes koneksi gagal: {info.get('error')}", {"ok": ok, "http": code})
        return info

    @r.post("/api/wa/cloud/send-test")
    async def cloud_send_test(body: SendTestIn, admin=Depends(require_admin)):
        _need_config()
        to = norm_phone(body.to)
        if len(to) < 9:
            raise HTTPException(400, "Nomor tujuan tidak valid")
        slot = int(datetime.now(timezone.utc).timestamp() // 30)  # cegah klik ganda dalam 30 detik
        if body.mode == "template":
            name = (body.template_name or "hello_world").strip()
            if not all(ch.islower() or ch.isdigit() or ch == "_" for ch in name):
                raise HTTPException(400, "Nama template tidak valid")
            msg = {"type": "template", "template": {"name": name, "language": {"code": (body.template_lang or "en_US").strip()}}}
        else:
            text = (body.text or "Pesan uji dari aplikasi TRIRARA TUNGGAL PUTRA.").strip()
            msg = {"type": "text", "text": {"preview_url": False, "body": text[:1000]}}
        doc = await outbox.send(to, msg, "test", f"test:{to}:{body.mode}:{slot}", actor=admin.name, label="Pesan uji")
        return {k: doc.get(k) for k in ("id", "status", "error", "attempts", "wa_message_id", "deduped", "to")}

    @r.post("/api/wa/cloud/register")
    async def cloud_register(body: PinIn, admin=Depends(require_admin)):
        pin = (body.pin or "").strip()
        if not (len(pin) == 6 and pin.isdigit()):
            raise HTTPException(400, "PIN harus 6 digit angka")
        _need_config()
        code, res = await graph_call("POST", f"{_env('WHATSAPP_PHONE_NUMBER_ID')}/register", json={"messaging_product": "whatsapp", "pin": pin})
        ok = code < 300 and bool(res.get("success", True))
        err = "" if ok else redact(((res.get("error") or {}).get("message")) or "Gagal")
        await audit("wa_register", admin.name, "", "Nomor terdaftar di Cloud API" if ok else f"Pendaftaran nomor gagal: {err}", {"ok": ok, "http": code})
        return {"ok": ok, "http": code, "error": err}

    @r.post("/api/wa/cloud/subscribe")
    async def cloud_subscribe(admin=Depends(require_admin)):
        _need_config()
        waba = _env("WHATSAPP_WABA_ID")
        if not waba:
            raise HTTPException(400, "WHATSAPP_WABA_ID belum diisi di Secrets")
        code, res = await graph_call("POST", f"{waba}/subscribed_apps")
        ok = code < 300 and bool(res.get("success", True))
        err = "" if ok else redact(((res.get("error") or {}).get("message")) or "Gagal")
        await audit("wa_subscribe", admin.name, "", "Aplikasi berlangganan webhook WABA" if ok else f"Langganan webhook gagal: {err}", {"ok": ok, "http": code})
        return {"ok": ok, "http": code, "error": err}

    @r.get("/api/wa/outbox")
    async def list_outbox(status: Optional[str] = None, kind: Optional[str] = None, limit: int = 200, admin=Depends(require_admin)):
        q: dict[str, Any] = {}
        if status and status != "all":
            q["status"] = {"$in": status.split(",")}
        if kind and kind != "all":
            q["kind"] = {"$in": kind.split(",")}
        rows = await db.wa_outbox.find(q, {"_id": 0}).sort("created_at", -1).to_list(min(max(limit, 1), 1000))
        counts = {s: await db.wa_outbox.count_documents({"status": s}) for s in ("sending", "sent", "delivered", "read", "failed", "simulated")}
        return {"items": rows, "counts": counts}

    @r.post("/api/wa/outbox/{oid}/retry")
    async def retry_outbox(oid: str, admin=Depends(require_admin)):
        try:
            doc = await outbox.retry(oid, admin.name)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {k: doc.get(k) for k in ("id", "status", "error", "attempts", "wa_message_id")}

    @r.post("/api/cron/wa-outbox-retry")
    async def cron_outbox_retry(request: Request, background: BackgroundTasks):
        # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
        secret = _env("WEBHOOK_CRON_SECRET")
        auth = request.headers.get("authorization", "")
        token = auth[7:] if auth.lower().startswith("bearer ") else ""
        if not secret or not token or not hmac.compare_digest(token, secret):
            return Response(content='{"detail":"Unauthorized"}', status_code=401, media_type="application/json")
        try:
            env = await request.json() if (await request.body()) else {}
        except ValueError:
            return Response(content='{"detail":"Invalid body"}', status_code=400, media_type="application/json")
        if env is not None and not isinstance(env, dict):
            return Response(content='{"detail":"Invalid body"}', status_code=400, media_type="application/json")
        run_key = request.headers.get("x-webhook-id") or (env or {}).get("run_id") or f"manual-{uuid.uuid4()}"
        res = await db.cron_runs.update_one({"run_id": f"retry:{run_key}"}, {"$setOnInsert": {"run_id": f"retry:{run_key}", "job": "wa-outbox-retry", "received_at": _now()}}, upsert=True)
        if res.upserted_id is None:
            return {"status": "duplicate"}

        async def _job():
            out = await outbox.retry_due()
            await db.cron_runs.update_one({"run_id": f"retry:{run_key}"}, {"$set": {"result": out, "finished_at": _now()}})
            if out["retried"] or out["stuck_marked"]:
                await audit("outbox_retry_run", "Penjadwal retry", "", f"Retry terjadwal: dicoba {out['retried']}, terkirim {out['sent']}, gagal {out['failed']}, macet {out['stuck_marked']}", out)
        background.add_task(_job)
        return {"status": "accepted"}

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
                for st in value.get("statuses", []) or []:
                    try:
                        await outbox.apply_status(st)
                    except Exception as e:  # noqa: BLE001
                        await audit("webhook_error", "Sistem", "", f"Status webhook gagal diproses: {redact(type(e).__name__)}")
                for m in value.get("messages", []):
                    await ingest_message(m, names)

    async def ingest_message(m: dict, names: dict, simulated: bool = False, sim_media: Optional[tuple] = None) -> dict:
        """Satu jalur untuk pesan masuk asli (webhook) maupun simulasi. Simulasi TIDAK menandai koneksi terverifikasi."""
        mid, sender = m.get("id"), m.get("from")
        tag = "WA (simulasi)" if simulated else "WA"
        if sender and not simulated:
            await db.wa_last_inbound.update_one({"phone": norm_phone(sender)}, {"$set": {"phone": norm_phone(sender), "at": _now()}}, upsert=True)
            await mark_connection(db, "inbound", sender)
        if not mid or not sender:
            return {"status": "ignored"}
        # idempoten: Meta bisa mengirim ulang webhook yang sama
        seen = await db.wa_seen_messages.update_one({"message_id": mid}, {"$setOnInsert": {"message_id": mid, "at": _now(), "simulated": simulated}}, upsert=True)
        if seen.upserted_id is None or await db.wa_inbox.find_one({"message_id": mid}):
            return {"status": "duplicate"}
        mtype = m.get("type")
        doc_img = m.get("document") or {}
        if mtype == "document" and str(doc_img.get("mime_type", "")).startswith("image/"):
            mtype, m = "image", {**m, "image": doc_img}
        who = f"{tag} {names.get(sender, '') or sender}"
        if mtype == "image":
            img = m.get("image") or {}
            try:
                data, mime = sim_media if simulated and sim_media else await wa_download_media(img["id"])
                doc = await create_item(data, mime, img.get("caption", ""), "whatsapp", sender, names.get(sender, ""), mid)
                if simulated:
                    await db.wa_inbox.update_one({"id": doc["id"]}, {"$set": {"simulated": True}})
                await audit("received", who, doc["id"], f"Pesan WhatsApp{' (simulasi)' if simulated else ''} · ket {img.get('caption') or '-'}")
                await send_text(sender, "Gambar diterima, sedang diproses AI. Anda akan menerima konfirmasi setelah tercatat.",
                                "ack", f"ack:{mid}", "Tanda terima gambar", {"inbox_id": doc["id"]})
                await process_item(doc["id"])
                return {"status": "image", "inbox_id": doc["id"]}
            except HTTPException as e:
                await audit("received_error", who, "", f"Gambar ditolak: {e.detail}")
                return {"status": "error", "error": e.detail}
            except Exception as e:  # noqa: BLE001
                eid = str(uuid.uuid4())
                await db.wa_inbox.insert_one({"id": eid, "source": "whatsapp", "message_id": mid, "from_phone": norm_phone(sender),
                                              "from_name": names.get(sender, ""), "caption": img.get("caption", ""), "status": "error",
                                              "error": f"Gagal mengunduh gambar: {redact(str(e))[:150]}", "received_at": _now(), "draft": {}, "warnings": [],
                                              "simulated": simulated})
                await audit("received_error", who, eid, f"Gagal mengunduh gambar: {redact(type(e).__name__)}")
                return {"status": "error", "inbox_id": eid}
        if mtype == "text":
            await audit("text_received", who, "", "Pesan teks diterima (bukan gambar)" + (f": {(m.get('text') or {}).get('body', '')[:80]}" if simulated else ""))
            # anti-spam: panduan format maks. 1x per nomor per hari (WITA)
            today = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Makassar")).strftime("%Y-%m-%d")
            ob = await send_text(sender, "Kirim FOTO bukti transfer atau foto layar HM, dengan keterangan unit (contoh: Sdlg 10).",
                                 "help", f"help:{norm_phone(sender)}:{today}", "Panduan format")
            return {"status": "text", "reply": ob.get("status"), "reply_deduped": bool(ob.get("deduped"))}
        await audit("text_received", who, "", f"Jenis pesan '{mtype}' diabaikan")
        return {"status": "ignored", "type": mtype}

    @r.post("/api/wa/simulate/inbound")
    async def simulate_inbound(background: BackgroundTasks, phone: str = Form(...), name: str = Form(""), text: str = Form(""),
                               caption: str = Form(""), message_id: str = Form(""), file: Optional[UploadFile] = File(None),
                               admin=Depends(require_admin)):
        """Uji alur pesan masuk TANPA Meta: melewati pipeline yang sama (dedupe, balasan via outbox simulasi, AI, auto-approve)."""
        p = norm_phone(phone)
        if len(p) < 9 or len(p) > 15:
            raise HTTPException(400, "Nomor pengirim tidak valid")
        mid = (message_id or "").strip() or f"sim.{uuid.uuid4().hex}"
        if not mid.startswith("sim."):
            mid = f"sim.{mid}"
        names = {p: name.strip()[:60]}
        if file is not None:
            data = await file.read()
            if not data:
                raise HTTPException(400, "File kosong")
            if len(data) > MAX_BYTES:
                raise HTTPException(400, "Ukuran gambar maksimal 12 MB")
            m = {"id": mid, "from": p, "type": "image", "image": {"id": "simulated", "caption": caption}}
            await audit("simulated_inbound", admin.name, "", f"Simulasi gambar dari +{p} · ket {caption or '-'}")
            seen = await db.wa_seen_messages.find_one({"message_id": mid})
            if seen:
                return {"status": "duplicate", "message_id": mid}
            background.add_task(ingest_message, m, names, True, (data, file.content_type or "image/jpeg"))
            return {"status": "accepted", "message_id": mid, "type": "image"}
        if not text.strip():
            raise HTTPException(400, "Isi teks atau lampirkan gambar")
        await audit("simulated_inbound", admin.name, "", f"Simulasi teks dari +{p}")
        res = await ingest_message({"id": mid, "from": p, "type": "text", "text": {"body": text.strip()[:1000]}}, names, True)
        return {**res, "message_id": mid}

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
