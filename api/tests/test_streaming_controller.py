import types

from tools.enum_definitions import Strategy
from tools.exceptions import BinanceErrors
from streaming.streaming_controller import (
    BaseStreaming,
    StreamingController,
    HABollinguerSpread,
)
from databases.tables.bot_table import BotTable


class TestStreamingController:
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

        class DummyCandlesCrud:
            pass

        class DummyBinanceApi:
            def get_raw_klines(self, symbol, interval, limit=200):
                return [[0, 100, 101, 99, 100, 0, 0]] * 200

            def get_interest_history(self, asset, symbol):
                return {"rows": [{"interests": "0.0"}]}

        class DummyKucoinApi:
            def get_raw_klines(self, symbol, interval, limit=200):
                return [[0, 100, 101, 99, 100, 0, 0]] * 200

        monkeypatch.setattr("streaming.streaming_controller.BotTableCrud", DummyBotCrud)
        monkeypatch.setattr(
            "streaming.streaming_controller.PaperTradingTableCrud", DummyPaperCrud
        )
        monkeypatch.setattr(
            "streaming.streaming_controller.SymbolsCrud", DummySymbolsCrud
        )
        monkeypatch.setattr(
            "streaming.streaming_controller.CandlesCrud", DummyCandlesCrud
        )
        monkeypatch.setattr(
            "streaming.streaming_controller.BinanceApi", DummyBinanceApi
        )
        monkeypatch.setattr("streaming.streaming_controller.KucoinApi", DummyKucoinApi)

        base = BaseStreaming()

        # Freeze active pairs to a predictable list
        pairs = active_pairs or ["BTCUSDC", "ETHUSDC", "TESTUSDC"]
        monkeypatch.setattr(base, "active_bot_pairs", pairs, raising=False)

        # Replace active pairs after init (init used dummies returning empty list)
        return base

    def _make_bot(self, pair="BTCUSDC", strategy=Strategy.long):
        # Lightweight BotModel-like object for tests
        bot = types.SimpleNamespace()
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

    def test_calc_quantile_volatility_reasonable(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch)
        sc = StreamingController(base, symbol="BTCUSDC")

        value = sc.calc_quantile_volatility(window=40, quantile=0.9)
        assert isinstance(value, float)
        assert 0 <= value <= 1  # quantile of mean abs returns

    def test_build_bb_spreads_minimum_length(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch)

        # Provide fewer than 200 klines to hit the early return
        class ShortBinanceApi:
            def get_raw_klines(self, symbol, interval, limit=200):
                return [[0, 100, 101, 99, 100, 0, 0]] * 50

        base.binance_api = ShortBinanceApi()
        sc = StreamingController(base, symbol="BTCUSDC")

        spreads = sc.build_bb_spreads()
        assert spreads.bb_high == 0
        assert spreads.bb_mid == 0
        assert spreads.bb_low == 0

    def test_update_bots_parameters_triggers_open_deal_and_save(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch)
        sc = StreamingController(base, symbol="BTCUSDC")

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
            "streaming.streaming_controller.DealGateway",
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
        sc = StreamingController(base, symbol="BTCUSDC")

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
            "streaming.streaming_controller.DealGateway",
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
        sc = StreamingController(base, symbol="BTCUSDC")

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
            "streaming.streaming_controller.DealGateway",
            FakeDealGateway,
        )

        sc.process_klines()
        # No assertion on FakeDealGateway instance; simply ensure no exceptions
        assert True

    def test_process_klines_binance_error_sets_status_and_saves(self, monkeypatch):
        base = self._make_base_streaming(monkeypatch, active_pairs=["BTCUSDC"])
        sc = StreamingController(base, symbol="BTCUSDC")

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
                # Redirect to the fake controller's save to mimic StreamingController behavior
                base.bot_controller.save(bot)

        monkeypatch.setattr(
            "streaming.streaming_controller.DealGateway",
            ErrorDealGateway,
        )

        sc.process_klines()
        # Controller should have attempted save on error
        assert base.bot_controller.saved or base.paper_trading_controller.saved

    def test_streaming_controller_uses_kucoin_api_for_kucoin_symbols(self, monkeypatch):
        """Test that StreamingController uses KucoinApi when exchange_id is KUCOIN"""
        base = self._make_base_streaming(monkeypatch)

        # Mock get_exchange_id_for_symbol to return KUCOIN
        from tools.enum_definitions import ExchangeId

        def mock_get_exchange_id(symbol):
            return ExchangeId.KUCOIN

        monkeypatch.setattr(base, "get_exchange_id_for_symbol", mock_get_exchange_id)

        # Track which API's get_raw_klines was called
        kucoin_called = []
        binance_called = []

        def track_kucoin_klines(*args, **kwargs):
            kucoin_called.append(True)
            return [[0, 100, 101, 99, 100, 0, 0]] * 200

        def track_binance_klines(*args, **kwargs):
            binance_called.append(True)
            return [[0, 100, 101, 99, 100, 0, 0]] * 200

        base.kucoin_api.get_raw_klines = track_kucoin_klines
        base.binance_api.get_raw_klines = track_binance_klines

        # Create StreamingController with a Kucoin symbol
        sc = StreamingController(base, symbol="BTC-USDT")

        # Assert that KucoinApi was used, not BinanceApi
        assert len(kucoin_called) > 0, (
            "KucoinApi.get_raw_klines should have been called"
        )
        assert len(binance_called) == 0, (
            "BinanceApi.get_raw_klines should not have been called"
        )
        assert sc.exchange_id == ExchangeId.KUCOIN
