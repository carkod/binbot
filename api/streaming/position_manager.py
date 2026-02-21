import logging
from datetime import datetime
from typing import Type, Union

from streaming.apex_flow_closing import ApexFlowClose
from deals.gateway import DealGateway
from bots.models import BotModel
from databases.crud.autotrade_crud import AutotradeCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from pybinbot import (
    DealType,
    KucoinKlineIntervals,
    OrderStatus,
    Status,
    Strategy,
    ExchangeId,
    round_numbers,
    BinanceKlineIntervals,
    Indicators,
    HeikinAshi,
    BinanceErrors,
    BinanceApi,
    KucoinApi,
    HABollinguerSpread,
    convert_to_kucoin_symbol,
    MarketType,
)
from copy import deepcopy
from streaming.base import BaseStreaming
from kucoin_universal_sdk.model.common import RestError
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
        self.benchmark_symbol = "BTCUSDT"
        self.kucoin_benchmark_symbol = "BTC-USDT"
        self.api: Union[BinanceApi, KucoinApi, KucoinFutures]

        binance_interval = BinanceKlineIntervals(
            self.autotrade_settings.candlestick_interval
        )
        kucoin_interval = KucoinKlineIntervals(
            BinanceKlineIntervals.to_kucoin_interval(binance_interval)
        )
        self.interval: Union[BinanceKlineIntervals, KucoinKlineIntervals]
        # Prepare interval based on exchange
        if self.base_streaming.exchange == ExchangeId.KUCOIN:
            self.interval = kucoin_interval
            if self.symbol.endswith("USDTM"):
                self.api = self.base_streaming.kucoin_futures_api
                # there's no BTCUSDTM
                self.kucoin_benchmark_symbol = "ETHBTCUSDTM"
            else:
                self.api = self.base_streaming.kucoin_api

        else:
            self.interval = binance_interval
            self.api = self.base_streaming.binance_api

        self.current_bot: BotModel | None = None
        self.current_test_bot: BotModel | None = None

    def dataframe_ops(self) -> None:
        """
        Converts klines to DataFrame for indicator calculations
        """

        # Get klines from the appropriate exchange
        self.klines = self.api.get_ui_klines(
            symbol=self.symbol,
            interval=str(self.interval.value),
        )
        self.btc_klines = self.api.get_ui_klines(
            symbol=self.kucoin_benchmark_symbol
            if self.base_streaming.exchange == ExchangeId.KUCOIN
            else self.benchmark_symbol,
            interval=str(self.interval.value),
        )
        candles = self.klines.copy()
        df, _, _ = HeikinAshi().pre_process(
            exchange=self.base_streaming.exchange, candles=candles
        )
        self.df = df
        btc_candles = self.btc_klines.copy()
        btc_df, _, _ = HeikinAshi().pre_process(
            exchange=self.base_streaming.exchange, candles=btc_candles
        )
        self.btc_df = btc_df

        self.df = Indicators.bollinguer_spreads(self.df)
        self.btc_df = Indicators.bollinguer_spreads(self.btc_df, window=20)

        self.df = HeikinAshi().post_process(self.df)
        self.btc_df = HeikinAshi().post_process(self.btc_df)

    def load_current_bots(self, symbol: str) -> None:
        try:
            current_bot_payload = self.base_streaming.get_current_bot(symbol)
            if current_bot_payload:
                self.current_bot = BotModel.model_validate(current_bot_payload)

            current_test_bot_payload = self.base_streaming.get_current_test_bot(symbol)
            if current_test_bot_payload:
                self.current_test_bot = BotModel.model_validate(
                    current_test_bot_payload
                )

        except ValueError:
            pass
        except Exception as e:
            logging.error(e)
            pass

    def build_bb_spreads(self) -> HABollinguerSpread:
        """
        Builds the bollinguer bands spreads without using pandas_ta
        """
        data = self.klines
        if len(data) < 200:
            return HABollinguerSpread(bb_high=0, bb_mid=0, bb_low=0)

        bb_spreads = HABollinguerSpread(
            bb_high=self.df["bb_upper"].iloc[-1],
            bb_mid=self.df["bb_mid"].iloc[-1],
            bb_low=self.df["bb_lower"].iloc[-1],
        )

        return bb_spreads

    def get_interests_short_margin(self, bot: BotModel) -> tuple[float, float, float]:
        close_timestamp = bot.deal.closing_timestamp
        if close_timestamp == 0:
            close_timestamp = int(datetime.now().timestamp() * 1000)

        asset = bot.pair.split(bot.fiat)[0]
        interest_details = self.base_streaming.binance_api.get_interest_history(
            asset=asset, symbol=bot.pair
        )

        if len(interest_details["rows"]) > 0:
            interests = float(interest_details["rows"][0]["interests"])
        else:
            interests = 0

        close_total = bot.deal.closing_price
        open_total = bot.deal.closing_price

        return interests, open_total, close_total

    def compute_single_bot_profit(self, bot: BotModel, current_price: float) -> float:
        if bot.deal and bot.deal.base_order_size > 0:
            price = (
                bot.deal.closing_price if bot.deal.closing_price > 0 else current_price
            )
            if bot.deal.opening_price > 0:
                buy_price = bot.deal.opening_price
                profit_change = ((price - buy_price) / buy_price) * 100
                if price == 0:
                    profit_change = 0
                return round_numbers(profit_change)
            elif bot.deal.opening_price > 0:
                # Completed margin short
                if bot.deal.closing_price > 0:
                    interests, open_total, close_total = (
                        self.get_interests_short_margin(bot)
                    )
                    profit_change = (
                        (open_total - close_total) / open_total - interests
                    ) * 100
                    return round(profit_change, 2)
                else:
                    # Not completed margin short
                    close_price = (
                        bot.deal.closing_price
                        if bot.deal.closing_price > 0
                        else current_price or bot.deal.current_price
                    )
                    if close_price == 0:
                        return 0
                    interests, open_total, close_total = (
                        self.get_interests_short_margin(bot)
                    )
                    profit_change = (
                        (open_total - close_price) / open_total - interests
                    ) * 100
                    return round(profit_change, 2)
            else:
                return 0
        else:
            return 0

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
        """
        LONG trailing logic.

        Rules:
        - stop_loss is a fixed safety net (handled elsewhere, never trailed)
        - trailing_profit is a ceiling trigger only
        - trailing_deviation is the real stop once trailing starts
        """
        raw_trail_profit = top_spread * trail_tighten_mult * expansion_multiplier

        # Progressive tightening as profits grow
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
        db_table: Type[Union[PaperTradingTable, BotTable]],
        current_price: float,
    ) -> None:
        """
        ApexFlow-aware trailing manager.

        Philosophy:
        - stop_loss = emergency only
        - trailing_deviation = active stop after trailing
        - trailing_profit = trigger, never exit
        """

        controller = (
            self.base_streaming.bot_controller
            if db_table == BotTable
            else self.base_streaming.paper_trading_controller
        )

        original_bot = deepcopy(bot)

        # ─────────────────────────────
        # Bollinger spreads
        # ─────────────────────────────
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

        # ─────────────────────────────
        # Profit
        # ─────────────────────────────
        bot_profit = self.compute_single_bot_profit(bot, current_price)

        # ─────────────────────────────
        # ApexFlow detectors
        # ─────────────────────────────
        row = self.apex_flow_closing.df.iloc[-1]
        detectors = self.apex_flow_closing.get_detectors()

        vce_signal = detectors.get("vce", False)
        mcd_signal = detectors.get("mcd", False)
        lcrs_signal = detectors.get("lcrs", False)

        expansion_range = row["high"] - row["low"]
        is_aggressive_momo = bot.name.lower().find("aggressive momo") != -1

        # ─────────────────────────────
        # Trend filter (only for tightening)
        # ─────────────────────────────
        ema_fast, ema_slow = self.apex_flow_closing.get_trend_ema()
        trend_up = ema_fast > ema_slow if ema_fast and ema_slow else True

        # ─────────────────────────────
        # Expansion multiplier
        # ─────────────────────────────
        expansion_multiplier = 1.0
        if vce_signal:
            expansion_multiplier += 0.2
        if mcd_signal:
            expansion_multiplier += 0.1
        expansion_multiplier = min(expansion_multiplier, 1.5)

        # ─────────────────────────────
        # Trailing tightening schedule
        # ─────────────────────────────
        if bot_profit < 2:
            trail_tighten_mult = 1.0
        elif bot_profit < 5:
            trail_tighten_mult = 0.7
        else:
            trail_tighten_mult = 0.45

        # Do not tighten against trend while signals are alive
        if (vce_signal or mcd_signal or lcrs_signal) and trend_up:
            trail_tighten_mult = max(trail_tighten_mult, 0.7)

        # ─────────────────────────────
        # Apply strategy-specific logic
        # ─────────────────────────────
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

        # ─────────────────────────────
        # Persist only if changed
        # ─────────────────────────────
        if (
            bot.trailling_profit != original_bot.trailling_profit
            or bot.trailling_deviation != original_bot.trailling_deviation
            or bot.stop_loss != original_bot.stop_loss
        ):
            controller.save(bot)

    def order_updates(self, bot: BotModel) -> BotModel:
        """
        Take order id from list of bot.orders
        and fetch order details from exchange
        """
        for order in bot.orders:
            if (
                self.base_streaming.exchange == ExchangeId.KUCOIN
                and order.status != OrderStatus.FILLED
            ):
                kucoin_symbol = convert_to_kucoin_symbol(bot)
                system_order = self.base_streaming.kucoin_api.get_order(
                    symbol=kucoin_symbol,
                    order_id=str(order.order_id),
                )

                # Check if order is expired based on 15m interval
                # this should be a good measure, because candles have closed
                interval_ms = self.base_streaming.interval.get_ms()
                now_ms = int(datetime.now().timestamp() * 1000)
                order_ms = int(order.timestamp * 1000)
                is_expired = (now_ms - order_ms) > interval_ms

                if system_order and float(system_order.funds) > 0:
                    if float(system_order.price) > 0:
                        order.price = round_numbers(
                            system_order.price, self.price_precision
                        )

                    order.qty = round_numbers(system_order.funds, self.qty_precision)
                    order.status = (
                        OrderStatus.NEW if system_order.active else OrderStatus.FILLED
                    )
                    order.timestamp = system_order.created_at
                    self.base_streaming.bot_controller.update_order(order)
                    bot.add_log(f"Order {order.order_id} updated from system")

                    if (
                        order.deal_type == DealType.base_order
                        and bot.deal.opening_price == 0
                        and order.price > 0
                    ):
                        bot.deal.opening_price = order.price
                        bot.deal.opening_qty = order.qty
                        bot.deal.opening_timestamp = order.timestamp
                        bot.status = Status.active

                    if (
                        (
                            order.deal_type == DealType.take_profit
                            or order.deal_type == DealType.stop_loss
                            or order.deal_type == DealType.panic_close
                            or order.deal_type == DealType.trailling_profit
                        )
                        and bot.deal.closing_price == 0
                        and order.price > 0
                    ):
                        bot.deal.closing_price = order.price
                        bot.deal.closing_qty = order.qty
                        bot.deal.closing_timestamp = order.timestamp
                        bot.status = Status.completed

                if not system_order or is_expired:
                    try:
                        self.base_streaming.kucoin_api.cancel_order_by_order_id_sync(
                            order_id=str(order.order_id)
                        )
                    except Exception as e:
                        # Order may already be cancelled or doesn't exist
                        bot.add_log(
                            f"Failed to cancel order {order.order_id}: {str(e)}"
                        )
                    if order.deal_type == DealType.base_order:
                        bot.status = Status.inactive
                        bot.add_log(
                            f"Order {order.order_id} expired and cancelled. Bot set to inactive.",
                        )
                    else:
                        bot.add_log(
                            f"Order {order.order_id} expired and cancelled.",
                        )

                    self.base_streaming.bot_controller.update_order(order)

            self.base_streaming.bot_controller.save(data=bot)

        return bot

    def futures_order_updates(self, bot: BotModel) -> BotModel:
        """
        Take order id from list of bot.orders
        and fetch order details from exchange
        """
        for order in bot.orders:
            if order.status == OrderStatus.FILLED:
                continue

            if (
                self.base_streaming.exchange == ExchangeId.KUCOIN
                and order.status != OrderStatus.FILLED
            ):
                kucoin_symbol = convert_to_kucoin_symbol(bot)

                # Check if order is expired based on 15m interval
                # this should be a good measure, because candles have closed
                interval_ms = self.base_streaming.interval.get_ms()
                now_ms = int(datetime.now().timestamp() * 1000)
                order_ms = int(order.timestamp * 1000)
                is_expired = (now_ms - order_ms) > interval_ms

                try:
                    # Fetch order details as source of truth for status/fills
                    system_order = (
                        self.base_streaming.kucoin_futures_api.retrieve_order(
                            str(order.order_id)
                        )
                    )
                    if is_expired:
                        raise RestError(
                            response=type(
                                "obj",
                                (object,),
                                {"code": 100001, "message": "Order expired"},
                            )()
                        )
                    status = OrderStatus.map_from_kucoin_status(
                        system_order.status.value
                    )
                    filled_size = float(system_order.filled_size)
                    price_used = float(system_order.avg_deal_price)
                    timestamp = system_order.created_at

                    if float(system_order.price) > 0:
                        order.price = round_numbers(
                            system_order.price, self.price_precision
                        )

                    order.qty = round_numbers(filled_size, self.qty_precision)
                    order.status = status
                    order.timestamp = timestamp
                    order.price = round_numbers(price_used, self.price_precision)
                    self.base_streaming.bot_controller.update_order(order)
                    bot.add_log(f"Order {order.order_id} updated from system")

                    if (
                        order.deal_type == DealType.base_order
                        and bot.deal.opening_price == 0
                        and order.price > 0
                    ):
                        bot.deal.opening_price = order.price
                        bot.deal.opening_qty = order.qty
                        bot.deal.opening_timestamp = order.timestamp
                        bot.status = Status.active

                    if (
                        (
                            order.deal_type == DealType.take_profit
                            or order.deal_type == DealType.stop_loss
                            or order.deal_type == DealType.panic_close
                            or order.deal_type == DealType.trailling_profit
                        )
                        and bot.deal.closing_price == 0
                        and order.price > 0
                    ):
                        bot.deal.closing_price = order.price
                        bot.deal.closing_qty = order.qty
                        bot.deal.closing_timestamp = order.timestamp
                        bot.status = Status.completed

                    self.base_streaming.bot_controller.save(data=bot)

                except RestError as e:
                    if float(e.response.code) == 100001:
                        try:
                            self.base_streaming.kucoin_futures_api.cancel_all_futures_orders(
                                kucoin_symbol
                            )
                            if order.deal_type == DealType.base_order:
                                bot.status = Status.inactive
                                bot.add_log(
                                    f"Order {order.order_id} expired and cancelled. Bot set to inactive.",
                                )
                                self.base_streaming.bot_controller.save(data=bot)
                            else:
                                bot.add_log(
                                    f"Order {order.order_id} expired and cancelled.",
                                )
                                self.base_streaming.bot_controller.save(data=bot)
                        except Exception as cancel_e:
                            bot.add_log(
                                f"Failed to cancel all futures orders for {kucoin_symbol}: {str(cancel_e)}"
                            )
                            self.base_streaming.bot_controller.save(data=bot)
                    else:
                        raise e

        return bot

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

        if converted_symbol in self.base_streaming.active_bot_pairs:
            self.dataframe_ops()
            self.apex_flow_closing = ApexFlowClose(self.df, self.btc_df)

            close_price = float(self.klines[-1][4])
            open_price = float(self.klines[-1][1])

            self.current_bot = self.base_streaming.get_current_bot(converted_symbol)
            self.current_test_bot = self.base_streaming.get_current_test_bot(
                converted_symbol
            )

            try:
                if self.current_bot:
                    # fill incomplete orders first
                    if self.base_streaming.exchange != ExchangeId.KUCOIN:
                        raise NotImplementedError(
                            "Order updates only implemented for Kucoin"
                        )
                    else:
                        if self.current_bot.market_type == MarketType.FUTURES:
                            self.futures_order_updates(bot=self.current_bot)
                        else:
                            self.order_updates(bot=self.current_bot)

                    if self.current_bot.dynamic_trailling:
                        self.market_trailing_analytics(
                            bot=self.current_bot,
                            db_table=BotTable,
                            current_price=close_price,
                        )
                    deal = DealGateway(bot=self.current_bot, db_table=BotTable)
                    deal.deal_exit_orchestration(
                        close_price,
                        open_price,
                    )
                elif self.current_test_bot:
                    if self.current_test_bot.dynamic_trailling:
                        self.market_trailing_analytics(
                            bot=self.current_test_bot,
                            db_table=PaperTradingTable,
                            current_price=close_price,
                        )
                    deal = DealGateway(
                        bot=self.current_test_bot, db_table=PaperTradingTable
                    )
                    deal.deal_exit_orchestration(
                        close_price,
                        open_price,
                    )
                else:
                    return

            except BinanceErrors as error:
                if error.code in (-2010, -1013):
                    if self.current_bot:
                        bot = self.current_bot
                    elif self.current_test_bot:
                        bot = self.current_test_bot
                    else:
                        return

                    bot.add_log(error.message)
                    bot.status = Status.error
                    deal.save(bot)

        return
