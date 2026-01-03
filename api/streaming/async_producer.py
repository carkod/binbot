from __future__ import annotations

import json
import logging
import os
from typing import Any

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class AsyncProducer:
    """Async Kafka Producer with low-latency tuning.

    Hardcoded configuration applied at start(); no __init__, no env overrides.
    """

    linger_ms: int = 5
    acks: str | int = 1
    max_in_flight: int = 5
    request_timeout_ms: int = 15000

    async def start(self) -> None:
        self.linger_ms = 5
        self.acks = 1  # use 'all' for durability
        self.max_in_flight = 5
        self.request_timeout_ms = 15000
        self.producer = AIOKafkaProducer(
            bootstrap_servers=f"{os.getenv('KAFKA_HOST', 'localhost')}:{os.getenv('KAFKA_PORT', 29092)}",
            linger_ms=self.linger_ms,
            acks=self.acks,
            max_in_flight_requests_per_connection=self.max_in_flight,
            enable_idempotence=False,
            request_timeout_ms=self.request_timeout_ms,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            max_batch_size=8192,
            compression_type=None,
            retry_backoff_ms=100,
            partitioner="murmur2",
        )
        await self.producer.start()
        return self.producer

    async def send(
        self,
        topic: str,
        value: Any,
        key: Any | None = None,
        partition: int | None = None,
    ) -> None:
        await self.producer.send_and_wait(
            topic=topic,
            value=value,
            key=None if key is None else json.dumps(key).encode("utf-8"),
            partition=partition,
        )
        return self.producer

    async def stop(self) -> None:
        try:
            await self.producer.stop()
            return self.producer
        finally:
            logger.info("AsyncLowLatencyProducer stopped")
            self.producer = None
