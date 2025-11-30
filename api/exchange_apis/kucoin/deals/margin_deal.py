from typing import Type, Union, Any
from databases.tables.bot_table import BotTable, PaperTradingTable
from bots.models import BotModel


class KucoinMarginDeal:
    """Stub KuCoin margin deal implementation matching Binance margin deal interface.

    Provides method signatures for polymorphic delegation; implementations pending.
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ) -> None:
        self.active_bot = bot
        self.db_table = db_table

    def margin_short_base_order(self) -> BotModel:
        raise NotImplementedError

    def short_open_deal_trailling_parameters(self) -> BotModel:
        raise NotImplementedError

    def short_update_deal_trailling_parameters(self) -> BotModel:
        raise NotImplementedError

    def execute_stop_loss(self) -> BotModel:
        raise NotImplementedError

    def margin_liquidation(self, symbol: str) -> dict:
        raise NotImplementedError

    def cancel_margin_order(self, symbol: str, order_id: int) -> Any:
        raise NotImplementedError

    def simulate_margin_order(self, pair: str, side: Any) -> dict:
        raise NotImplementedError

    def calculate_avg_price(self, fills: list[dict]) -> float:
        raise NotImplementedError

    def calculate_total_commissions(self, fills: list[dict]) -> float:
        raise NotImplementedError

    def compute_qty(self, symbol: str) -> float:
        raise NotImplementedError

    def close_open_orders(self, symbol: str):
        raise NotImplementedError

    def verify_deal_close_order(self):
        raise NotImplementedError
