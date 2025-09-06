import os, asyncio, time, orjson
from aiokafka import AIOKafkaProducer
from prometheus_client import start_http_server, Counter
messages_out = Counter("crisispulse_collector_messages_total","Messages published",["source"])
async def get_producer():
    producer = AIOKafkaProducer(bootstrap_servers=os.getenv("KAFKA_BROKERS","redpanda:9092"),
                                value_serializer=lambda v: orjson.dumps(v))
    for i in range(20):
        try:
            await producer.start(); return producer
        except Exception: await asyncio.sleep(0.5+i*0.2)
    raise RuntimeError("Kafka producer could not start")
def start_metrics_server(port:int=9100): start_http_server(port)
def event_envelope(source, payload): return {"source":source,"ingested_at":time.time(),"payload":payload}
