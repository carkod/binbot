from streaming.socket_manager import BinanceWebsocketClient

class SpotWebsocketStreamClient(BinanceWebsocketClient):
    ACTION_SUBSCRIBE = "SUBSCRIBE"
    ACTION_UNSUBSCRIBE = "UNSUBSCRIBE"

    def __init__(
        self,
        stream_url="wss://stream.binance.com:443",
        on_message=None,
        on_open=None,
        on_close=None,
        on_error=None,
        on_ping=None,
        on_pong=None,
        is_combined=False,
    ):
        if is_combined:
            stream_url = stream_url + "/stream"
        else:
            stream_url = stream_url + "/ws"
        super().__init__(
            stream_url,
            on_message=on_message,
            on_open=on_open,
            on_close=on_close,
            on_error=on_error,
            on_ping=on_ping,
            on_pong=on_pong,
        )

    def klines(self, markets: list, interval: str, id=None, action=None):
        """Kline/Candlestick Streams
        The Kline/Candlestick Stream push updates to the current klines/candlestick every second.
        Stream Name: <symbol>@kline_<interval>
        interval:
        m -> minutes; h -> hours; d -> days; w -> weeks; M -> months
        - 1m
        - 3m
        - 5m
        - 15m
        - 30m
        - 1h
        - 2h
        - 4h
        - 6h
        - 8h
        - 12h
        - 1d
        - 3d
        - 1w
        - 1M
        Update Speed: 2000ms
        """
        params = []
        if len(markets) == 0:
            # Listen to dummy stream to always trigger streaming
            markets.append("BNBBTC")
        for market in markets:
            params.append(f"{market.lower()}@kline_{interval}")

        self.send_message_to_server(params, action=action, id=id)
