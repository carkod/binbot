import json
import logging
import os

from kafka import KafkaConsumer
from streaming.streaming_controller import BbspreadsUpdater, StreamingController
from tools.enum_definitions import KafkaTopics

logging.basicConfig(
    level=logging.INFO,
    filename=None,
    format="%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    consumer = KafkaConsumer(
        KafkaTopics.klines_store_topic.value,
        KafkaTopics.restart_streaming.value,
        KafkaTopics.signals.value,
        bootstrap_servers=f'{os.environ["KAFKA_HOST"]}:{os.environ["KAFKA_PORT"]}',
        value_deserializer=lambda m: json.loads(m),
    )
    mu = StreamingController(consumer)
    bbu = BbspreadsUpdater()
    for message in consumer:
        if message.topic == KafkaTopics.klines_store_topic.value:
            mu.process_klines(message.value)
        if message.topic == KafkaTopics.signals.value:
            bbu.update_close_conditions(message.value)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logging.error(e)
            main()
