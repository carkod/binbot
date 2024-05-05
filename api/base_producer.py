from datetime import datetime
import json
import os
from confluent_kafka import Producer

from tools.round_numbers import round_numbers_ceiling
from tools.enum_definitions import KafkaTopics

class BaseProducer:
    def __init__(self):
        super().__init__()

    def start_producer(self):
        self.producer = Producer({
            "bootstrap.servers": f'{os.environ["CONFLUENT_GCP_BOOTSTRAP_SERVER"]}:{os.environ["KAFKA_PORT"]}',
            'sasl.mechanism': 'PLAIN',
            'security.protocol': 'SASL_SSL',
            'sasl.username': os.environ["CONFLUENT_API_KEY"],
            'sasl.password': os.environ["CONFLUENT_API_SECRET"],
        })
        return self.producer

    def on_send_success(self, record_metadata):
        timestamp = int(round_numbers_ceiling(record_metadata.timestamp / 1000, 0))
        print(
            f"{datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')} Produced: {record_metadata.topic}, {record_metadata.offset}"
        )

    def on_send_error(self, excp):
        print(f"Message production failed to send: {excp}")

    @staticmethod
    def update_required(producer: Producer, botId: str, action: str):
        """
        Streaming controller requires reload.
        Use Kafka to send signals to Binquant to restart streams
        """

        value = {"type": "restart", "botId": botId, "action": action}

        producer.produce(KafkaTopics.restart_streaming.value, value=json.dumps(value))

        return
