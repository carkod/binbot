from typing import Type, Union
from time import time
from pybinbot import (
    Strategy,
    round_numbers,
    DealType,
    convert_to_kucoin_symbol,
    Status,
    OrderType,
    OrderStatus,
)
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.bot_crud import BotTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from bots.models import BotModel
from exchange_apis.kucoin.deals.base import KucoinBaseBalance
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from pybinbot import BinbotErrors
from exchange_apis.kucoin.futures.api import KucoinFutures
from exchange_apis.kucoin.futures.balance import KucoinFuturesBalance
from bots.models import OrderModel


class KucoinFuturesDeal(KucoinBaseBalance):
    """
    Futures-only deal entry implementation (USDT-M).

    - Position-based (not balance-based)
    - Uses contracts, not qty
    - Orders create / modify positions
    - SL / TP are reduce-only orders
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ) -> None:
        super().__init__()
        self.active_bot = bot
        self.db_table = db_table
        self.kucoin_futures_api = KucoinFutures()
        self.controller: Union[BotTableCrud, PaperTradingTableCrud]

        if db_table == PaperTradingTable:
            self.controller = PaperTradingTableCrud()
        else:
            self.controller = BotTableCrud()

        self.symbol_info = SymbolsCrud().get_symbol(bot.pair)
        self.price_precision = self.symbol_info.price_precision
        self.kucoin_symbol = convert_to_kucoin_symbol(bot)

    def calculate_contracts(self, price: float) -> float:
        """
        Calculate the number of contracts based on balance, stop loss, risk per trade, price, and contract multiplier.

        balance: Available USDT balance.
        stop_loss_percent: Stop loss as a decimal (e.g., 3% = 0.03).
        max_risk_percent: Max risk per trade as a decimal (e.g., 5% = 0.05).
        price: Current price of FLOCK.
        multiplier: Size of one contract (default 1).

        Returns: Number of contracts to buy (float).
        """
        balance = self.active_bot.fiat_order_size
        stop_loss_percent = self.active_bot.stop_loss
        # max_allowed_leverage = self.kucoin_futures_api.get_max_allowed_leverage(self.kucoin_symbol, balance)
        max_risk_usdt = balance * self.kucoin_futures_api.DEFAULT_LEVERAGE
        info = self.kucoin_futures_api.get_symbol_info(self.kucoin_symbol)
        multiplier = info.multiplier
        if not multiplier:
            multiplier = self.kucoin_futures_api.DEFAULT_MULTIPLIER

        # Calculate the total position size you can afford if the stop loss hits
        max_position_size = max_risk_usdt / stop_loss_percent

        # Calculate the number of contracts
        contracts = round_numbers(
            max_position_size / (price * float(multiplier)), self.price_precision
        )

        return contracts

    def compute_available_balance(self):
        """Place a futures BUY order using available fiat balance.

        Balance lookup order:
        1. Futures account (available balance)
        2. Main account (spot main wallet)
        3. Trade account (spot trading wallet)

        Raises BinbotErrors if there is no fiat balance or if the
        configured base order size exceeds the available balance.
        """
        futures_available = 0.0
        try:
            _, _, futures_available = KucoinFuturesBalance().compute_futures_balance()
        except NotImplementedError:
            futures_available = 0.0

        available_balance = 0.0

        if futures_available > 0:
            available_balance = futures_available
        else:
            # 2) Fall back to MAIN, then TRADE accounts from spot API snapshot
            result_balances, _, _ = self.compute_balance()

            if (
                "main" in result_balances
                and self.fiat in result_balances["main"]
                and float(result_balances["main"][self.fiat]) > 0
            ):
                available_balance = float(result_balances["main"][self.fiat])
            elif (
                "trade" in result_balances
                and self.fiat in result_balances["trade"]
                and float(result_balances["trade"][self.fiat]) > 0
            ):
                available_balance = float(result_balances["trade"][self.fiat])

        if available_balance <= 0:
            raise BinbotErrors(
                f"Insufficient balances: no available {self.fiat} in futures, main, or trade accounts."
            )

        if self.active_bot.fiat_order_size > available_balance:
            raise BinbotErrors(
                f"Requested base order size {self.active_bot.fiat_order_size} {self.fiat} "
                f"exceeds available balance {available_balance} {self.fiat}."
            )

        return available_balance

    def base_order(self) -> BotModel:
        """
        Futures have positions intrinsically built, the base order can be either LONG or SHORT, we don't need to deal with loans, we simply set the position as an order
        """
        if self.active_bot.fiat_order_size <= 0:
            raise BinbotErrors("Fiat order size must be set.")

        available_balance = self.compute_available_balance()
        if self.active_bot.fiat_order_size > available_balance:
            raise BinbotErrors(
                f"Requested base order size {self.active_bot.fiat_order_size} {self.fiat} "
                f"exceeds available balance {available_balance} {self.fiat}."
            )

        price = self.kucoin_futures_api.matching_engine(
            symbol=self.kucoin_symbol, side=AddOrderReq.SideEnum.BUY, size=1
        )
        contracts = self.calculate_contracts(price)

        if contracts <= 0:
            raise BinbotErrors(
                "Calculated contracts is 0. Check if the order size, stop loss, and risk settings are correct."
            )

        if self.active_bot.strategy == Strategy.margin_short:
            order: OrderModel = self.kucoin_futures_api.sell(
                symbol=self.kucoin_symbol,
                qty=contracts,
            )
        else:
            order = self.kucoin_futures_api.buy(
                symbol=self.kucoin_symbol,
                qty=contracts,
            )

        order.deal_type = DealType.base_order
        self.active_bot.orders.append(order)

        position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)

        # For system to work. Only Futures these 2 values are the same (we are not trading underlying asset)
        self.active_bot.deal.base_order_size = self.active_bot.fiat_order_size
        self.active_bot.deal.opening_price = order.price
        self.active_bot.deal.opening_qty = order.qty
        self.active_bot.deal.opening_timestamp = order.timestamp
        self.active_bot.deal.current_price = position.mark_price
        self.active_bot.status = Status.active

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Futures LONG opened @ {position.mark_price} with {order.qty} contracts",
        )

        self.controller.save(self.active_bot)
        return self.active_bot

    def place_stop_loss(self) -> None:
        if self.active_bot.stop_loss <= 0:
            return

        stop_price = round_numbers(
            self.active_bot.deal.opening_price * (1 - self.active_bot.stop_loss / 100),
            self.price_precision,
        )

        if self.active_bot.strategy == Strategy.margin_short:
            side = AddOrderReq.SideEnum.BUY
        else:
            side = AddOrderReq.SideEnum.SELL

        self.kucoin_futures_api.place_futures_order(
            symbol=self.kucoin_symbol,
            side=side,
            order_type=OrderType.market,
            stop=AddOrderReq.StopEnum.DOWN,
            stop_price=stop_price,
            stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
            reduce_only=True,
            size=self.active_bot.deal.opening_qty,
        )

        self.active_bot.deal.stop_loss_price = stop_price

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Stop loss set @ {stop_price}",
        )

    def place_take_profit(self, price: float) -> None:
        price = round_numbers(price, self.price_precision)

        cancelled_ids = self.kucoin_futures_api.cancel_all_futures_orders(
            self.kucoin_symbol
        )
        if len(cancelled_ids) > 0:
            self.controller.update_logs(
                bot=self.active_bot,
                log_message=f"Cancelled existing TP orders: {', '.join(cancelled_ids)}",
            )
            for order_id in cancelled_ids:
                for index, existing_order in enumerate(self.active_bot.orders):
                    if existing_order.order_id == order_id:
                        existing_order.status = OrderStatus.CANCELED
                        self.active_bot.orders[index] = existing_order

        if self.active_bot.strategy == Strategy.margin_short:
            side = AddOrderReq.SideEnum.BUY
        else:
            side = AddOrderReq.SideEnum.SELL

        order = self.kucoin_futures_api.place_futures_order(
            symbol=self.kucoin_symbol,
            side=side,
            order_type=OrderType.limit,
            price=price,
            size=self.active_bot.deal.opening_qty,
            reduce_only=True,
        )
        self.active_bot.orders.append(order)

        self.active_bot.deal.take_profit_price = price

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Take profit set @ {price}",
        )

    def update_parameters(self) -> BotModel:
        if self.active_bot.stop_loss > 0:
            buy_price = self.active_bot.deal.opening_price
            stop_loss_price = buy_price - (
                buy_price * (self.active_bot.stop_loss / 100)
            )
            self.active_bot.deal.stop_loss_price = round_numbers(
                stop_loss_price, self.price_precision
            )
            stop_orders = self.kucoin_futures_api.get_all_stop_loss_orders(
                self.kucoin_symbol
            )
            stop_order_ids = [order.id for order in stop_orders]
            self.kucoin_futures_api.futures_order_api.batch_cancel_orders(
                stop_order_ids
            )

            self.place_stop_loss()

        if (
            self.active_bot.trailling
            and self.active_bot.trailling_deviation > 0
            and self.active_bot.trailling_profit > 0
        ):
            trailling_profit_price = float(self.active_bot.deal.opening_price) * (
                1 + (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.trailling_profit_price = round_numbers(
                trailling_profit_price, self.price_precision
            )

            if self.active_bot.deal.trailling_stop_loss_price != 0:
                # trailling_stop_loss_price should be updated during streaming
                # This resets it after "Update deal" because parameters have changed
                self.active_bot.deal.trailling_stop_loss_price = 0

        return self.active_bot

    def update_parameters_with_activation(self) -> BotModel:
        # Update stop loss regarless of base order
        if self.active_bot.stop_loss > 0:
            price = self.active_bot.deal.opening_price
            self.active_bot.deal.stop_loss_price = price + (
                price * (self.active_bot.stop_loss / 100)
            )

        # Keep trailling_stop_loss_price up to date in case of failure to update in autotrade
        # if we don't do this, the trailling stop loss will trigger
        if self.active_bot.trailling:
            trailling_profit = float(self.active_bot.deal.opening_price) * (
                1 + (float(self.active_bot.trailling_profit) / 100)
            )
            self.active_bot.deal.trailling_profit_price = trailling_profit
            # Reset trailling stop loss
            # this should be updated during streaming
            self.active_bot.deal.trailling_stop_loss_price = 0
            # Old property fix
            self.active_bot.deal.take_profit_price = 0

        else:
            # No trailling so only update take_profit
            take_profit_price = float(self.active_bot.deal.opening_price) * (
                1 + (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price

        self.active_bot.status = Status.active
        self.active_bot.add_log("Bot re-activated")
        self.controller.save(self.active_bot)
        return self.active_bot

    def close_all(self) -> BotModel:
        """
        Closes all open positions and cancels all orders.
        To be used also for panic selling from terminal.
        """
        position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)

        if position and float(position.current_qty) != 0:
            side_enum = (
                AddOrderReq.SideEnum.SELL
                if float(position.current_qty) > 0
                else AddOrderReq.SideEnum.BUY
            )

            self.kucoin_futures_api.place_futures_order(
                symbol=self.kucoin_symbol,
                side=side_enum,
                order_type=OrderType.market,
                size=abs(float(position.current_qty)),
                reduce_only=True,
            )

        self.active_bot.status = Status.completed
        self.active_bot.deal.closing_timestamp = int(time() * 1000)

        self.controller.update_logs(
            bot=self.active_bot,
            log_message="Futures position closed",
        )

        self.controller.save(self.active_bot)
        return self.active_bot

    def open_deal(self) -> BotModel:
        base_order = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == DealType.base_order
            ),
            None,
        )

        if not base_order:
            self.active_bot.add_log(
                f"Opening new future deal for {self.kucoin_symbol}..."
            )
            self.controller.save(self.active_bot)
            self.base_order()

        if (
            self.active_bot.status == Status.active
            or self.active_bot.deal.opening_price > 0
        ):
            # Update bot no activation required
            self.active_bot = self.update_parameters()
        else:
            # Activation required
            self.active_bot = self.update_parameters_with_activation()

        self.controller.save(self.active_bot)
        return self.active_bot
