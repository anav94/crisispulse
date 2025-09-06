import os, asyncio, random, time, argparse
from .common import get_producer, event_envelope, messages_out

RAW_TOPIC = os.getenv("RAW_TOPIC", "raw_events")

WORDS = ["fire","flood","earthquake","landslide","storm","outage","accident","spill","eruption"]
PLACE_COORDS = {
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Seattle": (47.6062, -122.3321),
    "Tokyo": (35.6762, 139.6503),
    "Berlin": (52.5200, 13.4050),
    "San Francisco": (37.7749, -122.4194),
    "Sydney": (-33.8688, 151.2093),
    "London": (51.5074, -0.1278),
}

def jitter(lat, lon):
    return lat + random.uniform(-0.2, 0.2), lon + random.uniform(-0.2, 0.2)

async def generate(count=None, burst=False):
    producer = await get_producer()
    sent = 0
    places = list(PLACE_COORDS.keys())
    while True:
        if count and sent >= count: break
        word = random.choice(WORDS).title()
        place = random.choice(places)
        base_lat, base_lon = PLACE_COORDS[place]
        lat, lon = jitter(base_lat, base_lon)
        title = f"{word} near {place}"
        payload = {
            "source_id": f"syn-{int(time.time()*1000)}-{random.randint(0,9999)}",
            "title": title,
            "body": f"Reports of {word.lower()} near {place}",
            "occurred_ts": time.time(),
            "lat": lat, "lon": lon,
            "magnitude": round(max(0, random.gauss(3.0, 1.5)), 2)
        }
        env = event_envelope("synthetic", payload)
        await producer.send_and_wait(RAW_TOPIC, env)
        messages_out.labels(source="synthetic").inc()
        sent += 1
        await asyncio.sleep(0.2 if burst else 2.0)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=None)
    ap.add_argument("--burst", action="store_true")
    args = ap.parse_args()
    await generate(count=args.count, burst=args.burst)

if __name__ == "__main__":
    asyncio.run(main())
