import logging
import time

from streaming.streaming_controller import StreamingController

logging.Formatter.converter = time.gmtime  # date time in GMT/UTC
logging.basicConfig(
    level=logging.INFO,
    filename=None,
    format="%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

try:
    mu = StreamingController()
    mu.get_user_data()
except Exception as error:
    logging.error(f"User data streaming error: {error}")
    mu = StreamingController()
    mu.get_user_data()
