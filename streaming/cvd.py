"""Public KuCoin Futures collector hosted by streaming.main; one owner per DB."""

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
import math
import random
import signal
import time
from typing import Any
from urllib.parse import urlencode

import requests
from sqlmodel import col
from pybinbot import ExchangeId
from sqlalchemy import Connection, Table, delete, select, text
from sqlalchemy.dialects.postgresql import insert
from websockets.asyncio.client import connect

from api.databases.tables.cvd_table import SOURCE, CvdBucketTable, CvdMinuteTable
from api.databases.tables.symbol_exchange_table import SymbolExchangeTable
from api.databases.tables.symbol_table import SymbolTable
from api.databases.utils import engine

log = logging.getLogger("cvd")
REST = "https://api-futures.kucoin.com"
SHARD_SIZE = 100  # Operational choice; Classic Futures currently has no topic cap.
LATE_SECONDS = 120
ACK_TIMEOUT = 10.0
LOCK_ID = 731840217


def public_request(path: str, method: str = "GET") -> Any:
    response = requests.request(method, REST + path, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "200000":
        raise ValueError(f"KuCoin public request failed: {payload.get('code')}")
    return payload["data"]


def discover_contracts(contracts: list[dict], registered: set[str]) -> dict[str, float]:
    result = {}
    for contract in contracts:
        if (
            contract.get("symbol") not in registered
            or contract.get("status") != "Open"
            or contract.get("settleCurrency") != "USDT"
            or contract.get("isInverse") is not False
        ):
            continue
        multiplier = float(contract["multiplier"])
        if not math.isfinite(multiplier) or multiplier <= 0:
            raise ValueError("Invalid contract multiplier")
        result[contract["symbol"]] = multiplier
    return result


def load_contracts() -> dict[str, float]:
    with engine.connect() as connection:
        registered = set(
            connection.execute(
                select(col(SymbolExchangeTable.symbol_id))
                .join(
                    SymbolTable,
                    col(SymbolTable.id) == col(SymbolExchangeTable.symbol_id),
                )
                .where(
                    col(SymbolExchangeTable.exchange_id) == ExchangeId.KUCOIN,
                    col(SymbolTable.active).is_(True),
                )
            ).scalars()
        )
    return discover_contracts(public_request("/api/v1/contracts/active"), registered)


@dataclass
class Bucket:
    multiplier: float
    buy: float = 0
    sell: float = 0
    covered: bool = False
    last_trade_ns: int = 0


@dataclass
class Minute:
    symbols: dict[str, Bucket]
    universe: str


@dataclass
class Flow:
    contracts: dict[str, float]
    started_ns: int
    minutes: dict[int, Minute] = field(default_factory=dict)
    acknowledged: dict[str, float] = field(default_factory=dict)
    seen: dict[int, set[tuple[str, str, str]]] = field(
        default_factory=lambda: defaultdict(set)
    )
    rejected: int = 0
    trades: int = 0
    last_trade_ns: int = 0
    last_tick: float = 0
    replay_cutoffs: dict[str, int] = field(default_factory=dict)

    def ensure_minute(self, minute: int) -> None:
        if minute not in self.minutes:
            universe = sha256(
                json.dumps(sorted(self.contracts.items())).encode()
            ).hexdigest()
            self.minutes[minute] = Minute(
                {
                    symbol: Bucket(
                        multiplier,
                        covered=self.acknowledged.get(symbol, math.inf) <= minute,
                    )
                    for symbol, multiplier in self.contracts.items()
                },
                universe,
            )

    def tick(self, now: float) -> None:
        minute = int(now) // 60 * 60
        first = max(
            self.started_ns // 60_000_000_000 * 60, int(self.last_tick) // 60 * 60
        )
        for timestamp in range(first, minute + 1, 60):
            self.ensure_minute(timestamp)
        if self.last_tick and now - self.last_tick > 20:
            self.invalidate_coverage(list(self.contracts), self.last_tick)
            for symbol in self.acknowledged:
                self.acknowledged[symbol] = now
        self.last_tick = now

    def disconnect(self, symbols: list[str], since: float) -> None:
        for symbol in symbols:
            self.acknowledged.pop(symbol, None)
        self.invalidate_coverage(symbols, since)

    def invalidate_coverage(self, symbols: list[str], since: float) -> None:
        for minute, state in self.minutes.items():
            if minute + 60 > since:
                for symbol in symbols:
                    if symbol in state.symbols:
                        state.symbols[symbol].covered = False

    def trade(self, payload: dict, now: float) -> bool:
        """Use exchange taker side and ns timestamp. No price-direction inference."""
        self.tick(now)
        try:
            symbol, trade_id = payload["symbol"], payload["tradeId"]
            side = payload["side"]
            timestamp_ns = int(payload["ts"])
            price, contracts = float(payload["price"]), float(payload["size"])
            if (
                not isinstance(symbol, str)
                or not isinstance(trade_id, (str, int))
                or not str(trade_id)
                or side not in ("buy", "sell")
                or timestamp_ns < self.started_ns
                or timestamp_ns <= self.replay_cutoffs.get(symbol, 0)
                or timestamp_ns > int((now + 5) * 1e9)
                or timestamp_ns < int((now - LATE_SECONDS) * 1e9)
                or not math.isfinite(price)
                or not math.isfinite(contracts)
                or price <= 0
                or contracts <= 0
                or not contracts.is_integer()
            ):
                raise ValueError("Invalid or out-of-window execution")
            minute = timestamp_ns // 60_000_000_000 * 60
            self.ensure_minute(minute)
            bucket = self.minutes[minute].symbols[symbol]
            key = (SOURCE, symbol, str(trade_id))
            if any(key in keys for keys in self.seen.values()):
                return False
            notional = price * contracts * bucket.multiplier
            if not math.isfinite(notional):
                raise ValueError("Invalid notional")
        except KeyError, TypeError, ValueError, OverflowError:
            self.rejected += 1
            return False
        # Bounded by three exchange minutes plus a hard fail-closed safety cap.
        if sum(map(len, self.seen.values())) >= 2_000_000:
            self.rejected += 1
            return False
        self.seen[minute].add(key)
        if side == "buy":
            bucket.buy += notional
        else:
            bucket.sell += notional
        bucket.last_trade_ns = max(bucket.last_trade_ns, timestamp_ns)
        self.last_trade_ns = max(self.last_trade_ns, timestamp_ns)
        self.trades += 1
        return True

    def snapshot(self, now: float) -> tuple[list[dict], list[dict]]:
        buckets, minutes = [], []
        for minute, state in self.minutes.items():
            for symbol, bucket in state.symbols.items():
                buckets.append(
                    {
                        "source": SOURCE,
                        "symbol": symbol,
                        "minute": minute,
                        "buy": bucket.buy,
                        "sell": bucket.sell,
                        "multiplier": bucket.multiplier,
                        "covered": bucket.covered,
                        "last_trade_ns": bucket.last_trade_ns,
                    }
                )
            minutes.append(
                {
                    "source": SOURCE,
                    "minute": minute,
                    "buy": sum(b.buy for b in state.symbols.values()),
                    "sell": sum(b.sell for b in state.symbols.values()),
                    "expected_symbols": len(state.symbols),
                    "covered_symbols": sum(b.covered for b in state.symbols.values()),
                    "universe": state.universe,
                    "finalized": now >= minute + 60 + LATE_SECONDS,
                    "updated_at": datetime.fromtimestamp(now, timezone.utc),
                }
            )
        return buckets, minutes

    def prune(self, now: float) -> None:
        # Only after successful persistence; late arrivals can no longer target these.
        for mapping in (self.minutes, self.seen):
            for minute in list(mapping):
                if minute + 60 < now - LATE_SECONDS:
                    del mapping[minute]


def acquire_owner(connection: Connection) -> None:
    if not connection.execute(
        text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_ID}
    ).scalar_one():
        raise RuntimeError("Another CVD collector owns this database")
    connection.commit()


def restore(connection: Connection, flow: Flow) -> None:
    bucket_table: Table = getattr(CvdBucketTable, "__table__")
    minute_table: Table = getattr(CvdMinuteTable, "__table__")
    cutoff = flow.started_ns // 60_000_000_000 * 60 - LATE_SECONDS
    with connection.begin():
        for row in connection.execute(
            select(minute_table).where(
                minute_table.c.source == SOURCE, minute_table.c.minute >= cutoff
            )
        ).mappings():
            flow.minutes[row["minute"]] = Minute({}, row["universe"])
        for row in connection.execute(
            select(bucket_table).where(
                bucket_table.c.source == SOURCE, bucket_table.c.minute >= cutoff
            )
        ).mappings():
            flow.last_trade_ns = max(flow.last_trade_ns, row["last_trade_ns"])
            flow.replay_cutoffs[row["symbol"]] = max(
                flow.replay_cutoffs.get(row["symbol"], 0), row["last_trade_ns"]
            )
            state = flow.minutes.get(row["minute"])
            if state is not None:
                # Restart uncertainty is permanent for these minutes.
                state.symbols[row["symbol"]] = Bucket(
                    row["multiplier"],
                    row["buy"],
                    row["sell"],
                    False,
                    row["last_trade_ns"],
                )


def persist(
    connection: Connection, snapshot: tuple[list[dict], list[dict]], now: float
) -> None:
    """Absolute replacement makes retries safe, including ambiguous commit results.

    This is the SAME physical connection holding the session advisory lock. Never
    reconnect/retry an invalidated connection: exit and let a new process restore.
    """
    if connection.invalidated:
        raise RuntimeError("CVD database owner connection lost")
    with connection.begin():
        for model, rows in zip((CvdBucketTable, CvdMinuteTable), snapshot):
            table: Table = getattr(model, "__table__")
            keys = [c.name for c in table.primary_key]
            for offset in range(0, len(rows), 500):
                statement = insert(table).values(rows[offset : offset + 500])
                connection.execute(
                    statement.on_conflict_do_update(
                        index_elements=keys,
                        set_={
                            c.name: statement.excluded[c.name]
                            for c in table.columns
                            if c.name not in keys
                        },
                    )
                )
            connection.execute(
                delete(table).where(table.c.minute < int(now) // 60 * 60 - 7 * 86400)
            )


async def stream_shard(flow: Flow, symbols: list[str], stop: asyncio.Event) -> None:
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
                        handle_message(flow, message, pending, symbols)
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
            flow.disconnect(symbols, time.time() - 30)
        failures = 0 if time.monotonic() - healthy_since > 60 else min(failures + 1, 6)
        try:
            await asyncio.wait_for(
                stop.wait(), min(60, 2**failures) + random.uniform(0, 1)
            )
        except TimeoutError:
            pass


def handle_message(
    flow: Flow, message: dict, pending: dict[str, tuple[str, float]], symbols: list[str]
) -> None:
    now = time.time()
    kind = message.get("type")
    if kind == "error":
        raise ValueError("KuCoin rejected subscription")
    if kind == "ack":
        entry = pending.pop(str(message.get("id")), None)
        if entry:
            flow.acknowledged[entry[0]] = now
    elif kind == "message" and message.get("subject") == "match":
        payload = message.get("data")
        if (
            not isinstance(payload, dict)
            or payload.get("symbol") not in symbols
            or message.get("topic")
            != f"/contractMarket/execution:{payload.get('symbol')}"
        ):
            flow.rejected += 1
            flow.disconnect(symbols, now)
            raise ValueError("Invalid execution envelope")
        rejected = flow.rejected
        flow.trade(payload, now)
        if flow.rejected != rejected:
            # Conservative uncertainty: rejected input must not leave the
            # mutable minutes labelled complete.
            for minute, state in flow.minutes.items():
                if payload["symbol"] in state.symbols:
                    state.symbols[payload["symbol"]].covered = False


@asynccontextmanager
async def owner_connection():
    connection = await asyncio.to_thread(engine.connect)
    try:
        await asyncio.to_thread(acquire_owner, connection)
        yield connection
    finally:
        try:
            await asyncio.to_thread(connection.invalidate)
        finally:
            connection.close()


async def run(stop: asyncio.Event | None = None) -> None:
    if stop is None:
        # Standalone diagnostics own signals; the shared worker supplies its stop event.
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
    # Never allow SQLAlchemy to reconnect this owner connection after failure.
    async with owner_connection() as connection:
        flow = Flow(await asyncio.to_thread(load_contracts), time.time_ns())
        await asyncio.to_thread(restore, connection, flow)
        tasks: list[asyncio.Task] = []
        next_refresh = time.time() + 900
        pending_contracts = None
        graceful = False
        try:
            while not stop.is_set():
                now = time.time()
                flow.tick(now)
                if now >= next_refresh:
                    try:
                        pending_contracts = await asyncio.to_thread(load_contracts)
                        next_refresh = now + 900
                    except Exception:
                        log.exception("contract refresh failed")
                        next_refresh = now + 60
                if (
                    pending_contracts is not None
                    and pending_contracts != flow.contracts
                    and int(now) % 60 < 10
                ):
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks = []
                    flow.disconnect(list(flow.contracts), now)
                    flow.contracts = pending_contracts
                    # Membership changes take effect at the NEXT UTC minute.
                    next_minute = int(now) // 60 * 60 + 60
                    log.info(
                        "universe refreshed effective_minute=%s symbols=%s",
                        next_minute,
                        len(flow.contracts),
                    )
                if not tasks and flow.contracts:
                    symbols = sorted(flow.contracts)
                    tasks = [
                        asyncio.create_task(
                            stream_shard(flow, symbols[i : i + SHARD_SIZE], stop)
                        )
                        for i in range(0, len(symbols), SHARD_SIZE)
                    ]
                    log.info(
                        "connections=%s subscriptions=%s", len(tasks), len(symbols)
                    )
                for task in tasks:
                    if task.done():
                        task.result()
                        raise RuntimeError("CVD shard exited unexpectedly")
                snapshot = flow.snapshot(now)
                try:
                    await asyncio.to_thread(persist, connection, snapshot, now)
                except Exception:
                    log.exception(
                        "flush failed; stopping owner, restart will retain saved totals and mark uncertainty"
                    )
                    raise
                flow.prune(now)
                log.info(
                    "checkpoint=%s expected=%s acknowledged=%s covered=%s last_trade_ns=%s trades=%s rejected=%s",
                    int(now),
                    len(flow.contracts),
                    len(flow.acknowledged),
                    snapshot[1][-1]["covered_symbols"] if snapshot[1] else 0,
                    flow.last_trade_ns,
                    flow.trades,
                    flow.rejected,
                )
                try:
                    await asyncio.wait_for(stop.wait(), 10)
                except TimeoutError:
                    pass
            graceful = True
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            # Graceful shutdown preserves arrivals since last checkpoint, and marks
            # the unfinished connection interval partial just like an abrupt stop.
            flow.disconnect(list(flow.contracts), time.time() - 30)
            if graceful and not connection.invalidated:
                await asyncio.to_thread(
                    persist, connection, flow.snapshot(time.time()), time.time()
                )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    asyncio.run(run())
