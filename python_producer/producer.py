
import json
import time
import random
from confluent_kafka import Producer

p = Producer({
    "bootstrap.servers": "kafka-broker-0.kafka-broker-service:19092",
    "enable.idempotence": True,
    "acks": "all",
})

def on_delivery(err, msg):
    if err:
        print(f"❌ Delivery failed: {err}")
    else:
        print(f"✅ Delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

try:
    while True:
      order = {
        "order_id": f"o-{int(time.time())}",
        "amount": round(random.uniform(5.0, 100.0), 2)
      }
      print("sent order:", order)
      p.produce(
              topic="demo",
      #         key=order["order_id"],
              value=json.dumps(order).encode(),
              callback=on_delivery
          )
      p.poll(0)
      time.sleep(1)

except KeyboardInterrupt:
    print("Stopping producer...")
finally:
    p.flush()