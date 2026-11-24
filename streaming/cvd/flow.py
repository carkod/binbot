"""Execution notionals, frozen minute universes, deduplication and coverage."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import time

from api.databases.tables.cvd_table import SOURCE

LATE_SECONDS = 120
MAX_SEEN_TRADES = 2_000_000


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
    # Keep the symbol once per minute, rather than in every execution key.
    # A Flow has one fixed SOURCE, so source needn't be repeated either.
    seen: dict[int, dict[str, set[str]]] = field(default_factory=dict)
    seen_count: int = field(default=0, init=False)
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
            trade_key = str(trade_id)
            if any(
                trade_key in symbols.get(symbol, ()) for symbols in self.seen.values()
            ):
                return False
            notional = price * contracts * bucket.multiplier
            if not math.isfinite(notional):
                raise ValueError("Invalid notional")
        except KeyError, TypeError, ValueError, OverflowError:
            self.rejected += 1
            return False
        # Bounded by three exchange minutes plus a hard fail-closed safety cap.
        if self.seen_count >= MAX_SEEN_TRADES:
            self.rejected += 1
            return False
        minute_keys = self.seen.setdefault(minute, {})
        symbol_keys = minute_keys.get(symbol)
        if symbol_keys is None:
            symbol_keys = minute_keys[symbol] = set()
        symbol_keys.add(trade_key)
        self.seen_count += 1
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
        for minute in list(self.minutes):
            if minute + 60 < now - LATE_SECONDS:
                del self.minutes[minute]
                expired_keys = self.seen.pop(minute, {})
                self.seen_count -= sum(map(len, expired_keys.values()))


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
