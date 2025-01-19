import json
from typing import Type, Union, no_type_check
from kafka import KafkaConsumer
from bots.models import BotModel
from database.autotrade_crud import AutotradeCrud
from database.models.bot_table import BotTable, PaperTradingTable
from database.paper_trading_crud import PaperTradingTableCrud
from database.bot_crud import BotTableCrud
from deals.factory import DealAbstract
from tools.round_numbers import round_numbers
from streaming.models import SignalsConsumer
from tools.enum_definitions import Status, Strategy
from deals.margin import MarginDeal
from deals.spot import SpotLongDeal
from tools.exceptions import BinanceErrors
from datetime import datetime
from apis import BinanceApi


class BaseStreaming:
    def __init__(self) -> None:
        self.binance_api = BinanceApi()
        self.bot_controller = BotTableCrud()
        self.paper_trading_controller = PaperTradingTableCrud()

    def get_current_bot(self, symbol: str) -> BotModel:
        current_bot = self.bot_controller.get_one(symbol=symbol, status=Status.active)
        bot = BotModel.dump_from_table(current_bot)
        return bot

    def get_current_test_bot(self, symbol: str) -> BotModel:
        current_test_bot = self.paper_trading_controller.get_one(
            symbol=symbol, status=Status.active
        )
        bot = BotModel.dump_from_table(current_test_bot)
        return bot


class StreamingController(BaseStreaming):
    def __init__(self, consumer: KafkaConsumer) -> None:
        super().__init__()
        # Gets any signal to restart streaming
        self.consumer = consumer
        self.autotrade_controller = AutotradeCrud()

    def load_data_on_start(self) -> None:
        """
        Load data on start and on update_required
        """
        self.list_bots = self.bot_controller.get_active_pairs()
        # Load paper trading bot settings
        self.list_paper_trading_bots = self.paper_trading_controller.get_active_pairs()

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
        if len(current_bot.orders) > 0:
            try:
                int(current_bot.orders[0].order_id)
            except Exception:
                print(current_bot.orders[0].order_id)
                pass

        # Margin short
        if current_bot.strategy == Strategy.margin_short:
            margin_deal = MarginDeal(current_bot, db_table=db_table)
            margin_deal.streaming_updates(close_price)

        elif current_bot.strategy == Strategy.long:
            spot_long_deal = SpotLongDeal(current_bot, db_table=db_table)
            spot_long_deal.streaming_updates(close_price, open_price)

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
        current_bot = None
        current_test_bot = None
        try:
            current_bot = self.get_current_bot(symbol)
        except ValueError:
            pass

        try:
            current_test_bot = self.get_current_test_bot(symbol)
        except ValueError:
            pass

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

        loan_details = self.binance_api.get_margin_loan_details(bot.deal.margin_loan_id)

        if len(loan_details["rows"]) > 0:
            interests = loan_details["rows"][0]["interests"]
        else:
            interests = 0

        close_total = bot.deal.closing_price
        open_total = bot.deal.closing_price

        return interests, open_total, close_total

    def compute_single_bot_profit(self, bot: BotModel, current_price: float) -> float:
        if bot.deal and bot.base_order_size > 0:
            if bot.deal.opening_price > 0:
                current_price = (
                    bot.deal.closing_price
                    if bot.deal.closing_price
                    else current_price or bot.deal.current_price
                )
                buy_price = bot.deal.opening_price
                profit_change = ((current_price - buy_price) / buy_price) * 100
                if current_price == 0:
                    profit_change = 0
                return round(profit_change, 2)
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
        bb_spreads: dict,
        db_table: Type[Union[PaperTradingTable, BotTable]],
        current_price: float,
    ) -> None:
        # multiplied by 1000 to get to the same scale stop_loss
        top_spread = round_numbers(
            (
                abs(
                    (bb_spreads["bb_high"] - bb_spreads["bb_mid"])
                    / bb_spreads["bb_high"]
                )
                * 100
            ),
            2,
        )
        whole_spread = round_numbers(
            (
                abs(
                    (bb_spreads["bb_high"] - bb_spreads["bb_low"])
                    / bb_spreads["bb_high"]
                )
                * 100
            ),
            2,
        )
        bottom_spread = round_numbers(
            abs((bb_spreads["bb_mid"] - bb_spreads["bb_low"]) / bb_spreads["bb_mid"])
            * 100,
            2,
        )

        # Otherwise it'll close too soon
        if 8 > whole_spread > 2:
            # check we are not duplicating the update
            if (
                bot.take_profit == top_spread
                and bot.stop_loss == whole_spread
                and bot.trailling_deviation == bottom_spread
            ):
                return

            bot.trailling = True
            # reset values to avoid too much risk when there's profit
            bot_profit = self.compute_single_bot_profit(bot, current_price)
            # when prices go up only
            if bot.strategy == Strategy.long:
                if bot_profit > 6:
                    bot.take_profit = 2.8
                    bot.trailling_deviation = 2.6
                    bot.stop_loss = 3.6
                # Only when TD_2 > TD_1
                elif bottom_spread > bot.trailling_deviation:
                    bot.take_profit = top_spread
                    # too much risk, reduce stop loss
                    bot.trailling_deviation = bottom_spread

                spot_deal = SpotLongDeal(bot, db_table=db_table)
                # reactivate includes saving
                spot_deal.open_deal()

                # No need to continue
                # Bots can only be either long or short
                return

            if bot.strategy == Strategy.margin_short:
                if bot_profit > 6:
                    bot.take_profit = 2.8
                    bot.trailling_deviation = 2.6
                    bot.stop_loss = 3.6

                # Decrease risk for margin shorts
                # as volatility is higher, we want to keep parameters tighter
                # also over time we'll be paying more interest, so better to liquidate sooner
                # that means smaller trailing deviation to close deal earlier
                elif bot.trailling_deviation > bottom_spread:
                    bot.take_profit = bottom_spread
                    bot.trailling_deviation = top_spread

                margin_deal = MarginDeal(bot, db_table=db_table)
                # reactivate includes saving
                margin_deal.open_deal()

    # To find a better interface for bb_xx once mature
    @no_type_check
    def update_close_conditions(self, message):
        """
        Update bot with dynamic trailling enabled to update
        take_profit and trailling according to bollinguer bands
        dynamic movements in the market
        """
        data = json.loads(message)
        signalsData = SignalsConsumer.model_validate(data)

        # Check if it matches any active bots
        self.load_current_bots(signalsData.symbol)

        bb_spreads = signalsData.bb_spreads
        if (
            (self.current_bot or self.current_test_bot)
            and bb_spreads
            and "bb_high" in bb_spreads
            and bb_spreads["bb_high"]  # my-py
            and "bb_low" in bb_spreads
            and bb_spreads["bb_low"]
            and "bb_mide" in bb_spreads
            and bb_spreads["bb_mid"]
        ):
            if self.current_bot:
                self.update_bots_parameters(
                    self.current_bot,
                    bb_spreads,
                    db_table=BotTable,
                    current_price=signalsData.current_price,
                )
            if self.current_test_bot:
                self.update_bots_parameters(
                    self.current_test_bot,
                    bb_spreads,
                    db_table=PaperTradingTable,
                    current_price=signalsData.current_price,
                )
