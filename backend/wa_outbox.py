"""Pengiriman WhatsApp terpusat (outbox) — satu jalur untuk SEMUA pesan keluar.

Jaminan:
- Anti kirim ganda: setiap pesan punya `dedupe_key` unik (unique index Mongo). Pesan yang sudah
  terkirim / sedang dikirim dengan kunci yang sama tidak akan dikirim lagi.
- Retry aman: hanya untuk error yang PASTI belum sampai ke Meta (gagal koneksi) atau ditolak sementara
  (HTTP 429 / 5xx). Timeout setelah request terkirim = status tidak pasti -> TIDAK di-retry otomatis
  (mencegah pesan dobel), admin dapat mengirim ulang manual setelah mengecek.
- Kredensial tidak pernah disimpan / dicatat: header Authorization tidak ikut dicatat dan setiap teks
  error disaring (redact) dari token / app secret.
- Status pengiriman dari webhook Meta (sent / delivered / read / failed) diperbarui per pesan.
- Status koneksi "Terhubung" hanya bila pesan masuk asli (webhook bertanda tangan) DAN pesan keluar
  terkonfirmasi delivered/read oleh Meta.
"""
import asyncio
import hashlib
import logging
import os
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from pymongo.errors import DuplicateKeyError

log = logging.getLogger("wa_outbox")
logging.getLogger("httpx").setLevel(logging.WARNING)  # jangan catat URL request (bisa memuat URL media bertanda tangan)

INLINE_ATTEMPTS = 2          # percobaan langsung saat pesan dibuat
MAX_ATTEMPTS = 6             # total percobaan termasuk retry terjadwal
STUCK_MINUTES = 10           # "sending" lebih lama dari ini dianggap tidak pasti
RANK = {"sending": 0, "sent": 1, "delivered": 2, "read": 3}
# Kode error Meta yang bersifat sementara (aman diulang)
RETRIABLE_META_CODES = {4, 80007, 130429, 131016, 131048, 131056, 133004}
ERROR_HINTS = {
    131047: "Di luar jendela 24 jam — gunakan template yang disetujui Meta",
    131026: "Nomor tujuan tidak dapat menerima pesan (belum WhatsApp / belum menerima ketentuan)",
    131030: "Nomor tujuan belum terdaftar sebagai nomor uji (mode development)",
    132000: "Jumlah parameter template tidak sesuai",
    132001: "Template tidak ditemukan / belum disetujui untuk bahasa ini",
    190: "Access token tidak valid atau kedaluwarsa",
    100: "Parameter tidak valid (cek Phone Number ID / nomor tujuan)",
    133010: "Nomor pengirim belum terdaftar di Cloud API (jalankan Daftarkan Nomor)",
    368: "Akun dibatasi sementara oleh Meta",
}


def _now_dt():
    return datetime.now(timezone.utc)


def _now():
    return _now_dt().isoformat()


def _env(k):
    return (os.environ.get(k) or "").strip()


def wa_configured() -> bool:
    return all(_env(k) for k in ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN"))


def graph_url(path: str) -> str:
    base = (_env("WHATSAPP_GRAPH_BASE_URL") or "https://graph.facebook.com").rstrip("/")
    return f"{base}/{_env('WHATSAPP_API_VERSION') or 'v25.0'}/{path}"


def norm_phone(p: str) -> str:
    d = "".join(ch for ch in (p or "") if ch.isdigit())
    if d.startswith("0"):
        d = "62" + d[1:]
    return d


def redact(s: Any) -> str:
    """Hapus token / secret dari teks apa pun sebelum disimpan atau ditampilkan."""
    s = str(s or "")
    for k in ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN", "WEBHOOK_CRON_SECRET", "EMERGENT_LLM_KEY"):
        v = _env(k)
        if v and len(v) >= 6:
            s = s.replace(v, "***")
    s = re.sub(r"(access_token=)[^&\s]+", r"\1***", s, flags=re.I)
    s = re.sub(r"(Bearer\s+)[A-Za-z0-9._\-]+", r"\1***", s)
    s = re.sub(r"\bEAA[A-Za-z0-9]{20,}\b", "***", s)  # pola token Meta
    return s[:400]


def config_fingerprint() -> str:
    """Sidik konfigurasi (bukan rahasia) — status 'Terhubung' di-reset bila nomor/token diganti."""
    raw = f"{_env('WHATSAPP_PHONE_NUMBER_ID')}|{hashlib.sha256(_env('WHATSAPP_ACCESS_TOKEN').encode()).hexdigest()[:8]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _auth():
    return {"Authorization": f"Bearer {_env('WHATSAPP_ACCESS_TOKEN')}"}


async def graph_call(method: str, path: str, json: Optional[dict] = None, params: Optional[dict] = None) -> tuple[int, dict]:
    """Panggilan Graph API dengan hasil yang sudah disaring (tanpa token)."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10)) as c:
            r = await c.request(method, graph_url(path), headers=_auth(), json=json, params=params)
        try:
            body = r.json()
        except Exception:
            body = {"raw": redact(r.text[:300])}
        return r.status_code, body
    except Exception as e:  # noqa: BLE001
        return 0, {"error": {"message": redact(type(e).__name__)}}


def _meta_error(body: dict) -> tuple[int, str]:
    err = (body or {}).get("error") or {}
    code = int(err.get("code") or 0) if str(err.get("code") or "0").isdigit() else 0
    msg = err.get("error_user_msg") or err.get("message") or ""
    det = ((err.get("error_data") or {}).get("details")) or ""
    hint = ERROR_HINTS.get(code, "")
    return code, redact(" · ".join(x for x in [hint, msg, det] if x))


class Outbox:
    def __init__(self, db):
        self.db = db

    async def ensure_indexes(self):
        await self.db.wa_outbox.create_index("dedupe_key", unique=True)
        await self.db.wa_outbox.create_index("wa_message_id")
        await self.db.wa_outbox.create_index([("status", 1), ("next_retry_at", 1)])

    async def _audit(self, action, actor, detail, data=None):
        await self.db.wa_audit.insert_one({"id": str(uuid.uuid4()), "at": _now(), "action": action, "actor": actor,
                                           "inbox_id": (data or {}).get("inbox_id", ""), "detail": redact(detail)[:500],
                                           "data": data or {}})

    # ---------- kirim ----------
    async def send(self, to: str, message: dict, kind: str, dedupe_key: str, actor: str = "Sistem",
                   ref: Optional[dict] = None, label: str = "") -> dict:
        """message: bagian payload Meta tanpa messaging_product/to, mis. {"type":"text","text":{...}}."""
        to = norm_phone(to)
        ref = ref or {}
        base = {"id": str(uuid.uuid4()), "kind": kind, "label": label or kind, "to": to, "message": message, "ref": ref,
                "attempts": 0, "created_at": _now(), "actor": actor, "history": []}
        if not to:
            return {**base, "status": "skipped", "error": "Nomor tujuan kosong"}
        if not wa_configured():
            prev = await self.db.wa_outbox.find_one({"logical_key": dedupe_key, "status": "simulated"}, {"_id": 0})
            if prev:
                await self._audit("wa_deduped", actor, f"{label or kind} → +{to} tidak dikirim ulang (simulasi sebelumnya {prev.get('created_at', '')[:16]})",
                                  {"outbox_id": prev.get("id"), **ref})
                return {**prev, "deduped": True}
            doc = {**base, "dedupe_key": f"sim:{base['id']}", "logical_key": dedupe_key, "status": "simulated",
                   "error": "WhatsApp belum dikonfigurasi — pesan disimpan sebagai simulasi"}
            await self.db.wa_outbox.insert_one(doc)
            doc.pop("_id", None)
            await self._audit("wa_simulated", actor, f"{label or kind} → +{to} (simulasi, belum terhubung)", {"outbox_id": doc["id"], **ref})
            return doc
        doc = {**base, "dedupe_key": dedupe_key, "logical_key": dedupe_key, "status": "sending", "sending_since": _now()}
        try:
            await self.db.wa_outbox.insert_one(doc)
        except DuplicateKeyError:
            ex = await self.db.wa_outbox.find_one({"dedupe_key": dedupe_key}, {"_id": 0})
            await self._audit("wa_deduped", actor, f"{label or kind} → +{to} tidak dikirim ulang (sudah ada: {ex.get('status')})",
                              {"outbox_id": ex.get("id"), **ref})
            return {**ex, "deduped": True}
        doc.pop("_id", None)
        return await self._attempt(doc, INLINE_ATTEMPTS, actor)

    async def _attempt(self, doc: dict, tries: int, actor: str) -> dict:
        payload = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": doc["to"], **doc["message"]}
        result: dict[str, Any] = {}
        for i in range(tries):
            attempt_no = int(doc.get("attempts") or 0) + 1
            doc["attempts"] = attempt_no
            outcome = await self._post(payload)
            doc["history"] = (doc.get("history") or [])[-9:] + [{"at": _now(), "attempt": attempt_no, **{k: v for k, v in outcome.items() if k != "wa_message_id"}}]
            result = outcome
            if outcome["ok"] or not outcome["retriable"] or attempt_no >= MAX_ATTEMPTS:
                break
            if i < tries - 1:
                await asyncio.sleep(1.0 + random.random())
        if result.get("ok"):
            upd = {"status": "sent", "wa_message_id": result.get("wa_message_id", ""), "sent_at": _now(), "error": "",
                   "attempts": doc["attempts"], "history": doc["history"], "retriable": False, "next_retry_at": None}
            await self.db.wa_outbox.update_one({"id": doc["id"]}, {"$set": upd, "$unset": {"sending_since": ""}})
            await self._audit("wa_sent", actor, f"{doc.get('label')} → +{doc['to']} diterima Meta (percobaan {doc['attempts']})",
                              {"outbox_id": doc["id"], **(doc.get("ref") or {})})
        else:
            retriable = bool(result.get("retriable")) and doc["attempts"] < MAX_ATTEMPTS
            nxt = (_now_dt() + timedelta(minutes=15 * (2 ** max(0, doc["attempts"] - INLINE_ATTEMPTS)))).isoformat() if retriable else None
            upd = {"status": "failed", "error": result.get("error", ""), "error_code": result.get("code", 0), "http_status": result.get("http", 0),
                   "attempts": doc["attempts"], "history": doc["history"], "retriable": retriable, "next_retry_at": nxt,
                   "uncertain": bool(result.get("uncertain")), "failed_at": _now()}
            await self.db.wa_outbox.update_one({"id": doc["id"]}, {"$set": upd, "$unset": {"sending_since": ""}})
            await self._audit("wa_failed", actor, f"{doc.get('label')} → +{doc['to']} gagal: {result.get('error', '')}"
                              + (" · dijadwalkan ulang" if retriable else ""), {"outbox_id": doc["id"], **(doc.get("ref") or {})})
        doc.update(upd)
        return doc

    async def _post(self, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(25, connect=8)) as c:
                r = await c.post(graph_url(f"{_env('WHATSAPP_PHONE_NUMBER_ID')}/messages"), headers=_auth(), json=payload)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout) as e:
            return {"ok": False, "retriable": True, "http": 0, "code": 0, "error": f"Gagal terhubung ke Meta ({type(e).__name__})"}
        except httpx.TimeoutException as e:
            # request mungkin sudah sampai Meta -> jangan retry otomatis (cegah dobel)
            return {"ok": False, "retriable": False, "uncertain": True, "http": 0, "code": 0,
                    "error": f"Timeout menunggu Meta ({type(e).__name__}) — status tidak pasti, cek WhatsApp sebelum kirim ulang"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "retriable": False, "http": 0, "code": 0, "error": redact(f"Error {type(e).__name__}")}
        try:
            body = r.json()
        except Exception:
            body = {}
        if r.status_code < 300:
            mid = ((body.get("messages") or [{}])[0] or {}).get("id", "")
            return {"ok": True, "http": r.status_code, "wa_message_id": mid}
        code, msg = _meta_error(body)
        retriable = r.status_code == 429 or r.status_code >= 500 or code in RETRIABLE_META_CODES
        return {"ok": False, "retriable": retriable, "http": r.status_code, "code": code, "error": f"HTTP {r.status_code} {msg}".strip()[:400]}

    # ---------- retry ----------
    async def retry(self, oid: str, actor: str) -> dict:
        if not wa_configured():
            raise ValueError("WhatsApp belum dikonfigurasi")
        doc = await self.db.wa_outbox.find_one_and_update(
            {"id": oid, "status": "failed"}, {"$set": {"status": "sending", "sending_since": _now()}}, projection={"_id": 0})
        if not doc:
            raise ValueError("Hanya pesan berstatus gagal yang bisa dikirim ulang")
        await self._audit("wa_retry", actor, f"Kirim ulang {doc.get('label')} → +{doc['to']}", {"outbox_id": oid, **(doc.get("ref") or {})})
        return await self._attempt(doc, 1, actor)

    async def retry_due(self, actor: str = "Penjadwal retry") -> dict:
        now = _now_dt()
        # pesan "sending" yang macet (proses mati di tengah) -> tidak pasti, tidak di-retry otomatis
        stuck = (now - timedelta(minutes=STUCK_MINUTES)).isoformat()
        res = await self.db.wa_outbox.update_many({"status": "sending", "sending_since": {"$lt": stuck}}, {"$set": {
            "status": "failed", "retriable": False, "uncertain": True, "failed_at": _now(),
            "error": "Pengiriman terhenti — status tidak pasti, cek WhatsApp sebelum kirim ulang"}, "$unset": {"sending_since": ""}})
        done = {"retried": 0, "sent": 0, "failed": 0, "stuck_marked": res.modified_count}
        if not wa_configured():
            return done
        for _ in range(50):
            doc = await self.db.wa_outbox.find_one_and_update(
                {"status": "failed", "retriable": True, "attempts": {"$lt": MAX_ATTEMPTS}, "next_retry_at": {"$lte": now.isoformat()}},
                {"$set": {"status": "sending", "sending_since": _now()}}, projection={"_id": 0})
            if not doc:
                break
            done["retried"] += 1
            out = await self._attempt(doc, 1, actor)
            done["sent" if out["status"] == "sent" else "failed"] += 1
        return done

    # ---------- status dari webhook ----------
    async def apply_status(self, st: dict):
        mid, s = st.get("id"), st.get("status")
        if not mid or s not in ("sent", "delivered", "read", "failed"):
            return
        doc = await self.db.wa_outbox.find_one({"wa_message_id": mid}, {"_id": 0, "id": 1, "status": 1, "to": 1, "label": 1, "ref": 1})
        if not doc:
            return
        upd: dict[str, Any] = {f"delivery.{s}_at": _now()}
        if s == "failed":
            errs = st.get("errors") or [{}]
            e0 = errs[0] or {}
            code = int(e0.get("code") or 0) if str(e0.get("code") or "0").isdigit() else 0
            msg = redact(" · ".join(x for x in [ERROR_HINTS.get(code, ""), e0.get("title") or e0.get("message") or "",
                                                ((e0.get("error_data") or {}).get("details") or "")] if x))
            upd.update({"status": "failed", "error": f"Meta: {msg}", "error_code": code, "retriable": False, "failed_at": _now()})
            await self._audit("wa_delivery_failed", "Meta", f"{doc.get('label')} → +{doc.get('to')} gagal diantar: {msg}",
                              {"outbox_id": doc["id"], **(doc.get("ref") or {})})
        elif RANK.get(s, 0) > RANK.get(doc.get("status"), -1):
            upd["status"] = s
        await self.db.wa_outbox.update_one({"id": doc["id"]}, {"$set": upd})
        if s in ("delivered", "read"):
            await mark_connection(self.db, "outbound", st.get("recipient_id") or doc.get("to", ""))


# ---------- status koneksi ----------
async def mark_connection(db, side: str, phone: str):
    fp = config_fingerprint()
    cur = await db.app_settings.find_one({"key": "wa_connection"}, {"_id": 0}) or {}
    if cur.get("fingerprint") != fp:
        cur = {"key": "wa_connection", "fingerprint": fp}
    first = not cur.get(f"{side}_verified_at")
    cur.update({f"{side}_verified_at": cur.get(f"{side}_verified_at") or _now(), f"{side}_last_at": _now(), f"{side}_phone": norm_phone(phone)})
    await db.app_settings.update_one({"key": "wa_connection"}, {"$set": cur}, upsert=True)
    if first:
        await db.wa_audit.insert_one({"id": str(uuid.uuid4()), "at": _now(), "action": "wa_connection_verified", "actor": "Meta",
                                      "inbox_id": "", "detail": ("Pesan MASUK asli pertama diterima dari" if side == "inbound" else
                                                                 "Pesan KELUAR pertama terkonfirmasi sampai ke") + f" +{norm_phone(phone)}", "data": {}})


async def connection_state(db) -> dict:
    missing = [k for k in ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN") if not _env(k)]
    cur = await db.app_settings.find_one({"key": "wa_connection"}, {"_id": 0}) or {}
    if cur.get("fingerprint") != config_fingerprint():
        cur = {}
    inbound, outbound = cur.get("inbound_verified_at"), cur.get("outbound_verified_at")
    if missing:
        level, label = "not_configured", "Belum Dikonfigurasi"
    elif inbound and outbound:
        level, label = "connected", "Terhubung · Terverifikasi"
    elif inbound or outbound:
        level, label = "partial", "Sebagian Terverifikasi"
    else:
        level, label = "unverified", "Kredensial Terisi · Belum Diuji"
    return {"level": level, "label": label, "missing": missing, "inbound_verified_at": inbound, "inbound_phone": cur.get("inbound_phone", ""),
            "outbound_verified_at": outbound, "outbound_phone": cur.get("outbound_phone", ""), "inbound_last_at": cur.get("inbound_last_at"),
            "outbound_last_at": cur.get("outbound_last_at"), "phone_check": cur.get("phone_check"),
            "waba_id_set": bool(_env("WHATSAPP_WABA_ID")), "api_version": _env("WHATSAPP_API_VERSION") or "v25.0"}


async def save_phone_check(db, info: dict):
    fp = config_fingerprint()
    cur = await db.app_settings.find_one({"key": "wa_connection"}, {"_id": 0}) or {}
    if cur.get("fingerprint") != fp:
        cur = {"key": "wa_connection", "fingerprint": fp}
    cur["phone_check"] = {**info, "at": _now()}
    await db.app_settings.update_one({"key": "wa_connection"}, {"$set": cur}, upsert=True)
