"""Unsigned KuCoin Futures REST and Classic public execution WebSockets."""

import asyncio
from collections.abc import Callable
import json
import logging
import random
import time
from typing import Any
from urllib.parse import urlencode

import requests
from websockets.asyncio.client import connect

log = logging.getLogger(__name__)
REST = "https://api-futures.kucoin.com"
ACK_TIMEOUT = 10.0


def public_request(path: str, method: str = "GET") -> Any:
    response = requests.request(method, REST + path, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "200000":
        raise ValueError(f"KuCoin public request failed: {payload.get('code')}")
    return payload["data"]


async def stream_executions(
    symbols: list[str],
    stop: asyncio.Event,
    on_message: Callable[[dict, dict[str, tuple[str, float]], list[str]], None],
    on_disconnect: Callable[[list[str], float], None],
) -> None:
    """Stream Classic Futures executions with acknowledgements and gap callbacks.

    Callbacks run on the caller's event loop. on_message receives the pending
    subscription map and removes acknowledged IDs; on_disconnect receives the
    conservative start of the connection gap, including heartbeat detection lag.
    """
    failures = 0
    while not stop.is_set():
        healthy_since = time.monotonic()
        try:
            token = await asyncio.to_thread(
                public_request, "/api/v1/bullet-public", "POST"
            )
            server = token["instanceServers"][0]
            url = (
                server["endpoint"]
                + "?"
                + urlencode({"token": token["token"], "connectId": str(time.time_ns())})
            )
            interval = min(9.0, float(server["pingInterval"]) / 2000)
            timeout = float(server["pingTimeout"]) / 1000
            async with connect(
                url, ping_interval=None, max_queue=4096, open_timeout=20
            ) as ws:
                welcome = json.loads(await asyncio.wait_for(ws.recv(), 10))
                if welcome.get("type") != "welcome":
                    raise ValueError("Missing welcome")
                pending: dict[str, tuple[str, float]] = {}
                ping: dict[str, Any] = {"id": None, "sent": time.monotonic()}

                async def subscribe() -> None:
                    for symbol in symbols:
                        request_id = str(time.time_ns())
                        pending[request_id] = (symbol, time.monotonic())
                        await ws.send(
                            json.dumps(
                                {
                                    "id": request_id,
                                    "type": "subscribe",
                                    "topic": f"/contractMarket/execution:{symbol}",
                                    "response": True,
                                }
                            )
                        )
                        await asyncio.sleep(0.22)

                async def heartbeat() -> None:
                    while True:
                        now = time.monotonic()
                        if ping["id"] and now - ping["sent"] > timeout:
                            raise TimeoutError("KuCoin pong timeout")
                        if not ping["id"] and now - ping["sent"] >= interval:
                            ping.update(id=str(time.time_ns()), sent=now)
                            await ws.send(
                                json.dumps({"id": ping["id"], "type": "ping"})
                            )
                        if any(
                            now - sent > ACK_TIMEOUT for _, sent in pending.values()
                        ):
                            raise TimeoutError("Subscription acknowledgement timeout")
                        await asyncio.sleep(0.5)

                async def receive() -> None:
                    async for raw in ws:
                        message = json.loads(raw)
                        if (
                            message.get("type") == "pong"
                            and str(message.get("id")) == ping["id"]
                        ):
                            ping["id"] = None
                        on_message(message, pending, symbols)
                    raise ConnectionError("KuCoin stream closed")

                async with asyncio.timeout(23 * 3600):
                    async with asyncio.TaskGroup() as group:
                        group.create_task(subscribe())
                        group.create_task(heartbeat())
                        group.create_task(receive())
        except asyncio.CancelledError:
            raise
        except Exception as error:
            log.warning(
                "shard disconnected symbols=%s reason=%s",
                len(symbols),
                str(error),
                exc_info=True,
            )
        finally:
            on_disconnect(symbols, time.time() - 30)
        failures = 0 if time.monotonic() - healthy_since > 60 else min(failures + 1, 6)
        try:
            await asyncio.wait_for(
                stop.wait(), min(60, 2**failures) + random.uniform(0, 1)
            )
        except TimeoutError:
            pass
