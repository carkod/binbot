from __future__ import annotations
from typing import Callable, Optional, Sequence
from streaming.socket_manager import AsyncBinanceWebsocketClient


class AsyncSpotWebsocketStreamClient(AsyncBinanceWebsocketClient):
    def __init__(
        self,
        stream_url: str = "wss://stream.binance.com:443",
        on_message: Optional[Callable] = None,
        on_open: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_ping: Optional[Callable] = None,
        on_pong: Optional[Callable] = None,
        is_combined: bool = False,
        **kwargs,
    ) -> None:
        base = stream_url.rstrip("/")
        suffix = "/stream" if is_combined else "/ws"
        super().__init__(
            stream_url=f"{base}{suffix}",
            on_message=on_message,
            on_open=on_open,
            on_close=on_close,
            on_error=on_error,
            on_ping=on_ping,
            on_pong=on_pong,
            **kwargs,
        )

    async def klines(
        self,
        markets: Sequence[str],
        interval: str,
        id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> None:
        """Subscribe/unsubscribe to kline streams.

        Each market produces a stream name: <symbol>@kline_<interval>
        If markets empty, a dummy market is added to keep stream active.
        """
        streams = []
        if not markets:
            markets = ["BNBBTC"]
        for m in markets:
            streams.append(f"{m.lower()}@kline_{interval}")
        await self.send_message_to_server(streams, action=action, id=id)

    async def user_data(
        self,
        listen_key: str,
        id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> None:
        """Stream user data using provided listen key."""
        await self.send_message_to_server(listen_key, action=action, id=id)
