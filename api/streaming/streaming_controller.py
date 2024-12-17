import json
import logging
import typing
from kafka import KafkaConsumer
from database.autotrade_crud import AutotradeCrud
from database.models.bot_table import BotTable
from database.models.paper_trading_table import PaperTradingTable
from database.paper_trading_crud import PaperTradingTableCrud
from database.bot_crud import BotTableCrud
from deals.controllers import CreateDealController
from tools.round_numbers import round_numbers
from streaming.models import SignalsConsumer
from tools.enum_definitions import Status, Strategy
from deals.margin import MarginDeal
from deals.spot import SpotLongDeal
from tools.exceptions import BinanceErrors


class BaseStreaming:
    def __init__(self) -> None:
        self.bot_controller = BotTableCrud()
        self.paper_trading_controller = PaperTradingTableCrud()

    def get_current_bot(self, symbol: str) -> BotTable:
        current_bot = self.bot_controller.get_one(symbol=symbol, status=Status.active)
        return current_bot

    def get_current_test_bot(self, symbol: str) -> PaperTradingTable:
        current_test_bot = self.paper_trading_controller.get_one(
            symbol=symbol, status=Status.active
        )
        return current_test_bot


class StreamingController(BaseStreaming):
    def __init__(self, consumer: KafkaConsumer) -> None:
        super().__init__()
        # Gets any signal to restart streaming
        self.consumer = consumer
        self.autotrade_controller = AutotradeCrud()
        self.load_data_on_start()

    def load_data_on_start(self) -> None:
        """
        New function to replace get_klines without websockets
        """
        # Load real bot settings
        self.list_bots = self.bot_controller.get_active_pairs()
        # Load paper trading bot settings
        self.list_paper_trading_bots = self.paper_trading_controller.get_active_pairs()
        return

    def execute_strategies(
        self,
        current_bot: BotTable | PaperTradingTable,
        close_price: str,
        open_price: str,
        create_deal_controller: CreateDealController,
    ) -> None:
        """
        Processes the deal market websocket price updates

        It updates the bots deals, safety orders, trailling orders, stop loss
        for both paper trading test bots and real bots
        """
        if len(current_bot["orders"]) > 0:
            try:
                int(current_bot["orders"][0]["order_id"])
            except Exception:
                print(current_bot["orders"][0]["order_id"])
                pass

        active_bot = BotTable.model_validate(current_bot)

        # Margin short
        if active_bot.strategy == Strategy.margin_short:
            margin_deal = MarginDeal(active_bot, create_deal_controller.controller)
            margin_deal.streaming_updates(close_price)

        else:
            # Long strategy starts
            if active_bot.strategy == Strategy.long:
                spot_long_deal = SpotLongDeal(
                    active_bot, create_deal_controller.controller
                )
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
        current_bot = self.get_current_bot(symbol)
        current_test_bot = self.get_current_test_bot(symbol)

        # temporary test that we get enough streaming update signals
        logging.info(f"Streaming update for {symbol}")

        try:
            if current_bot:
                create_deal_controller = CreateDealController(
                    bot=current_bot, controller=BotTableCrud
                )
                self.execute_strategies(
                    current_bot,
                    close_price,
                    open_price,
                    create_deal_controller,
                )
            if current_test_bot:
                create_deal_controller = CreateDealController(
                    bot=current_bot, controller=BotTableCrud
                )
                self.execute_strategies(
                    current_test_bot,
                    close_price,
                    open_price,
                    create_deal_controller,
                )
        except BinanceErrors as error:
            if error.code in (-2010, -1013):
                bot = current_bot if current_bot else current_test_bot
                create_deal_controller.controller.update_logs(error.message, bot)
                bot.status = Status.error
                create_deal_controller.controller.save(bot)

        return


class BbspreadsUpdater(BaseStreaming):
    def __init__(self) -> None:
        self.current_bot: BotTable | None = None
        self.current_test_bot: PaperTradingTable | None = None

    def load_current_bots(self, symbol: str) -> None:
        current_bot_payload = self.get_current_bot(symbol)
        if current_bot_payload:
            self.current_bot = BotTable.model_validate(current_bot_payload)

        current_test_bot_payload = self.get_current_test_bot(symbol)
        if current_test_bot_payload:
            self.current_test_bot = BotTable(**current_test_bot_payload)

    def update_bots_parameters(
        self,
        bot: BotTable,
        bb_spreads: dict,
        create_deal_controller: CreateDealController,
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
            # when prices go up only
            if bot.strategy == Strategy.long:
                # Only when TD_2 > TD_1
                if bottom_spread > bot.trailling_deviation:
                    bot.take_profit = top_spread
                    # too much risk, reduce stop loss
                    bot.trailling_deviation = bottom_spread
                    # reactivate includes saving
                    create_deal_controller.open_deal(bot)

                # No need to continue
                # Bots can only be either long or short
                return

            if bot.strategy == Strategy.margin_short:
                # Decrease risk for margin shorts
                # as volatility is higher, we want to keep parameters tighter
                # also over time we'll be paying more interest, so better to liquidate sooner
                # that means smaller trailing deviation to close deal earlier
                bot.take_profit = bottom_spread
                if bot.trailling_deviation > bottom_spread:
                    bot.trailling_deviation = top_spread
                    # reactivate includes saving
                    create_deal_controller.open_deal(bot)

    # To find a better interface for bb_xx once mature
    @typing.no_type_check
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
            and "bb_high" in bb_spreads
            and bb_spreads["bb_high"]  # my-py
            and "bb_low" in bb_spreads
            and bb_spreads["bb_low"]
            and "bb_mide" in bb_spreads
            and bb_spreads["bb_mid"]
        ):
            if self.current_bot:
                create_deal_controller = CreateDealController(
                    bot=self.current_bot, controller=BotTableCrud
                )
                self.update_bots_parameters(
                    self.current_bot,
                    bb_spreads,
                    create_deal_controller=create_deal_controller,
                )
            if self.current_test_bot:
                create_deal_controller = CreateDealController(
                    bot=self.current_test_bot, controller=PaperTradingTableCrud
                )
                self.update_bots_parameters(
                    self.current_test_bot,
                    bb_spreads,
                    create_deal_controller=create_deal_controller,
                )
