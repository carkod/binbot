from typing import Type, Union
from database.models.bot_table import BotTable, PaperTradingTable
from database.symbols_crud import SymbolsCrud
from bots.models import BotModel, OrderModel
from tools.enum_definitions import DealType, OrderSide, Status, OrderStatus
from tools.exceptions import TakeProfitError
from tools.round_numbers import round_numbers, round_timestamp
from deals.abstractions.base import BaseDeal
from deals.models import DealModel
from database.paper_trading_crud import PaperTradingTableCrud


class DealAbstract(BaseDeal):
    """
    Centralized deal controller.

    This is the first step that comes after a bot is saved
    1. Save bot
    2. Open deal (deal controller)
    3. Update deals (deal update controller)

    - db_collection = ["bots", "paper_trading"].
    paper_trading uses simulated orders and bot uses real binance orders.
    PaperTradingTable is implemented, PaperTradingController with the db operations is not.
    - bot: BotModel (at some point to refactor into BotTable as they are both pydantic models)
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ):
        super().__init__(bot, db_table)
        self.active_bot = bot
        self.db_table = db_table
        self.symbols_crud = SymbolsCrud()

    def calculate_avg_price(self, fills: list[dict]) -> float:
        """
        Calculate average price of fills
        """
        total_qty: float = 0
        total_price: float = 0
        for fill in fills:
            total_qty += float(fill["qty"])
            total_price += float(fill["price"]) * float(fill["qty"])
        return total_price / total_qty

    def take_profit_order(self) -> BotModel:
        """
        take profit order (Binance take_profit)
        - We only have stop_price, because there are no book bids/asks in t0
        - take_profit order can ONLY be executed once base order is filled (on Binance)
        """

        deal_buy_price = self.active_bot.deal.opening_price
        buy_total_qty = self.active_bot.deal.opening_qty
        price = (1 + (float(self.active_bot.take_profit) / 100)) * float(deal_buy_price)

        if self.db_table == PaperTradingTable:
            qty = self.active_bot.deal.opening_qty
        else:
            qty = self.compute_qty(self.active_bot.pair)

        qty = round_numbers(buy_total_qty, self.qty_precision)
        price = round_numbers(price, self.price_precision)

        if self.db_table == PaperTradingTable:
            res = self.simulate_order(self.active_bot.pair, OrderSide.sell)
        else:
            qty = round_numbers(qty, self.qty_precision)
            price = round_numbers(price, self.price_precision)
            res = self.sell_order(symbol=self.active_bot.pair, qty=qty)

        # If error pass it up to parent function, can't continue
        if "error" in res:
            raise TakeProfitError(res["error"])

        price = float(res["price"])
        if price == 0:
            # Market orders return 0
            price = self.calculate_avg_price(res["fills"])

        order_data = OrderModel(
            timestamp=int(res["transactTime"]),
            order_id=int(res["orderId"]),
            deal_type=DealType.take_profit,
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=price,
            qty=float(res["origQty"]),
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.deal.total_commissions = self.calculate_total_commissions(
            res["fills"]
        )

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.closing_price = price
        self.active_bot.deal.closing_qty = float(res["origQty"])
        self.active_bot.deal.closing_timestamp = round_timestamp(res["transactTime"])
        self.active_bot.status = Status.completed

        bot = self.controller.save(self.active_bot)
        bot = BotModel.model_construct(**bot.model_dump())
        self.controller.update_logs("Completed take profit", self.active_bot)

        return bot

    def base_order(self) -> BotModel:
        """
        Required initial order to trigger long strategy bot.
        Other orders require this to execute,
        therefore should fail if not successful

        1. Initial base purchase
        2. Set take_profit
        """

        # Long position does not need qty in take_profit
        # initial price with 1 qty should return first match
        price = float(
            self.matching_engine(
                self.active_bot.pair, True, qty=self.active_bot.base_order_size
            )
        )
        qty = round_numbers(
            (float(self.active_bot.base_order_size) / float(price)),
            self.qty_precision,
        )
        # setup stop_loss_price
        stop_loss_price: float = 0
        if float(self.active_bot.stop_loss) > 0:
            stop_loss_price = price - (price * (float(self.active_bot.stop_loss) / 100))

        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.simulate_order(
                self.active_bot.pair,
                OrderSide.buy,
            )
        else:
            res = self.buy_order(
                symbol=self.active_bot.pair,
                qty=qty,
            )
            if res["status"] == OrderStatus.expired:
                res = self.buy_order(symbol=self.active_bot.pair, qty=qty)

        price = float(res["price"])
        if price == 0:
            # Market orders return 0
            price = self.calculate_avg_price(res["fills"])

        order_data = OrderModel(
            timestamp=int(res["transactTime"]),
            order_id=res["orderId"],
            deal_type=DealType.base_order,
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=price,
            qty=float(res["origQty"]),
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.orders.append(order_data)
        tp_price = float(res["price"]) * 1 + (float(self.active_bot.take_profit) / 100)

        self.active_bot.deal = DealModel(
            opening_timestamp=int(res["transactTime"]),
            opening_price=price,
            opening_qty=float(res["origQty"]),
            current_price=float(res["price"]),
            take_profit_price=round_numbers(tp_price, self.price_precision),
            stop_loss_price=round_numbers(stop_loss_price, self.price_precision),
        )

        # temporary measures to keep deal up to date
        # once bugs are fixed, this can be removed to improve efficiency
        self.active_bot.status = Status.active
        self.controller.save(self.active_bot)

        # Only signal for the whole activation
        self.base_producer.update_required(self.producer, "EXECUTE_SPOT_OPEN_DEAL")
        return self.active_bot
