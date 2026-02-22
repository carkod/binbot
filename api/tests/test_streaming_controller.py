import types
import time

import pandas as pd
from pandas import Index
from typing import cast
from pybinbot import Strategy, Status, MarketType
from streaming.apex_flow_closing import ApexFlowClose
from streaming.position_manager import (
    PositionManager,
    HABollinguerSpread,
)
from streaming.base import BaseStreaming
from databases.tables.bot_table import BotTable
from pandas import DataFrame
from pybinbot import ExchangeId, HeikinAshi, BinanceErrors


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

        class DummyCandlesCrud:
            pass

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
        monkeypatch.setattr("streaming.base.CandlesCrud", DummyCandlesCrud)
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

        def patched_pre_process(self, exchange, candles):
            from pandas import to_datetime
            from typing import cast

            if exchange == ExchangeId.BINANCE:
                # Binance API may return extra columns; only take the expected ones
                df_raw = DataFrame(candles)
                cols = HeikinAshi().binance_cols
                df = df_raw.iloc[:, : len(cols)]
                df.columns = Index(cols)
            else:
                df_raw = DataFrame(candles)
                kucoin_cols = HeikinAshi().kucoin_cols
                if df_raw.shape[1] == len(kucoin_cols):
                    df_raw.columns = Index(kucoin_cols)
                elif df_raw.shape[1] == len(kucoin_cols) - 1:
                    # Recent Kucoin klines omit close_time; derive it from open_time
                    df_raw.columns = Index(kucoin_cols[:-1])
                    df_raw["close_time"] = df_raw["open_time"]
                else:
                    raise ValueError(
                        f"Unexpected KuCoin dummy kline column count: {df_raw.shape[1]}"
                    )
                df = df_raw

            # Convert numeric columns
            numeric_cols = ["open", "high", "low", "close", "volume"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # Set timestamp index for resampling
            df["timestamp"] = to_datetime(df["close_time"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df = df.sort_index()

            # Create aggregation dictionary
            resample_aggregation = {
                "open": "first",
                "close": "last",
                "high": "max",
                "low": "min",
                "volume": "sum",
                "close_time": "first",
                "open_time": "first",
            }

            # Resample to 4h and 1h
            df_4h = df.resample("4h").agg(cast(dict, resample_aggregation))
            df_1h = df.resample("1h").agg(cast(dict, resample_aggregation))

            return df, df_1h, df_4h

        monkeypatch.setattr(HeikinAshi, "pre_process", patched_pre_process)

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
        strategy=Strategy.long,
        market_type=MarketType.SPOT,
    ):
        # Lightweight BotModel-like object for tests
        bot = types.SimpleNamespace()
        bot.name = "apex_aggressive_momo"
        bot.pair = pair
        bot.fiat = "USDC"
        bot.strategy = strategy
        bot.dynamic_trailling = True
        bot.trailling = False
        bot.trailling_profit = 0.0
        bot.trailling_deviation = 0.0
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
        sc = PositionManager(base, symbol="BTCUSDC")
        sc.dataframe_ops()

        spreads = sc.build_bb_spreads()
        assert spreads.bb_high == 0
        assert spreads.bb_mid == 0
        assert spreads.bb_low == 0

    def test_market_trailing_analytics_updates_bot_parameters_and_saves(
        self, monkeypatch
    ):
        base = self._make_base_streaming(monkeypatch)
        sc = PositionManager(base, symbol="BTCUSDC")

        bot = self._make_bot(strategy=Strategy.long)

        # Force deterministic spreads and ApexFlow context
        monkeypatch.setattr(
            sc,
            "build_bb_spreads",
            lambda: HABollinguerSpread(bb_high=110, bb_mid=105, bb_low=100),
            raising=False,
        )
        sc.apex_flow_closing = cast(
            ApexFlowClose,
            types.SimpleNamespace(
                df=pd.DataFrame([{"high": 110.0, "low": 100.0}]),
                get_detectors=lambda: {"vce": True, "mcd": False, "lcrs": False},
                get_trend_ema=lambda: (2.0, 1.0),
            ),
        )

        sc.market_trailing_analytics(
            bot=bot,
            db_table=BotTable,
            current_price=101.0,
        )

        # Bot parameters must be updated and saved
        assert base.bot_controller.saved, "Expected controller.save to be called"
        saved_bot = base.bot_controller.saved[0]
        assert saved_bot.trailling_profit > 0
        assert saved_bot.trailling_deviation > 0

    def test_process_deal_runs_trailing_before_deal_exit(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDC"])
        # Set exchange to KUCOIN to avoid NotImplementedError for order updates
        from pybinbot import ExchangeId

        base.exchange = ExchangeId.KUCOIN
        sc = PositionManager(base, symbol="BTCUSDC")

        live_bot = self._make_bot(pair="BTCUSDC", strategy=Strategy.long)
        live_bot.dynamic_trailling = True

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

        call_order = []

        def fake_market(self, bot, db_table, current_price):
            call_order.append("trailing")
            assert bot is live_bot

        monkeypatch.setattr(
            PositionManager,
            "market_trailing_analytics",
            fake_market,
        )

        class FakeDealGateway:
            exit_calls: list[tuple[float, float]] = []

            def __init__(self, bot, db_table):
                self.bot = bot
                self.db_table = db_table

            def deal_exit_orchestration(self, close_price, open_price):
                call_order.append("deal_exit")
                FakeDealGateway.exit_calls.append((close_price, open_price))

            def save(self, bot):
                base.bot_controller.save(bot)

        monkeypatch.setattr(
            "streaming.position_manager.DealGateway",
            FakeDealGateway,
        )

        # Mock order_updates to prevent it from doing anything
        monkeypatch.setattr(
            PositionManager,
            "order_updates",
            lambda self, bot: bot,
        )

        sc.process_deal()

        assert call_order.count("trailing") == 1
        assert call_order.index("trailing") < call_order.index("deal_exit")
        assert FakeDealGateway.exit_calls, (
            "Expected deal_exit_orchestration to be called"
        )

    def test_process_deal_calls_deal_exit_orchestration_for_active_pair(
        self, monkeypatch
    ):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDC"])
        # Set exchange to KUCOIN to avoid NotImplementedError for order updates
        from pybinbot import ExchangeId

        base.exchange = ExchangeId.KUCOIN
        sc = PositionManager(base, symbol="BTCUSDC")

        # Provide a current bot via BaseStreaming.get_current_bot
        bot = self._make_bot(pair="BTCUSDC", strategy=Strategy.long)
        bot.dynamic_trailling = False

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

            def __init__(self, bot, db_table):
                self.bot = bot
                self.db_table = db_table

            def deal_exit_orchestration(self, close_price, open_price):
                FakeDealGateway.exit_calls.append((close_price, open_price))

            def save(self, bot):
                base.bot_controller.save(bot)

        monkeypatch.setattr(
            "streaming.position_manager.DealGateway",
            FakeDealGateway,
        )

        # Mock order_updates to prevent it from doing anything
        monkeypatch.setattr(
            PositionManager,
            "order_updates",
            lambda self, bot: bot,
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

        bot = self._make_bot(pair="BTCUSDC", strategy=Strategy.long)
        bot.dynamic_trailling = False

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
            def __init__(self, bot, db_table):
                self.bot = bot
                self.db_table = db_table

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

        # Mock order_updates to prevent it from doing anything
        monkeypatch.setattr(
            PositionManager,
            "order_updates",
            lambda self, bot: bot,
        )

        sc.process_deal()
        # Controller should have attempted save on error and status updated
        assert base.bot_controller.saved or base.paper_trading_controller.saved
        assert bot.status == Status.error

    def test_process_deal_calls_futures_order_updates_for_futures_bot(
        self, monkeypatch
    ):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDC"])
        from pybinbot import ExchangeId

        base.exchange = ExchangeId.KUCOIN
        sc = PositionManager(base, symbol="BTCUSDC")

        futures_bot = self._make_bot(
            pair="BTCUSDC",
            strategy=Strategy.long,
            market_type=MarketType.FUTURES,
        )
        futures_bot.dynamic_trailling = False

        monkeypatch.setattr(
            BaseStreaming,
            "get_current_bot",
            lambda self, symbol: futures_bot,
        )
        monkeypatch.setattr(
            BaseStreaming,
            "get_current_test_bot",
            lambda self, symbol: None,
        )

        call_order: list[str] = []

        def fake_futures_updates(self, bot):
            call_order.append("futures")
            return bot

        def fake_order_updates(self, bot):
            call_order.append("spot")
            return bot

        monkeypatch.setattr(
            PositionManager,
            "futures_order_updates",
            fake_futures_updates,
        )
        monkeypatch.setattr(PositionManager, "order_updates", fake_order_updates)

        class FakeDealGateway:
            exit_calls: list[tuple[float, float]] = []

            def __init__(self, bot, db_table):
                self.bot = bot
                self.db_table = db_table

            def deal_exit_orchestration(self, close_price, open_price):
                FakeDealGateway.exit_calls.append((close_price, open_price))

            def save(self, bot):
                base.bot_controller.save(bot)

        monkeypatch.setattr(
            "streaming.position_manager.DealGateway",
            FakeDealGateway,
        )

        sc.process_deal()

        assert call_order == ["futures"]
        assert FakeDealGateway.exit_calls, (
            "Expected deal_exit_orchestration to be called for futures bots"
        )

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
        sc = PositionManager(base, symbol="BTCUSDC")
        sc.dataframe_ops()

        # Assert that KucoinApi was used, not BinanceApi
        assert len(kucoin_called) > 0, "KucoinApi.get_ui_klines should have been called"
        assert len(binance_called) == 0, (
            "BinanceApi.get_ui_klines should not have been called"
        )
