"""Self-test Pengingat Piutang, Laporan Mingguan, Simulasi pesan masuk (DB terisolasi). python /app/tests/wa_selftest/t_reports.py"""
import io
import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
os.environ.update({"DB_NAME": "wa_selftest_rep", "ADMIN_USERNAME": "selftest", "ADMIN_PASSWORD": "selftest123"})
for k in ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN"):
    os.environ.pop(k, None)
from PIL import Image  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
import whatsapp  # noqa: E402


async def fake_extract(data, caption):
    return {"jenis": "transfer", "keyakinan": 0.95, "transfer": {"nominal": 750000, "no_ref": "SIMREF1", "tanggal": D(0)}}

whatsapp.extract_image = fake_extract
TZ = ZoneInfo("Asia/Makassar")
today = datetime.now(TZ).date()
D = lambda n: (today - timedelta(days=n)).isoformat()  # noqa: E731
SEC = os.environ.get("WEBHOOK_CRON_SECRET", "")
ok_all = True


def check(name, cond, extra=""):
    global ok_all
    ok_all &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name, str(extra)[:220])


with TestClient(server.app, base_url="https://testserver") as c:
    db = server.db
    call = c.portal.call
    call(lambda: db.units.insert_many([
        {"id": "ua", "unit_name": "SDLG", "nomor_lambung": "10", "kode_wa": "Sdlg 10", "pengurus": "Pak A", "tarif_sewa_per_jam": 100000},
        {"id": "ub", "unit_name": "CAT", "nomor_lambung": "20", "kode_wa": "Cat 20", "pengurus": "Pak B", "tarif_sewa_per_jam": 50000},
        {"id": "uc", "unit_name": "PC", "nomor_lambung": "30", "kode_wa": "Pc 30", "pengurus": "Pak C", "tarif_sewa_per_jam": 200000}]))
    call(lambda: db.wa_contacts.insert_many([
        {"id": "ca", "phone": "628111000001", "nama": "A", "tipe": "pengurus", "pengurus": "Pak A"},
        {"id": "cb", "phone": "628111000002", "nama": "B", "tipe": "pengurus", "pengurus": "Pak B"},
        {"id": "cc", "phone": "628111000003", "nama": "C", "tipe": "pengurus", "pengurus": "Pak C"}]))
    ops = [("o1", "ua", 40, 100, 110), ("o2", "ua", 20, 110, 120), ("o3", "ua", 5, 120, 130), ("o4", "ub", 6, 10, 20), ("o5", "uc", 50, 0, 10)]
    call(lambda: db.operations.insert_many([{"id": i, "unit_id": u, "tanggal": D(d), "hour_meter_awal": a, "hour_meter_akhir": z, "total_jam": z - a} for i, u, d, a, z in ops]))
    call(lambda: db.kas_masuk.insert_many([
        {"id": "k1", "tanggal": D(10), "debit": 1500000, "pengurus": "Pak A", "unit_id": "ua", "no_bukti": "KM-1"},
        {"id": "k2", "tanggal": D(4), "debit": 500000, "pengurus": "Pak B", "unit_id": "ub", "no_bukti": "KM-2"},
        {"id": "k3", "tanggal": D(4), "debit": 250000, "pengurus": "", "unit_id": "", "no_bukti": "KM-3", "uraian": "lain-lain"}]))
    call(lambda: db.wa_inbox.insert_one({"id": "pc1", "status": "pending", "jenis": "transfer", "draft": {"pengurus": "Pak C", "unit_id": "uc"}, "received_at": D(0)}))
    check("login", c.post("/api/auth/login", json={"username": "selftest", "password": "selftest123"}).status_code == 200)

    ag = {a["pengurus"]: a for a in c.get("/api/wa/piutang/aging").json()["items"]}
    A = ag["Pak A"]
    check("Piutang A = 3jt - 1.5jt", A["piutang"] == 1500000, A["piutang"])
    check("FIFO oldest unpaid A = D(20), umur 20", A["oldest_unpaid"] == D(20) and A["umur_hari"] == 20, (A["oldest_unpaid"], A["umur_hari"]))
    check("Bucket 0-30 = 1.5jt", A["buckets"]["0_30"] == 1500000, A["buckets"])
    check("B lunas", ag["Pak B"]["piutang"] == 0)
    check("C pending transfer counted", ag["Pak C"]["pending_transfer"] == 1 and ag["Pak C"]["piutang"] == 2000000)
    check("as_of past excludes later ops", next(a for a in c.get("/api/wa/piutang/aging", params={"as_of": D(15)}).json()["items"] if a["pengurus"] == "Pak A")["piutang"] == 2000000)

    r = c.put("/api/wa/reminder/settings", json={"enabled": True, "send_hour": 9, "days": [1, 2, 3, 4, 5, 6, 7], "min_nominal": 1000000, "min_age_days": 14, "cooldown_days": 3})
    check("reminder settings saved", r.status_code == 200 and r.json()["enabled"], r.text[:100])
    check("reminder settings validation cooldown", c.put("/api/wa/reminder/settings", json={"cooldown_days": 0}).status_code == 400)
    check("reminder settings validation days", c.put("/api/wa/reminder/settings", json={"days": [9]}).status_code == 400)
    pv = {x["pengurus"]: x for x in c.get("/api/wa/reminder/preview").json()["items"]}
    check("preview A eligible", pv["Pak A"]["eligible"], pv["Pak A"]["reason"])
    check("preview B lunas", not pv["Pak B"]["eligible"] and "Lunas" in pv["Pak B"]["reason"])
    check("preview C pending", not pv["Pak C"]["eligible"] and "verifikasi" in pv["Pak C"]["reason"])
    run1 = {x["pengurus"]: x for x in c.post("/api/wa/reminder/run", json={}).json()["results"]}
    check("run1 A simulated", run1["Pak A"]["status"] == "simulated", run1["Pak A"])
    run2 = {x["pengurus"]: x for x in c.post("/api/wa/reminder/run", json={}).json()["results"]}
    check("run2 A skipped (cooldown)", run2["Pak A"]["status"] == "skipped" and "jeda" in run2["Pak A"]["error"], run2["Pak A"]["error"])
    run3 = {x["pengurus"]: x for x in c.post("/api/wa/reminder/run", json={"force": True}).json()["results"]}
    check("force A simulated, B still skipped (lunas)", run3["Pak A"]["status"] == "simulated" and run3["Pak B"]["status"] == "skipped")
    c.put("/api/wa/reminder/settings", json={"enabled": True, "days": [1, 2, 3, 4, 5, 6, 7], "min_nominal": 1000000, "min_age_days": 30, "cooldown_days": 3})
    check("umur < batas -> not eligible", "Umur" in next(x for x in c.get("/api/wa/reminder/preview").json()["items"] if x["pengurus"] == "Pak A")["reason"])
    c.put("/api/wa/reminder/settings", json={"enabled": True, "days": [1, 2, 3, 4, 5, 6, 7], "min_nominal": 2000000, "min_age_days": 1, "cooldown_days": 3})
    check("nominal < batas -> not eligible", "batas" in next(x for x in c.get("/api/wa/reminder/preview").json()["items"] if x["pengurus"] == "Pak A")["reason"])
    call(lambda: db.kas_masuk.insert_one({"id": "k4", "tanggal": D(0), "debit": 1500000, "pengurus": "Pak A", "unit_id": "ua", "no_bukti": "KM-4"}))
    check("after payment A lunas", "Lunas" in next(x for x in c.get("/api/wa/reminder/preview").json()["items"] if x["pengurus"] == "Pak A")["reason"])
    hist = c.get("/api/wa/reminder/history").json()
    check("reminder history logged", len(hist) >= 9, len(hist))
    ob = c.get("/api/wa/outbox", params={"kind": "reminder"}).json()
    check("outbox reminder simulated entries", ob["counts"]["simulated"] >= 2 and all(x["status"] == "simulated" for x in ob["items"]), ob["counts"])

    # cron auth & schedule
    check("cron reminder 401", c.post("/api/cron/piutang-reminder").status_code == 401)
    hdr = {"Authorization": f"Bearer {SEC}"}
    h = datetime.now(TZ).hour
    c.put("/api/wa/reminder/settings", json={"enabled": True, "send_hour": (h + 3) % 24, "days": [1, 2, 3, 4, 5, 6, 7]})
    check("cron not scheduled now", c.post("/api/cron/piutang-reminder", headers={**hdr, "X-Webhook-Id": "r1"}).json().get("action") == "not_scheduled_now")
    check("cron duplicate id", c.post("/api/cron/piutang-reminder", headers={**hdr, "X-Webhook-Id": "r1"}).json().get("status") == "duplicate")
    c.put("/api/wa/reminder/settings", json={"enabled": True, "send_hour": h, "days": [1, 2, 3, 4, 5, 6, 7]})
    check("cron run at hour", c.post("/api/cron/piutang-reminder", headers={**hdr, "X-Webhook-Id": "r2"}).json().get("action") == "run")
    check("cron once per day", c.post("/api/cron/piutang-reminder", headers={**hdr, "X-Webhook-Id": "r3"}).json().get("action") == "already_ran_today")
    c.put("/api/wa/reminder/settings", json={"enabled": False})
    check("cron disabled", c.post("/api/cron/piutang-reminder", headers={**hdr, "X-Webhook-Id": "r4"}).json().get("action") == "disabled")

    # weekly
    ws = (today - timedelta(days=5)) - timedelta(days=(today - timedelta(days=5)).weekday())
    we = ws + timedelta(days=6)
    rep = c.get("/api/wa/weekly/preview", params={"week_start": (ws + timedelta(days=2)).isoformat()}).json()
    check("weekly normalizes to Monday", rep["week_start"] == ws.isoformat() and rep["week_end"] == we.isoformat())
    exp_jam = sum(z - a for i, u, d, a, z in ops if ws.isoformat() <= D(d) <= we.isoformat())
    exp_in = sum(k for k, d in [(1500000, 10), (500000, 4), (250000, 4), (1500000, 0)] if ws.isoformat() <= D(d) <= we.isoformat())
    check("weekly total_jam", rep["total_jam"] == exp_jam, (rep["total_jam"], exp_jam))
    check("weekly total_pemasukan", rep["total_pemasukan"] == exp_in, (rep["total_pemasukan"], exp_in))
    check("weekly pemasukan_lain = non-pengurus", rep["pemasukan_lain"] == (250000 if ws.isoformat() <= D(4) <= we.isoformat() else 0), rep["pemasukan_lain"])
    check("weekly pending list", len(rep["pending"]) == 1 and rep["text"].count("Menunggu Verifikasi (1)") == 1)
    check("weekly default recipient owner", c.get("/api/wa/weekly/settings").json()["recipients"][0]["phone"] == "6282343070023")
    check("weekly bad phone 400", c.put("/api/wa/weekly/settings", json={"enabled": True, "recipients": [{"nama": "x", "phone": "12"}]}).status_code == 400)
    w1 = c.post("/api/wa/weekly/run", json={"week_start": ws.isoformat()}).json()
    w2 = c.post("/api/wa/weekly/run", json={"week_start": ws.isoformat()}).json()
    w3 = c.post("/api/wa/weekly/run", json={"week_start": ws.isoformat(), "force": True}).json()
    check("weekly run simulated / dedupe / force", w1["counts"]["simulated"] == 1 and w2["counts"]["skipped"] == 1 and w3["counts"]["simulated"] == 1, (w1["counts"], w2["counts"], w3["counts"]))
    check("cron weekly 401", c.post("/api/cron/weekly-report").status_code == 401)
    check("cron weekly accepted", c.post("/api/cron/weekly-report", headers={**hdr, "X-Webhook-Id": "w1"}).json().get("status") == "accepted")
    check("cron weekly duplicate", c.post("/api/cron/weekly-report", headers={**hdr, "X-Webhook-Id": "w1"}).json().get("status") == "duplicate")

    # simulated inbound
    t1 = c.post("/api/wa/simulate/inbound", data={"phone": "081199990000", "name": "Op Sim", "text": "halo"}).json()
    t2 = c.post("/api/wa/simulate/inbound", data={"phone": "081199990000", "name": "Op Sim", "text": "halo lagi"}).json()
    check("sim text -> help simulated, 2nd deduped", t1.get("reply") == "simulated" and t2.get("reply_deduped"), (t1, t2))
    img = io.BytesIO(); Image.new("RGB", (30, 30), "white").save(img, "JPEG")
    s1 = c.post("/api/wa/simulate/inbound", data={"phone": "628111000001", "caption": "Sdlg 10", "message_id": "abc1"}, files={"file": ("a.jpg", img.getvalue(), "image/jpeg")}).json()
    time.sleep(2.5)
    s2 = c.post("/api/wa/simulate/inbound", data={"phone": "628111000001", "caption": "Sdlg 10", "message_id": "abc1"}, files={"file": ("a.jpg", img.getvalue(), "image/jpeg")}).json()
    item = call(lambda: db.wa_inbox.find_one({"message_id": "sim.abc1"}, {"_id": 0}))
    check("sim image -> inbox item simulated whatsapp", item and item.get("simulated") and item["source"] == "whatsapp" and item["status"] in ("pending", "approved"), item and item["status"])
    check("sim image duplicate message_id", s2.get("status") == "duplicate", s2)
    conn = c.get("/api/wa/connection").json()
    check("simulation does NOT verify connection", conn["level"] == "not_configured" and not conn["inbound_verified_at"], conn["level"])
    check("sim invalid phone 400", c.post("/api/wa/simulate/inbound", data={"phone": "12", "text": "x"}).status_code == 400)
    check("sim empty 400", c.post("/api/wa/simulate/inbound", data={"phone": "081199990000"}).status_code == 400)
    aud = c.get("/api/wa/audit", params={"action": "reminder_run,weekly_run,simulated_inbound,reminder_settings"}).json()
    check("audit entries for reminder/weekly/sim", {a["action"] for a in aud} >= {"reminder_run", "weekly_run", "simulated_inbound", "reminder_settings"}, {a["action"] for a in aud})
    call(lambda: db.client.drop_database("wa_selftest_rep"))
print("ALL PASS" if ok_all else "SOME FAILED")
