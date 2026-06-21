from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

from bots.models import BotModel, OrderModel, RecoveryBotModel
from databases.tables.bot_table import BotTable
from databases.tables.deal_table import DealTable
from databases.tables.recovery_bot_table import RecoveryBotTable
from exchange_apis.kucoin.futures.lifecycle import Lifecycle
from kucoin_universal_sdk.model.common import RestError
from pybinbot import MarketType, OrderStatus, QuoteAssets, Status, DealType, Position
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
    position_deal = cast(Any, Lifecycle.__new__(Lifecycle))
    position_deal.active_bot = bot
    position_deal.controller = controller
    position_deal.kucoin_futures_api = futures_api
    position_deal.kucoin_symbol = "BTCUSDTM"
    position_deal.symbol_info = type(
        "SymbolInfo",
        (),
        {"futures_leverage": 1, "cooldown": 0},
    )()
    position_deal.kucoin_symbol_data = type(
        "KucoinSymbolInfo",
        (),
        {"multiplier": 0.001},
    )()
    position_deal.symbols_crud = DummySymbolsCrud()
    position_deal.price_precision = 4
    position_deal.qty_precision = 0
    position_deal.klines = None
    return position_deal, controller


def make_long_bot():
    bot = make_mock_bot_active_model()
    bot.market_type = MarketType.FUTURES
    bot.position = Position.long
    bot.margin_short_reversal = True
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
        "exchange_apis.kucoin.futures.lifecycle.time",
        lambda: timestamp_seconds,
    )
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.futures_deal.time",
        lambda: timestamp_seconds,
    )


def test_reverse_position_closes_source_with_reduce_only_and_creates_pending_bot():
    bot = make_long_bot()
    futures_api = DummyFuturesApi(current_qty=68)
    position_deal, controller = make_position_deal(bot, futures_api)

    reversed_bot = Lifecycle.reverse_position(position_deal)

    # New bot is pending with flipped direction and no orders/deal
    assert reversed_bot.position == Position.short
    assert reversed_bot.status == Status.pending
    assert reversed_bot.orders == []
    assert reversed_bot.deal.opening_price == 0

    # Exactly one reduce_only sell was placed to close the long position
    assert len(futures_api.sell_calls) == 1
    assert futures_api.sell_calls[0]["reduce_only"] is True
    assert futures_api.sell_calls[0]["qty"] == 68

    # Source bot was marked completed with closing fields populated
    completed = [s for s in controller.saved if s.status == Status.completed]
    assert len(completed) == 1
    assert completed[0].deal.closing_qty == 68
    assert completed[0].deal.closing_price > 0


def test_reverse_position_short_closes_with_buy():
    bot = make_long_bot()
    bot.position = Position.short
    futures_api = DummyFuturesApi(current_qty=-68)
    position_deal, controller = make_position_deal(bot, futures_api)

    reversed_bot = Lifecycle.reverse_position(position_deal)

    assert reversed_bot.position == Position.long
    assert reversed_bot.status == Status.pending
    assert len(futures_api.buy_calls) == 1
    assert futures_api.buy_calls[0]["reduce_only"] is True
    assert futures_api.buy_calls[0]["qty"] == 68


def test_reverse_position_errors_when_no_position():
    bot = make_long_bot()

    class NoPositionApi(DummyFuturesApi):
        def get_futures_position(self, symbol):
            return None

    futures_api = NoPositionApi()
    position_deal, controller = make_position_deal(bot, futures_api)

    result = Lifecycle.reverse_position(position_deal)

    assert result.status == Status.error
    assert len(futures_api.sell_calls) == 0


def test_reverse_position_errors_when_reduce_only_fails():
    bot = make_long_bot()

    class FailingApi(DummyFuturesApi):
        def sell(self, symbol, qty, reduce_only, leverage=None, reference_price=None):
            raise RestError(
                msg="insufficient balance",
                response=DummyResponse(400100, "insufficient balance"),
            )

    futures_api = FailingApi()
    position_deal, controller = make_position_deal(bot, futures_api)

    result = Lifecycle.reverse_position(position_deal)

    assert result.status == Status.error
    # Source bot is NOT marked completed — close failed
    completed = [s for s in controller.saved if s.status == Status.completed]
    assert len(completed) == 0


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


def test_first_reversal_creates_recovery_bot_with_source_metadata():
    bot = make_long_bot()
    bot.stop_loss = 2.5
    bot.trailing_profit = 2.0
    bot.trailing_deviation = 1.0
    enable_source_recovery(bot)
    futures_api = DummyFuturesApi(current_qty=68)
    position_deal, _ = make_position_deal(bot, futures_api)
    position_deal.klines = recovery_klines(
        high=1.30,
        low=1.24,
        close=1.267,
        closed_count=4,
    )

    reversed_bot = position_deal.reverse_position()

    assert reversed_bot.position == Position.short
    assert reversed_bot.status == Status.pending
    assert reversed_bot.margin_short_reversal is False
    assert reversed_bot.recovery_params is not None
    assert reversed_bot.recovery_params.reversal_path == "recovery"
    assert reversed_bot.recovery_params.source_contracts == 68
    assert reversed_bot.recovery_params.source_loss_fiat > 0
    assert reversed_bot.stop_loss == reversed_bot.recovery_params.stop_loss_pct
    assert reversed_bot.stop_loss <= Lifecycle.RECOVERY_STOP_CAP_PCT
    assert reversed_bot.fiat_order_size == 15.0
    assert reversed_bot.trailing_profit >= 0.9 * reversed_bot.stop_loss
    assert (
        reversed_bot.trailing_deviation
        <= reversed_bot.trailing_profit - Lifecycle.RECOVERY_TRAILING_MIN_GAP_PCT
    )


def test_source_reversal_skips_recovery_and_starts_cooldown_when_structure_too_wide():
    bot = make_long_bot()
    enable_source_recovery(bot)
    futures_api = DummyFuturesApi(current_qty=68)
    position_deal, controller = make_position_deal(bot, futures_api)
    position_deal.klines = recovery_klines(
        high=1.40,
        low=1.20,
        close=1.267,
        closed_count=4,
    )

    result = position_deal.reverse_position()

    assert result.status == Status.completed
    assert controller.created == []
    assert position_deal.symbols_crud.cooldowns == [
        {
            "symbol": "BTCUSDT",
            "cooldown_seconds": 360 * 60,
        }
    ]


def test_recovery_reversal_with_valid_structure_creates_new_recovery_bot():
    """A recovery bot stopping out should chain to another recovery hop (infinite chain)."""
    bot = make_long_bot()
    bot.stop_loss = 2.5
    bot.trailing_profit = 2.0
    bot.trailing_deviation = 1.0
    mark_as_recovery(bot)
    futures_api = DummyFuturesApi(current_qty=68)
    position_deal, controller = make_position_deal(bot, futures_api)
    position_deal.klines = recovery_klines(
        high=1.30,
        low=1.24,
        close=1.267,
        closed_count=4,
    )

    reversed_bot = position_deal.reverse_position()

    assert reversed_bot.position == Position.short
    assert reversed_bot.status == Status.pending
    assert reversed_bot.margin_short_reversal is False
    assert reversed_bot.recovery_params is not None
    assert reversed_bot.recovery_params.reversal_path == "recovery"
    assert reversed_bot.recovery_params.source_contracts == 68
    assert reversed_bot.stop_loss <= Lifecycle.RECOVERY_STOP_CAP_PCT
    assert len(futures_api.sell_calls) == 1
    assert futures_api.sell_calls[0]["reduce_only"] is True
    assert position_deal.symbols_crud.cooldowns == []


def test_recovery_reversal_skips_new_bot_when_structure_too_wide():
    """Wide structure on a recovery bot hop should close and start cooldown, not chain."""
    bot = make_long_bot()
    mark_as_recovery(bot)
    futures_api = DummyFuturesApi(current_qty=68)
    position_deal, controller = make_position_deal(bot, futures_api)
    position_deal.klines = recovery_klines(
        high=1.40,
        low=1.20,
        close=1.267,
        closed_count=4,
    )

    result = position_deal.reverse_position()

    assert result.status == Status.completed
    assert controller.created == []
    assert len(futures_api.sell_calls) == 1
    assert position_deal.symbols_crud.cooldowns == [
        {
            "symbol": "BTCUSDT",
            "cooldown_seconds": 360 * 60,
        }
    ]


def test_kat_intrabar_stop_breach_keeps_source_long_until_candle_confirmation(
    monkeypatch,
):
    event_time = datetime(2026, 6, 9, 23, 32, 52, tzinfo=timezone.utc)
    set_lifecycle_time(monkeypatch, event_time)
    bot = prepare_kat_source_bot()
    position_deal, controller = make_position_deal(bot, DummyFuturesApi(150))
    position_deal.price_precision = 5
    position_deal.klines = kat_klines()
    reverse_calls: list[float | None] = []
    stop_calls: list[float | None] = []

    def reverse_position(reference_price: float | None = None) -> BotModel:
        reverse_calls.append(reference_price)
        return bot

    def execute_stop_loss(reference_price: float | None = None) -> BotModel:
        stop_calls.append(reference_price)
        return bot

    position_deal.reverse_position = reverse_position
    position_deal.execute_stop_loss = execute_stop_loss

    result = position_deal.exit(0.00613)

    assert result.position == Position.long
    assert result.status == Status.active
    assert reverse_calls == []
    assert stop_calls == []
    assert position_deal.symbols_crud.cooldowns == []
    assert any("Recovery reversal deferred" in log for log in result.logs)
    assert controller.created == []


def test_completed_bearish_body_breakout_allows_short_recovery(monkeypatch):
    event_time = datetime(2026, 6, 10, 0, 0, 1, tzinfo=timezone.utc)
    set_lifecycle_time(monkeypatch, event_time)
    bot = prepare_kat_source_bot()
    position_deal, _ = make_position_deal(bot, DummyFuturesApi(150))
    position_deal.price_precision = 5
    position_deal.klines = kat_klines(include_2345_close=True)
    reverse_calls: list[float | None] = []

    def reverse_position(reference_price: float | None = None) -> BotModel:
        reverse_calls.append(reference_price)
        bot.position = Position.short
        return bot

    position_deal.reverse_position = reverse_position

    result = position_deal.exit(0.00615)

    assert result.position == Position.short
    assert reverse_calls == [0.00616]
    assert any("Recovery candle confirmation approved" in log for log in result.logs)


def test_completed_bullish_body_breakout_is_required_for_long_recovery():
    bot = make_long_bot()
    bot.position = Position.short
    position_deal, _ = make_position_deal(bot, DummyFuturesApi(-68))
    completed_candles = [
        [1, 100, 101, 99, 99.5, 100, 2],
        [3, 99.5, 100, 98, 99, 100, 4],
        [5, 99, 100, 98.5, 99.2, 100, 6],
        [7, 99.1, 102, 99, 101.5, 100, 8],
    ]

    assert (
        position_deal.recovery_body_breakout_confirmed(
            target_position=Position.long,
            completed_candles=completed_candles,
        )
        is True
    )


def test_confirmed_stop_without_body_breakout_closes_without_reversing(monkeypatch):
    event_time = datetime(2026, 6, 10, 0, 0, 1, tzinfo=timezone.utc)
    set_lifecycle_time(monkeypatch, event_time)
    bot = prepare_kat_source_bot()
    position_deal, controller = make_position_deal(bot, DummyFuturesApi(150))
    position_deal.price_precision = 5
    candles = kat_klines()
    candles[-1][4] = 0.00615
    candles.append(
        timestamped_kline(
            int(datetime(2026, 6, 9, 23, 45, tzinfo=timezone.utc).timestamp() * 1000),
            0.00619,
            0.00622,
            0.00615,
            0.00617,
        )
    )
    position_deal.klines = candles
    stop_calls: list[float | None] = []
    reverse_calls: list[float | None] = []

    def execute_stop_loss(reference_price: float | None = None) -> BotModel:
        stop_calls.append(reference_price)
        bot.status = Status.completed
        return bot

    position_deal.execute_stop_loss = execute_stop_loss

    def reverse_position(reference_price: float | None = None) -> BotModel:
        reverse_calls.append(reference_price)
        return bot

    position_deal.reverse_position = reverse_position

    result = position_deal.exit(0.00616)

    assert result.status == Status.completed
    assert stop_calls == [0.00617]
    assert reverse_calls == []
    assert controller.created == []
    assert any("Recovery body breakout rejected" in log for log in result.logs)
    assert len(position_deal.symbols_crud.cooldowns) == 1


def test_emergency_breach_closes_source_without_recovery(monkeypatch):
    event_time = datetime(2026, 6, 9, 23, 32, 52, tzinfo=timezone.utc)
    set_lifecycle_time(monkeypatch, event_time)
    bot = prepare_kat_source_bot()
    position_deal, controller = make_position_deal(bot, DummyFuturesApi(150))
    position_deal.price_precision = 5
    position_deal.klines = kat_klines()
    stop_calls: list[float | None] = []
    reverse_calls: list[float | None] = []

    def execute_stop_loss(reference_price: float | None = None) -> BotModel:
        stop_calls.append(reference_price)
        bot.status = Status.completed
        return bot

    position_deal.execute_stop_loss = execute_stop_loss

    def reverse_position(reference_price: float | None = None) -> BotModel:
        reverse_calls.append(reference_price)
        return bot

    position_deal.reverse_position = reverse_position

    result = position_deal.exit(0.00607)

    assert result.status == Status.completed
    assert stop_calls == [0.00625]
    assert reverse_calls == []
    assert controller.created == []
    assert any("Recovery emergency threshold breached" in log for log in result.logs)
    assert len(position_deal.symbols_crud.cooldowns) == 1


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
    bot.margin_short_reversal = False
    mark_as_recovery(bot, stop_loss_pct=4.0)
    return bot


def test_recovery_bot_exit_all_gates_passed_calls_reverse_position(monkeypatch):
    """Recovery bot stopping out with a confirmed candle body breakout should
    call reverse_position(), not close terminally."""
    event_time = datetime(2026, 6, 10, 0, 0, 1, tzinfo=timezone.utc)
    set_lifecycle_time(monkeypatch, event_time)
    bot = prepare_kat_recovery_bot()
    position_deal, _ = make_position_deal(bot, DummyFuturesApi(150))
    position_deal.price_precision = 5
    position_deal.klines = kat_klines(include_2345_close=True)
    reverse_calls: list[float | None] = []

    def reverse_position(reference_price: float | None = None) -> BotModel:
        reverse_calls.append(reference_price)
        bot.position = Position.short
        return bot

    position_deal.reverse_position = reverse_position

    result = position_deal.exit(0.00615)

    assert result.position == Position.short
    assert reverse_calls == [0.00616]
    assert any("Recovery candle confirmation approved" in log for log in result.logs)


def test_recovery_bot_exit_body_breakout_rejected_closes_terminally(monkeypatch):
    """Recovery bot stopping out without a valid body breakout should close via
    _close_source_without_recovery — no further chain, cooldown started."""
    event_time = datetime(2026, 6, 10, 0, 0, 1, tzinfo=timezone.utc)
    set_lifecycle_time(monkeypatch, event_time)
    bot = prepare_kat_recovery_bot()
    position_deal, controller = make_position_deal(bot, DummyFuturesApi(150))
    position_deal.price_precision = 5
    candles = kat_klines()
    candles[-1][4] = 0.00615
    candles.append(
        timestamped_kline(
            int(datetime(2026, 6, 9, 23, 45, tzinfo=timezone.utc).timestamp() * 1000),
            0.00619,
            0.00622,
            0.00615,
            0.00617,
        )
    )
    position_deal.klines = candles
    stop_calls: list[float | None] = []
    reverse_calls: list[float | None] = []

    def execute_stop_loss(reference_price: float | None = None) -> BotModel:
        stop_calls.append(reference_price)
        bot.status = Status.completed
        return bot

    position_deal.execute_stop_loss = execute_stop_loss

    def reverse_position(reference_price: float | None = None) -> BotModel:
        reverse_calls.append(reference_price)
        return bot

    position_deal.reverse_position = reverse_position

    result = position_deal.exit(0.00616)

    assert result.status == Status.completed
    assert stop_calls == [0.00617]
    assert reverse_calls == []
    assert controller.created == []
    assert any("Recovery body breakout rejected" in log for log in result.logs)
    assert len(position_deal.symbols_crud.cooldowns) == 1
