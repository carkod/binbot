import logging
from time import sleep

from kucoin_universal_sdk.generate.margin.order.model_add_order_req import (
    AddOrderReq,
)
from kucoin_universal_sdk.generate.margin.order.model_get_order_by_order_id_resp import (
    GetOrderByOrderIdResp,
)
from kucoin_universal_sdk.model.common import RestError
from pybinbot import (
    DealType,
    OrderStatus,
    QuoteAssets,
    Status,
    Strategy,
    round_numbers,
    round_numbers_ceiling,
    round_numbers_floor,
)

from bots.models import BotModel, OrderModel
from databases.crud.bot_crud import BotTableCrud
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from exchange_apis.kucoin.deals.base import KucoinBaseBalance


class KucoinSpotDeal(KucoinBaseBalance):
    """
    Spot deal implementation matching BinanceSpotDeal interface.

    Starts when a bot is activated
    deal object is then filled up ready for Long Deal (streaming) operations.
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: type[PaperTradingTable | BotTable] = BotTable,
    ) -> None:
        super().__init__()
        self.active_bot = bot
        self.db_table = db_table
        self.controller: PaperTradingTableCrud | BotTableCrud
        if db_table == PaperTradingTable:
            self.controller = PaperTradingTableCrud()
        else:
            self.controller = BotTableCrud()

        # Provide a controller attribute for polymorphic access
        self.symbol_info = SymbolsCrud().get_symbol(bot.pair)
        self.price_precision = self.symbol_info.price_precision
        self.qty_precision = self.symbol_info.qty_precision
        self.symbol = self.get_symbol(bot.pair, bot.quote_asset)

    def check_trading_balance_and_update(self) -> bool:
        """
        Checks if there is available balance in the trading account for the quote asset.

        Returns:
            bool: True if there is available balance, False otherwise.
        """
        result_balances, _, _ = self.compute_balance()
        if not result_balances:
            return False

        quote_asset = self.active_bot.quote_asset.value

        # in theory main account should never be empty
        if quote_asset in result_balances["main"]:
            if (
                "trade" in result_balances
                and quote_asset in result_balances["trade"].keys()
            ):
                if (
                    float(result_balances["trade"][quote_asset])
                    >= self.active_bot.fiat_order_size
                ):
                    # There is enough money to trade
                    return True

                # Calculate amount needed to transfer
                amount_needed = self.active_bot.fiat_order_size - float(
                    result_balances["trade"][quote_asset]
                )

                # Absolutely no balance to trade
                if result_balances["main"][quote_asset] < amount_needed:
                    return False

            else:
                amount_needed = self.active_bot.fiat_order_size

            response = self.kucoin_api.transfer_main_to_trade(
                asset=quote_asset,
                amount=round_numbers_ceiling(amount_needed, self.price_precision),
            )
            if response.order_id:
                self.controller.update_logs(
                    bot=self.active_bot,
                    log_message=f"Transferred {self.active_bot.fiat_order_size} {quote_asset} from main to trading account.",
                )
                return True
            else:
                self.controller.update_logs(
                    bot=self.active_bot,
                    log_message=f"Failed to transfer {self.active_bot.fiat_order_size} {quote_asset} from main to trading account.",
                )

        return False

    def buy_quote_with_available_balance(
        self,
    ) -> GetOrderByOrderIdResp | None:
        """
        Places a buy order using the available balance for the base asset.

        Returns:
            The response from the KuCoin API after placing the buy order.
        """
        result_balances, _, _ = self.compute_balance()
        quote_asset = self.active_bot.quote_asset.value
        last_ticker_price = self.kucoin_api.get_ticker_price(self.symbol)

        if quote_asset in result_balances:
            available_balance = float(result_balances["trade"][quote_asset])
            if available_balance > 0:
                qty = round_numbers(
                    available_balance / last_ticker_price, self.qty_precision
                )
                order = self.kucoin_api.buy_order(symbol=self.symbol, qty=qty)
                return order
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

    def base_order(self, repurchase_multiplier: float = 1) -> BotModel:
        """
        Required initial order to trigger long strategy bot.
        Other orders require this to execute,
        therefore should fail if not successful

        1. Initial base purchase (0 qty)
            1.1 if not enough quote asset to purchase, redo it with exact qty needed
        2. Set take_profit
        """
        if (
            self.active_bot.quote_asset != QuoteAssets.USDC
            and self.active_bot.quote_asset != QuoteAssets.USDT
        ):
            system_order = self.buy_quote_with_available_balance()
            if system_order:
                order = OrderModel(
                    timestamp=system_order.created_at,
                    order_id=system_order.id,
                    deal_type=DealType.conversion,
                    pair=system_order.symbol,
                    order_side=AddOrderReq.SideEnum.BUY,
                    order_type=system_order.type,
                    price=system_order.price,
                    qty=float(system_order.size),
                    time_in_force=system_order.time_in_force,
                    status=OrderStatus.FILLED
                    if system_order.active
                    else OrderStatus.EXPIRED,
                )
                self.active_bot.orders.append(order)
                self.controller.update_logs(
                    bot=self.active_bot, log_message="Quote asset purchase successful."
                )
                self.active_bot.deal.base_order_size = float(system_order.size)
                if self.active_bot.quote_asset.is_fiat():
                    self.active_bot.deal.base_order_size = float(order.qty) * float(
                        order.price
                    )
                # give some time for order to complete
                sleep(3)

            # Long position does not need qty in take_profit
            # initial price with 1 qty should return first match
            last_ticker_price = self.kucoin_api.get_ticker_price(self.symbol)
            available_quote_asset = self.kucoin_api.get_single_spot_balance(
                self.active_bot.quote_asset
            )

            qty = round_numbers_floor(
                (available_quote_asset / last_ticker_price),
                self.qty_precision,
            )

        else:
            is_balance = self.check_trading_balance_and_update()
            if not is_balance:
                self.controller.update_logs(
                    bot=self.active_bot,
                    log_message="Base order failed due to insufficient balance.",
                )
                return self.active_bot

            self.active_bot.deal.base_order_size = self.active_bot.fiat_order_size
            last_ticker_price = self.kucoin_api.get_ticker_price(self.symbol)

            qty = round_numbers_ceiling(
                (self.active_bot.fiat_order_size / last_ticker_price),
                self.qty_precision,
            )

        system_order = None

        if isinstance(self.controller, PaperTradingTableCrud):
            system_order = self.kucoin_api.simulate_order(
                symbol=self.symbol,
                side=AddOrderReq.SideEnum.BUY,
            )
        else:
            # repurchase multiplier nullified with Kucoin API
            try:
                system_order = self.kucoin_api.buy_order(
                    symbol=self.symbol,
                    qty=(qty * repurchase_multiplier),
                )
            except RestError as e:
                code = float(e.response.code)
                if code == 20004:
                    if repurchase_multiplier - 0.2 <= 0:
                        self.controller.update_logs(
                            bot=self.active_bot,
                            log_message="Base order failed due to insufficient balance after retries.",
                        )
                        return self.active_bot
                    self.base_order(repurchase_multiplier=repurchase_multiplier - 0.2)

        # mostly for mypy to be happy
        if not system_order:
            self.controller.update_logs(
                bot=self.active_bot,
                log_message=f"Base order failed, system_order: {system_order}.",
            )
            return self.active_bot

        self.controller.update_logs(
            bot=self.active_bot, log_message="Base order executed."
        )

        res_price = float(system_order.price)

        if self.active_bot.deal.base_order_size == 0:
            self.active_bot.deal.base_order_size = float(system_order.size) * res_price

        order_data = OrderModel(
            timestamp=system_order.created_at,
            order_id=system_order.id,
            deal_type=DealType.base_order,
            pair=system_order.symbol,
            order_side=system_order.side,
            order_type=system_order.type,
            price=res_price,
            qty=float(system_order.size),
            time_in_force=system_order.time_in_force,
            status=OrderStatus.FILLED if system_order.active else OrderStatus.EXPIRED,
        )

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.total_commissions += float(system_order.fee)

        self.active_bot.deal.opening_timestamp = system_order.created_at
        self.active_bot.deal.opening_price = res_price
        self.active_bot.deal.opening_qty = float(system_order.size)
        self.active_bot.deal.current_price = float(system_order.price)

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
        """
        Close all open positions for spot long bot
        """
        if self.active_bot.deal.opening_qty > 0:
            if isinstance(self.controller, PaperTradingTableCrud):
                system_order = self.kucoin_api.simulate_order(
                    symbol=self.symbol,
                    side=AddOrderReq.SideEnum.SELL,
                )
            else:
                system_order = self.kucoin_api.sell_order(
                    symbol=self.symbol,
                    qty=self.active_bot.deal.opening_qty,
                )

            if system_order:
                order = OrderModel(
                    timestamp=system_order.created_at,
                    order_id=system_order.id,
                    deal_type=DealType.panic_close,
                    pair=system_order.symbol,
                    order_side=AddOrderReq.SideEnum.SELL,
                    order_type=system_order.type,
                    price=system_order.price,
                    qty=float(system_order.size),
                    time_in_force=system_order.time_in_force,
                    status=OrderStatus.FILLED
                    if system_order.active
                    else OrderStatus.EXPIRED,
                )
                self.active_bot.orders.append(order)
                self.controller.update_logs(
                    bot=self.active_bot, log_message="Spot position closed."
                )

        self.active_bot.deal.closing_price = system_order.price
        self.active_bot.deal.closing_timestamp = system_order.last_updated_at
        self.active_bot.status = Status.completed
        self.active_bot.add_log("Spot deal closed.")
        self.controller.save(self.active_bot)
        return self.active_bot
