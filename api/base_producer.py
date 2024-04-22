import json
import os
from kafka import KafkaProducer

from tools.enum_definitions import KafkaTopics


class BaseProducer:
    def start_producer(self):
        kafka_producer = KafkaProducer(
            bootstrap_servers=f'{os.environ["KAFKA_HOST"]}:{os.environ["KAFKA_PORT"]}',
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks=1,
        )
        return kafka_producer

    def close_producer(self, producer: KafkaProducer):
        producer.close()

    @classmethod
    def update_required(cls, botId: str, action: str):
        """
        Streaming controller requires reload.
        Use Kafka to send signals to Binquant to restart streams
        """

        value = {"botId": botId, "action": action}

        cls.producer.send(KafkaTopics.restart_streaming.value, value=json.dumps(value))

        return
