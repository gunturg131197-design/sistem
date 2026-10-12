import os, sys, json, hmac, hashlib, time
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv; load_dotenv("/app/backend/.env")
os.environ.update({"DB_NAME":"wa_selftest","WHATSAPP_ACCESS_TOKEN":"EAAtesttokenvalue12345678901234567890","WHATSAPP_PHONE_NUMBER_ID":"999","WHATSAPP_APP_SECRET":"sec","WHATSAPP_VERIFY_TOKEN":"vt","WHATSAPP_GRAPH_BASE_URL":"http://localhost:8099"})
from fastapi.testclient import TestClient
import server
with TestClient(server.app) as c:
    print("verify:", c.get("/api/whatsapp/webhook", params={"hub.mode":"subscribe","hub.verify_token":"vt","hub.challenge":"123"}).text)
    print("verify bad:", c.get("/api/whatsapp/webhook", params={"hub.mode":"subscribe","hub.verify_token":"x","hub.challenge":"123"}).status_code)
    def post(p, sig=True):
        raw=json.dumps(p).encode(); h={"Content-Type":"application/json"}
        if sig: h["X-Hub-Signature-256"]="sha256="+hmac.new(b"sec",raw,hashlib.sha256).hexdigest()
        return c.post("/api/whatsapp/webhook", content=raw, headers=h)
    msg={"object":"whatsapp_business_account","entry":[{"changes":[{"value":{"contacts":[{"wa_id":"62811000001","profile":{"name":"Op"}}],"messages":[{"id":"wamid.IN1","from":"62811000001","type":"text","text":{"body":"halo"}}]}}]}]}
    print("bad sig:", post(msg, False).status_code)
    print("ok:", post(msg).json()); print("dup:", post(msg).json())
    msg2=json.loads(json.dumps(msg)); msg2["entry"][0]["changes"][0]["value"]["messages"][0]["id"]="wamid.IN2"
    post(msg2)
    time.sleep(1)
    import asyncio
    db=server.db
    async def chk():
        ob=await db.wa_outbox.find({}, {"_id":0,"kind":1,"status":1,"dedupe_key":1,"wa_message_id":1}).to_list(10); print("outbox:", ob)
        aud=await db.wa_audit.find({}, {"_id":0,"action":1}).to_list(50); print("audit:", [a["action"] for a in aud])
        return ob
    ob=c.portal.call(chk) if hasattr(c,"portal") and c.portal else None
    # status update -> delivered
    wid=[o for o in ob if o["kind"]=="help"][0]["wa_message_id"]
    st={"object":"whatsapp_business_account","entry":[{"changes":[{"value":{"statuses":[{"id":wid,"status":"delivered","recipient_id":"62811000001"}]}}]}]}
    post(st); time.sleep(0.5)
    print("conn:", c.portal.call(lambda: __import__("wa_outbox").connection_state(db))["level"])
    c.portal.call(lambda: db.client.drop_database("wa_selftest"))
