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
    convert_to_kucoin_symbol,
    round_numbers,
    Position,
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

    # SL replacement gating — stop loss is "emergency only", we only
    # touch the on-exchange order when it materially changes, and even
    # then no more often than the cooldown.
    STOP_LOSS_REPLACE_MIN_MOVE_RATIO = 0.0015  # 0.15% of price
    STOP_LOSS_REPLACE_MIN_TICKS = 2
    STOP_LOSS_REPLACE_COOLDOWN_MS = 30_000

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[BotTable] | Type[PaperTradingTable] = BotTable,
        base_streaming: BaseStreaming | None = None,
    ) -> None:
        super().__init__()
        self.base_streaming = base_streaming or BaseStreaming()
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
        self.kucoin_futures_api.DEFAULT_LEVERAGE = self.symbol_info.futures_leverage
        self.kucoin_symbol = convert_to_kucoin_symbol(bot)
        self.kucoin_symbol_data = self.kucoin_futures_api.get_symbol_info(
            self.kucoin_symbol
        )
        self.price_precision = self.symbol_info.price_precision

    def _direction_multiplier(self) -> int:
        return -1 if self.active_bot.position == Position.short else 1

    def create_controller(self) -> PaperTradingTableCrud | BotTableCrud:
        """
        Separate sessions to avoid locking database
        when continuously saving (self.controller.save)
        """
        if isinstance(self.controller, PaperTradingTableCrud):
            return PaperTradingTableCrud()
        else:
            return BotTableCrud()

    def calculate_contracts(self, balance: float, price: float) -> int:
        """
        Size futures positions from initial margin (margin-spend interpretation).

        ``fiat_order_size`` is the initial margin the bot commits, not the
        risk-at-stop. ``notional = balance * symbol_info.futures_leverage`` and
        ``contracts = notional / (price * multiplier)``. Per-symbol leverage is
        sourced from the symbol table, capped at ``le=3``.
        """
        if balance <= 0 or price <= 0:
            return 0

        symbol_data = getattr(self, "kucoin_symbol_data", None)
        multiplier = float(
            getattr(symbol_data, "multiplier", 0)
            or getattr(self.kucoin_futures_api, "DEFAULT_MULTIPLIER", 1)
            or 1
        )

        contracts = balance * self.symbol_info.futures_leverage / (price * multiplier)
        return int(round_numbers(contracts, self.symbol_info.qty_precision))

    def _is_reversal_possible(
        self, mark_price: float, current_contracts: float
    ) -> float:
        reversal_buffer = 1.40
        min_contract_step = float(self.kucoin_symbol_data.lot_size or 1)
        available_balance = float(self.compute_available_balance())
        min_step_margin = self.required_margin_for_contracts(
            min_contract_step, mark_price
        )
        estimated_available_buffer = available_balance - reversal_buffer

        if estimated_available_buffer <= 0 or min_step_margin <= 0:
            return float(current_contracts)

        minimum_flip_contracts = round_numbers(
            float(current_contracts) + min_contract_step,
            self.symbol_info.qty_precision,
        )

        if estimated_available_buffer < min_step_margin:
            return float(current_contracts)

        return float(minimum_flip_contracts)

    def estimate_reversal_possible_for_new_bot(self) -> bool:
        """
        Estimate whether a newly activated futures bot is likely to support a
        same-size one-order reversal later.

        This is weaker than the live reversal pre-check because there is no
        current exchange position yet; it estimates contracts from the current
        market and then reuses the internal affordability logic.
        """
        if not self.active_bot.margin_short_reversal or self.active_bot.stop_loss <= 0:
            return True

        side = (
            AddOrderReq.SideEnum.SELL
            if self.active_bot.position == Position.short
            else AddOrderReq.SideEnum.BUY
        )
        estimated_price = self.kucoin_futures_api.matching_engine(
            symbol=self.kucoin_symbol,
            side=side,
            size=1,
        )
        estimated_contracts = self.calculate_contracts(
            self.active_bot.fiat_order_size, estimated_price
        )

        if estimated_contracts <= 0:
            return False

        available_contracts = self._is_reversal_possible(
            estimated_price, estimated_contracts
        )
        return available_contracts > estimated_contracts

    def contracts_to_fiat_order_size(self, contracts: float, price: float) -> float:
        """
        Invert calculate_contracts() so fiat_order_size reflects the initial
        margin actually committed by an open futures position.
        """
        if contracts <= 0 or price <= 0:
            return 0.0

        symbol_data = getattr(self, "kucoin_symbol_data", None)
        multiplier = float(
            getattr(symbol_data, "multiplier", 0)
            or getattr(self.kucoin_futures_api, "DEFAULT_MULTIPLIER", 1)
        )

        return round_numbers(
            contracts * price * multiplier / self.symbol_info.futures_leverage,
            8,
        )

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

    def notional_for_contracts(self, contracts: float, price: float) -> float:
        multiplier = (
            self.kucoin_symbol_data.multiplier
            or self.kucoin_futures_api.DEFAULT_MULTIPLIER
        )
        return contracts * price * multiplier

    def required_margin_for_contracts(self, contracts: float, price: float) -> float:
        """
        Estimate the margin needed for a futures order before submitting it.

        Under margin-spend sizing the required margin for a freshly calculated
        position should equal ``fiat_order_size`` (modulo rounding from
        integer contracts), but we recompute it from the contracts actually
        placed so the affordability check uses the exchange-truth notional.
        """
        if contracts <= 0 or price <= 0:
            return 0.0

        notional = self.notional_for_contracts(contracts, price)
        initial_margin = notional / self.symbol_info.futures_leverage
        fees = 2 * notional * (self.kucoin_symbol_data.taker_fee_rate or 0)
        return round_numbers(initial_margin + fees, 8)

    def max_contracts_for_margin(self, available_balance: float, price: float) -> int:
        if available_balance <= 0 or price <= 0:
            return 0

        min_contract_step = self.kucoin_symbol_data.lot_size or 1
        per_contract_margin = self.required_margin_for_contracts(
            min_contract_step, price
        )
        if per_contract_margin <= 0:
            return 0

        contracts = round_numbers(
            (available_balance / per_contract_margin) * min_contract_step,
            self.symbol_info.qty_precision,
        )

        while (
            contracts > 0
            and self.required_margin_for_contracts(contracts, price) > available_balance
        ):
            contracts = round_numbers(
                contracts - min_contract_step,
                self.symbol_info.qty_precision,
            )

        return int(contracts)

    def backfill_position_from_fills(self) -> BotModel:
        self.active_bot.add_log(
            "Position not found in exchange, cannot update size. ADL might have happened, or position might have been closed without bot's knowledge."
        )
        side = (
            GetTradeHistoryReq.SideEnum.BUY
            if self.active_bot.position == Position.short
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
            if self.active_bot.position == Position.short:
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
            if order.deal_type == DealType.trailing_profit
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
                order.deal_type == DealType.trailing_profit
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
            self.active_bot.orders = [
                o for o in self.active_bot.orders if o.order_id not in stop_order_ids
            ]
        else:
            self.remove_stale_orders()

    def _bot_known_stop_loss(self) -> tuple[float | None, int | None]:
        """
        Source of truth from the bot's local order list:
        return (price, timestamp_ms) of the most recent open SL order, or
        (None, None) if there is no open SL recorded.
        """
        for order in reversed(self.active_bot.orders):
            if order.deal_type != DealType.stop_loss:
                continue
            if order.status in {
                OrderStatus.FILLED,
                OrderStatus.CANCELED,
                OrderStatus.EXPIRED,
                OrderStatus.REJECTED,
            }:
                continue
            order_price = float(order.price or 0)
            ts = int(order.timestamp or 0)
            if order_price > 0:
                return order_price, ts
            sl_price = float(self.active_bot.deal.stop_loss_price or 0)
            if sl_price > 0:
                return sl_price, ts
        return None, None

    def _exchange_stop_loss_price(self) -> tuple[bool, float | None]:
        """
        Source of truth from the exchange.

        Returns ``(ok, price)``:
          - ``ok=True, price=float``  → exchange has an SL at this price
          - ``ok=True, price=None``   → exchange confirmed no SL exists
          - ``ok=False, price=None``  → query failed; caller must NOT treat
            this as "no SL", or it will cancel/replace a still-valid one.
        """
        try:
            stop_orders = self.kucoin_futures_api.get_all_stop_loss_orders(
                self.kucoin_symbol
            )
        except Exception as exc:
            self.active_bot.add_log(f"Could not query exchange stop orders: {exc}")
            return False, None

        if not stop_orders:
            return True, None

        for order in stop_orders:
            stop_price = float(getattr(order, "stop_price", 0) or 0)
            if stop_price > 0:
                return True, stop_price
        return True, None

    def should_replace_stop_loss_order(
        self,
        current_stop_price: float | None,
        new_stop_price: float,
        last_replace_ts_ms: int | None = None,
    ) -> bool:
        """
        Decide whether the on-exchange SL needs replacing.

        Replace only when:
          - we have a meaningful new price, and
          - either there's no current SL, or the new one is *better* by more
            than the min-move threshold, and
          - the cooldown since the last replace has elapsed.
        """
        if new_stop_price <= 0:
            return False

        if current_stop_price is None or current_stop_price <= 0:
            return True

        direction = self._direction_multiplier()
        improvement = (new_stop_price - current_stop_price) * direction
        if improvement <= 0:
            return False

        tick_size = 10 ** (-self.price_precision)
        min_replace_move = max(
            abs(current_stop_price) * self.STOP_LOSS_REPLACE_MIN_MOVE_RATIO,
            tick_size * self.STOP_LOSS_REPLACE_MIN_TICKS,
        )
        if improvement < min_replace_move:
            return False

        if last_replace_ts_ms and last_replace_ts_ms > 0:
            now_ms = int(time() * 1000)
            if now_ms - last_replace_ts_ms < self.STOP_LOSS_REPLACE_COOLDOWN_MS:
                return False

        return True

    def reconcile_exchange_sl(self) -> None:
        """
        Reconcile the on-exchange emergency stop loss with what the bot
        thinks should be there.

        Cases handled:
          1. Bot expects SL but exchange has none — re-place (it was cancelled
             externally, expired, or never made it through).
          2. Exchange has an SL at a price that disagrees with the bot's
             local record — adopt the exchange price as truth (someone moved
             it manually) and only replace if it's now unsafe.
          3. Bot wants to ratchet SL closer to entry — only replace if the
             move is material and the cooldown has elapsed.

        Skipped when:
          - margin_short_reversal is active (handled elsewhere)
          - trailing has armed (trailing_stop_loss_price != 0); in that
            mode the exit is bot-side, the emergency SL is left alone.
        """
        if self.active_bot.stop_loss <= 0:
            return
        if self.active_bot.margin_short_reversal:
            return
        if self.active_bot.deal.trailing_stop_loss_price != 0:
            trailing_reconciler = getattr(self, "reconcile_trailing_stop_loss", None)
            if callable(trailing_reconciler):
                trailing_reconciler()
            return

        # Intended price
        if self.active_bot.deal.stop_loss_price <= 0:
            return

        exchange_ok, exchange_price = self._exchange_stop_loss_price()
        if not exchange_ok:
            # API blip — we don't know what's on the exchange. Bail out and
            # try again next tick rather than risk cancelling/duplicating
            # a still-valid emergency SL.
            return

        bot_known_price, last_replace_ts_ms = self._bot_known_stop_loss()

        # Case 1: exchange confirmed no SL exists — re-place.
        if exchange_price is None:
            if bot_known_price is not None:
                self.active_bot.add_log(
                    "Exchange SL missing — re-placing emergency stop."
                )
            self.cancel_current_sl()  # cleans local stale records, no-op on empty
            self.place_stop_loss()
            return

        # Case 2: exchange disagrees with our local record. The exchange
        # is authoritative — adopt it. Only replace if it's now unsafe vs.
        # the bot's intended (ratcheted) price.
        if bot_known_price is not None and abs(exchange_price - bot_known_price) > (
            10**-self.price_precision
        ):
            self.active_bot.add_log(
                f"Exchange SL drift detected: bot={bot_known_price} exchange={exchange_price}; trusting exchange."
            )
            self.active_bot.deal.stop_loss_price = round_numbers(
                exchange_price, self.price_precision
            )

        # Case 3: ratchet — replace only if materially better and not on cooldown.
        if self.should_replace_stop_loss_order(
            current_stop_price=exchange_price,
            new_stop_price=self.active_bot.deal.stop_loss_price,
            last_replace_ts_ms=last_replace_ts_ms,
        ):
            self.cancel_current_sl()
            self.place_stop_loss()

    def base_order(self) -> BotModel:
        """
        Futures have positions intrinsically built, the base order can be either LONG or SHORT, we don't need to deal with loans, we simply set the position as an order
        """
        if self.active_bot.fiat_order_size <= 0:
            raise BinbotErrors("Fiat order size must be set.")

        available_balance = self.compute_available_balance()
        price = self.kucoin_futures_api.matching_engine(
            symbol=self.kucoin_symbol,
            side=AddOrderReq.SideEnum.BUY,
            size=available_balance,
        )

        margin_sized_contracts = self.calculate_contracts(
            self.active_bot.fiat_order_size, price
        )

        if margin_sized_contracts <= 0:
            raise BinbotErrors(
                "Calculated contracts is 0. Check if the order size, stop loss, and risk settings are correct."
            )

        affordable_contracts = self.max_contracts_for_margin(available_balance, price)
        contracts = min(margin_sized_contracts, affordable_contracts)

        if contracts <= 0:
            min_contract_margin = self.required_margin_for_contracts(
                self.kucoin_symbol_data.lot_size or 1, price
            )
            raise BinbotErrors(
                f"Required futures margin {min_contract_margin} {self.fiat} for the minimum contract size "
                f"exceeds available balance {available_balance} {self.fiat}."
            )

        required_margin = self.required_margin_for_contracts(contracts, price)
        if required_margin > available_balance:
            raise BinbotErrors(
                f"Required futures margin {required_margin} {self.fiat} for {contracts} contracts "
                f"exceeds available balance {available_balance} {self.fiat}."
            )

        actual_margin = self.contracts_to_fiat_order_size(contracts, price)
        notional = round_numbers(self.notional_for_contracts(contracts, price), 8)

        if contracts < margin_sized_contracts:
            self.active_bot.add_log(
                f"Futures order downsized from {margin_sized_contracts} to {contracts} contracts "
                f"because required margin exceeded available balance."
            )

        self.active_bot.add_log(
            f"Futures activation sizing: contracts={contracts}, notional={notional} {self.fiat}, "
            f"leverage={self.symbol_info.futures_leverage}x, required_margin={required_margin} {self.fiat}, "
            f"available_balance={available_balance} {self.fiat}, planned_margin={self.active_bot.fiat_order_size} {self.fiat}, "
            f"actual_margin={actual_margin} {self.fiat}."
        )

        if self.active_bot.position == Position.short:
            order: OrderBase = self.kucoin_futures_api.sell(
                symbol=self.kucoin_symbol,
                qty=contracts,
                leverage=self.symbol_info.futures_leverage,
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

        position_label = getattr(
            self.active_bot.position,
            "name",
            self.active_bot.position,
        )
        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Futures {position_label} opened @ {position.mark_price} with {order.qty} contracts",
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

        if self.active_bot.position == Position.short:
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
            leverage=self.symbol_info.futures_leverage,
        )

        if order_response.price and order_response.qty:
            self.active_bot.add_log(
                f"Stop loss placed @ {order_response.price} for {order_response.qty} contracts."
            )
            self.remove_stale_orders()

        order_response.deal_type = DealType.stop_loss
        order_model = OrderModel(**order_response.model_dump())
        self.active_bot.orders.append(order_model)
        self.active_bot.deal.stop_loss_price = stop_price

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Stop loss set @ {stop_price}",
        )

    def recompute_derived_prices(self) -> BotModel:
        """
        Pure in-memory recomputation of derived deal prices from the bot's
        percent parameters and opening price. Safe to call every tick — does
        no exchange I/O, places no orders.
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

        if (
            self.active_bot.trailing
            and self.active_bot.trailing_deviation > 0
            and self.active_bot.trailing_profit > 0
        ):
            entry_price = float(self.active_bot.deal.opening_price)
            trailing_profit_price = entry_price * (
                1 + direction * (float(self.active_bot.trailing_profit) / 100)
            )
            self.active_bot.deal.trailing_profit_price = round_numbers(
                trailing_profit_price, self.price_precision
            )
            # NOTE: trailing_stop_loss_price is intentionally preserved here.
            # Resetting an armed trail every tick would (a) defeat dynamic
            # trailing and (b) bypass the trailing-armed guard in
            # reconcile_exchange_sl(). The "Update Deal" flow that needs to
            # disarm the trail does so explicitly in open_deal().

        return self.active_bot

    def update_parameters(self) -> BotModel:
        """
        Update derived prices in-memory and reconcile the on-exchange
        emergency SL with what the bot now expects. The two halves are
        deliberately separated:

          - recompute_derived_prices() is pure and tick-safe.
          - reconcile_exchange_sl() touches the exchange and is gated by
            drift detection + min-move + cooldown to avoid order churn.
        """
        self.recompute_derived_prices()
        self.reconcile_exchange_sl()
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

        if self.active_bot.trailing:
            trailing_profit = float(self.active_bot.deal.opening_price) * (
                1 + direction * (float(self.active_bot.trailing_profit) / 100)
            )
            self.active_bot.deal.trailing_profit_price = trailing_profit
            self.active_bot.deal.trailing_stop_loss_price = 0
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

    def close_all(self, algorithmic_close: bool = False) -> BotModel:
        """
        Closes all open positions and cancels all orders.
        To be used also for panic selling from terminal.
        """
        deal_type = (
            DealType.algorithmic_close if algorithmic_close else DealType.panic_close
        )
        position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)

        if position and float(position.current_qty) != 0:
            if self.active_bot.position == Position.short:
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
                    leverage=self.symbol_info.futures_leverage,
                )

            order_model = OrderModel(**order_response.model_dump())
            order_model.deal_type = deal_type
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
            # Update bot, no activation required. This path is the user-driven
            # "Update Deal" flow — disarm any active trail since the parameters
            # it was computed against may have just changed.
            self.active_bot.deal.trailing_stop_loss_price = 0
            self.active_bot = self.update_parameters()
        else:
            # Activation required
            self.active_bot = self.update_parameters_with_activation()

        self.controller.save(self.active_bot)
        return self.active_bot
