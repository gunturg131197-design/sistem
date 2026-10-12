"""Self-test HM janggal (DB terisolasi wa_selftest_hm, AI di-mock). Jalankan: python /app/tests/wa_selftest/t_hm.py"""
import io
import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
os.environ.update({"DB_NAME": "wa_selftest_hm", "ADMIN_USERNAME": "selftest", "ADMIN_PASSWORD": "selftest123"})
for k in ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN"):
    os.environ.pop(k, None)

from PIL import Image  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
import whatsapp  # noqa: E402

FAKE = {}


async def fake_extract(data, caption):
    return FAKE["ai"]


whatsapp.extract_image = fake_extract  # dipakai lewat nama global di modul
TZ = ZoneInfo("Asia/Makassar")
today = datetime.now(TZ).date()
D = lambda n: (today - timedelta(days=n)).isoformat()  # noqa: E731
img = io.BytesIO()
Image.new("RGB", (40, 40), "white").save(img, "JPEG")
IMG = img.getvalue()
ok_all = True


def check(name, cond, extra=""):
    global ok_all
    ok_all &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name, extra)


with TestClient(server.app, base_url="https://testserver") as c:
    db = server.db
    c.portal.call(lambda: db.units.insert_one({"id": "u1", "unit_name": "SDLG", "nomor_lambung": "10", "kode_wa": "Sdlg 10", "operator_id": "op1", "pengurus": "Pak Test"}))
    c.portal.call(lambda: db.operations.insert_one({"id": "o1", "unit_id": "u1", "tanggal": D(3), "hour_meter_awal": 990, "hour_meter_akhir": 1000, "total_jam": 10}))
    r = c.post("/api/auth/login", json={"username": "selftest", "password": "selftest123"})
    check("login", r.status_code == 200, r.text[:100])
    c.put("/api/wa/auto-settings", json={"transfer_enabled": True, "hm_enabled": True, "min_confidence": 0.9, "hm_spike_check": True, "hm_max_per_day": 20})

    def send(hm, conf=0.97, tgl=None):
        FAKE["ai"] = {"jenis": "hour_meter", "keyakinan": conf, "hour_meter": {"hm": hm, "tanggal": tgl or D(1)}}
        r = c.post("/api/wa/upload", files={"file": ("a.jpg", IMG, "image/jpeg")}, data={"caption": "Sdlg 10"})
        assert r.status_code == 200, r.text
        iid = r.json()["id"]
        for _ in range(30):
            it = c.portal.call(lambda: db.wa_inbox.find_one({"id": iid}, {"_id": 0}))
            if it["status"] != "processing":
                return it
            time.sleep(0.2)
        return it

    it = send(995)
    check("HM turun -> pending + flag", it["status"] == "pending" and it["hm_flag"] and any(a["kode"] == "turun" for a in it["hm_anomalies"]), str(it.get("hm_anomalies")))
    it = send(1100)
    check("HM lonjakan (100 jam/2 hari) -> manual", it["status"] == "pending" and any(a["kode"] == "lonjakan" for a in it["hm_anomalies"]), str(it.get("hm_anomalies")))
    it = send(1020, conf=0.6)
    check("HM tidak jelas (60%) -> manual", it["status"] == "pending" and any(a["kode"] == "tidak_terbaca" for a in it["hm_anomalies"]))
    it_z = send(0)
    check("HM 0 tidak terbaca -> manual", it_z["status"] == "pending" and any(a["kode"] == "tidak_terbaca" for a in it_z["hm_anomalies"]))
    it_f = send(1010, tgl=(today + timedelta(days=2)).isoformat())
    check("Tanggal masa depan -> manual", it_f["status"] == "pending" and any(a["kode"] == "tanggal" for a in it_f["hm_anomalies"]))
    # manual approve tanpa konfirmasi -> 409, dengan konfirmasi -> OK
    r = c.post(f"/api/wa/inbox/{it['id']}/approve", json={"jenis": "hour_meter", "draft": {}})
    check("Approve janggal tanpa konfirmasi -> 409", r.status_code == 409, r.text[:120])
    r = c.post(f"/api/wa/inbox/{it['id']}/approve", json={"jenis": "hour_meter", "draft": {}, "confirm_anomaly": True})
    check("Approve janggal dengan konfirmasi -> 200", r.status_code == 200 and r.json().get("anomalies"), r.text[:160])
    aud = c.get("/api/wa/audit", params={"action": "hm_anomaly,hm_anomaly_confirmed"}).json()
    check("Audit hm_anomaly + confirmed", any(a["action"] == "hm_anomaly_confirmed" for a in aud) and any(a["action"] == "hm_anomaly" for a in aud), str(len(aud)))
    # HM wajar -> auto-approve (prev sekarang 1020 tgl D(1)); kirim untuk hari ini 1030
    it_ok = send(1030, tgl=D(0))
    check("HM wajar -> auto approved", it_ok["status"] == "approved" and it_ok.get("auto_approved") and not it_ok["hm_flag"], f"{it_ok['status']} {it_ok.get('auto_check')}")
    # urutan: sisipkan laporan mundur D(2) dengan HM 1025 (> HM awal laporan sesudahnya D(1)=1000..1020?)
    it_u = send(1025, tgl=D(2))
    check("HM melebihi laporan sesudahnya -> manual", it_u["status"] == "pending" and any(a["kode"] == "urutan" for a in it_u["hm_anomalies"]), str(it_u.get("hm_anomalies")))
    # spike off -> lonjakan tidak dideteksi, tapi turun tetap
    c.put("/api/wa/auto-settings", json={"transfer_enabled": True, "hm_enabled": True, "min_confidence": 0.9, "hm_spike_check": False})
    cfg = c.get("/api/wa/auto-settings").json()
    check("Settings partial update keeps max/day", cfg["hm_max_per_day"] == 20 and cfg["hm_spike_check"] is False, str(cfg))
    r = c.put("/api/wa/auto-settings", json={"transfer_enabled": True, "hm_enabled": True, "min_confidence": 0.9, "hm_max_per_day": 30})
    check("Validasi max/day 1-24", r.status_code == 400)
    flt = c.get("/api/wa/inbox", params={"status": "pending,duplicate", "flag": "hm"}).json()
    check("Filter flag=hm", len(flt) >= 4 and all(x["hm_flag"] for x in flt), str(len(flt)))
    c.portal.call(lambda: db.client.drop_database("wa_selftest_hm"))
print("ALL PASS" if ok_all else "SOME FAILED")
