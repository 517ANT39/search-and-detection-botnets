import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer

from .config import KAFKA_BOOTSTRAP, ALERTS_TOPIC
from .utils import manager, send_email_alert

log = logging.getLogger(__name__)


async def consume_alerts():
    """
    Читает traffics.alert и рассылает всем WebSocket-клиентам.
    Email отправляется только для severity=critical, чтобы не спамить.
    """
    consumer = AIOKafkaConsumer(
        ALERTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True,
        group_id="webapp-alert-relay",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            alert = msg.value
            # WebSocket — всем
            try:
                await manager.broadcast(json.dumps(alert, default=str))
            except Exception as e:
                log.warning(f"[ws] broadcast error: {e}")
            # Email — только critical
            # if alert.get("severity") == "critical":
            #     asyncio.create_task(send_email_alert(alert))
    finally:
        await consumer.stop()