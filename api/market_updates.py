import json
import logging
import os

from kafka import KafkaConsumer
from streaming.streaming_controller import StreamingController
from tools.enum_definitions import KafkaTopics

def main():
    consumer = KafkaConsumer(
        KafkaTopics.klines_store_topic.value,
        KafkaTopics.restart_streaming.value,
        bootstrap_servers=f'{os.environ["KAFKA_HOST"]}:{os.environ["KAFKA_PORT"]}',
        value_deserializer=lambda m: json.loads(m),
        auto_offset_reset="latest",
        enable_auto_commit=True,
    )
    mu = StreamingController(consumer)
    for message in consumer:
        if message.topic == KafkaTopics.restart_streaming.value:
            mu.load_data_on_start()
        if message.topic == KafkaTopics.klines_store_topic.value:
            mu.process_klines(message.value)

       
if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logging.error(e)
            main()