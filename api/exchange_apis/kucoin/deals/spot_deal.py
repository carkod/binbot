from typing import Type, Union, Any
from databases.tables.bot_table import BotTable, PaperTradingTable
from bots.models import BotModel
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.bot_crud import BotTableCrud


class KucoinSpotDeal:
    """Stub KuCoin spot deal implementation matching BinanceSpotDeal interface.

    Methods raise NotImplementedError until proper KuCoin spot logic is added.
    Used for polymorphic delegation via `deal_base`.
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ) -> None:
        self.active_bot = bot
        self.db_table = db_table
        # Provide a controller attribute for polymorphic access
        self.controller: Union[PaperTradingTableCrud, BotTableCrud, Any]
        self.controller = None

    # Core order / deal lifecycle methods
    def open_deal(self) -> BotModel:
        """Open or activate a spot deal. Stub for parity with BinanceSpotDeal."""
        raise NotImplementedError

    def close_all(self) -> BotModel:
        """Close all orders and finalize the spot deal. Stub only."""
        raise NotImplementedError

    def streaming_updates(self, close_price: float, open_price: float) -> BotModel:
        """Process streaming price updates. Stub only."""
        raise NotImplementedError

    def update_spot_orders(self) -> BotModel:
        raise NotImplementedError

    def execute_stop_loss(self) -> BotModel:
        raise NotImplementedError

    def trailling_profit(self) -> BotModel | None:
        raise NotImplementedError

    def close_conditions(self, current_price: float) -> None:
        raise NotImplementedError

    def long_open_deal_trailling_parameters(self) -> BotModel:
        raise NotImplementedError

    def long_update_deal_trailling_parameters(self) -> BotModel:
        raise NotImplementedError

    def base_order(self) -> BotModel:
        raise NotImplementedError

    # Order operations expected by LongDeal
    def buy_order(self, symbol: str, qty: float) -> dict:
        raise NotImplementedError

    def sell_order(self, symbol: str, qty: float) -> dict:
        raise NotImplementedError

    def delete_order(self, symbol: str, order_id: int) -> Any:
        raise NotImplementedError

    def simulate_order(self, pair: str, side: Any, qty: float = 1) -> dict:
        raise NotImplementedError

    # Utilities referenced indirectly
    def calculate_avg_price(self, fills: list[dict]) -> float:
        raise NotImplementedError

    def calculate_total_commissions(self, fills: list[dict]) -> float:
        raise NotImplementedError

    def sell_quote_asset(self) -> BotModel:
        raise NotImplementedError

    def compute_qty(self, symbol: str) -> float:
        raise NotImplementedError

    def close_open_orders(self, symbol: str):
        raise NotImplementedError

    def verify_deal_close_order(self):
        raise NotImplementedError
