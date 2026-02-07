import json
from confluent_kafka import Producer
from constants import CONFIG_PRODUCER

class ProducerIml(Producer):

    def produce(
        self,
        topic,
        value = None,
        key = None,
        partition = -1,
        callback = None,
        on_delivery = None,
        timestamp = 0,
        headers = None,
    ):
        super().produce(topic, json.dumps(value).encode("utf-8"), key, partition, callback, on_delivery, timestamp, headers)

producer = ProducerIml(CONFIG_PRODUCER)