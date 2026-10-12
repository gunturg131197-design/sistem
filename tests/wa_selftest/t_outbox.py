import asyncio, os, sys
sys.path.insert(0, "/app/backend")
os.environ.update({"WHATSAPP_ACCESS_TOKEN":"EAAtesttokenvalue12345678901234567890","WHATSAPP_PHONE_NUMBER_ID":"999","WHATSAPP_APP_SECRET":"sec","WHATSAPP_VERIFY_TOKEN":"vt","WHATSAPP_GRAPH_BASE_URL":"http://localhost:8099"})
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv; load_dotenv("/app/backend/.env", override=False)
import wa_outbox as W
async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])["outbox_selftest"]
    await db.wa_outbox.drop(); await db.wa_audit.drop(); await db.app_settings.drop()
    ob = W.Outbox(db); await ob.ensure_indexes()
    m={"type":"text","text":{"body":"hi"}}
    a=await ob.send("0811000001",m,"test","k1"); print("ok:",a["status"],a.get("wa_message_id"))
    b=await ob.send("0811000001",m,"test","k1"); print("dedupe:",b.get("deduped"),b["status"])
    c=await ob.send("62811000002",m,"test","k2"); print("5xx:",c["status"],c["retriable"],c["attempts"],c["next_retry_at"] is not None)
    d=await ob.send("62811000003",m,"test","k3"); print("4xx:",d["status"],d["retriable"],d["error"])
    e=await ob.send("62811000005",m,"test","k5"); print("token redacted:","EAAtest" not in e["error"], e["error"])
    f=await ob.send("62811000004",m,"test","k4"); print("timeout:",f["status"],f["retriable"],f.get("uncertain"))
    # status webhook
    await ob.apply_status({"id":a["wa_message_id"],"status":"delivered","recipient_id":"62811000001"})
    await ob.apply_status({"id":a["wa_message_id"],"status":"sent"})
    x=await db.wa_outbox.find_one({"id":a["id"]}); print("status after delivered+sent:",x["status"])
    st=await W.connection_state(db); print("conn:",st["level"])
    await W.mark_connection(db,"inbound","62811000001"); st=await W.connection_state(db); print("conn:",st["level"])
    # retry due
    await db.wa_outbox.update_one({"id":c["id"]},{"$set":{"next_retry_at":"2000-01-01"}})
    r=await ob.retry_due(); print("retry_due:",r)
    y=await db.wa_outbox.find_one({"id":c["id"]}); print("attempts now",y["attempts"])
    audits=await db.wa_audit.find({}).to_list(100); print("audit leak:", any("EAAtest" in str(z) for z in audits), len(audits))
    leak=await db.wa_outbox.find({}).to_list(100); print("outbox leak:", any("EAAtest" in str(z) for z in leak))
    await db.client.drop_database("outbox_selftest")
asyncio.run(main())
