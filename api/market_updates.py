import json
import logging
import os
import time
from typing import Any

from kafka import KafkaConsumer
from streaming.streaming_controller import (
    BbspreadsUpdater,
    StreamingController,
    BaseStreaming,
)
from tools.enum_definitions import KafkaTopics

logging.basicConfig(
    level=os.environ["LOG_LEVEL"],
    filename=None,
    format="%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    consumer = KafkaConsumer(
        KafkaTopics.klines_store_topic.value,
        KafkaTopics.restart_streaming.value,
        bootstrap_servers=f"{os.environ['KAFKA_HOST']}:{os.environ['KAFKA_PORT']}",
        value_deserializer=lambda m: json.loads(m),
        group_id="streaming-group",
        api_version=(2, 5, 0),
    )
    bs = BaseStreaming()
    mu = StreamingController(bs, consumer)

    # --- Tick scheduler state (Option A) ---
    grace_seconds = int(os.environ.get("TICK_GRACE_SECONDS", "15"))
    last_tick_epoch = 0
    # Cache last message per symbol and idempotency tracking
    last_msg_by_symbol: dict[str, str | dict[str, Any]] = {}
    last_close_time_by_symbol: dict[str, int] = {}
    last_processed_close_time_by_symbol: dict[str, int] = {}

    def _coerce_to_dict(val: Any) -> dict[str, Any]:
        if isinstance(val, dict):
            return val
        try:
            return json.loads(val)
        except Exception:
            return {}

    def _coerce_to_json(val: Any) -> str:
        if isinstance(val, str):
            return val
        try:
            return json.dumps(val)
        except Exception:
            return "{}"

    def _now_sec() -> int:
        return int(time.time())

    def _aligned_5m(ts_sec: int) -> int:
        return (ts_sec // 300) * 300

    def _to_seconds(ts: Any) -> int:
        """Coerce ts (ms or sec, possibly string) into seconds as int."""
        try:
            if ts is None:
                return 0
            # Allow strings like "1691600000000" or "1691600000"
            if isinstance(ts, str):
                # Handle floats encoded as strings too
                ts = int(float(ts)) if ts else 0
            else:
                ts = int(ts)
        except (ValueError, TypeError):
            return 0
        # If looks like milliseconds, convert to seconds
        return ts // 1000 if ts > 10_000_000_000 else ts

    latest_restart_action = ""

    while True:
        # Tick scheduler: run once per 5m window with grace
        try:
            now = _now_sec()
            tick = _aligned_5m(now)
            if tick != last_tick_epoch and now >= tick + grace_seconds:
                for symbol, raw_msg in list(last_msg_by_symbol.items()):
                    payload = _coerce_to_dict(raw_msg)
                    close_time = _to_seconds(payload.get("close_time", 0))
                    # Process only if this symbol has a candle at/after this tick not yet processed
                    if close_time and close_time >= tick:
                        last_done = last_processed_close_time_by_symbol.get(symbol, 0)
                        if close_time > last_done:
                            serialized = _coerce_to_json(raw_msg)
                            try:
                                mu.process_klines(serialized)
                                BbspreadsUpdater(base=bs).dynamic_trailling(serialized)
                                last_processed_close_time_by_symbol[symbol] = int(
                                    payload.get("close_time", 0)
                                )
                                logging.debug(
                                    f"Tick-processed {symbol} at tick {tick} with close_time {payload.get('close_time')}"
                                )
                            except Exception as e:
                                logging.error(
                                    f"Tick processing error for {symbol}: {e}",
                                    exc_info=True,
                                )
                last_tick_epoch = tick
        except Exception as e:
            logging.error(f"Tick scheduler error: {e}", exc_info=True)

        # Normal Kafka polling/processing
        messages = consumer.poll(timeout_ms=1000)
        for topic_partition, message_batch in messages.items():
            for message in message_batch:
                if message.topic == KafkaTopics.restart_streaming.value:
                    payload = _coerce_to_dict(message.value)
                    action_raw = payload.get("action", "")
                    action_str = (
                        action_raw
                        if isinstance(action_raw, str)
                        else str(action_raw or "")
                    )
                    if latest_restart_action != action_str:
                        bs.load_data_on_start()
                        latest_restart_action = action_str

                if message.topic == KafkaTopics.klines_store_topic.value:
                    # Cache last candle per symbol for scheduler
                    msg_dict: dict[str, Any] | None = None
                    msg_symbol: str | None = None
                    try:
                        msg_dict = _coerce_to_dict(message.value)
                        msg_symbol = msg_dict.get("symbol")
                        if msg_symbol:
                            last_msg_by_symbol[msg_symbol] = message.value
                            last_close_time_by_symbol[msg_symbol] = int(
                                msg_dict.get("close_time", 0)
                            )
                    except Exception:
                        pass

                    # Immediate processing (kept for low latency); also idempotency mark
                    try:
                        serialized = _coerce_to_json(message.value)
                        mu.process_klines(serialized)
                        BbspreadsUpdater(base=bs).dynamic_trailling(serialized)
                        if msg_dict and msg_symbol:
                            last_processed_close_time_by_symbol[msg_symbol] = int(
                                msg_dict.get("close_time", 0)
                            )
                    except Exception as e:
                        logging.error(f"Realtime processing error: {e}", exc_info=True)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logging.error(e)
            main()
