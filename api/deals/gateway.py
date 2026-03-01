from exchange_apis.kucoin.deals.long_deal import KucoinLongDeal
from databases.tables.bot_table import BotTable, PaperTradingTable
from pybinbot import ExchangeId, Strategy, MarketType
from bots.models import BotModel
from typing import Union, Type
from exchange_apis.kucoin.deals.short_deal import KucoinShortDeal
from databases.crud.autotrade_crud import AutotradeCrud
from exchange_apis.binance.deals.short import BinanceShortDeal
from exchange_apis.binance.deals.long import BinanceLongDeal
from exchange_apis.kucoin.futures.position_deal import PositionDeal


class DealGateway:
    """
    A facade class to create deal instances, this is where
    exchanges, strategies and deal types are mapped to their respective classes.

    Methods here should be minimal to expose only the necessary common interface for deal operations.
    """

    def __init__(
        self, bot: BotModel, db_table: Type[BotTable] | Type[PaperTradingTable]
    ) -> None:
        self.autotrade_settings = AutotradeCrud().get_settings()
        self.bot = bot
        self.db_table = db_table
        self.deal: Union[
            BinanceLongDeal,
            BinanceShortDeal,
            KucoinLongDeal,
            KucoinShortDeal,
            PositionDeal,
        ]
        if self.autotrade_settings.exchange_id == ExchangeId.KUCOIN:
            if bot.market_type == MarketType.FUTURES:
                self.deal = PositionDeal(bot, db_table=db_table)
            else:
                if bot.strategy == Strategy.margin_short:
                    self.deal = KucoinShortDeal(bot, db_table=db_table)
                else:
                    if bot.market_type == MarketType.FUTURES:
                        self.deal = PositionDeal(bot, db_table=db_table)
                    else:
                        raise NotImplementedError(
                            "Spot trading is not supported for Kucoin exchange"
                        )
        else:
            if bot.strategy == Strategy.margin_short:
                self.deal = BinanceShortDeal(bot, db_table=db_table)
            else:
                self.deal = BinanceLongDeal(bot, db_table=db_table)

    def open_deal(
        self,
    ) -> BotModel:
        """
        Abstract method for opening deals during creation
        """
        return self.deal.open_deal()

    def update_logs(self, message: str | list[str]) -> BotTable | PaperTradingTable:
        """
        Abstract method for updating logs during bot runtime
        """
        return self.deal.controller.update_logs(bot=self.bot, log_message=message)

    def deactivation(self) -> BotModel:
        """
        Abstract method for deactivation (which is pretty much closing all deals) during bot runtime
        """
        return self.deal.close_all()

    def deal_exit_orchestration(
        self, close_price: float, open_price: float
    ) -> BotModel:
        """
        Abstract method for streaming deals during bot runtime
        """
        return self.deal.deal_exit_orchestration(
            close_price=close_price, open_price=open_price
        )

    def save(self, bot: BotModel) -> Union[BotTable, PaperTradingTable]:
        """
        Abstract method for saving bot state
        """
        return self.deal.controller.save(bot)
