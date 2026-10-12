import asyncio, json
from aiohttp import web
calls=[]
async def msgs(req):
    b=await req.json(); calls.append(b); to=b["to"]
    if to.endswith("01"): return web.json_response({"messages":[{"id":f"wamid.{len(calls)}"}]})
    if to.endswith("02"): return web.json_response({"error":{"message":"Service unavailable","code":2}},status=503)
    if to.endswith("03"): return web.json_response({"error":{"message":"Re-engagement message","code":131047}},status=400)
    if to.endswith("04"): await asyncio.sleep(40); return web.json_response({})
    return web.json_response({"error":{"message":"bad token EAAtesttokenvalue12345678901234567890","code":190}},status=401)
async def phone(req): return web.json_response({"display_phone_number":"+62 811","verified_name":"TRIRARA","quality_rating":"GREEN"})
async def count(req): return web.json_response({"n":len(calls)})
app=web.Application(); app.router.add_post("/v25.0/{pid}/messages",msgs); app.router.add_get("/v25.0/{pid}",phone); app.router.add_get("/count",count)
web.run_app(app,port=8099,print=None)
