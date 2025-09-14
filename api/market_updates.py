import json
import logging
import os
import time
import uuid
from confluent_kafka import Consumer, TopicPartition, OFFSET_END
from streaming.streaming_controller import (
    BbspreadsUpdater,
    StreamingController,
    BaseStreaming,
)
from tools.enum_definitions import KafkaTopics
from tools.logging_config import configure_logging


def main():
    configure_logging(force=True)
    consumer = Consumer(
        {
            "bootstrap.servers": f"{os.environ['KAFKA_HOST']}:{os.environ['KAFKA_PORT']}",
            "group.id": f"streaming-group-{uuid.uuid4()}",
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe(
        [
            KafkaTopics.klines_store_topic.value,
            KafkaTopics.restart_streaming.value,
        ]
    )

    # Ensure partition assignment then seek to the end (latest) for each
    partitions = []
    for _ in range(10):  # retry a few times to get assignment
        consumer.poll(0)
        partitions = consumer.assignment()
        if partitions:
            break
        time.sleep(0.1)
    if partitions:
        for p in partitions:
            # Use OFFSET_END so we only consume new messages arriving after startup
            tp = TopicPartition(p.topic, p.partition, OFFSET_END)
            try:
                consumer.seek(tp)
            except Exception as e:
                logging.warning(f"Seek failed for {tp}: {e}")

    bs = BaseStreaming()
    mu = StreamingController(bs, consumer)
    latest_restart_action = ""
    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            logging.error(f"Consumer error: {msg.error()}")
            continue
        topic = msg.topic()
        raw_value = msg.value()
        if raw_value is None:
            continue
        value = (
            raw_value.decode("utf-8")
            if isinstance(raw_value, (bytes, bytearray))
            else raw_value
        )
        if topic == KafkaTopics.restart_streaming.value:
            payload = json.loads(json.loads(value))
            if latest_restart_action != payload.get("action", None):
                bs.load_data_on_start()
                latest_restart_action = payload.get("action", None)
        elif topic == KafkaTopics.klines_store_topic.value:
            data = json.loads(value)
            mu.process_klines(data)
            BbspreadsUpdater(base=bs).dynamic_trailling(data)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logging.error(e)
            main()
