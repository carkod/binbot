import logging
import time

from streaming.user_data_streaming import UserDataStreaming

logging.Formatter.converter = time.gmtime  # date time in GMT/UTC
logging.basicConfig(
    level=logging.INFO,
    filename=None,
    format="%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

try:
    mu = UserDataStreaming()
    mu.get_user_data()
except Exception as error:
    logging.error(f"User data streaming error: {error}")
    mu = UserDataStreaming()
    mu.get_user_data()
