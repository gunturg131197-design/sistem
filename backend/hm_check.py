"""Deteksi HM janggal (Hour Meter) — dipakai sebelum persetujuan otomatis DAN saat persetujuan manual.

Aturan (WAJIB, tidak bisa dimatikan):
- tidak_terbaca : angka HM kosong/0, atau keyakinan AI di bawah ambang (foto kurang jelas)
- turun         : HM lebih kecil dari HM terakhir unit sebelum tanggal tsb.
- urutan        : HM melebihi HM awal pada laporan tanggal SESUDAHNYA (laporan disisipkan mundur)
- tanggal       : tanggal laporan di masa depan (WITA)
Aturan dapat diatur:
- lonjakan      : kenaikan HM > batas jam/hari x selisih hari, atau total jam satu hari > batas jam/hari

HM yang janggal TIDAK PERNAH disetujui otomatis; admin wajib mencentang konfirmasi saat menyetujui manual.
"""
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Makassar")
HM_DEFAULT = {"hm_spike_check": True, "hm_max_per_day": 20.0}


def _f(v) -> Optional[float]:
    try:
        return None if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return None


def _fmt(v) -> str:
    return f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def hm_anomalies(db, unit_id: str, tanggal: str, hm_awal, hm_akhir, conf: Optional[float], cfg: dict,
                       exclude_op_id: Optional[str] = None) -> list[dict]:
    out: list[dict] = []
    akhir, awal = _f(hm_akhir), _f(hm_awal)
    min_conf = float(cfg.get("min_confidence", 0.9))
    if not akhir or akhir <= 0:
        out.append({"kode": "tidak_terbaca", "pesan": "Angka HM tidak terbaca / kosong"})
    if conf is not None and conf < min_conf:
        out.append({"kode": "tidak_terbaca", "pesan": f"Foto kurang jelas — keyakinan AI {conf:.0%} di bawah {min_conf:.0%}"})
    tgl = (tanggal or "")[:10]
    try:
        d = datetime.strptime(tgl, "%Y-%m-%d").date()
    except ValueError:
        out.append({"kode": "tanggal", "pesan": "Tanggal laporan tidak valid"})
        return out
    today = datetime.now(TZ).date()
    if d > today:
        out.append({"kode": "tanggal", "pesan": f"Tanggal laporan {tgl} di masa depan (hari ini {today.isoformat()} WITA)"})
    if not unit_id or not akhir:
        return out
    excl = {"id": {"$ne": exclude_op_id}} if exclude_op_id else {}
    prev = await db.operations.find({"unit_id": unit_id, "tanggal": {"$lt": tgl}, **excl}, {"_id": 0}).sort(
        [("tanggal", -1), ("hour_meter_akhir", -1)]).to_list(1)
    nxt = await db.operations.find({"unit_id": unit_id, "tanggal": {"$gt": tgl}, **excl}, {"_id": 0}).sort(
        [("tanggal", 1), ("hour_meter_awal", 1)]).to_list(1)
    max_day = float(cfg.get("hm_max_per_day") or HM_DEFAULT["hm_max_per_day"])
    if prev:
        p = prev[0]
        p_akhir = _f(p.get("hour_meter_akhir")) or 0.0
        if akhir < p_akhir:
            out.append({"kode": "turun", "pesan": f"HM turun: {_fmt(akhir)} lebih kecil dari HM terakhir {_fmt(p_akhir)} ({p.get('tanggal')})"})
        elif cfg.get("hm_spike_check", True):
            try:
                days = max(1, (d - datetime.strptime(p.get("tanggal", tgl)[:10], "%Y-%m-%d").date()).days)
            except ValueError:
                days = 1
            delta = akhir - p_akhir
            if delta > max_day * days:
                out.append({"kode": "lonjakan", "pesan": f"HM melonjak {_fmt(delta)} jam dalam {days} hari sejak {p.get('tanggal')} "
                                                          f"(batas {_fmt(max_day)} jam/hari)"})
    if cfg.get("hm_spike_check", True) and awal is not None and akhir - awal > max_day and not any(a["kode"] == "lonjakan" for a in out):
        out.append({"kode": "lonjakan", "pesan": f"Total jam satu hari {_fmt(akhir - awal)} melebihi batas {_fmt(max_day)} jam/hari"})
    if nxt:
        n = nxt[0]
        n_awal = _f(n.get("hour_meter_awal")) or _f(n.get("hour_meter_akhir")) or 0.0
        if n_awal and akhir > n_awal:
            out.append({"kode": "urutan", "pesan": f"HM {_fmt(akhir)} melebihi HM awal laporan sesudahnya {_fmt(n_awal)} ({n.get('tanggal')})"})
    # buang duplikat pesan
    seen, uniq = set(), []
    for a in out:
        if a["pesan"] not in seen:
            seen.add(a["pesan"])
            uniq.append(a)
    return uniq
