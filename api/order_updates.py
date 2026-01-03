import logging

from streaming.user_data_streaming import UserDataStreaming

try:
    mu = UserDataStreaming()
    mu.start()
except Exception as error:
    logging.error(f"User data streaming error: {error}")
    mu = UserDataStreaming()
    mu.start()
