import json
import logging
from aiokafka import AIOKafkaConsumer
from .config import KAFKA_BOOTSTRAP, ALERTS_TOPIC, HOST_TOPIC
from .db import db
from .utils import manager, send_email_alert

logger = logging.getLogger(__name__)

async def consume_alerts():
    consumer = AIOKafkaConsumer(
        ALERTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="alert_processor",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            alert = msg.value
            logger.info(f"Received alert: {alert}")
            try:
                # Преобразуем window_start в timestamp, если нужно
                if "window_start" in alert and "timestamp" not in alert:
                    alert["timestamp"] = alert["window_start"]
                await db.insert_alert(alert)
                # await send_email_alert(alert)
                await manager.broadcast(json.dumps(alert))
            except Exception as e:
                logger.error(f"Error processing alert: {e}")
    finally:
        await consumer.stop()

async def consume_host_info():
    # Предполагаем, что в топик приходят JSON-сериализованные данные (или Protobuf – нужно адаптировать)
    consumer = AIOKafkaConsumer(
        HOST_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="host_processor",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            host_data = msg.value
            # Преобразуем boot_time_sec и register_ts в секундах в datetime для ClickHouse
            # Но в ClickHouse мы храним DateTime, поэтому передаём как есть (число) — адаптер aiochclient сам преобразует?
            # Для безопасности, преобразуем в datetime в Python:
            from datetime import datetime
            if "boot_time_sec" in host_data:
                host_data["boot_time_sec"] = datetime.fromtimestamp(host_data["boot_time_sec"])
            if "register_ts" in host_data:
                host_data["register_ts"] = datetime.fromtimestamp(host_data["register_ts"])
            await db.insert_host(host_data)
            logger.info(f"Host info saved: {host_data['host_id']}")
    finally:
        await consumer.stop()