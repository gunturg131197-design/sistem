"""Pengingat Piutang & Laporan Mingguan Pemilik (WhatsApp, mode simulasi bila Meta belum dikonfigurasi).

Piutang (data TERVALIDASI saja — konsisten dengan Ringkasan Harian):
  tagihan  = jam kerja Ops Report x tarif sewa/jam (tarif unit, fallback tarif pengurus)
  bayar    = Kas Masuk milik pengurus (bukti WA baru dihitung setelah disetujui)
  piutang  = total tagihan s/d tanggal - total bayar s/d tanggal
  umur     = FIFO: pembayaran melunasi tagihan TERTUA dulu; umur = hari sejak tagihan tertua yang belum lunas

Pengingat (anti-spam): hanya bila piutang >= batas nominal DAN umur >= batas hari, tidak ada bukti transfer
yang sedang menunggu verifikasi (opsional), dan tidak ada pengingat dalam masa jeda (cooldown). Maks 1x per hari.
Laporan mingguan: Senin 08:00 WITA untuk minggu sebelumnya (Senin–Minggu), maks 1x per minggu per penerima.
"""
import hmac
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from wa_outbox import Outbox, _env, norm_phone, wa_configured

log = logging.getLogger("wa_reports")
TZ = ZoneInfo("Asia/Makassar")
PENDING = ["pending", "duplicate", "error", "processing"]
OWNER_DEFAULT = "6282343070023"
REMINDER_DEFAULT = {"enabled": False, "send_hour": 9, "days": [1, 2, 3, 4, 5, 6], "min_nominal": 1_000_000.0, "min_age_days": 14,
                    "cooldown_days": 3, "skip_if_pending_transfer": True, "cc_owner": False, "exclude": [],
                    "template_name": "", "template_lang": "id"}
WEEKLY_DEFAULT = {"enabled": True, "recipients": [{"nama": "Pemilik", "phone": OWNER_DEFAULT}], "template_name": "", "template_lang": "id"}
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
REMINDER_TEMPLATE = ("Pengingat Piutang TRIRARA TUNGGAL PUTRA\nYth. {{1}},\nPer {{2}}, sisa tagihan sewa alat yang belum dibayar: {{3}}.\n"
                     "Tagihan tertua belum lunas: {{4}}.\nPembayaran terakhir: {{5}}.\n"
                     "Mohon kirim foto bukti transfer ke nomor ini dengan keterangan kode unit. Abaikan pesan ini bila sudah membayar.")
WEEKLY_TEMPLATE = ("Laporan Mingguan TRIRARA TUNGGAL PUTRA\nPeriode: {{1}}\nTotal jam kerja (HM): {{2}}\nTotal pemasukan: {{3}}\n"
                   "Pembayaran diterima: {{4}}\nPiutang berjalan: {{5}}\nMenunggu verifikasi: {{6}}\nDetail lengkap tersedia di aplikasi.")


def _now():
    return datetime.now(timezone.utc).isoformat()


def now_wita() -> datetime:
    return datetime.now(TZ)


def idr(n) -> str:
    v = float(n or 0)
    return ("-" if v < 0 else "") + "Rp" + f"{abs(v):,.0f}".replace(",", ".")


def num(n) -> str:
    return f"{float(n or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip("0").rstrip(",")


def tgl_id(s: str) -> str:
    bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    try:
        d = datetime.strptime(s[:10], "%Y-%m-%d")
        return f"{d.day} {bulan[d.month - 1]} {d.year}"
    except Exception:
        return s


def one_line(s: str, limit: int = 900) -> str:
    s = " ".join(str(s or "-").replace("\t", " ").splitlines())
    while "     " in s:
        s = s.replace("     ", "    ")
    return s[:limit] or "-"


def _parse_date(s: str, field: str = "tanggal") -> date:
    try:
        return datetime.strptime((s or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, f"Format {field} YYYY-MM-DD")


async def _ctx(db):
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
        return float(u.get("tarif_sewa_per_jam") or 0) or float((reg.get((nama or "").lower()) or {}).get("tarif_sewa_per_jam") or 0)

    def op_owner(o):
        return canon(o.get("pengurus") or (units.get(o.get("unit_id")) or {}).get("pengurus"))

    def km_owner(k):
        n = (k.get("pengurus") or "").strip() or ((units.get(k.get("unit_id")) or {}).get("pengurus") or "").strip()
        return canon(n)

    def phone_of(nama):
        c = next((c for c in contacts if canon(c.get("pengurus") or c.get("nama")).lower() == (nama or "").lower()), None)
        return (c or {}).get("phone", ""), (c or {}).get("nama", "")

    names = {canon(c.get("pengurus") or c.get("nama")) for c in contacts} | {r["nama"] for r in registry}
    names |= {canon(u.get("pengurus")) for u in units.values() if u.get("pengurus")}
    names.discard("")
    return {"units": units, "canon": canon, "tarif": tarif, "op_owner": op_owner, "km_owner": km_owner, "phone_of": phone_of, "names": names}


def unit_label(u: dict) -> str:
    return (u.get("kode_wa") or "").split(",")[0].strip() or f"{u.get('unit_name', '')} {u.get('nomor_lambung', '')}".strip()


async def piutang_aging(db, as_of: str) -> list:
    """Piutang per pengurus per tanggal `as_of` (inklusif) dengan umur FIFO."""
    cx = await _ctx(db)
    asof = _parse_date(as_of, "as_of")
    ops = await db.operations.find({"tanggal": {"$lte": as_of}}, {"_id": 0}).to_list(200000)
    kms = await db.kas_masuk.find({"tanggal": {"$lte": as_of}}, {"_id": 0}).to_list(200000)
    pend = await db.wa_inbox.find({"status": {"$in": PENDING}, "jenis": "transfer"}, {"_id": 0, "draft": 1, "status": 1}).to_list(5000)
    out = []
    for nama in sorted(cx["names"], key=str.lower):
        key = nama.lower()
        my_ops = sorted([o for o in ops if cx["op_owner"](o).lower() == key], key=lambda o: (o.get("tanggal") or "", o.get("hour_meter_awal") or 0))
        my_km = sorted([k for k in kms if cx["km_owner"](k).lower() == key], key=lambda k: k.get("tanggal") or "")
        bills = []
        jam_tanpa_tarif = 0.0
        for o in my_ops:
            t = cx["tarif"](o, nama)
            jam = float(o.get("total_jam") or 0)
            if t <= 0 and jam > 0:
                jam_tanpa_tarif += jam
            amt = jam * t
            if amt > 0:
                u = cx["units"].get(o.get("unit_id")) or {}
                bills.append({"tanggal": o.get("tanggal"), "unit": unit_label(u), "jam": jam, "nominal": amt, "sisa": amt})
        total_tagihan = sum(b["nominal"] for b in bills)
        total_bayar = sum(float(k.get("debit") or 0) for k in my_km)
        rest = total_bayar
        for b in bills:  # FIFO
            pay = min(rest, b["sisa"])
            b["sisa"] = round(b["sisa"] - pay, 2)
            rest -= pay
        unpaid = [b for b in bills if b["sisa"] > 0.5]
        piutang = total_tagihan - total_bayar
        buckets = {"0_30": 0.0, "31_60": 0.0, "61_90": 0.0, "90_plus": 0.0}
        for b in unpaid:
            age = (asof - _parse_date(b["tanggal"])).days
            b["umur_hari"] = age
            k = "0_30" if age <= 30 else "31_60" if age <= 60 else "61_90" if age <= 90 else "90_plus"
            buckets[k] += b["sisa"]
        oldest = unpaid[0]["tanggal"] if unpaid else None
        last = my_km[-1] if my_km else None
        phone, cname = cx["phone_of"](nama)
        pending_tf = sum(1 for p in pend if ((p.get("draft") or {}).get("pengurus") or "").strip().lower() == key
                         or ((cx["units"].get((p.get("draft") or {}).get("unit_id")) or {}).get("pengurus") or "").strip().lower() == key)
        out.append({"pengurus": nama, "phone": phone, "contact_name": cname, "as_of": as_of, "total_tagihan": round(total_tagihan, 2),
                    "total_bayar": round(total_bayar, 2), "piutang": round(piutang, 2), "oldest_unpaid": oldest,
                    "umur_hari": (asof - _parse_date(oldest)).days if oldest else 0, "buckets": {k: round(v, 2) for k, v in buckets.items()},
                    "unpaid": unpaid[-50:], "unpaid_count": len(unpaid), "last_payment": {"tanggal": last.get("tanggal"), "nominal": float(last.get("debit") or 0),
                                                                                          "no_bukti": last.get("no_bukti", "")} if last else None,
                    "pending_transfer": pending_tf, "jam_tanpa_tarif": round(jam_tanpa_tarif, 2)})
    return out


def reminder_text(a: dict, tanggal: str) -> tuple[str, list]:
    b = a["buckets"]
    lp = a.get("last_payment")
    lp_s = f"{tgl_id(lp['tanggal'])} {idr(lp['nominal'])}" if lp else "belum ada"
    old_s = f"{tgl_id(a['oldest_unpaid'])} ({a['umur_hari']} hari)" if a.get("oldest_unpaid") else "-"
    L = ["*Pengingat Piutang — TRIRARA TUNGGAL PUTRA*", f"Yth. {a['pengurus']},", "",
         f"Per {tgl_id(tanggal)} WITA, sisa tagihan sewa alat yang belum dibayar: *{idr(a['piutang'])}*",
         f"Tagihan tertua belum lunas: {old_s}", "",
         "*Rincian umur piutang*", f"- 0–30 hari: {idr(b['0_30'])}", f"- 31–60 hari: {idr(b['31_60'])}",
         f"- 61–90 hari: {idr(b['61_90'])}", f"- > 90 hari: {idr(b['90_plus'])}", "",
         f"Pembayaran terakhir: {lp_s}", "",
         "Mohon kirim foto bukti transfer ke nomor ini dengan keterangan kode unit (contoh: Sdlg 10).",
         "Abaikan pesan ini bila sudah membayar. Terima kasih."]
    params = [one_line(a["pengurus"], 60), one_line(tgl_id(tanggal), 30), one_line(idr(a["piutang"])), one_line(old_s), one_line(lp_s)]
    return "\n".join(L), params


def week_bounds(week_start: Optional[str] = None) -> tuple[str, str]:
    if week_start:
        d = _parse_date(week_start, "week_start")
    else:
        d = now_wita().date() - timedelta(days=7)  # minggu lalu
    mon = d - timedelta(days=d.weekday())
    return mon.isoformat(), (mon + timedelta(days=6)).isoformat()


async def build_weekly(db, week_start: Optional[str] = None) -> dict:
    start, end = week_bounds(week_start)
    cx = await _ctx(db)
    ops = await db.operations.find({"tanggal": {"$gte": start, "$lte": end}}, {"_id": 0}).to_list(100000)
    kms = await db.kas_masuk.find({"tanggal": {"$gte": start, "$lte": end}}, {"_id": 0}).to_list(100000)
    pend = await db.wa_inbox.find({"status": {"$in": PENDING}}, {"_id": 0, "media_id": 0, "ai": 0}).sort("received_at", 1).to_list(2000)
    per_unit: dict[str, dict] = {}
    for o in ops:
        u = cx["units"].get(o.get("unit_id")) or {}
        k = o.get("unit_id") or "?"
        r = per_unit.setdefault(k, {"unit": unit_label(u) or o.get("unit_label") or "?", "pengurus": cx["op_owner"](o), "hm_awal": None, "hm_akhir": None, "jam": 0.0, "hari": set()})
        a, z = float(o.get("hour_meter_awal") or 0), float(o.get("hour_meter_akhir") or 0)
        r["hm_awal"] = a if r["hm_awal"] is None else min(r["hm_awal"], a)
        r["hm_akhir"] = z if r["hm_akhir"] is None else max(r["hm_akhir"], z)
        r["jam"] += float(o.get("total_jam") or 0)
        r["hari"].add(o.get("tanggal"))
    units_rows = sorted([{**r, "jam": round(r["jam"], 2), "hari": len(r["hari"])} for r in per_unit.values()], key=lambda x: x["unit"].lower())
    total_jam = round(sum(r["jam"] for r in units_rows), 2)
    total_pemasukan = sum(float(k.get("debit") or 0) for k in kms)
    pay_by: dict[str, dict] = {}
    for k in kms:
        n = cx["km_owner"](k)
        if not n:
            continue
        p = pay_by.setdefault(n, {"pengurus": n, "nominal": 0.0, "jumlah": 0})
        p["nominal"] += float(k.get("debit") or 0)
        p["jumlah"] += 1
    payments = sorted(pay_by.values(), key=lambda x: -x["nominal"])
    total_bayar = sum(p["nominal"] for p in payments)
    aging = await piutang_aging(db, end)
    piutang_rows = [{"pengurus": a["pengurus"], "piutang": a["piutang"], "umur_hari": a["umur_hari"], "oldest_unpaid": a["oldest_unpaid"]}
                    for a in aging if abs(a["piutang"]) > 0.5]
    total_piutang = sum(max(0.0, a["piutang"]) for a in aging)
    total_lebih = sum(-a["piutang"] for a in aging if a["piutang"] < -0.5)
    pending = [{"id": p["id"], "jenis": p.get("jenis") or "-", "status": p["status"], "caption": p.get("caption") or "-",
                "hm_flag": bool(p.get("hm_flag")), "received_at": p.get("received_at"),
                "ket": (p.get("draft") or {}).get("no_ref") or (p.get("draft") or {}).get("hm_akhir") or (p.get("draft") or {}).get("debit") or ""} for p in pend]
    jl = {"transfer": "Transfer", "hour_meter": "HM"}
    periode = f"{tgl_id(start)} – {tgl_id(end)}"
    L = ["*Laporan Mingguan TRIRARA TUNGGAL PUTRA*", f"Periode: {periode} (WITA)", "", "*Jam Kerja per Unit (HM)*"]
    L += [f"- {r['unit']}: {num(r['hm_awal'])} -> {num(r['hm_akhir'])} = {num(r['jam'])} jam ({r['hari']} hari)" for r in units_rows] or ["- Tidak ada laporan HM"]
    L += [f"Total: {num(total_jam)} jam", "", "*Pemasukan*", f"Total pemasukan (Kas Masuk): {idr(total_pemasukan)} ({len(kms)} transaksi)",
          f"Pembayaran sewa diterima: {idr(total_bayar)}"]
    L += [f"- {p['pengurus']}: {idr(p['nominal'])} ({p['jumlah']}x)" for p in payments]
    L += ["", f"*Piutang Berjalan per {tgl_id(end)}*"]
    L += [(f"- {p['pengurus']}: {idr(p['piutang'])}" + (f" · tertua {p['umur_hari']} hari" if p["oldest_unpaid"] else "")) if p["piutang"] > 0
          else f"- {p['pengurus']}: lebih bayar {idr(-p['piutang'])}" for p in piutang_rows] or ["- Tidak ada piutang"]
    L += [f"Total piutang: *{idr(total_piutang)}*"] + ([f"Total lebih bayar (deposit): {idr(total_lebih)}"] if total_lebih else []) + ["", f"*Menunggu Verifikasi ({len(pending)})*"]
    L += [f"- {jl.get(p['jenis'], p['jenis'])} · {p['caption']}{(' · ' + str(p['ket'])) if p['ket'] else ''}{' · HM janggal' if p['hm_flag'] else ''}" for p in pending[:15]] or ["- Tidak ada"]
    if len(pending) > 15:
        L.append(f"- … dan {len(pending) - 15} lainnya")
    params = [one_line(periode, 60), one_line("; ".join(f"{r['unit']} {num(r['jam'])} jam" for r in units_rows) + f" | Total {num(total_jam)} jam"),
              one_line(f"{idr(total_pemasukan)} ({len(kms)} transaksi)"),
              one_line(("; ".join(f"{p['pengurus']} {idr(p['nominal'])}" for p in payments) or "Belum ada") + f" | Total {idr(total_bayar)}"),
              one_line(("; ".join(f"{p['pengurus']} {idr(p['piutang'])}" for p in piutang_rows if p["piutang"] > 0) or "Tidak ada") + f" | Total {idr(total_piutang)}"),
              one_line(f"{len(pending)} item" + (": " + "; ".join(f"{jl.get(p['jenis'], p['jenis'])} {p['caption']}" for p in pending[:5]) if pending else ""))]
    return {"week_start": start, "week_end": end, "periode": periode, "units": units_rows, "total_jam": total_jam,
            "total_pemasukan": total_pemasukan, "jumlah_transaksi": len(kms), "payments": payments, "total_bayar": total_bayar,
            "pemasukan_lain": round(total_pemasukan - total_bayar, 2), "piutang": piutang_rows, "total_piutang": round(total_piutang, 2), "total_lebih_bayar": round(total_lebih, 2),
            "pending": pending, "text": "\n".join(L), "params": params}


def _cron_auth(request: Request) -> bool:
    secret = _env("WEBHOOK_CRON_SECRET")
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else ""
    return bool(secret and token and hmac.compare_digest(token, secret))


async def _cron_envelope(request: Request):
    try:
        env = await request.json() if (await request.body()) else {}
    except ValueError:
        return None, JSONResponse({"detail": "Invalid body"}, status_code=400)
    if env is not None and not isinstance(env, dict):
        return None, JSONResponse({"detail": "Invalid body"}, status_code=400)
    return (env or {}), None


def build_reports_router(db, require_admin: Callable) -> APIRouter:
    r = APIRouter()
    outbox = Outbox(db)

    async def audit(action, actor, detail, data=None):
        await db.wa_audit.insert_one({"id": str(uuid.uuid4()), "at": _now(), "action": action, "actor": actor, "inbox_id": "",
                                      "detail": detail[:500], "data": data or {}})

    async def _cfg(key, default):
        doc = await db.app_settings.find_one({"key": key}, {"_id": 0}) or {}
        return {**default, **{k: v for k, v in doc.items() if k in default}}

    def _msg(text: str, params: list, cfg: dict, phone: str, in_window: bool):
        if in_window or not wa_configured():
            return {"type": "text", "text": {"preview_url": False, "body": text[:4096]}}, "text" if wa_configured() else "simulasi"
        if cfg.get("template_name"):
            return {"type": "template", "template": {"name": cfg["template_name"], "language": {"code": cfg.get("template_lang") or "id"},
                                                     "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]}}, "template"
        return None, "none"

    async def _in_window(phone: str) -> bool:
        last = await db.wa_last_inbound.find_one({"phone": norm_phone(phone)}, {"_id": 0})
        return bool(last) and datetime.fromisoformat(last["at"]) > datetime.now(timezone.utc) - timedelta(hours=24)

    def _status(ob: Optional[dict]) -> tuple[str, str]:
        if ob is None:
            return "skipped", "Di luar jendela 24 jam & template Utility belum diatur"
        if ob.get("deduped"):
            return "skipped", f"Tidak dikirim ulang (sudah ada: {ob.get('status')})"
        if ob.get("status") == "simulated":
            return "simulated", "WhatsApp belum terhubung — disimpan sebagai simulasi"
        if ob.get("status") in ("sent", "delivered", "read"):
            return "sent", ""
        return "failed", (ob.get("error") or "") + (" · dijadwalkan ulang otomatis" if ob.get("retriable") else "")

    # =================== Pengingat Piutang ===================
    class ReminderCfg(BaseModel):
        enabled: bool = False
        send_hour: int = 9
        days: list[int] = [1, 2, 3, 4, 5, 6]
        min_nominal: float = 1_000_000
        min_age_days: int = 14
        cooldown_days: int = 3
        skip_if_pending_transfer: bool = True
        cc_owner: bool = False
        exclude: list[str] = []
        template_name: str = ""
        template_lang: str = "id"

    async def reminder_decisions(tanggal: str, cfg: dict) -> list:
        aging = await piutang_aging(db, tanggal)
        excl = {x.strip().lower() for x in cfg.get("exclude") or [] if x.strip()}
        since = (datetime.now(timezone.utc) - timedelta(days=int(cfg["cooldown_days"]))).isoformat()
        out = []
        for a in aging:
            reason = ""
            last = await db.wa_reminders.find({"pengurus": a["pengurus"], "status": {"$in": ["sent", "simulated"]}}, {"_id": 0}).sort("created_at", -1).to_list(1)
            last = last[0] if last else None
            if a["pengurus"].lower() in excl:
                reason = "Dikecualikan di pengaturan"
            elif a["piutang"] <= 0.5:
                reason = "Lunas / tidak ada piutang"
            elif a["piutang"] < float(cfg["min_nominal"]):
                reason = f"Piutang di bawah batas {idr(cfg['min_nominal'])}"
            elif a["umur_hari"] < int(cfg["min_age_days"]):
                reason = f"Umur piutang {a['umur_hari']} hari < batas {cfg['min_age_days']} hari"
            elif cfg.get("skip_if_pending_transfer") and a["pending_transfer"]:
                reason = f"Ada {a['pending_transfer']} bukti transfer menunggu verifikasi"
            elif not a["phone"]:
                reason = "Pengurus belum terdaftar di Kontak WA (tipe Pengurus)"
            elif last and last["created_at"] > since:
                reason = f"Masa jeda {cfg['cooldown_days']} hari (terakhir {last['created_at'][:10]})"
            text, params = reminder_text(a, tanggal)
            out.append({**{k: a[k] for k in ("pengurus", "phone", "piutang", "umur_hari", "oldest_unpaid", "buckets", "last_payment", "pending_transfer", "unpaid_count")},
                        "eligible": not reason, "reason": reason, "text": text, "params": params,
                        "last_reminder_at": (last or {}).get("created_at")})
        return out

    async def reminder_run(trigger: str, actor: str, force: bool = False, only: Optional[str] = None) -> dict:
        cfg = await _cfg("wa_reminder", REMINDER_DEFAULT)
        tanggal = now_wita().date().isoformat()
        run_id = str(uuid.uuid4())
        wcfg = await _cfg("wa_weekly", WEEKLY_DEFAULT)
        owner = (wcfg.get("recipients") or [{}])[0].get("phone") or OWNER_DEFAULT
        results = []
        for d in await reminder_decisions(tanggal, cfg):
            if only and d["pengurus"].lower() != only.lower():
                continue
            base = {"id": str(uuid.uuid4()), "run_id": run_id, "trigger": trigger, "tanggal": tanggal, "pengurus": d["pengurus"], "phone": d["phone"],
                    "piutang": d["piutang"], "umur_hari": d["umur_hari"], "text": d["text"], "created_at": _now(), "actor": actor}
            hard_skip = d["reason"] and (d["piutang"] <= 0.5 or not d["phone"] or "verifikasi" in d["reason"])
            if (not d["eligible"] and not force) or (force and hard_skip):
                doc = {**base, "status": "skipped", "error": d["reason"]}
            else:
                key = f"reminder:{tanggal}:{norm_phone(d['phone'])}" + (f":{run_id}" if force else "")
                msg, mode = _msg(d["text"], d["params"], cfg, d["phone"], await _in_window(d["phone"]))
                ob = await outbox.send(d["phone"], msg, "reminder", key, actor=actor, ref={"reminder_id": base["id"]},
                                       label=f"Pengingat piutang {d['pengurus']}") if msg else None
                st, err = _status(ob)
                doc = {**base, "status": st, "error": err, "mode": mode, "outbox_id": (ob or {}).get("id", "")}
                if cfg.get("cc_owner") and st in ("sent", "simulated") and owner:
                    cc_text = f"[Tembusan pemilik]\n{d['text']}"
                    cmsg, _m = _msg(cc_text, d["params"], cfg, owner, await _in_window(owner))
                    if cmsg:
                        await outbox.send(owner, cmsg, "reminder", f"{key}:cc", actor=actor, ref={"reminder_id": base["id"]},
                                          label=f"Tembusan pengingat {d['pengurus']}")
            await db.wa_reminders.insert_one(doc)
            doc.pop("_id", None)
            results.append(doc)
        counts = {k: sum(1 for x in results if x["status"] == k) for k in ("sent", "simulated", "skipped", "failed")}
        await audit("reminder_run", actor, f"Pengingat piutang {tanggal} ({trigger}): terkirim {counts['sent']}, simulasi {counts['simulated']}, "
                                           f"dilewati {counts['skipped']}, gagal {counts['failed']}", counts)
        return {"run_id": run_id, "tanggal": tanggal, "counts": counts, "results": results}

    @r.get("/api/wa/piutang/aging")
    async def aging(as_of: Optional[str] = None, admin=Depends(require_admin)):
        t = as_of or now_wita().date().isoformat()
        _parse_date(t, "as_of")
        rows = await piutang_aging(db, t)
        return {"as_of": t, "items": rows, "total": round(sum(a["piutang"] for a in rows), 2)}

    @r.get("/api/wa/reminder/settings")
    async def get_reminder(admin=Depends(require_admin)):
        return {**(await _cfg("wa_reminder", REMINDER_DEFAULT)), "template_text": REMINDER_TEMPLATE, "whatsapp_configured": wa_configured(),
                "cron_secret_set": bool(_env("WEBHOOK_CRON_SECRET")), "today": now_wita().date().isoformat()}

    @r.put("/api/wa/reminder/settings")
    async def put_reminder(body: ReminderCfg, admin=Depends(require_admin)):
        if not 0 <= body.send_hour <= 23:
            raise HTTPException(400, "Jam kirim 0–23")
        if not body.days or any(d not in range(1, 8) for d in body.days):
            raise HTTPException(400, "Pilih minimal 1 hari kirim (1=Senin … 7=Minggu)")
        if body.min_nominal < 0 or body.min_age_days < 0:
            raise HTTPException(400, "Batas nominal / umur tidak boleh negatif")
        if not 1 <= body.cooldown_days <= 60:
            raise HTTPException(400, "Masa jeda 1–60 hari")
        name = body.template_name.strip()
        if name and not all(ch.islower() or ch.isdigit() or ch == "_" for ch in name):
            raise HTTPException(400, "Nama template hanya huruf kecil, angka, dan garis bawah")
        before = await _cfg("wa_reminder", REMINDER_DEFAULT)
        new = {**body.model_dump(), "days": sorted(set(body.days)), "template_name": name, "exclude": [x.strip() for x in body.exclude if x.strip()]}
        await db.app_settings.update_one({"key": "wa_reminder"}, {"$set": {"key": "wa_reminder", **new, "updated_by": admin.name, "updated_at": _now()}}, upsert=True)
        await audit("reminder_settings", admin.name, "Pengaturan pengingat piutang diubah", {"sebelum": before, "sesudah": new})
        return await get_reminder(admin)

    @r.get("/api/wa/reminder/preview")
    async def preview_reminder(admin=Depends(require_admin)):
        cfg = await _cfg("wa_reminder", REMINDER_DEFAULT)
        t = now_wita().date().isoformat()
        return {"tanggal": t, "items": await reminder_decisions(t, cfg)}

    class RunIn(BaseModel):
        force: bool = False
        pengurus: Optional[str] = None
        week_start: Optional[str] = None

    @r.post("/api/wa/reminder/run")
    async def run_reminder(body: RunIn, admin=Depends(require_admin)):
        return await reminder_run("manual", admin.name, force=body.force, only=body.pengurus)

    @r.get("/api/wa/reminder/history")
    async def reminder_history(limit: int = 200, admin=Depends(require_admin)):
        return await db.wa_reminders.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(max(limit, 1), 1000))

    @r.post("/api/cron/piutang-reminder")
    async def cron_reminder(request: Request, background: BackgroundTasks):
        # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
        if not _cron_auth(request):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        env, err = await _cron_envelope(request)
        if err:
            return err
        run_key = request.headers.get("x-webhook-id") or env.get("run_id") or f"manual-{uuid.uuid4()}"
        res = await db.cron_runs.update_one({"run_id": f"reminder:{run_key}"}, {"$setOnInsert": {"run_id": f"reminder:{run_key}", "job": "piutang-reminder", "received_at": _now()}}, upsert=True)
        if res.upserted_id is None:
            return {"status": "duplicate"}
        cfg = await _cfg("wa_reminder", REMINDER_DEFAULT)
        now = now_wita()
        if not cfg["enabled"]:
            return {"status": "accepted", "action": "disabled"}
        if now.hour != int(cfg["send_hour"]) or now.isoweekday() not in cfg["days"]:
            return {"status": "accepted", "action": "not_scheduled_now"}
        day_lock = await db.cron_runs.update_one({"run_id": f"reminder-day:{now.date().isoformat()}"},
                                                 {"$setOnInsert": {"run_id": f"reminder-day:{now.date().isoformat()}", "job": "piutang-reminder", "received_at": _now()}}, upsert=True)
        if day_lock.upserted_id is None:
            return {"status": "accepted", "action": "already_ran_today"}
        background.add_task(reminder_run, "cron", f"Penjadwal {cfg['send_hour']:02d}:00 WITA")
        return {"status": "accepted", "action": "run"}

    # =================== Laporan Mingguan Pemilik ===================
    class Recipient(BaseModel):
        nama: str = "Pemilik"
        phone: str

    class WeeklyCfg(BaseModel):
        enabled: bool = True
        recipients: list[Recipient] = []
        template_name: str = ""
        template_lang: str = "id"

    async def weekly_run(trigger: str, actor: str, week_start: Optional[str] = None, force: bool = False) -> dict:
        cfg = await _cfg("wa_weekly", WEEKLY_DEFAULT)
        rep = await build_weekly(db, week_start)
        run_id = str(uuid.uuid4())
        results = []
        for rc in cfg.get("recipients") or []:
            phone = norm_phone(rc.get("phone", ""))
            base = {"id": str(uuid.uuid4()), "run_id": run_id, "trigger": trigger, "week_start": rep["week_start"], "week_end": rep["week_end"],
                    "nama": rc.get("nama", ""), "phone": phone, "text": rep["text"], "created_at": _now(), "actor": actor,
                    "total_jam": rep["total_jam"], "total_pemasukan": rep["total_pemasukan"], "total_bayar": rep["total_bayar"],
                    "total_piutang": rep["total_piutang"], "pending_count": len(rep["pending"])}
            if not phone:
                doc = {**base, "status": "skipped", "error": "Nomor penerima kosong"}
            elif not cfg["enabled"] and trigger == "cron":
                doc = {**base, "status": "skipped", "error": "Laporan mingguan dinonaktifkan"}
            else:
                key = f"weekly:{rep['week_start']}:{phone}" + (f":{run_id}" if force else "")
                msg, mode = _msg(rep["text"], rep["params"], cfg, phone, await _in_window(phone))
                ob = await outbox.send(phone, msg, "weekly_report", key, actor=actor, ref={"weekly_id": base["id"]},
                                       label=f"Laporan mingguan {rep['week_start']}") if msg else None
                st, err = _status(ob)
                doc = {**base, "status": st, "error": err, "mode": mode, "outbox_id": (ob or {}).get("id", "")}
            await db.wa_weekly.insert_one(doc)
            doc.pop("_id", None)
            results.append(doc)
        counts = {k: sum(1 for x in results if x["status"] == k) for k in ("sent", "simulated", "skipped", "failed")}
        await audit("weekly_run", actor, f"Laporan mingguan {rep['periode']} ({trigger}): terkirim {counts['sent']}, simulasi {counts['simulated']}, "
                                         f"dilewati {counts['skipped']}, gagal {counts['failed']}", counts)
        return {"run_id": run_id, "week_start": rep["week_start"], "week_end": rep["week_end"], "counts": counts, "results": results}

    @r.get("/api/wa/weekly/settings")
    async def get_weekly(admin=Depends(require_admin)):
        return {**(await _cfg("wa_weekly", WEEKLY_DEFAULT)), "template_text": WEEKLY_TEMPLATE, "schedule": "Setiap Senin 08:00 WITA (Asia/Makassar) — minggu sebelumnya",
                "whatsapp_configured": wa_configured(), "cron_secret_set": bool(_env("WEBHOOK_CRON_SECRET")), "default_week_start": week_bounds()[0]}

    @r.put("/api/wa/weekly/settings")
    async def put_weekly(body: WeeklyCfg, admin=Depends(require_admin)):
        recs = []
        for rc in body.recipients:
            p = norm_phone(rc.phone)
            if len(p) < 10 or len(p) > 15:
                raise HTTPException(400, f"Nomor tidak valid: {rc.phone}")
            recs.append({"nama": (rc.nama or "Pemilik").strip()[:60], "phone": p})
        if not recs:
            raise HTTPException(400, "Minimal 1 penerima")
        name = body.template_name.strip()
        if name and not all(ch.islower() or ch.isdigit() or ch == "_" for ch in name):
            raise HTTPException(400, "Nama template hanya huruf kecil, angka, dan garis bawah")
        before = await _cfg("wa_weekly", WEEKLY_DEFAULT)
        new = {"enabled": body.enabled, "recipients": recs, "template_name": name, "template_lang": body.template_lang.strip() or "id"}
        await db.app_settings.update_one({"key": "wa_weekly"}, {"$set": {"key": "wa_weekly", **new, "updated_by": admin.name, "updated_at": _now()}}, upsert=True)
        await audit("settings_changed", admin.name, "Pengaturan laporan mingguan diubah", {"sebelum": before, "sesudah": new})
        return await get_weekly(admin)

    @r.get("/api/wa/weekly/preview")
    async def preview_weekly(week_start: Optional[str] = None, admin=Depends(require_admin)):
        return await build_weekly(db, week_start)

    @r.post("/api/wa/weekly/run")
    async def run_weekly(body: RunIn, admin=Depends(require_admin)):
        return await weekly_run("manual", admin.name, body.week_start, force=body.force)

    @r.get("/api/wa/weekly/history")
    async def weekly_history(limit: int = 200, admin=Depends(require_admin)):
        return await db.wa_weekly.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(max(limit, 1), 1000))

    @r.post("/api/cron/weekly-report")
    async def cron_weekly(request: Request, background: BackgroundTasks):
        # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
        if not _cron_auth(request):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        env, err = await _cron_envelope(request)
        if err:
            return err
        run_key = request.headers.get("x-webhook-id") or env.get("run_id") or f"manual-{uuid.uuid4()}"
        res = await db.cron_runs.update_one({"run_id": f"weekly:{run_key}"}, {"$setOnInsert": {"run_id": f"weekly:{run_key}", "job": "weekly-report", "received_at": _now()}}, upsert=True)
        if res.upserted_id is None:
            return {"status": "duplicate"}
        background.add_task(weekly_run, "cron", "Penjadwal Senin 08:00 WITA")
        return {"status": "accepted"}

    return r
