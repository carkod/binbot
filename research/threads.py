import threading
from api.research.market_updates import MarketUpdates


def market_update_thread():
    market_data_updates = MarketUpdates()
    market_updates_thread = threading.Thread(
        name="market_updates_thread", target=market_data_updates.start_stream
    )
    market_updates_thread.start()
