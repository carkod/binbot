from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import websockets
from websockets import client
from websockets.exceptions import ConnectionClosed as _ConnectionClosed
from websockets.legacy.client import WebSocketClientProtocol

Callback = Callable[..., Awaitable[None] | None]


class AsyncBinanceWebsocketClient:
    """Async Binance WebSocket client.

    Methods mirror the Binance API subscription protocol. All network operations
    are async; callbacks may be sync or async callables with signature:
        callback(client, *args)
    """

    ACTION_SUBSCRIBE = "SUBSCRIBE"
    ACTION_UNSUBSCRIBE = "UNSUBSCRIBE"

    def __init__(
        self,
        stream_url: str,
        on_message: Callback | None = None,
        on_open: Callback | None = None,
        on_close: Callback | None = None,
        on_error: Callback | None = None,
        on_ping: Callback | None = None,
        on_pong: Callback | None = None,
        logger: logging.Logger | None = None,
        auto_reconnect: bool = True,
        reconnect_delay: float = 3.0,
        ping_interval: float | None = None,
        ping_timeout: float | None = None,  # <-- new param
    ) -> None:
        self.stream_url = stream_url
        self.on_message = on_message
        self.on_open = on_open
        self.on_close = on_close
        self.on_error = on_error
        self.on_ping = on_ping
        self.on_pong = on_pong
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout  # <-- store it
        self.logger = logger or logging.getLogger(__name__)

        self._websocket: WebSocketClientProtocol | None = None
        self._listen_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._stopping = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    async def connect(self) -> None:
        """Open the websocket connection and start listener tasks."""
        self.logger.debug("Connecting to Binance WS: %s", self.stream_url)
        try:
            connect_fn = getattr(websockets, "connect", None) or getattr(
                client, "connect", None
            )
            if not connect_fn:  # pragma: no cover
                raise RuntimeError(
                    "websockets.connect not available in this installation"
                )
            # IMPORTANT: pass the configured ping settings to websockets.connect
            self._websocket = await connect_fn(
                self.stream_url,
                # allow using built-in pings when ping_interval is set
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
            )
        except Exception as e:  # pragma: no cover - network dependent
            await self._safe_callback(self.on_error, e)
            raise
        await self._safe_callback(self.on_open)
        # reset stopping flag on successful connect
        self._stopping = False
        self._listen_task = asyncio.create_task(self._listen_loop())
        if self.ping_interval:
            # keep the manual ping loop option if you also want application-level pings
            self._ping_task = asyncio.create_task(self._ping_loop())

    async def _ping_loop(self) -> None:
        assert self.ping_interval is not None
        while not self._stopping and self.is_connected:
            try:
                await asyncio.sleep(self.ping_interval)
                await self.ping()
            except Exception as e:  # pragma: no cover
                self.logger.warning("Ping loop error: %s", e)
                await self._safe_callback(self.on_error, e)
                break

    async def _listen_loop(self) -> None:
        ws = self._websocket
        assert ws is not None
        while not self._stopping and ws and not ws.closed:
            try:
                msg = await ws.recv()
            except _ConnectionClosed as e:
                self.logger.info(
                    "WebSocket closed: code=%s reason=%s",
                    getattr(e, "code", "?"),
                    getattr(e, "reason", "?"),
                )
                await self._safe_callback(self.on_close)
                if self.auto_reconnect and not self._stopping:
                    await self._attempt_reconnect()
                return
            except Exception as e:  # pragma: no cover
                self.logger.error("Receive error: %s", e)
                await self._safe_callback(self.on_error, e)
                if self.auto_reconnect and not self._stopping:
                    await self._attempt_reconnect()
                return
            else:
                # --- NEW: handle Binance text/JSON pings here ---
                # msg may be str or bytes; handle only text forms
                try:
                    if isinstance(msg, (bytes, bytearray)):
                        # leave binary messages to on_message
                        await self._safe_callback(self.on_message, msg)
                        continue
                    # quick raw checks
                    if msg == "ping":
                        # reply with exactly "pong"
                        await self.send_raw("pong")
                        continue
                    # try to parse JSON and respond to {"ping": <num>}
                    try:
                        obj = json.loads(msg)
                    except Exception:
                        obj = None
                    if isinstance(obj, dict) and "ping" in obj:
                        # reply with matching pong payload if present
                        try:
                            pong_payload = {"pong": obj.get("ping")}
                            await self.send_raw(json.dumps(pong_payload))
                        except Exception:
                            # fall back to plain pong if anything fails
                            await self.send_raw("pong")
                        continue
                    # otherwise forward to on_message
                    await self._safe_callback(self.on_message, msg)
                except Exception as cb_exc:
                    # make sure a callback error doesn't stop the loop
                    self.logger.exception(
                        "Error while handling incoming message: %s", cb_exc
                    )
                    await self._safe_callback(self.on_error, cb_exc)

        # Normal exit (only reached if loop condition ends)
        await self._safe_callback(self.on_close)

    async def _attempt_reconnect(self) -> None:
        self.logger.warning("Attempting reconnect in %.1fs", self.reconnect_delay)
        await asyncio.sleep(self.reconnect_delay)
        if self._stopping:
            return
        try:
            await self.connect()
        except Exception as e:  # pragma: no cover
            self.logger.error("Reconnect failed: %s", e)
            await self._safe_callback(self.on_error, e)

    @property
    def is_connected(self) -> bool:
        return self._websocket is not None and not self._websocket.closed

    async def stop(self) -> None:
        """Stop listener tasks and close connection."""
        self._stopping = True
        tasks = [t for t in (self._listen_task, self._ping_task) if t]
        for t in tasks:
            t.cancel()
        for t in tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
        if self._websocket and not self._websocket.closed:
            await self._websocket.close()
        self._websocket = None
        await self._safe_callback(self.on_close)

    # ------------------------------------------------------------------
    # Binance protocol helpers
    # ------------------------------------------------------------------
    def get_timestamp(self) -> int:
        return int(time.time() * 1000)

    async def send_raw(self, message: str) -> None:
        if not self.is_connected:
            raise RuntimeError("WebSocket not connected")
        async with self._lock:
            assert self._websocket is not None
            await self._websocket.send(message)
        self.logger.debug("Sent raw: %s", message)

    async def send_json(self, payload: dict) -> None:
        await self.send_raw(json.dumps(payload))

    async def subscribe(self, streams: Sequence[str], id: int | None = None) -> None:
        if id is None:
            id = self.get_timestamp()
        await self.send_json(
            {"method": self.ACTION_SUBSCRIBE, "params": list(streams), "id": id}
        )

    async def unsubscribe(self, streams: Sequence[str], id: int | None = None) -> None:
        if id is None:
            id = self.get_timestamp()
        await self.send_json(
            {"method": self.ACTION_UNSUBSCRIBE, "params": list(streams), "id": id}
        )

    async def list_subscriptions(self, id: int | None = None) -> None:
        if id is None:
            id = self.get_timestamp()
        await self.send_json({"method": "LIST_SUBSCRIPTIONS", "id": id})

    async def send_message_to_server(
        self,
        message: str | Sequence[str],
        action: str | None = None,
        id: int | None = None,
    ) -> None:
        if isinstance(message, str):
            streams = [message]
        else:
            streams = list(message)
        if action == self.ACTION_UNSUBSCRIBE:
            await self.unsubscribe(streams, id=id)
        else:
            await self.subscribe(streams, id=id)

    async def ping(self) -> None:
        if not self.is_connected:
            raise RuntimeError("WebSocket not connected")
        assert self._websocket is not None
        await self._websocket.ping()
        await self._safe_callback(self.on_ping)

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    async def _safe_callback(self, callback: Callback | None, *args: Any) -> None:
        if not callback:
            return
        try:
            result = callback(self, *args)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:  # pragma: no cover
            self.logger.error(
                "Callback error in %s: %s", getattr(callback, "__name__", callback), e
            )
            if callback is not self.on_error and self.on_error:
                try:
                    err_result = self.on_error(self, e)
                    if asyncio.iscoroutine(err_result):
                        await err_result
                except Exception:
                    pass
