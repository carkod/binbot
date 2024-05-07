import logging
import os

from confluent_kafka import Consumer, KafkaException, KafkaError
from streaming.streaming_controller import StreamingController
from tools.enum_definitions import KafkaTopics

def main():
    consumer = Consumer({
        "bootstrap.servers": f'{os.environ["CONFLUENT_GCP_BOOTSTRAP_SERVER"]}:{os.environ["KAFKA_PORT"]}',
        'sasl.mechanism': 'PLAIN',
        'security.protocol': 'SASL_SSL',
        'sasl.username': os.environ["CONFLUENT_API_KEY"],
        'sasl.password': os.environ["CONFLUENT_API_SECRET"],
        "group.id": "market-updates-consumer",
    })
    consumer.subscribe([KafkaTopics.klines_store_topic.value,
        KafkaTopics.restart_streaming.value])

    mu = StreamingController(consumer)
    while True:
        try:
            message = consumer.poll(1)
            if message is None: continue
            if message.error():
                if message.error().code() == KafkaError._TIMEOUT:
                    consumer.flush()
                else:
                    raise KafkaException(message.error())
            else:
                topic = message.topic()
                if topic == KafkaTopics.restart_streaming.value:
                    mu.load_data_on_start()
                if topic == KafkaTopics.klines_store_topic.value:
                    mu.process_klines(message.value())
        except Exception as error:
            main()
        finally:
            consumer.close()

if __name__ == "__main__":
    main()