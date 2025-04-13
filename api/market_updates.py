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
        bootstrap_servers=f'{os.environ["KAFKA_HOST"]}:{os.environ["KAFKA_PORT"]}',
        value_deserializer=lambda m: json.loads(m),
        api_version=(2, 5, 0),
    )
    mu = StreamingController(consumer)
    bbu = BbspreadsUpdater()
    while True:
        messages = consumer.poll(timeout_ms=1000)
        for topic_partition, message_batch in messages.items():
            for message in message_batch:
                if message.topic == KafkaTopics.klines_store_topic.value:
                    mu.process_klines(message.value)
                    bbu.dynamic_trailling(message.value)
                if message.topic == KafkaTopics.restart_streaming.value:
                    mu.load_data_on_start()


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logging.error(e)
            main()
