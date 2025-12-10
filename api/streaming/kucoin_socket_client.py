from __future__ import annotations
from typing import Callable, Optional, Sequence
from streaming.socket_manager import AsyncBinanceWebsocketClient
import requests


class AsyncKucoinWebsocketStreamClient(AsyncBinanceWebsocketClient):
    """
    Kucoin WebSocket client for market data streaming.

    Kucoin uses a different connection model than Binance:
    1. First, obtain connection details via REST API
    2. Connect to the websocket with token
    3. Subscribe to channels
    """

    def __init__(
        self,
        stream_url: str = None,  # Will be obtained from API
        on_message: Optional[Callable] = None,
        on_open: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_ping: Optional[Callable] = None,
        on_pong: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        # Get Kucoin websocket connection details
        if stream_url is None:
            stream_url = self._get_kucoin_ws_url()

        super().__init__(
            stream_url=stream_url,
            on_message=on_message,
            on_open=on_open,
            on_close=on_close,
            on_error=on_error,
            on_ping=on_ping,
            on_pong=on_pong,
            **kwargs,
        )
        self._connection_id: Optional[str] = None

    def _get_kucoin_ws_url(self) -> str:
        """
        Get Kucoin websocket connection details from REST API.
        Returns the websocket URL with token.
        """
        try:
            # Public websocket endpoint (no authentication needed for market data)
            response = requests.post(
                "https://api.kucoin.com/api/v1/bullet-public", timeout=10
            )
            data = response.json()

            if data.get("code") == "200000" and data.get("data"):
                token = data["data"]["token"]
                endpoint = data["data"]["instanceServers"][0]["endpoint"]
                # Connection ID for identifying this connection
                self._connection_id = f"id_{self.get_timestamp()}"
                return f"{endpoint}?token={token}&connectId={self._connection_id}"
            else:
                # Fallback to default endpoint
                return "wss://ws-api-spot.kucoin.com"
        except Exception:
            # Fallback to default endpoint if API call fails
            return "wss://ws-api-spot.kucoin.com"

    async def klines(
        self,
        markets: Sequence[str],
        interval: str,
        id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> None:
        """
        Subscribe/unsubscribe to Kucoin kline (candle) streams.

        Kucoin uses a different format:
        - Topic: /market/candles:{symbol}_{interval}
        - Example: /market/candles:BTC-USDT_15min

        Args:
            markets: List of trading pairs (e.g., ["BTC-USDT", "ETH-USDT"])
            interval: Kline interval (e.g., "15min", "1hour", "1day")
            id: Optional message ID
            action: "SUBSCRIBE" or "UNSUBSCRIBE" (mapped to subscribe/unsubscribe)
        """
        if id is None:
            id = self.get_timestamp()

        # Build Kucoin topic list
        topics = []
        if not markets:
            markets = ["BTC-USDT"]  # Default pair

        for market in markets:
            # Kucoin format: /market/candles:SYMBOL_INTERVAL
            topic = f"/market/candles:{market}_{interval}"
            topics.append(topic)

        # Kucoin subscription format
        if action == self.ACTION_UNSUBSCRIBE:
            message = {
                "id": str(id),
                "type": "unsubscribe",
                "topic": ",".join(topics),
                "response": True,
            }
        else:
            message = {
                "id": str(id),
                "type": "subscribe",
                "topic": ",".join(topics),
                "response": True,
            }

        await self.send_json(message)

    async def user_data(
        self,
        listen_key: str,
        id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> None:
        """
        Stream user data using provided listen key.
        Note: Kucoin user data streaming may require different implementation.
        """
        # Kucoin private channels require authentication
        # This is a placeholder - implement when needed
        pass
