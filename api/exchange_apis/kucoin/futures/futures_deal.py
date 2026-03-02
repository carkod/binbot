from typing import Union, Type
from time import time
from pybinbot import (
    OrderBase,
    Strategy,
    round_numbers,
    DealType,
    convert_to_kucoin_symbol,
    Status,
    OrderType,
    OrderStatus,
    BinbotErrors,
    KucoinFutures,
)
from exchange_apis.kucoin.futures.position_market import PositionMarket
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.bot_crud import BotTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from bots.models import BotModel
from bots.models import OrderModel
from exchange_apis.kucoin.deals.base import KucoinBaseBalance
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from exchange_apis.kucoin.futures.balance import KucoinFuturesBalance
from streaming.apex_flow_closing import ApexFlowClose
from copy import deepcopy
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
        self.controller: Union[BotTableCrud, PaperTradingTableCrud]

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
            symbol=self.kucoin_symbol, side=AddOrderReq.SideEnum.BUY, size=1
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
            if len(stop_orders) > 0:
                stop_order_ids = [order.id for order in stop_orders]
                self.kucoin_futures_api.batch_cancel_stop_loss_orders(stop_order_ids)

            # stop loss placed in the market will reduce the position to 0
            if not self.active_bot.margin_short_reversal:
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

    def market_trailing_analytics(
        self,
        position_market_cls: PositionMarket,
        current_price: float,
    ) -> None:
        """
        ApexFlow-aware trailing manager.

        Philosophy:
        1. Initiates PositionMarket (abstraction layer to reduce complexity of KucoinPositionDeal)
        - stop_loss = emergency only
        - trailing_deviation = active stop after trailing
        - trailing_profit = trigger, never exit
        """
        self.apex_flow_closing = ApexFlowClose(
            position_market_cls.df, position_market_cls.btc_df
        )

        original_bot = deepcopy(self.active_bot)

        # ─────────────────────────────
        # Bollinger spreads
        # ─────────────────────────────
        bb_spreads = position_market_cls.build_bb_spreads()
        if bb_spreads.bb_high == 0 or bb_spreads.bb_low == 0:
            return

        top_spread = (
            abs((bb_spreads.bb_high - bb_spreads.bb_mid) / bb_spreads.bb_high) * 100
        )
        bottom_spread = (
            abs((bb_spreads.bb_mid - bb_spreads.bb_low) / bb_spreads.bb_mid) * 100
        )

        top_spread = min(max(top_spread, 1.5), 6.0)
        bottom_spread = min(max(bottom_spread, 1.0), 4.0)

        # ─────────────────────────────
        # Profit
        # ─────────────────────────────
        bot_profit = self.base_streaming.compute_single_bot_profit(
            self.active_bot, current_price
        )

        # ─────────────────────────────
        # ApexFlow detectors
        # ─────────────────────────────
        row = self.apex_flow_closing.df.iloc[-1]
        detectors = self.apex_flow_closing.get_detectors()

        vce_signal = detectors.get("vce", False)
        mcd_signal = detectors.get("mcd", False)
        lcrs_signal = detectors.get("lcrs", False)

        expansion_range = row["high"] - row["low"]
        is_aggressive_momo = self.active_bot.name.lower().find("aggressive momo") != -1

        # ─────────────────────────────
        # Trend filter (only for tightening)
        # ─────────────────────────────
        ema_fast, ema_slow = self.apex_flow_closing.get_trend_ema()
        trend_up = ema_fast > ema_slow if ema_fast and ema_slow else True

        # ─────────────────────────────
        # Expansion multiplier
        # ─────────────────────────────
        expansion_multiplier = 1.0
        if vce_signal:
            expansion_multiplier += 0.2
        if mcd_signal:
            expansion_multiplier += 0.1
        expansion_multiplier = min(expansion_multiplier, 1.5)

        # ─────────────────────────────
        # Trailing tightening schedule
        # ─────────────────────────────
        if bot_profit < 2:
            trail_tighten_mult = 1.0
        elif bot_profit < 5:
            trail_tighten_mult = 0.7
        else:
            trail_tighten_mult = 0.45

        # Do not tighten against trend while signals are alive
        if (vce_signal or mcd_signal or lcrs_signal) and trend_up:
            trail_tighten_mult = max(trail_tighten_mult, 0.7)

        # ─────────────────────────────
        # Apply strategy-specific logic
        # ─────────────────────────────
        position_market_cls.set_trailing_params(
            top_spread=top_spread,
            bottom_spread=bottom_spread,
            bot_profit=bot_profit,
            expansion_multiplier=expansion_multiplier,
            is_aggressive_momo=is_aggressive_momo,
            expansion_range=expansion_range,
            trail_tighten_mult=trail_tighten_mult,
        )

        # ─────────────────────────────
        # Persist only if changed
        # ─────────────────────────────
        if (
            self.active_bot.trailling_profit != original_bot.trailling_profit
            or self.active_bot.trailling_deviation != original_bot.trailling_deviation
            or self.active_bot.stop_loss != original_bot.stop_loss
        ):
            self.active_bot = self.update_parameters()
            self.controller.save(self.active_bot)
