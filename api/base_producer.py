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
            bootstrap_servers=f'{os.getenv("KAFKA_HOST", "localhost")}:{os.getenv("KAFKA_PORT", 9092)}',
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            api_version=(3, 4, 1),
        )
        return kafka_producer

    def close_producer(self, producer: KafkaProducer):
        producer.close()

    @staticmethod
    def update_required(producer: KafkaProducer, action: str):
        """
        Streaming controller requires reload.
        Use Kafka to send signals to Binquant to restart streams
        """

        value = {"type": "restart", "action": action}

        producer.send(
            KafkaTopics.restart_streaming.value, value=json.dumps(value), partition=0
        )

        return


class AsyncBaseProducer:
    def __init__(self):
        kafka_producer = KafkaProducer(
            bootstrap_servers=f'{os.getenv("KAFKA_HOST", "localhost")}:{os.getenv("KAFKA_PORT", 9092)}',
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            api_version=(3, 4, 1),
        )
        self.producer = kafka_producer

    async def create(self):
        """
        Kafka producer for sending restart messages to steaming.

        This means, messages can come from multiple places
        but only one is enough to restart the streaming.
        So acks config needs to make sure it is received
        and the message repitition doesn't matter, so consumer
        must start from latest offset always.
        """
        kafka_producer = KafkaProducer(
            bootstrap_servers=f'{os.getenv("KAFKA_HOST", "localhost")}:{os.getenv("KAFKA_PORT", 9092)}',
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            api_version=(3, 4, 1),
        )
        return kafka_producer

    def update_required(self, action: str):
        """
        Streaming controller requires reload.
        Use Kafka to send signals to Binquant to restart streams
        """

        value = {"type": "restart", "action": action}

        self.producer.send(
            KafkaTopics.restart_streaming.value, value=json.dumps(value), partition=0
        )
        self.producer.flush()
