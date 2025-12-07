import logging
from typing import Type, Union, Any
from tools.maths import round_numbers_floor, round_numbers
from tools.enum_definitions import DealType, QuoteAssets, Status, Strategy, OrderSide
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.bot_crud import BotTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from bots.models import BotModel, OrderModel
from exchange_apis.kucoin.deals.base import KucoinBaseBalance
from tools.handle_error import BinanceErrors
from time import sleep


class KucoinSpotDeal(KucoinBaseBalance):
    """Stub KuCoin spot deal implementation matching BinanceSpotDeal interface.

    Methods raise NotImplementedError until proper KuCoin spot logic is added.
    Used for polymorphic delegation via `deal_base`.
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ) -> None:
        super().__init__()
        self.active_bot = bot
        self.db_table = db_table
        # Provide a controller attribute for polymorphic access
        self.controller: Union[PaperTradingTableCrud, BotTableCrud, Any]
        self.controller = None
        self.symbol_info = SymbolsCrud().get_symbol(bot.pair)
        self.price_precision = self.symbol_info.price_precision
        self.qty_precision = self.symbol_info.qty_precision

    def buy_order_with_available_balance(self) -> dict | None:
        """
        Places a buy order using the available balance for the base asset.

        Returns:
            The response from the KuCoin API after placing the buy order.
        """
        result_balances, estimated_total_fiat, fiat_available = self.compute_balance()
        symbol = f"{self.active_bot.quote_asset.value}-{self.active_bot.fiat}"
        quote_asset = self.active_bot.quote_asset.value
        last_ticker_price = float(self.kucoin_api.get_ticker_price(symbol))

        if quote_asset in result_balances:
            available_balance = float(result_balances[quote_asset])
            if available_balance > 0:
                qty = available_balance / last_ticker_price
                order_response = self.buy_order(symbol=symbol, qty=qty)
                return order_response
        return None

    def long_open_deal_trailling_parameters(self) -> BotModel:
        """
        This updates trailling parameters for spot long bots
        Once bot is activated.

        Inherits from old open_deal method
        this one simplifies by separating strategy specific
        """

        if self.active_bot.strategy == Strategy.margin_short:
            logging.error("Bot executing wrong long_open_deal_trailling_parameters")
            return self.active_bot

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
        self.active_bot.add_log("Bot activated")
        self.controller.save(self.active_bot)
        return self.active_bot

    def long_update_deal_trailling_parameters(self) -> BotModel:
        """
        Same as long_open_deal_trailling_parameters
        but when clicked on "update deal".

        This makes sure deal trailling values are up to date and
        not out of sync with the bot parameters
        """

        if self.active_bot.strategy == Strategy.margin_short:
            logging.error("Bot executing wrong long_update_deal_trailling_parameters")
            return self.active_bot

        if self.active_bot.stop_loss > 0:
            buy_price = self.active_bot.deal.opening_price
            stop_loss_price = buy_price - (
                buy_price * (self.active_bot.stop_loss / 100)
            )
            self.active_bot.deal.stop_loss_price = round_numbers(
                stop_loss_price, self.price_precision
            )

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

    def base_order(self, repurchase_multiplier: float = 0.95) -> BotModel:
        """
        Required initial order to trigger long strategy bot.
        Other orders require this to execute,
        therefore should fail if not successful

        1. Initial base purchase (0 qty)
            1.1 if not enough quote asset to purchase, redo it with exact qty needed
        2. Set take_profit
        """
        if self.active_bot.quote_asset != QuoteAssets.USDC:
            response = self.buy_order_with_available_balance()
            if response:
                order = OrderModel(
                    timestamp=int(response["transactTime"]),
                    order_id=int(response["orderId"]),
                    deal_type=DealType.conversion,
                    pair=response["symbol"],
                    order_side=response["side"],
                    order_type=response["type"],
                    price=float(response["price"]),
                    qty=float(response["origQty"]),
                    time_in_force=response["timeInForce"],
                    status=response["status"],
                )
                self.active_bot.orders.append(order)
                self.controller.update_logs(
                    bot=self.active_bot, log_message="Quote asset purchase successful."
                )
                self.active_bot.deal.base_order_size = float(response["origQty"])
                if self.active_bot.quote_asset.is_fiat():
                    self.active_bot.deal.base_order_size = float(
                        response["origQty"]
                    ) * float(response["price"])
                # give some time for order to complete
                sleep(3)

            # Long position does not need qty in take_profit
            # initial price with 1 qty should return first match
            last_ticker_price = self.kucoin_api.get_ticker_price(self.active_bot.pair)

            if self.active_bot.strategy == Strategy.margin_short:
                # Use all available quote asset balance
                # this avoids diffs in ups and downs in prices and fees
                available_quote_asset = self.kucoin_api.get_single_spot_balance(
                    self.active_bot.quote_asset
                )
            else:
                available_quote_asset = self.kucoin_api.get_isolated_balance(
                    self.active_bot.quote_asset
                )

            qty = round_numbers_floor(
                (available_quote_asset / last_ticker_price),
                self.qty_precision,
            )

        else:
            self.active_bot.deal.base_order_size = self.active_bot.fiat_order_size
            last_ticker_price = self.kucoin_api.get_ticker_price(self.active_bot.pair)

            qty = round_numbers_floor(
                (self.active_bot.deal.base_order_size / last_ticker_price),
                self.qty_precision,
            )

        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.simulate_order(
                self.active_bot.pair,
                OrderSide.buy,
            )
        else:
            try:
                res = self.buy_order(
                    symbol=self.active_bot.pair,
                    qty=(qty * repurchase_multiplier),
                )
            except BinanceErrors as error:
                if error.code == -2010:
                    self.controller.update_logs(
                        bot=self.active_bot,
                        log_message=error.message,
                    )
                    if (
                        error.message
                        == "This symbol is not permitted for this account."
                    ):
                        return self.active_bot

                    if repurchase_multiplier > 0.80:
                        self.base_order(
                            repurchase_multiplier=repurchase_multiplier - 0.05
                        )
                    return self.active_bot

        self.controller.update_logs(
            bot=self.active_bot, log_message="Base order executed."
        )

        res_price = float(res["price"])

        if self.active_bot.deal.base_order_size == 0:
            self.active_bot.deal.base_order_size = float(res["origQty"]) * res_price

        if res_price == 0:
            # Market orders return 0
            res_price = self.calculate_avg_price(res["fills"])

        order_data = OrderModel(
            timestamp=int(res["transactTime"]),
            order_id=res["orderId"],
            deal_type=DealType.base_order,
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=res_price,
            qty=float(res["origQty"]),
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.total_commissions += self.calculate_total_commissions(
            res["fills"]
        )

        self.active_bot.deal.opening_timestamp = int(res["transactTime"])
        self.active_bot.deal.opening_price = res_price
        self.active_bot.deal.opening_qty = float(res["origQty"])
        self.active_bot.deal.current_price = float(res["price"])

        # temporary measures to keep deal up to date
        # once bugs are fixed, this can be removed to improve efficiency
        self.active_bot.status = Status.active
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
            if not self.symbol_info.is_margin_trading_allowed:
                self.active_bot.margin_short_reversal = False
                self.active_bot.add_log(
                    "Auto short bot reversal disabled. Exchange doesn't support margin trading for this pair."
                )

            self.controller.update_logs(
                f"Opening new spot deal for {self.active_bot.pair}...", self.active_bot
            )
            self.controller.save(self.active_bot)
            self.base_order()

        if (
            self.active_bot.status == Status.active
            or self.active_bot.deal.opening_price > 0
        ):
            # Update bot no activation required
            self.active_bot = self.long_update_deal_trailling_parameters()
        else:
            # Activation required
            self.active_bot = self.long_open_deal_trailling_parameters()

        self.controller.save(self.active_bot)
        return self.active_bot

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
