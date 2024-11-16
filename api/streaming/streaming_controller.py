import json
import logging

from tools.round_numbers import round_numbers
from streaming.models import SignalsConsumer
from bots.schemas import BotSchema
from autotrade.controller import AutotradeSettingsController
from bots.controllers import Bot
from tools.enum_definitions import Status, Strategy
from database.db import Database
from deals.margin import MarginDeal
from deals.spot import SpotLongDeal
from tools.exceptions import BinanceErrors


class BaseStreaming(Database):

    def get_current_bot(self, symbol):
        current_bot = Bot(collection_name="bots").get_one(
            symbol=symbol, status=Status.active
        )
        return current_bot

    def get_current_test_bot(self, symbol):
        current_test_bot = Bot(collection_name="paper_trading").get_one(
            symbol=symbol, status=Status.active
        )
        current_test_bot = current_test_bot
        return current_test_bot


class StreamingController(BaseStreaming):
    def __init__(self, consumer):
        super().__init__()
        self.streaming_db = self._db
        # Gets any signal to restart streaming
        self.consumer = consumer
        self.autotrade_controller = AutotradeSettingsController()
        self.load_data_on_start()

    def load_data_on_start(self):
        """
        New function to replace get_klines without websockets
        """
        # Load real bot settings
        bot_controller = Bot(collection_name="bots")
        self.list_bots = bot_controller.get_active_pairs()
        # Load paper trading bot settings
        paper_trading_controller_paper = Bot(collection_name="paper_trading")
        self.list_paper_trading_bots = paper_trading_controller_paper.get_active_pairs()
        return

    def execute_strategies(
        self,
        current_bot,
        close_price: str,
        open_price: str,
        db_collection_name,
    ):
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
        try:
            active_bot = BotSchema(**current_bot)
            pass
        except Exception as error:
            logging.info(error)
            return
        # Margin short
        if active_bot.strategy == Strategy.margin_short:
            margin_deal = MarginDeal(active_bot, db_collection_name)
            try:
                margin_deal.streaming_updates(close_price)
            except BinanceErrors as error:
                if error.code in (-2010, -1013):
                    margin_deal.update_deal_logs(error.message, active_bot)
            except Exception as error:
                logging.info(error)
                margin_deal.update_deal_logs(error, active_bot)
                pass

        else:
            # Long strategy starts
            if active_bot.strategy == Strategy.long:
                spot_long_deal = SpotLongDeal(active_bot, db_collection_name)
                try:
                    spot_long_deal.streaming_updates(close_price, open_price)
                except BinanceErrors as error:
                    if error.code in (-2010, -1013):
                        spot_long_deal.update_deal_logs(error.message, active_bot)
                        active_bot.status = Status.error
                        active_bot = self.save_bot_streaming(active_bot)
                except Exception as error:
                    logging.info(error)
                    spot_long_deal.update_deal_logs(error, active_bot)
                    pass

        pass

    def process_klines(self, message):
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

        if current_bot:
            self.execute_strategies(
                current_bot,
                close_price,
                open_price,
                "bots",
            )
        if current_test_bot:
            self.execute_strategies(
                current_test_bot,
                close_price,
                open_price,
                "paper_trading",
            )

        return


class BbspreadsUpdater(BaseStreaming):
    def __init__(self):
        self.current_bot: BotSchema | None = None
        self.current_test_bot: BotSchema | None = None

    def load_current_bots(self, symbol):
        current_bot_payload = self.get_current_bot(symbol)
        if current_bot_payload:
            self.current_bot = BotSchema(**current_bot_payload)

        current_test_bot_payload = self.get_current_test_bot(symbol)
        if current_test_bot_payload:
            self.current_test_bot = BotSchema(**current_test_bot_payload)

    def reactivate_bot(self, bot: BotSchema, collection_name="bots"):
        bot_instance = Bot(collection_name=collection_name)
        activated_bot = bot_instance.activate(bot)
        return activated_bot

    def update_bots_parameters(
        self, bot: BotSchema, bb_spreads, collection_name="bots"
    ):

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
                    self.reactivate_bot(bot, collection_name=collection_name)

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
                    self.reactivate_bot(bot, collection_name=collection_name)

    def update_close_conditions(self, message):
        """
        Update bot with dynamic trailling enabled to update
        take_profit and trailling according to bollinguer bands
        dynamic movements in the market
        """
        data = json.loads(message)
        signalsData = SignalsConsumer(**data)

        # Check if it matches any active bots
        self.load_current_bots(signalsData.symbol)

        bb_spreads = signalsData.bb_spreads
        if (
            (self.current_bot or self.current_test_bot)
            and bb_spreads["bb_high"]
            and bb_spreads["bb_low"]
            and bb_spreads["bb_mid"]
        ):
            if self.current_bot:
                self.update_bots_parameters(self.current_bot, bb_spreads)
            if self.current_test_bot:
                self.update_bots_parameters(
                    self.current_test_bot, bb_spreads, collection_name="paper_trading"
                )
