"""Ringkasan Harian WhatsApp untuk setiap pengurus (dijadwalkan 20:00 WITA via .emergent/crons.yml).

Isi: rekap HM awal/akhir & total jam per unit hari itu, transfer diterima hari itu (nominal + No. Ref),
total penerimaan, piutang berjalan bulan ini, dan daftar yang masih menunggu verifikasi.

Piutang hanya memakai data TERVALIDASI:
  tagihan   = jam kerja di Ops Report x tarif sewa/jam (tarif unit, fallback tarif pengurus)
  pembayaran= Kas Masuk yang ditandai pengurus/unit (item WA baru masuk Kas Masuk setelah disetujui;
              No. Ref unik sehingga tidak terhitung ganda)
  piutang berjalan = saldo awal bulan (kumulatif sebelum bulan ini) + tagihan bulan ini - pembayaran bulan ini
"""
import hmac
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from wa_outbox import Outbox, _env, norm_phone, wa_configured

log = logging.getLogger("daily_summary")
TZ = ZoneInfo("Asia/Makassar")  # WITA
PENDING = ["pending", "duplicate", "error", "processing"]
SUMMARY_DEFAULT = {"enabled": True, "template_name": "", "template_lang": "id"}
TEMPLATE_TEXT = (
    "Ringkasan Harian TRIRARA TUNGGAL PUTRA\n"
    "Pengurus: {{1}}\nTanggal: {{2}}\n"
    "Jam kerja unit: {{3}}\n"
    "Transfer diterima hari ini: {{4}}\n"
    "Piutang berjalan bulan ini: {{5}}\n"
    "Menunggu verifikasi: {{6}}\n"
    "Detail lengkap tersedia di aplikasi."
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def today_wita() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d")


def idr(n) -> str:
    v = float(n or 0)
    return ("-" if v < 0 else "") + "Rp" + f"{abs(v):,.0f}".replace(",", ".")


def num(n) -> str:
    return f"{float(n or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip("0").rstrip(",")


def tgl_id(s: str) -> str:
    bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    try:
        d = datetime.strptime(s, "%Y-%m-%d")
        return f"{d.day} {bulan[d.month - 1]} {d.year}"
    except Exception:
        return s


def _one_line(s: str, limit: int = 900) -> str:
    """Parameter template Meta tidak boleh mengandung baris baru / tab / >4 spasi beruntun."""
    s = " ".join(str(s or "-").replace("\t", " ").splitlines())
    while "     " in s:
        s = s.replace("     ", "    ")
    return s[:limit] or "-"


async def build_summaries(db, tanggal: str) -> list:
    month = tanggal[:7]
    units = {u["id"]: u for u in await db.units.find({}, {"_id": 0}).to_list(5000)}
    registry = await db.pengurus_excavator.find({}, {"_id": 0}).to_list(1000)
    reg = {(r.get("nama") or "").strip().lower(): r for r in registry}
    contacts = await db.wa_contacts.find({"tipe": "pengurus"}, {"_id": 0}).to_list(1000)

    def canon(n):
        n = (n or "").strip()
        r = reg.get(n.lower())
        return r["nama"] if r else n

    def tarif(op, nama):
        u = units.get(op.get("unit_id")) or {}
        return float(u.get("tarif_sewa_per_jam") or 0) or float((reg.get(nama.lower()) or {}).get("tarif_sewa_per_jam") or 0)

    ops = await db.operations.find({"tanggal": {"$lte": tanggal}}, {"_id": 0}).to_list(100000)
    kms = await db.kas_masuk.find({"tanggal": {"$lte": tanggal}}, {"_id": 0}).to_list(100000)
    pend = await db.wa_inbox.find({"status": {"$in": PENDING}}, {"_id": 0, "media_id": 0, "ai": 0}).to_list(2000)

    names = {canon(c.get("pengurus") or c.get("nama")) for c in contacts}
    names |= {r["nama"] for r in registry}
    names |= {canon(u.get("pengurus")) for u in units.values() if u.get("pengurus")}
    names.discard("")

    out = []
    for nama in sorted(names, key=str.lower):
        key = nama.lower()
        my_units = [u for u in units.values() if (u.get("pengurus") or "").strip().lower() == key]
        my_ops = [o for o in ops if canon(o.get("pengurus") or (units.get(o.get("unit_id")) or {}).get("pengurus")).lower() == key]
        unit_ids = {u["id"] for u in my_units} | {o.get("unit_id") for o in my_ops if o.get("tanggal") == tanggal}

        rows = []
        for uid in unit_ids:
            u = units.get(uid) or {}
            day = [o for o in my_ops if o.get("unit_id") == uid and o.get("tanggal") == tanggal]
            label = u.get("kode_wa", "").split(",")[0].strip() or f"{u.get('unit_name', '')} {u.get('nomor_lambung', '')}".strip()
            if day:
                rows.append({"unit": label, "hm_awal": min(float(o.get("hour_meter_awal") or 0) for o in day),
                             "hm_akhir": max(float(o.get("hour_meter_akhir") or 0) for o in day),
                             "jam": round(sum(float(o.get("total_jam") or 0) for o in day), 2), "lapor": True})
            else:
                rows.append({"unit": label, "hm_awal": None, "hm_akhir": None, "jam": 0.0, "lapor": False})
        rows.sort(key=lambda x: x["unit"].lower())

        def paid(k):
            n = (k.get("pengurus") or "").strip() or ((units.get(k.get("unit_id")) or {}).get("pengurus") or "").strip()
            return canon(n).lower() == key

        my_km = [k for k in kms if paid(k)]
        transfers = [{"no_bukti": k.get("no_bukti", ""), "nominal": float(k.get("debit") or 0), "no_ref": k.get("no_ref") or "-",
                      "unit": k.get("unit_label") or k.get("tujuan_dana") or ""} for k in my_km if k.get("tanggal") == tanggal]
        tagihan_bulan = sum(float(o.get("total_jam") or 0) * tarif(o, nama) for o in my_ops if (o.get("tanggal") or "").startswith(month))
        tagihan_lalu = sum(float(o.get("total_jam") or 0) * tarif(o, nama) for o in my_ops if (o.get("tanggal") or "") < f"{month}-01")
        bayar_bulan = sum(float(k.get("debit") or 0) for k in my_km if (k.get("tanggal") or "").startswith(month))
        bayar_lalu = sum(float(k.get("debit") or 0) for k in my_km if (k.get("tanggal") or "") < f"{month}-01")
        saldo_awal = tagihan_lalu - bayar_lalu
        piutang = saldo_awal + tagihan_bulan - bayar_bulan
        jam_tanpa_tarif = sum(float(o.get("total_jam") or 0) for o in my_ops if (o.get("tanggal") or "").startswith(month) and tarif(o, nama) <= 0)

        pending = [{"id": p["id"], "jenis": p.get("jenis") or "-", "status": p["status"], "caption": p.get("caption") or "-",
                    "ket": (p.get("draft") or {}).get("no_ref") or (p.get("draft") or {}).get("hm_akhir") or ""}
                   for p in pend if ((p.get("draft") or {}).get("pengurus") or "").strip().lower() == key or (p.get("draft") or {}).get("unit_id") in unit_ids]
        no_hm = [r["unit"] for r in rows if not r["lapor"]]

        contact = next((c for c in contacts if canon(c.get("pengurus") or c.get("nama")).lower() == key), None)
        total_jam = round(sum(r["jam"] for r in rows), 2)
        total_tf = sum(t["nominal"] for t in transfers)

        # ---- teks lengkap (dalam jendela 24 jam) ----
        L = [f"*Ringkasan Harian TRIRARA TUNGGAL PUTRA*", f"Pengurus: {nama}", f"Tanggal: {tgl_id(tanggal)}", "", "*Jam Kerja Unit (HM)*"]
        for r_ in rows:
            L.append(f"- {r_['unit']}: {num(r_['hm_awal'])} -> {num(r_['hm_akhir'])} = {num(r_['jam'])} jam" if r_["lapor"] else f"- {r_['unit']}: belum ada laporan HM")
        if not rows:
            L.append("- Tidak ada unit")
        L.append(f"Total: {num(total_jam)} jam")
        L += ["", "*Transfer Diterima Hari Ini*"]
        L += [f"- {idr(t['nominal'])} · Ref {t['no_ref']} ({t['no_bukti']})" for t in transfers] or ["- Belum ada"]
        L.append(f"Total penerimaan: {idr(total_tf)}")
        L += ["", "*Piutang Berjalan Bulan Ini*", f"Saldo awal bulan: {idr(saldo_awal)}", f"Tagihan bulan ini: {idr(tagihan_bulan)}",
              f"Pembayaran bulan ini: {idr(bayar_bulan)}", f"Piutang berjalan: *{idr(piutang)}*"]
        if jam_tanpa_tarif:
            L.append(f"(Catatan: {num(jam_tanpa_tarif)} jam belum memiliki tarif sewa)")
        L += ["", "*Menunggu Verifikasi*"]
        L += [f"- {'Transfer' if p['jenis'] == 'transfer' else 'HM' if p['jenis'] == 'hour_meter' else p['jenis']} · {p['caption']}{(' · ' + str(p['ket'])) if p['ket'] else ''}" for p in pending] or ["- Tidak ada"]
        if no_hm:
            L.append(f"- Unit belum lapor HM: {', '.join(no_hm)}")

        params = [
            _one_line(nama, 60), _one_line(tgl_id(tanggal), 30),
            _one_line("; ".join(f"{r_['unit']} {num(r_['hm_awal'])}-{num(r_['hm_akhir'])} = {num(r_['jam'])} jam" if r_["lapor"] else f"{r_['unit']} belum lapor" for r_ in rows) + f" | Total {num(total_jam)} jam"),
            _one_line(("; ".join(f"{idr(t['nominal'])} Ref {t['no_ref']}" for t in transfers) or "Belum ada") + f" | Total {idr(total_tf)}"),
            _one_line(f"{idr(piutang)} (tagihan {idr(tagihan_bulan)}, dibayar {idr(bayar_bulan)}, saldo awal {idr(saldo_awal)})"),
            _one_line((f"{len(pending)} item" + (": " + "; ".join(f"{p['jenis']} {p['caption']}" for p in pending[:5]) if pending else "")) + (f" | Belum lapor HM: {', '.join(no_hm)}" if no_hm else "")),
        ]
        out.append({
            "pengurus": nama, "phone": (contact or {}).get("phone", ""), "contact_name": (contact or {}).get("nama", ""),
            "tanggal": tanggal, "units": rows, "total_jam": total_jam, "transfers": transfers, "total_transfer": total_tf,
            "piutang": {"saldo_awal": saldo_awal, "tagihan_bulan": tagihan_bulan, "bayar_bulan": bayar_bulan, "piutang": piutang, "jam_tanpa_tarif": jam_tanpa_tarif},
            "pending": pending, "unit_belum_lapor": no_hm, "text": "\n".join(L), "params": params,
        })
    return out


def build_summary_router(db, require_admin: Callable, audit_fn: Optional[Callable] = None) -> APIRouter:
    r = APIRouter()
    outbox = Outbox(db)

    async def get_cfg():
        doc = await db.app_settings.find_one({"key": "wa_summary"}, {"_id": 0}) or {}
        return {**SUMMARY_DEFAULT, **{k: v for k, v in doc.items() if k in SUMMARY_DEFAULT}}

    async def audit(action, actor, detail, data=None):
        await db.wa_audit.insert_one({"id": str(uuid.uuid4()), "at": _now(), "action": action, "actor": actor, "inbox_id": "",
                                      "detail": detail[:500], "data": data or {}})

    async def run(tanggal: str, trigger: str, actor: str, force: bool = False, only: Optional[str] = None) -> dict:
        cfg = await get_cfg()
        run_id = str(uuid.uuid4())
        sums = await build_summaries(db, tanggal)
        results = []
        for s_ in sums:
            if only and s_["pengurus"].lower() != only.lower():
                continue
            base = {"id": str(uuid.uuid4()), "run_id": run_id, "trigger": trigger, "tanggal": tanggal, "pengurus": s_["pengurus"],
                    "phone": s_["phone"], "text": s_["text"], "params": s_["params"], "created_at": _now(), "actor": actor,
                    "total_jam": s_["total_jam"], "total_transfer": s_["total_transfer"], "piutang": s_["piutang"]["piutang"],
                    "pending_count": len(s_["pending"])}
            status, mode, err = "skipped", "", ""
            if not s_["phone"]:
                err = "Pengurus belum terdaftar di Kontak WA (tipe Pengurus)"
            elif not cfg["enabled"] and trigger == "cron":
                err = "Ringkasan harian dinonaktifkan"
            elif not force and await db.wa_summaries.find_one({"tanggal": tanggal, "phone": s_["phone"], "status": "sent"}):
                err = "Sudah terkirim untuk tanggal ini"
            elif not wa_configured():
                key = f"summary:{tanggal}:{norm_phone(s_['phone'])}" + (f":{run_id}" if force else "")
                ob = await outbox.send(s_["phone"], {"type": "text", "text": {"preview_url": False, "body": s_["text"][:4096]}},
                                       "daily_summary", key, actor=actor, ref={"summary_id": base["id"]},
                                       label=f"Ringkasan harian {s_['pengurus']} {tanggal}")
                base["outbox_id"] = ob.get("id", "")
                if ob.get("deduped"):
                    status, mode, err = "skipped", "simulasi", "Sudah disimulasikan untuk tanggal ini (gunakan Kirim Ulang Paksa)"
                else:
                    status, mode, err = "preview", "simulasi", "WhatsApp belum terhubung — disimpan sebagai simulasi"
            else:
                last = await db.wa_last_inbound.find_one({"phone": norm_phone(s_["phone"])}, {"_id": 0})
                in_window = bool(last) and datetime.fromisoformat(last["at"]) > datetime.now(timezone.utc) - timedelta(hours=24)
                key = f"summary:{tanggal}:{norm_phone(s_['phone'])}" + (f":{run_id}" if force else "")
                label = f"Ringkasan harian {s_['pengurus']} {tanggal}"
                ob = None
                if in_window:
                    mode = "text"
                    ob = await outbox.send(s_["phone"], {"type": "text", "text": {"preview_url": False, "body": s_["text"][:4096]}},
                                           "daily_summary", key, actor=actor, ref={"summary_id": base["id"]}, label=label)
                elif cfg["template_name"]:
                    mode = "template"
                    ob = await outbox.send(s_["phone"], {"type": "template", "template": {
                        "name": cfg["template_name"], "language": {"code": cfg["template_lang"] or "id"},
                        "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in s_["params"]]}]}},
                        "daily_summary", key, actor=actor, ref={"summary_id": base["id"]}, label=label)
                else:
                    err, mode = "Di luar jendela 24 jam & template Utility belum diatur", "none"
                if ob is None:
                    status = "skipped"
                elif ob.get("deduped"):
                    status, err = "skipped", f"Tidak dikirim ulang (pesan sebelumnya: {ob.get('status')})"
                elif ob.get("status") in ("sent", "delivered", "read"):
                    status, err = "sent", ""
                else:
                    status, err = "failed", ob.get("error", "") + (" · dijadwalkan ulang otomatis" if ob.get("retriable") else "")
                base["outbox_id"] = (ob or {}).get("id", "")
            doc = {**base, "status": status, "mode": mode, "error": err}
            await db.wa_summaries.insert_one(doc)
            doc.pop("_id", None)
            results.append(doc)
        counts = {k: sum(1 for x in results if x["status"] == k) for k in ("sent", "preview", "skipped", "failed")}
        await db.cron_runs.update_one({"run_id": run_id}, {"$set": {"run_id": run_id, "job": "daily-summary", "tanggal": tanggal, "trigger": trigger,
                                                                    "counts": counts, "finished_at": _now()}}, upsert=True)
        await audit("summary_run", actor, f"Ringkasan {tanggal} ({trigger}): terkirim {counts['sent']}, simulasi {counts['preview']}, "
                                          f"dilewati {counts['skipped']}, gagal {counts['failed']}", counts)
        log.info("daily summary %s trigger=%s counts=%s", tanggal, trigger, counts)
        return {"run_id": run_id, "tanggal": tanggal, "counts": counts, "results": results}

    # ---------- Cron (platform) ----------
    @r.post("/api/cron/daily-summary")
    async def cron_daily(request: Request, background: BackgroundTasks):
        # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
        secret = _env("WEBHOOK_CRON_SECRET")
        auth = request.headers.get("authorization", "")
        token = auth[7:] if auth.lower().startswith("bearer ") else ""
        if not secret or not token or not hmac.compare_digest(token, secret):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        try:
            env = await request.json() if (await request.body()) else {}
        except ValueError:
            return JSONResponse({"detail": "Invalid body"}, status_code=400)
        if env is not None and not isinstance(env, dict):
            return JSONResponse({"detail": "Invalid body"}, status_code=400)
        run_key = request.headers.get("x-webhook-id") or (env or {}).get("run_id") or f"manual-{uuid.uuid4()}"
        res = await db.cron_runs.update_one({"run_id": f"cron:{run_key}"},
                                            {"$setOnInsert": {"run_id": f"cron:{run_key}", "job": "daily-summary", "received_at": _now()}}, upsert=True)
        if res.upserted_id is None:
            return {"status": "duplicate"}
        background.add_task(run, today_wita(), "cron", "Penjadwal 20:00 WITA")
        return {"status": "accepted"}

    # ---------- Admin ----------
    class SumCfg(BaseModel):
        enabled: bool = True
        template_name: str = ""
        template_lang: str = "id"

    class RunIn(BaseModel):
        tanggal: Optional[str] = None
        force: bool = False
        pengurus: Optional[str] = None

    @r.get("/api/wa/summary/settings")
    async def sum_settings(admin=Depends(require_admin)):
        return {**(await get_cfg()), "template_text": TEMPLATE_TEXT, "schedule": "Setiap hari 20:00 WITA (Asia/Makassar)",
                "whatsapp_configured": wa_configured(), "cron_secret_set": bool(_env("WEBHOOK_CRON_SECRET")), "today": today_wita()}

    @r.put("/api/wa/summary/settings")
    async def put_sum_settings(body: SumCfg, admin=Depends(require_admin)):
        name = body.template_name.strip()
        if name and not all(ch.islower() or ch.isdigit() or ch == "_" for ch in name):
            raise HTTPException(400, "Nama template hanya huruf kecil, angka, dan garis bawah (contoh: ringkasan_harian)")
        await db.app_settings.update_one({"key": "wa_summary"}, {"$set": {"key": "wa_summary", **body.model_dump(), "template_name": name,
                                                                         "updated_by": admin.name, "updated_at": _now()}}, upsert=True)
        await audit("settings_changed", admin.name, "Pengaturan ringkasan harian diubah", body.model_dump())
        return await sum_settings(admin)

    @r.get("/api/wa/summary/preview")
    async def preview(tanggal: Optional[str] = None, admin=Depends(require_admin)):
        t = tanggal or today_wita()
        try:
            datetime.strptime(t, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "Format tanggal YYYY-MM-DD")
        return {"tanggal": t, "items": await build_summaries(db, t)}

    @r.post("/api/wa/summary/run")
    async def run_now(body: RunIn, admin=Depends(require_admin)):
        t = body.tanggal or today_wita()
        try:
            datetime.strptime(t, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "Format tanggal YYYY-MM-DD")
        return await run(t, "manual", admin.name, force=body.force, only=body.pengurus)

    @r.get("/api/wa/summary/history")
    async def history(limit: int = 200, admin=Depends(require_admin)):
        return await db.wa_summaries.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(max(limit, 1), 1000))

    return r
