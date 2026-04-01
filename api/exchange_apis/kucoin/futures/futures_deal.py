from time import time
from typing import Type

from bots.models import BotModel, OrderModel
from databases.crud.bot_crud import BotTableCrud
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from exchange_apis.kucoin.deals.base import KucoinBaseBalance
from exchange_apis.kucoin.futures.balance import KucoinFuturesBalance
from kucoin_universal_sdk.generate.futures.order import GetTradeHistoryReq
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from pybinbot import (
    BinbotErrors,
    DealType,
    KucoinFutures,
    OrderBase,
    OrderStatus,
    OrderType,
    Status,
    Strategy,
    convert_to_kucoin_symbol,
    round_numbers,
)
from streaming.base import BaseStreaming


class KucoinPositionDeal(KucoinBaseBalance):
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
        db_table: Type[BotTable] | Type[PaperTradingTable] = BotTable,
    ) -> None:
        super().__init__()
        self.base_streaming = BaseStreaming()
        self.active_bot = bot
        self.db_table = db_table
        self.kucoin_futures_api = KucoinFutures(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.controller: BotTableCrud | PaperTradingTableCrud

        if db_table == PaperTradingTable:
            self.controller = PaperTradingTableCrud()
        else:
            self.controller = BotTableCrud()

        self.symbol_info = SymbolsCrud().get_symbol(bot.pair)
        self.kucoin_symbol = convert_to_kucoin_symbol(bot)
        self.kucoin_symbol_data = self.kucoin_futures_api.get_symbol_info(
            self.kucoin_symbol
        )
        self.price_precision = self.symbol_info.price_precision

    def _direction_multiplier(self) -> int:
        return -1 if self.active_bot.strategy == Strategy.margin_short else 1

    def calculate_contracts(self, price: float) -> int:
        """
        Calculate the number of contracts based on balance, stop loss, risk per trade, price, and contract multiplier.

        balance: Available USDT balance.
        stop_loss_percent: Stop loss as a decimal (e.g., 3% = 0.03).
        max_risk_percent: Max risk per trade as a decimal (e.g., 5% = 0.05).
        price: Current price of FLOCK.
        multiplier: Size of one contract (default 1).

        Returns: Number of contracts to buy (int).
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

        return int(contracts)

    def compute_available_balance(self) -> float:
        """
        Compute the available balance for placing a futures BUY order.

        Balance lookup order:
        1. Futures account (available balance)
        2. Main account (spot main wallet)
        3. Trade account (spot trading wallet)

        Raises BinbotErrors if there is no fiat balance or if the
        configured base order size exceeds the available balance.
        """
        _, _, futures_available = KucoinFuturesBalance().compute_futures_balance()

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

        return available_balance

    def min_required_balance(self) -> float:
        """
        Calculate the minimum required balance to place a futures order based on stop loss and risk settings.
        """
        multiplier = self.kucoin_symbol_data.multiplier
        min_qty = self.kucoin_symbol_data.lot_size
        price = self.kucoin_symbol_data.mark_price
        taker_fee_rate = self.kucoin_symbol_data.taker_fee_rate
        self.kucoin_symbol_data
        maintenance_margin = self.kucoin_symbol_data.maintain_margin
        notional = price * min_qty * multiplier

        initial_margin = notional / self.kucoin_futures_api.DEFAULT_LEVERAGE
        fees = 2 * notional * taker_fee_rate

        required_balance = initial_margin + maintenance_margin + fees
        return required_balance

    def backfill_position_from_fills(self) -> BotModel:
        self.active_bot.add_log(
            "Position not found in exchange, cannot update size. ADL might have happened, or position might have been closed without bot's knowledge."
        )
        side = (
            GetTradeHistoryReq.SideEnum.BUY
            if self.active_bot.strategy == Strategy.margin_short
            else GetTradeHistoryReq.SideEnum.SELL
        )

        start_at = int(self.active_bot.deal.opening_timestamp)  # already ms
        now_ms = int(time() * 1000)

        fills = self.base_streaming.kucoin_futures_api.get_fills(
            side=side,
            symbol=self.kucoin_symbol,
            start_at=start_at,
            end_at=now_ms,
        )
        self.active_bot.add_log(
            f"Fetched fills history to check for position updates. Number of fills found: {len(fills.items)}."
        )
        if len(fills.items) > 0:
            total_qty = sum(abs(float(fill.size)) for fill in fills.items)
            order_resp = fills.items[0]
            total_notional = sum(
                abs(float(fill.size)) * float(fill.price) for fill in fills.items
            )
            closing_price = (
                round_numbers(total_notional / total_qty, self.price_precision)
                if total_qty > 0
                else float(order_resp.price)
            )
            if self.active_bot.strategy == Strategy.margin_short:
                deal_type = (
                    DealType.take_profit
                    if (closing_price < self.active_bot.deal.opening_price)
                    else DealType.stop_loss
                )
            else:
                deal_type = (
                    DealType.take_profit
                    if (closing_price > self.active_bot.deal.opening_price)
                    else DealType.stop_loss
                )

            exit_order = OrderModel(
                order_id=order_resp.order_id,
                order_type=order_resp.order_type.value,
                pair=order_resp.symbol,
                timestamp=order_resp.created_at,
                order_side=order_resp.side.value,
                qty=total_qty,
                price=closing_price,
                status=OrderStatus.FILLED,
                # no data, assumed
                time_in_force="GTC",
                deal_type=deal_type,
            )
            self.active_bot.orders.append(exit_order)
            self.active_bot.deal.closing_price = closing_price
            self.active_bot.deal.closing_qty = total_qty
            self.active_bot.deal.closing_timestamp = order_resp.created_at
            self.active_bot.deal.total_commissions += float(order_resp.fee)
            self.active_bot.status = Status.completed
            self.active_bot.add_log(
                f"Position size updated from fills history. New size: {total_qty}."
            )
            return self.active_bot

        else:
            self.active_bot.add_log(
                "No fills found in history, cannot update position size. ADL might have happened, or position might have been closed without bot's knowledge."
            )
            self.active_bot.status = Status.error

        return self.active_bot

    def remove_stale_orders(self) -> None:
        stale_orders = [
            order
            for order in self.active_bot.orders
            if order.deal_type == DealType.trailling_profit
            and order.status == OrderStatus.FILLED
            and order.price == 0
            and order.qty == 0
        ]
        for stale_order in stale_orders:
            try:
                self.controller.delete_order(
                    str(stale_order.order_id), str(self.active_bot.id)
                )
            except BinbotErrors:
                pass

        self.active_bot.orders = [
            order
            for order in self.active_bot.orders
            if not (
                order.deal_type == DealType.trailling_profit
                and order.status == OrderStatus.FILLED
                and order.price == 0
                and order.qty == 0
            )
        ]

    def cancel_current_sl(self) -> None:
        """
        Find current stop loss orders in exchange in place and batch cancel them.
        this works for both trailing and stop loss, long and short
        """
        stop_orders = self.kucoin_futures_api.get_all_stop_loss_orders(
            self.kucoin_symbol
        )
        if len(stop_orders) > 0:
            stop_order_ids = [order.id for order in stop_orders]
            self.kucoin_futures_api.batch_cancel_stop_loss_orders(stop_order_ids)
            for index, existing_order in enumerate(self.active_bot.orders):
                if existing_order.order_id in stop_order_ids:
                    existing_order.status = OrderStatus.CANCELED
                    self.active_bot.orders[index] = existing_order
        else:
            self.remove_stale_orders()

    def base_order(self) -> BotModel:
        """
        Futures have positions intrinsically built, the base order can be either LONG or SHORT, we don't need to deal with loans, we simply set the position as an order
        """
        if self.active_bot.fiat_order_size <= 0:
            raise BinbotErrors("Fiat order size must be set.")

        available_balance = self.compute_available_balance()
        if self.active_bot.fiat_order_size > available_balance:
            required_balance = self.min_required_balance()

            if required_balance > available_balance:
                raise BinbotErrors(
                    f"Requested base order size {self.active_bot.fiat_order_size} {self.fiat} "
                    f"exceeds available balance {available_balance} {self.fiat}."
                )

        price = self.kucoin_futures_api.matching_engine(
            symbol=self.kucoin_symbol,
            side=AddOrderReq.SideEnum.BUY,
            size=available_balance,
        )

        contracts = self.calculate_contracts(price)

        if contracts <= 0:
            raise BinbotErrors(
                "Calculated contracts is 0. Check if the order size, stop loss, and risk settings are correct."
            )

        if self.active_bot.strategy == Strategy.margin_short:
            order: OrderBase = self.kucoin_futures_api.sell(
                symbol=self.kucoin_symbol,
                qty=contracts,
            )
        else:
            order = self.kucoin_futures_api.buy(
                symbol=self.kucoin_symbol,
                qty=contracts,
            )

        order.deal_type = DealType.base_order
        order = OrderModel(**order.model_dump())
        self.active_bot.orders.append(order)

        position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)

        # For Futures, base_order_size is contracts
        # Kucoin only operates with contracts, not underlying asset (qty)
        # so in Binbot we only care about that
        self.active_bot.deal.base_order_size = contracts
        self.active_bot.deal.opening_price = order.price
        self.active_bot.deal.opening_qty = contracts
        self.active_bot.deal.opening_timestamp = order.timestamp
        self.active_bot.deal.current_price = position.mark_price
        self.active_bot.status = Status.active

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Futures {self.active_bot.strategy.name} opened @ {position.mark_price} with {order.qty} contracts",
        )

        self.controller.save(self.active_bot)
        return self.active_bot

    def place_stop_loss(self) -> None:
        if self.active_bot.stop_loss <= 0:
            return

        direction = self._direction_multiplier()
        stop_price = float(self.active_bot.deal.stop_loss_price)
        if stop_price <= 0:
            stop_price = round_numbers(
                self.active_bot.deal.opening_price
                - (
                    self.active_bot.deal.opening_price
                    * (self.active_bot.stop_loss / 100)
                    * direction
                ),
                self.price_precision,
            )

        if self.active_bot.strategy == Strategy.margin_short:
            side = AddOrderReq.SideEnum.BUY
            stop = AddOrderReq.StopEnum.UP
        else:
            side = AddOrderReq.SideEnum.SELL
            stop = AddOrderReq.StopEnum.DOWN

        order_response = self.kucoin_futures_api.place_futures_order(
            symbol=self.kucoin_symbol,
            side=side,
            order_type=OrderType.market,
            stop=stop,
            stop_price=stop_price,
            stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
            reduce_only=True,
            size=self.active_bot.deal.opening_qty,
        )

        order_model = OrderModel(**order_response.model_dump())
        self.active_bot.orders.append(order_model)
        self.active_bot.deal.stop_loss_price = stop_price

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Stop loss set @ {stop_price}",
        )

    def update_parameters(self) -> BotModel:
        """
        Updates stop loss and take profit orders based on the current bot parameters.

        direction is determined by the strategy (long or short) and is used to calculate the correct stop loss price.
        """
        direction = self._direction_multiplier()

        # edge case, should be set from base_order
        if self.active_bot.deal.opening_price == 0:
            for order in self.active_bot.orders:
                if order.deal_type == DealType.base_order:
                    self.active_bot.deal.opening_price = order.price
                    self.active_bot.deal.opening_qty = order.qty
                    self.active_bot.deal.opening_timestamp = order.timestamp
                    break

        if self.active_bot.stop_loss > 0:
            entry_price = float(self.active_bot.deal.opening_price)
            delta = entry_price * (self.active_bot.stop_loss / 100)
            stop_loss_price = entry_price - (delta * direction)
            self.active_bot.deal.stop_loss_price = round_numbers(
                stop_loss_price, self.price_precision
            )
            self.cancel_current_sl()

            # stop loss placed in the market will reduce the position to 0
            if not self.active_bot.margin_short_reversal:
                self.place_stop_loss()

        if (
            self.active_bot.trailling
            and self.active_bot.trailling_deviation > 0
            and self.active_bot.trailling_profit > 0
        ):
            entry_price = float(self.active_bot.deal.opening_price)
            trailling_profit_price = entry_price * (
                1 + direction * (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.trailling_profit_price = round_numbers(
                trailling_profit_price, self.price_precision
            )

            # trailling_stop_loss_price and trailling_profit should be updated during streaming
            # This resets it after "Update deal" because parameters have changed
            if self.active_bot.trailling_profit != 0:
                new_trailing_profit_price = self.active_bot.deal.opening_price * (
                    1 + direction * (float(self.active_bot.trailling_profit) / 100)
                )
                self.active_bot.deal.trailling_profit_price = round_numbers(
                    new_trailing_profit_price, self.price_precision
                )
            if self.active_bot.deal.trailling_stop_loss_price != 0:
                self.active_bot.deal.trailling_stop_loss_price = 0

        return self.active_bot

    def update_parameters_with_activation(self) -> BotModel:
        """
        update_parameters with some additional logic for activation:
        - If the bot is already active, it means we are updating parameters without changing the position, so we just call update_parameters.
        - If the bot is not active, it means we are activating the bot, so we need to set the parameters and then activate it. This is used for example when we open a new deal and we want to set the SL and TP at the same time, so we update parameters with activation right after opening the deal.
        """
        direction = self._direction_multiplier()

        if self.active_bot.stop_loss > 0:
            price = float(self.active_bot.deal.opening_price)
            delta = price * (self.active_bot.stop_loss / 100)
            self.active_bot.deal.stop_loss_price = price - (delta * direction)

        if self.active_bot.trailling:
            trailling_profit = float(self.active_bot.deal.opening_price) * (
                1 + direction * (float(self.active_bot.trailling_profit) / 100)
            )
            self.active_bot.deal.trailling_profit_price = trailling_profit
            self.active_bot.deal.trailling_stop_loss_price = 0
            self.active_bot.deal.take_profit_price = 0
        else:
            take_profit_price = float(self.active_bot.deal.opening_price) * (
                1 + direction * (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price

        self.active_bot.status = Status.active
        if direction == -1:
            self.active_bot.add_log("Bot re-activated (short)")
        else:
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
            if self.active_bot.strategy == Strategy.margin_short:
                order_response = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=abs(int(position.current_qty)),
                    reduce_only=True,
                )
            else:
                order_response = self.kucoin_futures_api.sell(
                    symbol=self.kucoin_symbol,
                    qty=abs(int(position.current_qty)),
                    reduce_only=True,
                )

            order_model = OrderModel(**order_response.model_dump())
            self.active_bot.orders.append(order_model)
            self.active_bot.deal.closing_price = order_response.price
            self.active_bot.deal.closing_qty = abs(int(position.current_qty))
            self.active_bot.status = Status.completed
            self.controller.update_logs(
                bot=self.active_bot,
                log_message="Futures position panic-closed successfully",
            )

        else:
            self.active_bot = self.backfill_position_from_fills()

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
