import json
import logging
from datetime import datetime
from typing import Type, Union, no_type_check

import pandas as pd
from bots.models import BotModel
from charts.controllers import Candlestick
from database.autotrade_crud import AutotradeCrud
from database.bot_crud import BotTableCrud
from database.models.bot_table import BotTable, PaperTradingTable
from database.paper_trading_crud import PaperTradingTableCrud
from database.symbols_crud import SymbolsCrud
from deals.abstractions.factory import DealAbstract
from deals.margin import MarginDeal
from deals.spot import SpotLongDeal
from exchange_apis.binance import BinanceApi
from kafka import KafkaConsumer
from streaming.models import BollinguerSpread, SingleCandle
from tools.enum_definitions import Status, Strategy
from tools.exceptions import BinanceErrors, BinbotErrors
from tools.round_numbers import round_numbers
from typing import Sequence
from copy import deepcopy

class BaseStreaming:
    def __init__(self) -> None:
        self.binance_api = BinanceApi()
        self.bot_controller = BotTableCrud()
        self.paper_trading_controller = PaperTradingTableCrud()
        self.symbols_controller = SymbolsCrud()
        self.cs = Candlestick()
        self.active_bot_pairs: Sequence = []
        self.paper_trading_active_bots: Sequence = []
        self.load_data_on_start()

    def load_data_on_start(self):
        """
        Load data on start and on update_required
        """
        logging.info(
            "Loading controller, active bots and available symbols (not blacklisted)..."
        )
        # self.autotrade_settings: dict = self.get_autotrade_settings()
        self.active_bot_pairs = self.bot_controller.get_active_pairs()
        self.paper_trading_active_bots = (
            self.paper_trading_controller.get_active_pairs()
        )
        pass

    def get_current_bot(self, symbol: str) -> BotModel:
        try:
            current_bot = self.bot_controller.get_one(
                symbol=symbol, status=Status.active
            )
            bot = BotModel.dump_from_table(current_bot)
            return bot
        except BinbotErrors:
            bot = None
            return bot

    def get_current_test_bot(self, symbol: str) -> BotModel:
        try:
            current_test_bot = self.paper_trading_controller.get_one(
                symbol=symbol, status=Status.active
            )
            bot = BotModel.dump_from_table(current_test_bot)
            return bot
        except BinbotErrors:
            bot = None
            return bot

    def build_bb_spreads(self, last_candle: SingleCandle) -> BollinguerSpread:
        """
        Builds the bollinguer bands spreads without using pandas_ta
        """
        data = self.cs.raw_klines(symbol=last_candle.symbol, limit=200)
        if len(data) < 200:
            return BollinguerSpread(bb_high=0, bb_mid=0, bb_low=0)

        df = pd.DataFrame(data)
        df.drop(columns=["_id"], inplace=True)
        close_prices = df["close"]
        rolling_mean = close_prices.rolling(window=20).mean()
        rolling_std = close_prices.rolling(window=20).std()

        df["bb_high"] = rolling_mean + (rolling_std * 2)
        df["bb_mid"] = rolling_mean
        df["bb_low"] = rolling_mean - (rolling_std * 2)

        df.reset_index(drop=True, inplace=True)

        bb_spreads = BollinguerSpread(
            bb_high=df["bb_high"].iloc[-1],
            bb_mid=df["bb_mid"].iloc[-1],
            bb_low=df["bb_low"].iloc[-1],
        )

        return bb_spreads


class StreamingController(BaseStreaming):
    def __init__(self, consumer: KafkaConsumer) -> None:
        super().__init__()
        # Gets any signal to restart streaming
        self.consumer = consumer
        self.autotrade_controller = AutotradeCrud()

    def execute_strategies(
        self,
        current_bot: BotModel,
        close_price: str,
        open_price: str,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ) -> None:
        """
        Processes the deal market websocket price updates

        It updates the bots deals, safety orders, trailling orders, stop loss
        for both paper trading test bots and real bots
        """

        # Margin short
        if current_bot.strategy == Strategy.margin_short:
            margin_deal = MarginDeal(current_bot, db_table=db_table)
            margin_deal.streaming_updates(float(close_price))

        elif current_bot.strategy == Strategy.long:
            spot_long_deal = SpotLongDeal(current_bot, db_table=db_table)
            spot_long_deal.streaming_updates(float(close_price), float(open_price))

        pass

    def process_klines(self, message: str) -> None:
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        data = json.loads(message)
        close_price = data["close_price"]
        open_price = data["open_price"]
        symbol = data["symbol"]

        if symbol in self.active_bot_pairs or symbol in self.paper_trading_active_bots:
            current_bot = self.get_current_bot(symbol)
            current_test_bot = self.get_current_test_bot(symbol)

            try:
                if current_bot:
                    create_deal_controller = DealAbstract(
                        bot=current_bot, db_table=BotTable
                    )
                    self.execute_strategies(
                        current_bot,
                        close_price,
                        open_price,
                        db_table=BotTable,
                    )
                elif current_test_bot:
                    create_deal_controller = DealAbstract(
                        bot=current_test_bot, db_table=PaperTradingTable
                    )
                    self.execute_strategies(
                        current_test_bot,
                        close_price,
                        open_price,
                        db_table=PaperTradingTable,
                    )
                else:
                    return
            except BinanceErrors as error:
                if error.code in (-2010, -1013):
                    if current_bot:
                        bot = current_bot
                    elif current_test_bot:
                        bot = current_test_bot
                    else:
                        return

                    bot.logs.append(error.message)
                    bot.status = Status.error
                    create_deal_controller.controller.save(bot)

        return


class BbspreadsUpdater(BaseStreaming):
    def __init__(self) -> None:
        super().__init__()
        self.current_bot: BotModel | None = None
        self.current_test_bot: BotModel | None = None

    def load_current_bots(self, symbol: str) -> None:
        try:
            current_bot_payload = self.get_current_bot(symbol)
            if current_bot_payload:
                self.current_bot = BotModel.model_validate(current_bot_payload)

            current_test_bot_payload = self.get_current_test_bot(symbol)
            if current_test_bot_payload:
                self.current_test_bot = BotModel.model_validate(
                    current_test_bot_payload
                )
        except ValueError:
            pass

    def get_interests_short_margin(self, bot: BotModel) -> tuple[float, float, float]:
        close_timestamp = bot.deal.closing_timestamp
        if close_timestamp == 0:
            close_timestamp = int(datetime.now().timestamp() * 1000)

        asset = bot.pair.split(bot.fiat)[0]
        interest_details = self.binance_api.get_interest_history(
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
        if bot.deal and bot.base_order_size > 0:
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

    def update_bots_parameters(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]],
        current_price: float,
        bb_spreads: BollinguerSpread,
    ) -> None:
        if db_table == BotTable:
            self.bot_controller = BotTableCrud()
        
        if db_table == PaperTradingTable:
            self.bot_controller = PaperTradingTableCrud()

        # Avoid duplicate updates
        original_bot = deepcopy(bot)

        # not enough data
        if bb_spreads.bb_high == 0 or bb_spreads.bb_low == 0 or bb_spreads.bb_mid == 0:
            return

        # multiplied by 1000 to get to the same scale stop_loss
        top_spread = round_numbers(
            (abs((bb_spreads.bb_high - bb_spreads.bb_mid) / bb_spreads.bb_high) * 100),
            2,
        )
        whole_spread = round_numbers(
            (abs((bb_spreads.bb_high - bb_spreads.bb_low) / bb_spreads.bb_high) * 100),
            2,
        )
        bottom_spread = round_numbers(
            abs((bb_spreads.bb_mid - bb_spreads.bb_low) / bb_spreads.bb_mid) * 100,
            2,
        )

        # Otherwise it'll close too soon or incur too much loss
        if whole_spread > 8:
            whole_spread = 8
            top_spread = 6
            bottom_spread = 4

        if whole_spread < 2:
            whole_spread = 2
            top_spread = 1.5
            bottom_spread = 1

        bot.trailling = True
        # reset values to avoid too much risk when there's profit
        bot_profit = self.compute_single_bot_profit(bot, current_price)
        # when prices go up only
        if bot.strategy == Strategy.long:

            # Only when TD_2 > TD_1
            bot.trailling_profit = original_bot.trailling_profit
            # too much risk, reduce stop loss
            bot.trailling_deviation = original_bot.trailling_deviation
            bot.stop_loss = original_bot.stop_loss

            # Already decent profit, do not increase risk
            if bot_profit > 6:
                bot.trailling_profit = 2.8
                bot.trailling_deviation = 2.6
                bot.stop_loss = 3.2


            # check we are not duplicating the update
            if (
                bot.trailling_profit == original_bot.trailling_profit
                and bot.stop_loss == original_bot.stop_loss
                and bot.trailling_deviation == original_bot.trailling_deviation
            ):
                return

            self.bot_controller.save(bot)
            spot_deal = SpotLongDeal(bot, db_table=db_table)
            # reactivate includes saving
            spot_deal.open_deal()

            # No need to continue
            # Bots can only be either long or short
            return

        if bot.strategy == Strategy.margin_short:

            if bot_profit > 6:
                bot.trailling_profit = 2.8
                bot.trailling_deviation = 2.6
                bot.stop_loss = 3.6

            # Decrease risk for margin shorts
            # as volatility is higher, we want to keep parameters tighter
            # also over time we'll be paying more interest, so better to liquidate sooner
            # that means smaller trailing deviation to close deal earlier
            elif bot.trailling_deviation > bottom_spread:
                bot.trailling_profit = bottom_spread
                bot.trailling_deviation = top_spread

            # check we are not duplicating the update
            if (
                bot.trailling_profit == original_bot.trailling_profit
                and bot.stop_loss == original_bot.stop_loss
                and bot.trailling_deviation == original_bot.trailling_deviation
            ):
                return

            margin_deal = MarginDeal(bot, db_table=db_table)
            # reactivate includes saving
            margin_deal.open_deal()

    # To find a better interface for bb_xx once mature
    @no_type_check
    def dynamic_trailling(self, message) -> None:
        """
        Update bot with dynamic trailling enabled to update
        take_profit and trailling according to bollinguer bands
        dynamic movements in the market
        """
        data = json.loads(message)
        single_candle = SingleCandle.model_validate(data)

        # Check if it matches any active bots
        self.load_current_bots(single_candle.symbol)

        bb_spreads = self.build_bb_spreads(single_candle)
        if self.current_bot and self.current_bot.dynamic_trailling:
            self.update_bots_parameters(
                bot=self.current_bot,
                bb_spreads=bb_spreads,
                db_table=BotTable,
                current_price=single_candle.close_price,
            )

        if self.current_test_bot and self.current_test_bot.dynamic_trailling:
            self.update_bots_parameters(
                bot=self.current_test_bot,
                bb_spreads=bb_spreads,
                db_table=PaperTradingTable,
                current_price=single_candle.close_price,
            )

            pass
