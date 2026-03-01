from typing import Type, Union
from pandas import DataFrame
from deals.gateway import DealGateway
from bots.models import BotModel
from databases.crud.autotrade_crud import AutotradeCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from pybinbot import (
    MarketType,
    ExchangeId,
    BinanceApi,
    KucoinApi,
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
