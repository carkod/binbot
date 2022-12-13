import os


if os.getenv("ENV") != "ci":
    order_updates = OrderUpdates()
    # start a worker process to move the received stream_data from the stream_buffer to a print function
    worker_thread = threading.Thread(
        name="order_updates_thread", target=order_updates.run_stream
    )
    worker_thread.start()

    # Research market updates
    market_updates = MarketUpdates()
    market_updates_thread = threading.Thread(
        name="market_updates_thread", target=market_updates.start_stream
    )
    market_updates_thread.start()
    pass