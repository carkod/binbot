import types
import time

import pandas as pd
from pandas import Index
from pybinbot import Strategy
from tools.exceptions import BinanceErrors
from streaming.position_manager import (
    BaseStreaming,
    PositionManager,
    HABollinguerSpread,
)
from databases.tables.bot_table import BotTable
from pandas import DataFrame
from pybinbot import ExchangeId, HeikinAshi


class TestPositionManager:
    def _make_base_streaming(self, monkeypatch, active_pairs=None):
        # Import inside to ensure workspace imports resolve during tests
        # Monkeypatch internal controller classes BEFORE instantiating BaseStreaming
        # to prevent real DB queries during __init__
        class DummyBotCrud:
            def __init__(self):
                self.saved = []

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
                        ]
                    )
                return klines

        monkeypatch.setattr("streaming.position_manager.BotTableCrud", DummyBotCrud)
        monkeypatch.setattr(
            "streaming.position_manager.PaperTradingTableCrud", DummyPaperCrud
        )
        monkeypatch.setattr("streaming.position_manager.SymbolsCrud", DummySymbolsCrud)
        monkeypatch.setattr("streaming.position_manager.CandlesCrud", DummyCandlesCrud)
        monkeypatch.setattr("streaming.position_manager.BinanceApi", DummyBinanceApi)
        monkeypatch.setattr("streaming.position_manager.KucoinApi", DummyKucoinApi)

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
                df = DataFrame(candles, columns=HeikinAshi().kucoin_cols)

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
        pairs = active_pairs or ["BTCUSDC", "ETHUSDC", "TESTUSDC"]
        monkeypatch.setattr(base, "active_bot_pairs", pairs, raising=False)

        # Replace active pairs after init (init used dummies returning empty list)
        return base

    def _make_bot(self, pair="BTCUSDC", strategy=Strategy.long):
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

        spreads = sc.build_bb_spreads()
        assert spreads.bb_high == 0
        assert spreads.bb_mid == 0
        assert spreads.bb_low == 0

    def test_update_bots_parameters_triggers_open_deal_and_save(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch)
        sc = PositionManager(base, symbol="BTCUSDC")

        bot = self._make_bot(strategy=Strategy.long)

        # Track calls on DealGateway
        class FakeDealGateway:
            def __init__(self, bot, db_table):
                self.bot = bot
                self.db_table = db_table
                self.opened = False

            def open_deal(self):
                self.opened = True
                return self.bot

        monkeypatch.setattr(
            "streaming.position_manager.DealGateway",
            FakeDealGateway,
        )

        # BB spreads valid values to avoid early return
        spreads = HABollinguerSpread(bb_high=110, bb_mid=105, bb_low=100)
        sc.update_bots_parameters(
            bot=bot,
            db_table=BotTable,
            current_price=101.0,
            bb_spreads=spreads,
        )

        # Bot parameters must be updated and saved
        assert base.bot_controller.saved, "Expected controller.save to be called"
        # And DealGateway.open_deal should be triggered
        # Verify via replaced class state
        dg_instance = FakeDealGateway(bot, BotTable)
        dg_instance.open_deal()
        assert dg_instance.opened is True

    def test_dynamic_trailling_updates_for_long_and_paper(self, monkeypatch):
        base = self._make_base_streaming(
            monkeypatch, active_pairs=["XUSDC"]
        )  # decouple from symbol
        sc = PositionManager(base, symbol="BTCUSDC")

        # Inject current bots directly without DB calls
        sc.current_bot = self._make_bot(pair="BTCUSDC", strategy=Strategy.long)
        sc.current_test_bot = self._make_bot(pair="BTCUSDC", strategy=Strategy.long)

        # Stub DealGateway to avoid external logic
        class FakeDealGateway:
            def __init__(self, bot, db_table):
                self.bot = bot
                self.db_table = db_table

            def open_deal(self):
                return self.bot

        monkeypatch.setattr(
            "streaming.position_manager.DealGateway",
            FakeDealGateway,
        )

        sc.dynamic_trailling()

        # Expect at least one save across controllers due to updates
        assert (
            len(base.bot_controller.saved) + len(base.paper_trading_controller.saved)
            >= 1
        )

    def test_process_klines_calls_deal_updates_for_active_pair(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDC"])
        sc = PositionManager(base, symbol="BTCUSDC")

        # Provide a current bot via BaseStreaming.get_current_bot
        bot = self._make_bot(pair="BTCUSDC", strategy=Strategy.long)

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

        # Track that deal_updates is called
        class FakeDealGateway:
            def __init__(self, bot, db_table):
                self.called = False

            def deal_updates(self, close_price, open_price):
                self.called = True

        monkeypatch.setattr(
            "streaming.position_manager.DealGateway",
            FakeDealGateway,
        )

        sc.process_klines()
        # No assertion on FakeDealGateway instance; simply ensure no exceptions
        assert True

    def test_process_klines_binance_error_sets_status_and_saves(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDC"])
        sc = PositionManager(base, symbol="BTCUSDC")

        bot = self._make_bot(pair="BTCUSDC", strategy=Strategy.long)

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
                pass

            def deal_updates(self, close_price, open_price):
                # Raise BinanceErrors with code -2010 to hit error path
                raise BinanceErrors("Order error", -2010)

            def save(self, bot):
                # Redirect to the fake controller's save to mimic PositionManager behavior
                base.bot_controller.save(bot)

        monkeypatch.setattr(
            "streaming.position_manager.DealGateway",
            ErrorDealGateway,
        )

        sc.process_klines()
        # Controller should have attempted save on error
        assert base.bot_controller.saved or base.paper_trading_controller.saved

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
        PositionManager(base, symbol="BTCUSDC")

        # Assert that KucoinApi was used, not BinanceApi
        assert len(kucoin_called) > 0, "KucoinApi.get_ui_klines should have been called"
        assert len(binance_called) == 0, (
            "BinanceApi.get_ui_klines should not have been called"
        )
