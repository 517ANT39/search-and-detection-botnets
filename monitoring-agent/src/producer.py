import json
from kafka import KafkaProducer
from constants import KAFKA_SERVERS

producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    compression_type='gzip',
)

def send_data(topic, data,key=None):
    future = producer.send(topic, key=key, value=data)
    future.get(timeout=10)