import json

from confluent_kafka import Producer
from constants import CONFIG_PRODUCER

producer = Producer(CONFIG_PRODUCER)

def send_data(topic, data,key=None):
    producer.produce(topic, key=key, value=json.dumps(data).encode('utf-8'))
    producer.flush()