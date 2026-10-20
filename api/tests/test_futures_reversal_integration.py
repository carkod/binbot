from datetime import datetime, timezone
import types
from typing import Any, cast
from uuid import uuid4

from pybinbot import (
    BotModel,
    DealType,
    MarketType,
    OrderModel,
    OrderStatus,
    Position,
    QuoteAssets,
    RecoveryBotModel,
)

from api.databases.tables.bot_table import BotTable
from api.databases.tables.deal_table import DealTable
from api.databases.tables.recovery_bot_table import RecoveryBotTable
from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from streaming.base import BaseStreaming
from streaming.lifecycle import Lifecycle
from tests.fixtures.mock_bot_table import make_mock_bot_active_model


class DummyController:
    def __init__(self):
        self.saved: list[BotModel] = []
        self.created: list[BotTable] = []

    def save(self, bot: BotModel) -> BotModel:
        snapshot = BotModel.model_validate(bot.model_dump())
        self.saved.append(snapshot)
        return snapshot

    def create(self, new_bot) -> BotTable:
        data = new_bot.model_dump(exclude={"recovery_params"})
        created = BotTable(**data, deal=DealTable(), orders=[])
        recovery_params = new_bot.recovery_params
        if recovery_params is not None:
            recovery_id = uuid4()
            created.recovery_mode_id = recovery_id
            created.recovery_params = RecoveryBotTable(
                **recovery_params.model_dump(),
                id=recovery_id,
                created_at=1,
                updated_at=1,
            )
        self.created.append(created)
        return created


class DummyFuturesApi:
    def __init__(self, current_qty: float = 68):
        self._position = type(
            "pos", (object,), {"current_qty": current_qty, "mark_price": 1.27}
        )()
        self.sell_calls: list[dict] = []
        self.buy_calls: list[dict] = []

    def get_futures_position(self, symbol):
        return self._position

    def sell(self, symbol, qty, reduce_only, leverage=None, reference_price=None):
        self.sell_calls.append({"qty": qty, "reduce_only": reduce_only})
        return OrderModel(
            order_id="close-order-1",
            order_type="market",
            pair=symbol,
            timestamp=1774770587226,
            order_side="sell",
            qty=qty,
            price=1.267,
            status=OrderStatus.FILLED,
            time_in_force="GTC",
            deal_type=DealType.margin_short,
        )

    def buy(self, symbol, qty, reduce_only, leverage=None, reference_price=None):
        self.buy_calls.append({"qty": qty, "reduce_only": reduce_only})
        return OrderModel(
            order_id="close-order-1",
            order_type="market",
            pair=symbol,
            timestamp=1774770587226,
            order_side="buy",
            qty=qty,
            price=1.267,
            status=OrderStatus.FILLED,
            time_in_force="GTC",
            deal_type=DealType.margin_short,
        )


class DummySymbolsCrud:
    def __init__(self):
        self.cooldowns: list[dict] = []

    def start_cooldown(self, symbol: str, cooldown_seconds: int) -> None:
        self.cooldowns.append(
            {
                "symbol": symbol,
                "cooldown_seconds": cooldown_seconds,
            }
        )


class DummyResponse:
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


def make_position_deal(bot, futures_api):
    controller = DummyController()
    execution = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    execution.active_bot = bot
    execution.controller = controller
    execution.kucoin_futures_api = futures_api
    execution.kucoin_symbol = "BTCUSDTM"
    execution.symbol_info = type(
        "SymbolInfo",
        (),
        {"futures_leverage": 1, "cooldown": 0, "qty_precision": 0},
    )()
    execution.kucoin_symbol_data = type(
        "KucoinSymbolInfo",
        (),
        {"multiplier": 0.001},
    )()
    execution.symbols_crud = DummySymbolsCrud()
    execution.price_precision = 4
    execution.interval_ms = 15 * 60 * 1000
    position_deal = Lifecycle(
        execution=execution,
        base_streaming=cast(
            BaseStreaming,
            types.SimpleNamespace(
                interval=types.SimpleNamespace(get_ms=lambda: execution.interval_ms)
            ),
        ),
    )
    position_deal.klines = None
    return position_deal, controller


def make_long_bot():
    bot = make_mock_bot_active_model()
    bot.market_type = MarketType.FUTURES
    bot.position = Position.long
    bot.pair = "BTCUSDT"
    bot.quote_asset = QuoteAssets.USDT
    bot.fiat = "USDT"
    bot.orders = []
    bot.deal.base_order_size = 68
    bot.deal.opening_price = 1.31
    bot.deal.opening_qty = 68
    bot.deal.opening_timestamp = 1774751364351
    return bot


def enable_source_recovery(bot: BotModel) -> None:
    recovery_id = uuid4()
    bot.recovery_mode_id = recovery_id
    bot.recovery_params = RecoveryBotModel(
        id=recovery_id,
        reversal_path="source",
        source_contracts=0,
        source_loss_fiat=0,
        stop_loss_pct=0,
        created_at=1,
        updated_at=1,
    )


def mark_as_recovery(bot: BotModel, stop_loss_pct: float = 3.0) -> None:
    recovery_id = uuid4()
    bot.recovery_mode_id = recovery_id
    bot.recovery_params = RecoveryBotModel(
        id=recovery_id,
        reversal_path="recovery",
        source_contracts=68,
        source_loss_fiat=2.5,
        stop_loss_pct=stop_loss_pct,
        created_at=1,
        updated_at=1,
    )


def recovery_klines(
    *,
    high: float,
    low: float,
    close: float,
    closed_count: int,
) -> list[list[float]]:
    candles = [
        [index, close, high, low, close, 100, index + 1]
        for index in range(closed_count)
    ]
    candles.append([closed_count, close, high, low, close, 100, closed_count + 1])
    return candles


def timestamped_kline(
    open_time_ms: int,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> list[float]:
    interval_ms = 15 * 60 * 1000
    return [
        open_time_ms,
        open_price,
        high,
        low,
        close,
        100,
        open_time_ms + interval_ms - 1,
    ]


def kat_klines(include_2345_close: bool = False) -> list[list[float]]:
    start_ms = int(datetime(2026, 6, 9, 19, 45, tzinfo=timezone.utc).timestamp() * 1000)
    candles = [
        timestamped_kline(
            start_ms + index * 15 * 60 * 1000,
            0.0061,
            0.0061675,
            0.0060325,
            0.0061,
        )
        for index in range(11)
    ]
    candles.extend(
        [
            timestamped_kline(
                int(
                    datetime(2026, 6, 9, 22, 30, tzinfo=timezone.utc).timestamp() * 1000
                ),
                0.00608,
                0.00616,
                0.00605,
                0.00615,
            ),
            timestamped_kline(
                int(
                    datetime(2026, 6, 9, 22, 45, tzinfo=timezone.utc).timestamp() * 1000
                ),
                0.00613,
                0.00625,
                0.00608,
                0.00616,
            ),
            timestamped_kline(
                int(
                    datetime(2026, 6, 9, 23, 0, tzinfo=timezone.utc).timestamp() * 1000
                ),
                0.00619,
                0.00646,
                0.00618,
                0.00625,
            ),
            timestamped_kline(
                int(
                    datetime(2026, 6, 9, 23, 15, tzinfo=timezone.utc).timestamp() * 1000
                ),
                0.00624,
                0.00636,
                0.00618,
                0.00625,
            ),
            timestamped_kline(
                int(
                    datetime(2026, 6, 9, 23, 30, tzinfo=timezone.utc).timestamp() * 1000
                ),
                0.00624,
                0.00625,
                0.0061,
                0.00618,
            ),
        ]
    )
    if include_2345_close:
        candles.append(
            timestamped_kline(
                int(
                    datetime(2026, 6, 9, 23, 45, tzinfo=timezone.utc).timestamp() * 1000
                ),
                0.00617,
                0.00625,
                0.00613,
                0.00616,
            )
        )
    return candles


def prepare_kat_source_bot() -> BotModel:
    bot = make_long_bot()
    bot.pair = "KATUSDTM"
    bot.stop_loss = 4
    bot.trailing = False
    bot.deal.opening_price = 0.00644
    bot.deal.stop_loss_price = 0.00618
    enable_source_recovery(bot)
    return bot


def set_lifecycle_time(monkeypatch, when: datetime) -> None:
    timestamp_seconds = when.timestamp()
    monkeypatch.setattr(
        "streaming.lifecycle.time",
        lambda: timestamp_seconds,
    )
    monkeypatch.setattr(
        "api.exchange_apis.kucoin.futures.futures_deal.time",
        lambda: timestamp_seconds,
    )


def test_compute_recovery_stop_uses_structure_and_atr_floor():
    bot = make_long_bot()
    bot.stop_loss = 2.5
    position_deal, _ = make_position_deal(bot, DummyFuturesApi())
    position_deal.klines = recovery_klines(
        high=102,
        low=100,
        close=100,
        closed_count=15,
    )

    stop_loss_pct = position_deal.compute_recovery_stop_loss_pct(
        reference_price=100,
        target_position=Position.short,
    )

    # Structure distance 2% + 0.5 * 2% ATR = 3%; ATR floor is also 3%.
    assert stop_loss_pct == 3.0


def test_compute_recovery_stop_uses_fixed_buffer_without_atr():
    bot = make_long_bot()
    bot.stop_loss = 2.5
    position_deal, _ = make_position_deal(bot, DummyFuturesApi())
    position_deal.klines = recovery_klines(
        high=103,
        low=99,
        close=100,
        closed_count=4,
    )

    stop_loss_pct = position_deal.compute_recovery_stop_loss_pct(
        reference_price=100,
        target_position=Position.short,
    )

    assert stop_loss_pct == 3.75
    assert any("ATR unavailable" in log for log in bot.logs)


def test_compute_recovery_stop_rejects_structure_beyond_cap():
    bot = make_long_bot()
    position_deal, _ = make_position_deal(bot, DummyFuturesApi())
    position_deal.klines = recovery_klines(
        high=107,
        low=99,
        close=100,
        closed_count=4,
    )

    stop_loss_pct = position_deal.compute_recovery_stop_loss_pct(
        reference_price=100,
        target_position=Position.short,
    )

    assert stop_loss_pct is None
    assert any("above 6.50% cap" in log for log in bot.logs)


# ---------------------------------------------------------------------------
# Recovery-chain: exit() gated path for recovery bots (infinite hop tests)
# ---------------------------------------------------------------------------


def prepare_kat_recovery_bot() -> BotModel:
    """Like prepare_kat_source_bot() but marked as a recovery hop."""
    bot = make_long_bot()
    bot.pair = "KATUSDTM"
    bot.stop_loss = 4
    bot.trailing = False
    bot.deal.opening_price = 0.00644
    bot.deal.stop_loss_price = 0.00618
    mark_as_recovery(bot, stop_loss_pct=4.0)
    return bot
