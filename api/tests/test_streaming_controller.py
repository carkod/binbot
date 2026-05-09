import types
import time

import pandas as pd
import pytest
from bots.models import OrderModel
from kucoin_universal_sdk.model.common import RestError
from typing import Any, cast
from pybinbot import MarketType
from streaming.position_manager import PositionManager
from streaming.base import BaseStreaming
from pybinbot import (
    ExchangeId,
    BinanceErrors,
    HABollinguerSpread,
    OrderStatus,
    Status,
    DealType,
    Position,
)
from streaming.futures_position import FuturesPosition


class TestPositionManager:
    def _make_base_streaming(self, monkeypatch, active_pairs=None):
        # Import inside to ensure workspace imports resolve during tests
        # Monkeypatch internal controller classes BEFORE instantiating BaseStreaming
        # to prevent real DB queries during __init__
        class DummyBotCrud:
            def __init__(self, *args, **kwargs):
                self.saved = []
                # sessions may be passed by BaseStreaming but unused here
                self.session = kwargs.get("session") if kwargs else None

            def get_active_pairs(self):
                return []

            def get_one(self, symbol, status):
                raise Exception("No real DB access in tests")

            def save(self, bot):
                self.saved.append(bot)

        class DummyPaperCrud(DummyBotCrud):
            pass

        class DummySymbolsCrud:
            def __init__(self):
                self.saved = []

            # Minimal symbol resolver used by PositionManager.__init__
            def get_symbol(self, symbol: str):
                # Assume 4-letter quote (USDT/USDC). Good enough for tests.
                base, quote = symbol[:-4], symbol[-4:]
                return types.SimpleNamespace(
                    base_asset=base,
                    quote_asset=quote,
                    price_precision=4,
                    qty_precision=4,
                )

        class DummyBinanceApi:
            def __init__(self, *args, **kwargs):
                pass

            def get_ui_klines(self, symbol, interval, limit=200):
                # Return list of lists (raw klines format)
                current_time = int(time.time() * 1000)
                klines = []
                for i in range(200):
                    timestamp = current_time - (200 - i) * 60000
                    base_price = 100
                    variation = (i % 10) - 5
                    open_price = base_price + variation
                    high_price = base_price + variation + 2
                    low_price = base_price + variation - 1
                    close_price = base_price + variation + 1
                    klines.append(
                        [
                            timestamp,
                            open_price,
                            high_price,
                            low_price,
                            close_price,
                            1000,
                            timestamp + 60000,
                            500,
                            50,
                            600,
                            300,
                            0,
                        ]
                    )
                return klines

            def get_interest_history(self, asset, symbol):
                return {"rows": [{"interests": "0.0"}]}

        class DummyKucoinApi:
            def __init__(self, *args, **kwargs):
                pass

            def get_ui_klines(self, symbol, interval, limit=200):
                # Return list of lists (raw klines format)
                current_time = int(time.time() * 1000)
                klines = []
                for i in range(200):
                    timestamp = current_time - (200 - i) * 60000
                    base_price = 100
                    variation = (i % 10) - 5
                    open_price = base_price + variation
                    high_price = base_price + variation + 2
                    low_price = base_price + variation - 1
                    close_price = base_price + variation + 1
                    klines.append(
                        [
                            timestamp,
                            open_price,
                            high_price,
                            low_price,
                            close_price,
                            1000,
                            500,
                        ]
                    )
                return klines

            def get_symbol_info(self, symbol):
                class DummySymbolInfo:
                    last_trade_price = 101.0

                return DummySymbolInfo()

        monkeypatch.setattr("streaming.base.BotTableCrud", DummyBotCrud)
        monkeypatch.setattr("streaming.base.PaperTradingTableCrud", DummyPaperCrud)
        monkeypatch.setattr("streaming.base.SymbolsCrud", DummySymbolsCrud)
        monkeypatch.setattr("streaming.base.BinanceApi", DummyBinanceApi)
        monkeypatch.setattr("streaming.base.KucoinApi", DummyKucoinApi)
        monkeypatch.setattr("streaming.base.KucoinFutures", DummyKucoinApi)

        # Mock get_symbol_info for KucoinFutures used in process_deal
        class DummySymbolInfo:
            last_trade_price = 101.0

        def dummy_get_symbol_info(symbol):
            return DummySymbolInfo()

        monkeypatch.setattr(
            "exchange_apis.kucoin.futures.futures_deal.KucoinFutures.get_symbol_info",
            dummy_get_symbol_info,
        )

        base = BaseStreaming()

        # Freeze active pairs to a predictable list
        pairs = list(active_pairs or ["BTCUSDC", "ETHUSDC", "TESTUSDC"])
        # Include Kucoin-style dashed symbols so converted_symbol lookups succeed
        dash_pairs = []
        for pair in pairs:
            if "-" not in pair and len(pair) > 4:
                dash_pairs.append(f"{pair[:-4]}-{pair[-4:]}")
        pairs.extend(dash_pairs)
        monkeypatch.setattr(base, "active_bot_pairs", pairs, raising=False)

        # Replace active pairs after init (init used dummies returning empty list)
        return base

    def _make_bot(
        self,
        pair="BTCUSDC",
        position=Position.long,
        market_type=MarketType.SPOT,
    ):
        # Lightweight BotModel-like object for tests
        bot = types.SimpleNamespace()
        bot.name = "apex_aggressive_momo"
        bot.pair = pair
        bot.fiat = "USDC"
        bot.position = position
        bot.dynamic_trailing = True
        bot.trailing = False
        bot.trailing_profit = 0.0
        bot.trailing_deviation = 0.0
        bot.stop_loss = 0.0
        bot.status = None
        bot.name = "test_bot"
        bot.market_type = market_type

        # Add dummy orders list to satisfy order_updates logic
        bot.orders = []

        # deal payload used by profit computation
        deal = types.SimpleNamespace()
        deal.base_order_size = 10
        deal.opening_price = 100.0
        deal.closing_price = 0.0
        deal.current_price = 100.0
        deal.closing_timestamp = 0
        bot.deal = deal

        # methods used in error handling
        bot.add_log = lambda msg: None
        return bot

    def test_base_streaming_bot_controller_uses_short_lived_sessions(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch)

        assert base.bot_controller.session is None

    def test_build_bb_spreads_minimum_length(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch)

        # Provide fewer than 200 klines to hit the early return
        class ShortBinanceApi:
            def get_ui_klines(self, symbol, interval, limit=200):
                # Return list of lists with fewer rows
                current_time = int(time.time() * 1000)
                klines = []
                for i in range(50):
                    timestamp = current_time - (50 - i) * 60000
                    base_price = 100
                    variation = (i % 10) - 5
                    open_price = base_price + variation
                    high_price = base_price + variation + 2
                    low_price = base_price + variation - 1
                    close_price = base_price + variation + 1
                    klines.append(
                        [
                            timestamp,
                            open_price,
                            high_price,
                            low_price,
                            close_price,
                            1000,
                            timestamp + 60000,
                            500,
                            50,
                            600,
                            300,
                            0,
                        ]
                    )
                return klines

        base.binance_api = ShortBinanceApi()
        sc = cast(Any, PositionManager(base, symbol="BTCUSDC"))
        sc.api = base.binance_api

        # Mock PositionMarket method on PositionManager for test
        setattr(
            sc,
            "build_bb_spreads",
            lambda: HABollinguerSpread(bb_high=0, bb_mid=0, bb_low=0),
        )
        spreads = sc.build_bb_spreads()
        assert spreads.bb_high == 0
        assert spreads.bb_mid == 0
        assert spreads.bb_low == 0

    def test_process_deal_runs_trailing_before_deal_exit(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDC"])
        # Set exchange to KUCOIN to avoid NotImplementedError for order updates
        from pybinbot import ExchangeId

        base.exchange = ExchangeId.KUCOIN
        sc = PositionManager(base, symbol="BTCUSDC")
        sc.api = base.kucoin_api
        sc.api = base.kucoin_api
        sc.api = base.kucoin_api
        sc.api = base.kucoin_api

        live_bot = self._make_bot(pair="BTCUSDC", position=Position.long)
        live_bot.dynamic_trailing = True

        monkeypatch.setattr(
            BaseStreaming,
            "get_current_bot",
            lambda self, symbol: live_bot,
        )
        monkeypatch.setattr(
            BaseStreaming,
            "get_current_test_bot",
            lambda self, symbol: None,
        )

        class FakeDealGateway:
            exit_calls: list[tuple[float, float]] = []
            base_streaming = None

            def __init__(self, bot, db_table, base_streaming=None):
                self.bot = bot
                self.db_table = db_table
                FakeDealGateway.base_streaming = base_streaming

            def deal_exit_orchestration(self, close_price, open_price):
                FakeDealGateway.exit_calls.append((close_price, open_price))

            def save(self, bot):
                base.bot_controller.save(bot)

        monkeypatch.setattr(
            "streaming.position_manager.DealGateway",
            FakeDealGateway,
        )

        sc.process_deal()

        assert FakeDealGateway.exit_calls, (
            "Expected deal_exit_orchestration to be called"
        )
        assert FakeDealGateway.base_streaming is base

    def test_process_deal_calls_deal_exit_orchestration_for_active_pair(
        self, monkeypatch
    ):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDC"])
        # Set exchange to KUCOIN to avoid NotImplementedError for order updates
        from pybinbot import ExchangeId

        base.exchange = ExchangeId.KUCOIN
        sc = PositionManager(base, symbol="BTCUSDC")

        # Provide a current bot via BaseStreaming.get_current_bot
        bot = self._make_bot(pair="BTCUSDC", position=Position.long)
        bot.dynamic_trailing = False

        # Mock DB access by overriding BaseStreaming.get_current_bot at class level
        monkeypatch.setattr(
            BaseStreaming,
            "get_current_bot",
            lambda self, symbol: bot,
        )
        # Ensure paper trading path does not hit DB
        monkeypatch.setattr(
            BaseStreaming,
            "get_current_test_bot",
            lambda self, symbol: None,
        )

        # Track that deal_exit_orchestration is called
        class FakeDealGateway:
            exit_calls: list[tuple[float, float]] = []

            def __init__(self, bot, db_table, base_streaming=None):
                self.bot = bot
                self.db_table = db_table
                self.base_streaming = base_streaming

            def deal_exit_orchestration(self, close_price, open_price):
                FakeDealGateway.exit_calls.append((close_price, open_price))

            def save(self, bot):
                base.bot_controller.save(bot)

        monkeypatch.setattr(
            "streaming.position_manager.DealGateway",
            FakeDealGateway,
        )

        # Mock delegated order updates to prevent it from doing anything
        monkeypatch.setattr(
            "streaming.spot_position.SpotPosition.order_updates",
            lambda self: None,
        )
        monkeypatch.setattr(
            "streaming.futures_position.FuturesPosition.order_updates",
            lambda self: None,
        )

        sc.process_deal()
        assert FakeDealGateway.exit_calls, (
            "Expected deal_exit_orchestration to be called"
        )

    def test_process_deal_binance_error_sets_status_and_saves(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDC"])
        # Set exchange to KUCOIN to avoid NotImplementedError for order updates
        from pybinbot import ExchangeId

        base.exchange = ExchangeId.KUCOIN
        sc = PositionManager(base, symbol="BTCUSDC")

        bot = self._make_bot(pair="BTCUSDC", position=Position.long)
        bot.dynamic_trailing = False

        # Mock DB access by overriding BaseStreaming.get_current_bot at class level
        monkeypatch.setattr(
            BaseStreaming,
            "get_current_bot",
            lambda self, symbol: bot,
        )
        # Ensure paper trading path does not hit DB
        monkeypatch.setattr(
            BaseStreaming,
            "get_current_test_bot",
            lambda self, symbol: None,
        )

        class ErrorDealGateway:
            def __init__(self, bot, db_table, base_streaming=None):
                self.bot = bot
                self.db_table = db_table
                self.base_streaming = base_streaming

            def deal_exit_orchestration(self, close_price, open_price):
                # Raise BinanceErrors with code -2010 to hit error path
                raise BinanceErrors("Order error", -2010)

            def save(self, bot):
                # Redirect to the fake controller's save to mimic PositionManager behavior
                base.bot_controller.save(bot)

        monkeypatch.setattr(
            "streaming.position_manager.DealGateway",
            ErrorDealGateway,
        )

        # Mock delegated order updates to prevent it from doing anything
        monkeypatch.setattr(
            "streaming.spot_position.SpotPosition.order_updates",
            lambda self: None,
        )
        monkeypatch.setattr(
            "streaming.futures_position.FuturesPosition.order_updates",
            lambda self: None,
        )

        with pytest.raises(BinanceErrors):
            sc.process_deal()

    def test_streaming_controller_uses_kucoin_api_for_kucoin_symbols(self, monkeypatch):
        """Test that PositionManager uses KucoinApi when exchange_id is KUCOIN"""
        base = self._make_base_streaming(monkeypatch)
        # Force KUCOIN exchange path directly on BaseStreaming
        from pybinbot import ExchangeId

        base.exchange = ExchangeId.KUCOIN

        # Track which API's get_raw_klines was called
        kucoin_called = []
        binance_called = []

        def track_kucoin_klines(*args, **kwargs):
            kucoin_called.append(True)
            # Return list of lists (raw klines format)
            current_time = int(time.time() * 1000)
            klines = []
            for i in range(200):
                timestamp = current_time - (200 - i) * 60000
                base_price = 100
                variation = (i % 10) - 5
                open_price = base_price + variation
                high_price = base_price + variation + 2
                low_price = base_price + variation - 1
                close_price = base_price + variation + 1
                klines.append(
                    [
                        timestamp,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        1000,
                        timestamp + 60000,
                        500,
                    ]
                )
            return klines

        def track_binance_klines(*args, **kwargs):
            binance_called.append(True)
            # Return list of lists (raw klines format)
            current_time = int(time.time() * 1000)
            klines = []
            for i in range(200):
                timestamp = current_time - (200 - i) * 60000
                base_price = 100
                variation = (i % 10) - 5
                open_price = base_price + variation
                high_price = base_price + variation + 2
                low_price = base_price + variation - 1
                close_price = base_price + variation + 1
                klines.append(
                    [
                        timestamp,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        1000,
                        timestamp + 60000,
                        500,
                        50,
                        600,
                        300,
                        0,
                    ]
                )

            return klines

        base.kucoin_api.get_ui_klines = track_kucoin_klines
        base.binance_api.get_ui_klines = track_binance_klines
        # Instantiate controller to trigger klines fetch
        sc = cast(Any, PositionManager(base, symbol="BTCUSDC"))
        sc.api = base.kucoin_api

        def fake_dataframe_ops():
            interval = str(base.interval.value)
            sc.api.get_ui_klines(symbol="BTCUSDC", interval=interval)
            sc.api.get_ui_klines(
                symbol=base.kucoin_benchmark_symbol,
                interval=interval,
            )
            return pd.DataFrame(), pd.DataFrame()

        setattr(sc, "dataframe_ops", fake_dataframe_ops)
        sc.dataframe_ops()

        # Assert that KucoinApi was used, not BinanceApi
        assert len(kucoin_called) > 0, "KucoinApi.get_ui_klines should have been called"
        assert len(binance_called) == 0, (
            "BinanceApi.get_ui_klines should not have been called"
        )

    def test_process_deal_futures_does_not_complete_while_position_is_open(
        self, monkeypatch
    ):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDT"])
        base.exchange = ExchangeId.KUCOIN
        sc = PositionManager(base, symbol="BTCUSDT")

        bot = self._make_bot(
            pair="BTCUSDT",
            position=Position.long,
            market_type=MarketType.FUTURES,
        )
        bot.orders = [
            OrderModel(
                order_id="tp-order-1",
                order_type="market",
                pair="BTCUSDTM",
                timestamp=int(time.time() * 1000),
                order_side="sell",
                qty=0,
                price=0,
                status=OrderStatus.NEW,
                time_in_force="GTC",
                deal_type=DealType.take_profit,
            )
        ]

        monkeypatch.setattr(
            BaseStreaming,
            "get_current_bot",
            lambda self, symbol: bot,
        )
        monkeypatch.setattr(
            BaseStreaming,
            "get_current_test_bot",
            lambda self, symbol: None,
        )
        monkeypatch.setattr(
            OrderStatus,
            "map_from_kucoin_status",
            staticmethod(lambda _: OrderStatus.FILLED),
        )
        monkeypatch.setattr(
            "streaming.futures_position.convert_to_kucoin_symbol",
            lambda _bot: "BTCUSDTM",
        )

        base.bot_controller.update_order = lambda order: order
        base.bot_controller.save = lambda *args, **kwargs: (
            base.bot_controller.saved.append(
                kwargs.get("data") if "data" in kwargs else args[0]
            )
        )
        base.kucoin_futures_api.retrieve_order = lambda order_id: types.SimpleNamespace(
            status=types.SimpleNamespace(value="done"),
            filled_size=70,
            avg_deal_price=1.267,
            created_at=int(time.time() * 1000),
            price=1.267,
        )
        base.kucoin_futures_api.get_futures_position = lambda symbol: (
            types.SimpleNamespace(current_qty=2)
        )

        class FakeDealGateway:
            def __init__(self, bot, db_table, base_streaming=None):
                self.bot = bot
                self.db_table = db_table
                self.base_streaming = base_streaming

            def deal_exit_orchestration(self, close_price, open_price):
                fp = cast(Any, FuturesPosition.__new__(FuturesPosition))
                fp.base_streaming = base
                fp.bot = self.bot
                fp.active_bot = self.bot
                fp.price_precision = 4
                fp.qty_precision = 4
                fp.cancel_current_sl = lambda: None
                fp.backfill_position_from_fills = lambda: self.bot
                return FuturesPosition.order_updates(fp)

        monkeypatch.setattr("streaming.position_manager.DealGateway", FakeDealGateway)

        sc.process_deal()

        assert bot.deal.closing_price == 0
        assert bot.status != Status.completed

    def test_process_deal_futures_uses_backfill_when_position_missing(
        self, monkeypatch
    ):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDT"])
        base.exchange = ExchangeId.KUCOIN
        sc = PositionManager(base, symbol="BTCUSDT")

        bot = self._make_bot(
            pair="BTCUSDT",
            position=Position.long,
            market_type=MarketType.FUTURES,
        )
        bot.orders = [
            OrderModel(
                order_id="tp-order-2",
                order_type="market",
                pair="BTCUSDTM",
                timestamp=int(time.time() * 1000),
                order_side="sell",
                qty=0,
                price=0,
                status=OrderStatus.NEW,
                time_in_force="GTC",
                deal_type=DealType.take_profit,
            )
        ]

        monkeypatch.setattr(
            BaseStreaming,
            "get_current_bot",
            lambda self, symbol: bot,
        )
        monkeypatch.setattr(
            BaseStreaming,
            "get_current_test_bot",
            lambda self, symbol: None,
        )
        monkeypatch.setattr(
            OrderStatus,
            "map_from_kucoin_status",
            staticmethod(lambda _: OrderStatus.FILLED),
        )
        monkeypatch.setattr(
            "streaming.futures_position.convert_to_kucoin_symbol",
            lambda _bot: "BTCUSDTM",
        )

        base.bot_controller.update_order = lambda order: order
        base.bot_controller.save = lambda *args, **kwargs: (
            base.bot_controller.saved.append(
                kwargs.get("data") if "data" in kwargs else args[0]
            )
        )
        base.kucoin_futures_api.retrieve_order = lambda order_id: types.SimpleNamespace(
            status=types.SimpleNamespace(value="done"),
            filled_size=70,
            avg_deal_price=1.267,
            created_at=int(time.time() * 1000),
            price=1.267,
        )
        base.kucoin_futures_api.get_futures_position = lambda symbol: None

        backfill_called = {"value": False}

        class FakeDealGateway:
            def __init__(self, bot, db_table, base_streaming=None):
                self.bot = bot
                self.db_table = db_table
                self.base_streaming = base_streaming

            def deal_exit_orchestration(self, close_price, open_price):
                fp = cast(Any, FuturesPosition.__new__(FuturesPosition))
                fp.base_streaming = base
                fp.bot = self.bot
                fp.active_bot = self.bot
                fp.price_precision = 4
                fp.qty_precision = 4
                fp.cancel_current_sl = lambda: None

                def backfill():
                    backfill_called["value"] = True
                    self.bot.deal.closing_price = 1.267
                    self.bot.deal.closing_qty = 70
                    self.bot.deal.closing_timestamp = int(time.time() * 1000)
                    self.bot.status = Status.completed
                    return self.bot

                fp.backfill_position_from_fills = backfill
                return FuturesPosition.order_updates(fp)

        monkeypatch.setattr("streaming.position_manager.DealGateway", FakeDealGateway)

        sc.process_deal()

        assert backfill_called["value"] is True
        assert bot.status == Status.completed
        assert bot.deal.closing_price > 0
        assert bot.deal.closing_qty == 70

    def test_futures_order_updates_does_not_expire_protective_stop(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDT"])
        base.exchange = ExchangeId.KUCOIN
        base.interval = types.SimpleNamespace(get_ms=lambda: 15 * 60 * 1000)

        bot = self._make_bot(
            pair="BTCUSDT",
            position=Position.long,
            market_type=MarketType.FUTURES,
        )
        bot.orders = [
            OrderModel(
                order_id="trail-stop-1",
                order_type="market",
                pair="BTCUSDTM",
                timestamp=int(time.time() * 1000) - (60 * 60 * 1000),
                order_side="sell",
                qty=116,
                price=0.0713,
                status=OrderStatus.NEW,
                time_in_force="GTC",
                deal_type=DealType.trailing_profit,
            )
        ]

        deleted: list[str] = []
        saved: list[Any] = []
        updated: list[OrderModel] = []

        monkeypatch.setattr(
            OrderStatus,
            "map_from_kucoin_status",
            staticmethod(lambda _: OrderStatus.NEW),
        )
        monkeypatch.setattr(
            "streaming.futures_position.convert_to_kucoin_symbol",
            lambda _bot: "BTCUSDTM",
        )

        base.kucoin_futures_api.retrieve_order = lambda order_id: types.SimpleNamespace(
            status=types.SimpleNamespace(value="active"),
            filled_size=0,
            avg_deal_price=0,
            created_at=int(time.time() * 1000),
            price=0,
        )
        base.bot_controller.update_order = lambda order: updated.append(order)
        base.bot_controller.save = lambda *args, **kwargs: saved.append(
            kwargs.get("data") if "data" in kwargs else args[0]
        )

        fp = cast(Any, FuturesPosition.__new__(FuturesPosition))
        fp.base_streaming = base
        fp.active_bot = bot
        fp.price_precision = 4
        fp.qty_precision = 4
        fp.bot_crud = types.SimpleNamespace(
            delete_order=lambda order_id, bot_id: deleted.append(order_id)
        )
        fp.cancel_current_sl = lambda: deleted.append("cancel_current_sl")

        FuturesPosition.order_updates(fp)

        assert deleted == []
        assert updated == []
        assert saved == []
        assert bot.orders[0].qty == 116

    def test_futures_order_updates_does_not_cancel_live_stops_for_missing_protective_order(
        self, monkeypatch
    ):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDT"])
        base.exchange = ExchangeId.KUCOIN
        base.interval = types.SimpleNamespace(get_ms=lambda: 15 * 60 * 1000)

        bot = self._make_bot(
            pair="BTCUSDT",
            position=Position.long,
            market_type=MarketType.FUTURES,
        )
        bot.id = "bot-1"
        bot.orders = [
            OrderModel(
                order_id="missing-trail-stop",
                order_type="market",
                pair="BTCUSDTM",
                timestamp=int(time.time() * 1000) - (60 * 60 * 1000),
                order_side="sell",
                qty=116,
                price=0.0713,
                status=OrderStatus.NEW,
                time_in_force="GTC",
                deal_type=DealType.trailing_profit,
            )
        ]

        deleted: list[str] = []
        saved: list[Any] = []

        monkeypatch.setattr(
            "streaming.futures_position.convert_to_kucoin_symbol",
            lambda _bot: "BTCUSDTM",
        )
        base.kucoin_futures_api.retrieve_order = lambda order_id: (_ for _ in ()).throw(
            RestError(
                msg="not found",
                response=types.SimpleNamespace(code=100001, message="not found"),
            )
        )
        base.bot_controller.save = lambda *args, **kwargs: saved.append(
            kwargs.get("data") if "data" in kwargs else args[0]
        )

        fp = cast(Any, FuturesPosition.__new__(FuturesPosition))
        fp.base_streaming = base
        fp.active_bot = bot
        fp.price_precision = 4
        fp.qty_precision = 4
        fp.bot_crud = types.SimpleNamespace(
            delete_order=lambda order_id, bot_id: deleted.append(order_id)
        )
        fp.cancel_current_sl = lambda: deleted.append("cancel_current_sl")

        FuturesPosition.order_updates(fp)

        assert deleted == ["missing-trail-stop"]
        assert [order.order_id for order in bot.orders] == []
        assert saved == [bot]
