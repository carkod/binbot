import json
import os
from kafka import KafkaProducer

from tools.enum_definitions import KafkaTopics


class BaseProducer:
    def start_producer(self):
        """
        Kafka producer for sending restart messages to steaming.

        This means, messages can come from multiple places
        but only one is enough to restart the streaming.
        So acks config needs to make sure it is received
        and the message repitition doesn't matter, so consumer
        must start from latest offset always.
        """
        kafka_producer = KafkaProducer(
            bootstrap_servers=f'{os.environ["KAFKA_HOST"]}:{os.environ["KAFKA_PORT"]}',
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
        )
        return kafka_producer

    def close_producer(self, producer: KafkaProducer):
        producer.close()

    @staticmethod
    def update_required(producer: KafkaProducer, botId: str, action: str):
        """
        Streaming controller requires reload.
        Use Kafka to send signals to Binquant to restart streams
        """

        value = {"type": "restart", "botId": botId, "action": action}

        producer.send(KafkaTopics.restart_streaming.value, value=json.dumps(value), partition=0)

        return
