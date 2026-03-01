from copy import deepcopy
from typing import Type, Union
from pandas import DataFrame
from deals.gateway import DealGateway
from bots.models import BotModel
from databases.crud.autotrade_crud import AutotradeCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from pybinbot import (
    Strategy,
    MarketType,
    ExchangeId,
    BinanceApi,
    KucoinApi,
    HABollinguerSpread,
    Indicators,
    HeikinAshi,
    round_numbers,
)
from streaming.apex_flow_closing import ApexFlowClose
from streaming.base import BaseStreaming
from streaming.futures_position import FuturesPosition
from streaming.spot_position import SpotPosition
from exchange_apis.kucoin.futures.futures_deal import KucoinFutures


class PositionManager:
    def __init__(self, base: BaseStreaming, symbol: str) -> None:
        super().__init__()
        # Gets any signal to restart streaming
        self.autotrade_controller = AutotradeCrud()
        self.symbol_data = base.symbols_crud.get_symbol(symbol)
        self.autotrade_settings = self.autotrade_controller.get_settings()
        self.price_precision = self.symbol_data.price_precision
        self.qty_precision = self.symbol_data.qty_precision
        self.base_streaming = base
        self.symbol = symbol
        self.api: Union[BinanceApi, KucoinApi, KucoinFutures] = self._default_api()

        self.current_bot: BotModel | None = None
        self.current_test_bot: BotModel | None = None
        self.klines: list[list[float]] = []
        self.btc_klines: list[list[float]] = []
        self.df = DataFrame()
        self.btc_df = DataFrame()
        self.apex_flow_closing: ApexFlowClose | None = None

    def load_current_bots(self) -> None:
        current_bot_payload = self.base_streaming.get_current_bot(self.symbol)
        if current_bot_payload:
            self.current_bot = BotModel.model_validate(current_bot_payload)

        current_test_bot_payload = self.base_streaming.get_current_test_bot(self.symbol)
        if current_test_bot_payload:
            self.current_test_bot = BotModel.model_validate(current_test_bot_payload)

    def _default_api(self) -> Union[BinanceApi, KucoinApi, KucoinFutures]:
        if self.base_streaming.exchange == ExchangeId.KUCOIN:
            return self.base_streaming.kucoin_api
        return self.base_streaming.binance_api

    def _resolve_controller(self, db_table: Type[BotTable] | Type[PaperTradingTable]):
        return (
            self.base_streaming.bot_controller
            if db_table == BotTable
            else self.base_streaming.paper_trading_controller
        )

    def _create_position_handler(
        self, bot: BotModel, db_table: Type[BotTable] | Type[PaperTradingTable]
    ) -> Union[SpotPosition, FuturesPosition]:
        handler_cls: type[SpotPosition] | type[FuturesPosition]
        if bot.market_type == MarketType.FUTURES:
            handler_cls = FuturesPosition
        else:
            handler_cls = SpotPosition
        return handler_cls(
            base_streaming=self.base_streaming,
            bot=bot,
            price_precision=self.price_precision,
            qty_precision=self.qty_precision,
            db_table=db_table,
        )

    def process_deal(self) -> None:
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        if (
            self.base_streaming.exchange == ExchangeId.KUCOIN
            and not self.symbol.endswith("USDTM")
        ):
            converted_symbol = (
                self.symbol_data.base_asset + "-" + self.symbol_data.quote_asset
            )
        else:
            converted_symbol = self.symbol

        if converted_symbol not in self.base_streaming.active_bot_pairs:
            return

        self.current_bot = self.base_streaming.get_current_bot(converted_symbol)
        self.current_test_bot = self.base_streaming.get_current_test_bot(
            converted_symbol
        )

        bot: BotModel | None
        db_table: Type[BotTable] | Type[PaperTradingTable]

        if self.current_bot:
            bot = self.current_bot
            db_table = BotTable
        elif self.current_test_bot:
            bot = self.current_test_bot
            db_table = PaperTradingTable
        else:
            return

        deal = DealGateway(bot=bot, db_table=db_table)

        if self.base_streaming.exchange != ExchangeId.KUCOIN:
            raise NotImplementedError("Order updates only implemented for Kucoin")

        position_handler = self._create_position_handler(bot, db_table)
        position_handler.order_updates()

        deal.deal_exit_orchestration(0, 0)

    def dataframe_ops(self):
        if not self.api:
            raise ValueError("API client is not configured for PositionManager")

        interval = str(self.base_streaming.interval.value)
        self.klines = self.api.get_ui_klines(
            symbol=self.symbol,
            interval=interval,
        )

        benchmark_symbol = (
            self.base_streaming.kucoin_benchmark_symbol
            if self.base_streaming.exchange == ExchangeId.KUCOIN
            else self.base_streaming.benchmark_symbol
        )

        self.btc_klines = self.api.get_ui_klines(
            symbol=benchmark_symbol,
            interval=interval,
        )

        candles = self.klines.copy()
        df, _, _ = HeikinAshi().pre_process(
            exchange=self.base_streaming.exchange,
            candles=candles,
        )
        btc_candles = self.btc_klines.copy()
        btc_df, _, _ = HeikinAshi().pre_process(
            exchange=self.base_streaming.exchange,
            candles=btc_candles,
        )

        self.df = Indicators.bollinguer_spreads(df)
        self.btc_df = Indicators.bollinguer_spreads(btc_df, window=20)

        self.df = HeikinAshi().post_process(self.df)
        self.btc_df = HeikinAshi().post_process(self.btc_df)

        if self.apex_flow_closing is None:
            self.apex_flow_closing = ApexFlowClose(self.df, self.btc_df)

        return self.df, self.btc_df

    def build_bb_spreads(self) -> HABollinguerSpread:
        if not self.klines:
            return HABollinguerSpread(bb_high=0, bb_mid=0, bb_low=0)

        if not self.df or len(self.klines) < 200:
            return HABollinguerSpread(bb_high=0, bb_mid=0, bb_low=0)

        return HABollinguerSpread(
            bb_high=self.df["bb_upper"].iloc[-1],
            bb_mid=self.df["bb_mid"].iloc[-1],
            bb_low=self.df["bb_lower"].iloc[-1],
        )

    def set_long_trail_params(
        self,
        top_spread: float,
        bottom_spread: float,
        bot_profit: float,
        bot: BotModel,
        expansion_multiplier: float,
        is_aggressive_momo: bool,
        expansion_range: float,
        trail_tighten_mult: float,
    ) -> None:
        raw_trail_profit = top_spread * trail_tighten_mult * expansion_multiplier

        if bot_profit >= 5:
            raw_trail_profit = min(raw_trail_profit, 2.0)
        elif bot_profit >= 3:
            raw_trail_profit = min(raw_trail_profit, 3.0)

        bot.trailling_profit = round_numbers(max(0.6, raw_trail_profit), 2)
        bot.trailling_deviation = round_numbers(
            max(0.6, bottom_spread * trail_tighten_mult),
            2,
        )

        if bot.stop_loss == 0:
            if is_aggressive_momo:
                bot.stop_loss = round_numbers(
                    bot.deal.opening_price - (expansion_range * 0.5),
                    self.symbol_data.price_precision,
                )
            else:
                bot.stop_loss = round_numbers(
                    bot.deal.opening_price * (1 - 0.03),
                    self.symbol_data.price_precision,
                )

    def market_trailing_analytics(
        self,
        bot: BotModel,
        db_table: Type[BotTable] | Type[PaperTradingTable],
        current_price: float,
    ) -> None:
        self.dataframe_ops()

        if self.apex_flow_closing is None:
            self.apex_flow_closing = ApexFlowClose(self.df, self.btc_df)

        controller = self._resolve_controller(db_table)
        original_bot = deepcopy(bot)

        bb_spreads = self.build_bb_spreads()
        if bb_spreads.bb_high == 0 or bb_spreads.bb_low == 0:
            return

        top_spread = (
            abs((bb_spreads.bb_high - bb_spreads.bb_mid) / bb_spreads.bb_high) * 100
        )
        bottom_spread = (
            abs((bb_spreads.bb_mid - bb_spreads.bb_low) / bb_spreads.bb_mid) * 100
        )

        top_spread = min(max(top_spread, 1.5), 6.0)
        bottom_spread = min(max(bottom_spread, 1.0), 4.0)

        bot_profit = self.base_streaming.compute_single_bot_profit(bot, current_price)

        row = self.apex_flow_closing.df.iloc[-1]
        detectors = self.apex_flow_closing.get_detectors()

        vce_signal = detectors.get("vce", False)
        mcd_signal = detectors.get("mcd", False)
        lcrs_signal = detectors.get("lcrs", False)

        expansion_range = row["high"] - row["low"]
        is_aggressive_momo = bot.name.lower().find("aggressive momo") != -1

        ema_fast, ema_slow = self.apex_flow_closing.get_trend_ema()
        trend_up = ema_fast > ema_slow if ema_fast and ema_slow else True

        expansion_multiplier = 1.0
        if vce_signal:
            expansion_multiplier += 0.2
        if mcd_signal:
            expansion_multiplier += 0.1
        expansion_multiplier = min(expansion_multiplier, 1.5)

        if bot_profit < 2:
            trail_tighten_mult = 1.0
        elif bot_profit < 5:
            trail_tighten_mult = 0.7
        else:
            trail_tighten_mult = 0.45

        if (vce_signal or mcd_signal or lcrs_signal) and trend_up:
            trail_tighten_mult = max(trail_tighten_mult, 0.7)

        if bot.strategy == Strategy.long:
            self.set_long_trail_params(
                top_spread=top_spread,
                bottom_spread=bottom_spread,
                bot_profit=bot_profit,
                bot=bot,
                expansion_multiplier=expansion_multiplier,
                is_aggressive_momo=is_aggressive_momo,
                expansion_range=expansion_range,
                trail_tighten_mult=trail_tighten_mult,
            )

        if (
            bot.trailling_profit != original_bot.trailling_profit
            or bot.trailling_deviation != original_bot.trailling_deviation
            or bot.stop_loss != original_bot.stop_loss
        ):
            controller.save(bot)
