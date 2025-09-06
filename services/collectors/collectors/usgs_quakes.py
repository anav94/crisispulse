import os, asyncio, aiohttp
from .common import get_producer, event_envelope, messages_out, start_metrics_server
RAW_TOPIC=os.getenv("RAW_TOPIC","raw_events")
USGS_FEED=os.getenv("USGS_FEED","https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson")
POLL_SECONDS=int(os.getenv("POLL_SECONDS","30"))
async def fetch_feed(session):
    async with session.get(USGS_FEED, timeout=20) as resp:
        resp.raise_for_status(); return await resp.json()
async def run():
    start_metrics_server(9100); producer=await get_producer(); seen=set()
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                data=await fetch_feed(session)
                for feat in data.get("features",[]):
                    fid=feat.get("id")
                    if not fid or fid in seen: continue
                    seen.add(fid)
                    props=feat.get("properties",{}) or {}; geom=feat.get("geometry",{}) or {}
                    coords=(geom.get("coordinates") or [None,None])
                    payload={"source_id":fid,"title":props.get("title") or "","body":props.get("place") or "",
                             "occurred_ts":(props.get("time") or 0)/1000.0,"lat":coords[1],"lon":coords[0],
                             "magnitude":props.get("mag"),"raw":feat}
                    await producer.send_and_wait(RAW_TOPIC, event_envelope("usgs_quakes", payload))
                    messages_out.labels(source="usgs_quakes").inc()
            except Exception:
                await asyncio.sleep(5)
            await asyncio.sleep(POLL_SECONDS)
async def main(): await run()
if __name__=="__main__": asyncio.run(main())
