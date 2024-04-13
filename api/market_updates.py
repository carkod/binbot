import asyncio
import json
import logging
import os

from streaming.streaming_controller import StreamingController
from aiokafka import AIOKafkaConsumer
from tools.enum_definitions import KafkaTopics

async def main():
    try:
        consumer = AIOKafkaConsumer(
            KafkaTopics.klines_store_topic.value,
            KafkaTopics.restart_streaming.value,
            bootstrap_servers=f'{os.environ["KAFKA_HOST"]}:{os.environ["KAFKA_PORT"]}',
            group_id="restart_streaming",
            value_deserializer=lambda m: json.loads(m),
        )
        await consumer.start()
        mu = StreamingController(consumer)
        async for result in consumer:
            if result.topic == KafkaTopics.klines_store_topic.value:
                mu.process_klines(result.value)
            if result.topic == KafkaTopics.restart_streaming.value:
                mu.load_data_on_start()

    except Exception as error:
        logging.error(f"Streaming controller error: {error}")
        await main()

if __name__ == "__main__":
    asyncio.run(main())