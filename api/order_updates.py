import logging
from streaming.user_data_streaming import UserDataStreaming

try:
    mu = UserDataStreaming()
    mu.get_user_data()
except Exception as error:
    logging.error(f"User data streaming error: {error}")
    mu = UserDataStreaming()
    mu.get_user_data()
