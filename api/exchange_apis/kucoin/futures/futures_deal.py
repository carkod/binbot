from uuid import uuid4

from typing import Callable

from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from kucoin_universal_sdk.model.common import RestError
from pybinbot import (
    BinbotErrors,
    BotModel,
    DealType,
    EntryMode,
    OrderBase,
    OrderModel,
    OrderStatus,
    OrderType,
    Position,
    Status,
    round_numbers,
)

from api.deals.conditional_entry import ConditionalEntry
from api.tools.utils import submission_guard
from api.exchange_apis.kucoin.futures.balance import KucoinFuturesBalance
from api.exchange_apis.kucoin.futures.entry_pricing import EntryPricing
from api.tools.constants import (
    TOP_GAINER_EARLY_MOMENTUM_ALGO,
    TOP_GAINER_EARLY_MOMENTUM_PENDING_ENTRY_CANDLES,
    TOP_GAINER_FAILURE_REVERSAL_ALGO,
    TOP_GAINER_FAILURE_REVERSAL_PENDING_ENTRY_TTL_MS,
)


class KucoinPositionDeal(EntryPricing):
    """
    Futures-only deal entry implementation (USDT-M).

    - Position-based (not balance-based)
    - Uses contracts, not qty
    - Orders create / modify positions
    - SL / TP are reduce-only orders
    """

    def _is_recovery_bot(self) -> bool:
        recovery_params = self.active_bot.recovery_params
        return (
            recovery_params is not None and recovery_params.reversal_path == "recovery"
        )

    def calculate_contracts(self, balance: float, price: float) -> int:
        """
        Size futures positions from initial margin (margin-spend interpretation).

        ``fiat_order_size`` is the initial margin the bot commits, not the
        risk-at-stop. ``notional = balance * active_bot.futures_leverage`` and
        ``contracts = notional / (price * multiplier)``. Leverage is saved on
        each bot and bounded to 1x–5x.
        """
        if balance <= 0 or price <= 0:
            return 0

        symbol_data = self.kucoin_symbol_data
        multiplier = (
            symbol_data.multiplier or self.kucoin_futures_api.DEFAULT_MULTIPLIER or 1
        )

        contracts = balance * self.active_bot.futures_leverage / (price * multiplier)
        return int(round_numbers(contracts, self.symbol_info.qty_precision))

    def contracts_to_fiat_order_size(self, contracts: float, price: float) -> float:
        """Convert contracts back to their initial-margin equivalent."""
        if contracts <= 0 or price <= 0:
            return 0.0

        multiplier = float(
            self.kucoin_symbol_data.multiplier
            or self.kucoin_futures_api.DEFAULT_MULTIPLIER
        )

        return round_numbers(
            contracts * price * multiplier / self.active_bot.futures_leverage,
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
        initial_margin = notional / self.active_bot.futures_leverage
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

    def base_order(self) -> BotModel:
        """
        Executes entry order for bot which:
        - fills out the deal
        - sets out logic for conditional limit
        - handles immediate entry orders
        - validates margin requirements for the entry order
        - submits the entry order to the exchange
        - returns the bot model after submission
        """
        if self.active_bot.entry_mode == EntryMode.conditional_limit:
            # Handle conditional limit entry separately
            return ConditionalEntry(self).submit()

        with submission_guard(self.active_bot.id) as (bot, _):
            self.active_bot = bot
            if (
                bot.entry_mode != EntryMode.immediate
                or bot.status in {Status.completed, Status.error}
                or any(order.deal_type == DealType.base_order for order in bot.orders)
            ):
                return bot
            if bot.deal.entry_client_oid is not None:
                restored = self.restore_entry_order(bot.deal.entry_client_oid)
                if restored is None:
                    return bot
                order, contracts, entry_limit_price = restored
            else:
                if bot.fiat_order_size <= 0:
                    raise BinbotErrors("Fiat order size must be set.")
                available_balance = self.compute_available_balance()
                candidate_limit_price = self.body_capped_entry_limit_price()
                sized_contracts = self.size_entry_contracts(
                    available_balance, candidate_limit_price
                )
                if sized_contracts <= 0:
                    min_contract_margin = self.required_margin_for_contracts(
                        self.kucoin_symbol_data.lot_size or 1, candidate_limit_price
                    )
                    raise BinbotErrors(
                        f"Required futures margin {min_contract_margin} {self.fiat} for the minimum contract size "
                        f"exceeds available balance {available_balance} {self.fiat}."
                    )
                entry_limit_price = self.prepare_entry_limit_price(
                    candidate_limit_price
                )
                self.validate_entry_margin(
                    sized_contracts, entry_limit_price, available_balance
                )
                contracts = sized_contracts
                order = self.submit_entry_order(
                    sized_contracts,
                    entry_limit_price,
                    post_only=self._entry_post_only
                    if bot.position == Position.long
                    else False,
                )

            pending_entry_minutes = 5
            if bot.name == TOP_GAINER_EARLY_MOMENTUM_ALGO:
                pending_entry_minutes = (
                    self.interval_ms
                    * TOP_GAINER_EARLY_MOMENTUM_PENDING_ENTRY_CANDLES
                    // 60_000
                )
            elif bot.name == TOP_GAINER_FAILURE_REVERSAL_ALGO:
                pending_entry_minutes = (
                    TOP_GAINER_FAILURE_REVERSAL_PENDING_ENTRY_TTL_MS // 60_000
                )
            return self.record_entry_order(
                order,
                contracts,
                entry_limit_price,
                pending_entry_minutes=pending_entry_minutes,
            )

    def restore_entry_order(
        self, client_oid: str
    ) -> tuple[OrderBase, float, float] | None:
        """Adopt the original exchange identity after an ambiguous acknowledgement."""
        try:
            details = self.kucoin_futures_api.retrieve_order_by_client_oid(client_oid)
        except RestError as exc:
            if str(exc.response.code) == "100001" or "getOrder.orderNotExist" in str(
                exc.response.message
            ):
                self.active_bot.add_log(
                    "Entry acknowledgement unresolved; retaining clientOid without resubmitting."
                )
                self.active_bot.status = Status.pending
                self.controller.save(self.active_bot)
                return None
            raise
        contracts = float(details.size or 0)
        entry_limit_price = float(details.price or 0)
        order = OrderBase(
            order_id=str(details.id),
            client_oid=client_oid,
            requested_qty=contracts,
            pair=self.kucoin_symbol,
            order_type="limit",
            time_in_force="GTC",
            order_side="sell" if self.active_bot.position == Position.short else "buy",
            price=float(details.avg_deal_price or 0),
            qty=float(details.filled_size or 0),
            timestamp=int(details.created_at or 0),
            status=OrderStatus.map_from_kucoin_status(details.status.value),
            deal_type=DealType.base_order,
        )
        return order, contracts, entry_limit_price

    def size_entry_contracts(self, available_balance: float, price: float) -> int:
        """Clamp initial-margin sizing to contracts the account can afford."""
        margin_sized_contracts = self.calculate_contracts(
            self.active_bot.fiat_order_size, price
        )
        if margin_sized_contracts <= 0:
            raise BinbotErrors(
                "Calculated contracts is 0. Check if the order size, stop loss, and risk settings are correct."
            )
        contracts = min(
            margin_sized_contracts,
            self.max_contracts_for_margin(available_balance, price),
        )
        if 0 < contracts < margin_sized_contracts:
            self.active_bot.add_log(
                f"Futures order downsized from {margin_sized_contracts} to "
                f"{contracts} contracts because required margin exceeded available balance."
            )
        return contracts

    def validate_entry_margin(
        self, contracts: int, price: float, available_balance: float
    ) -> None:
        """Recheck the final exchange price and record the margin committed."""
        required_margin = self.required_margin_for_contracts(contracts, price)
        if required_margin > available_balance:
            raise BinbotErrors(
                f"Required futures margin {required_margin} {self.fiat} for {contracts} contracts "
                f"exceeds available balance {available_balance} {self.fiat}."
            )
        notional = round_numbers(self.notional_for_contracts(contracts, price), 8)
        recovery_params = self.active_bot.recovery_params
        if (
            self._is_recovery_bot()
            and recovery_params is not None
            and recovery_params.source_contracts > 0
            and contracts < recovery_params.source_contracts * 0.60
        ):
            self.active_bot.add_log(
                "underpowered_recovery: "
                f"opening {contracts} contracts, below 60% of source "
                f"{recovery_params.source_contracts} contracts."
            )
        self.active_bot.add_log(
            f"Futures activation sizing: contracts={contracts}, notional={notional} {self.fiat}, "
            f"leverage={self.active_bot.futures_leverage}x, required_margin={required_margin} {self.fiat}, "
            f"available_balance={available_balance} {self.fiat}, planned_margin={self.active_bot.fiat_order_size} {self.fiat}."
        )

    def submit_entry_order(
        self, contracts: int, price: float, *, post_only: bool
    ) -> OrderBase:
        """Persist a client identity before sending any order to the exchange."""
        client_oid = str(uuid4())
        self.active_bot.status = Status.pending
        self.active_bot.deal.entry_client_oid = client_oid
        self.controller.save(self.active_bot)
        return self.kucoin_futures_api.place_futures_order(
            symbol=self.kucoin_symbol,
            side=AddOrderReq.SideEnum.SELL
            if self.active_bot.position == Position.short
            else AddOrderReq.SideEnum.BUY,
            size=contracts,
            leverage=self.active_bot.futures_leverage,
            order_type=OrderType.limit,
            price=price,
            time_in_force=AddOrderReq.TimeInForceEnum.GOOD_TILL_CANCELED,
            post_only=post_only,
            reduce_only=False,
            client_oid=client_oid,
        )

    def record_entry_order(
        self,
        order: OrderBase,
        contracts: float,
        entry_limit_price: float,
        *,
        pending_entry_minutes: float,
    ) -> BotModel:
        """Keep acknowledgements pending until streaming verifies actual fills."""
        order.deal_type = DealType.base_order
        stored_order = OrderModel(**order.model_dump())
        self.active_bot.orders.append(stored_order)
        stored_order.status = OrderStatus.NEW
        stored_order.qty = contracts
        self.active_bot.deal.base_order_size = contracts
        self.active_bot.deal.opening_timestamp = stored_order.timestamp
        self.active_bot.status = Status.pending
        self.controller.update_logs(
            bot=self.active_bot,
            log_message=(
                f"Futures entry limit order {stored_order.order_id} submitted at {entry_limit_price} "
                f"with {contracts} contracts. Bot is pending for up to "
                f"{pending_entry_minutes} minutes awaiting fill confirmation by lifecycle order updates."
            ),
        )
        self.controller.save(self.active_bot)
        return self.active_bot

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
                    if self.active_bot.deal.current_position_qty == 0:
                        self.active_bot.deal.current_position_qty = order.qty
                    self.active_bot.deal.opening_timestamp = order.timestamp
                    break

        if self.active_bot.stop_loss > 0:
            entry_price = self.active_bot.deal.opening_price
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
            entry_price = self.active_bot.deal.opening_price
            trailing_profit_price = entry_price * (
                1 + direction * (self.active_bot.trailing_profit / 100)
            )
            if (
                not self.active_bot.dynamic_position_sizing
                or self.active_bot.deal.trailing_profit_price == 0
            ):
                self.active_bot.deal.trailing_profit_price = round_numbers(
                    trailing_profit_price, self.price_precision
                )
            # NOTE: trailing_stop_loss_price is intentionally preserved here.
            # Resetting an armed trail every tick would (a) defeat dynamic
            # trailing and (b) bypass the trailing-armed guard in
            # reconcile_exchange_sl(). The "Update Deal" flow that needs to
            # disarm the trail does so explicitly in open_deal().

        return self.active_bot

    def update_parameters(self, *, allow_stop_loss_widening: bool = False) -> BotModel:
        """
        Update derived prices in-memory and reconcile the on-exchange
        emergency SL with what the bot now expects. The two halves are
        deliberately separated:

          - recompute_derived_prices() is pure and tick-safe.
          - reconcile_exchange_sl() touches the exchange and is gated by
            drift detection + min-move + cooldown to avoid order churn.
        """
        self.recompute_derived_prices()
        self.reconcile_exchange_sl(allow_widening=allow_stop_loss_widening)
        return self.active_bot

    def update_parameters_with_activation(self) -> BotModel:
        """
        update_parameters with some additional logic for activation:
        - If the bot is already active, it means we are updating parameters without changing the position, so we just call update_parameters.
        - If the bot is not active, it means we are activating the bot, so we need to set the parameters and then activate it. This is used for example when we open a new deal and we want to set the SL and TP at the same time, so we update parameters with activation right after opening the deal.
        """
        direction = self._direction_multiplier()

        if self.active_bot.stop_loss > 0:
            price = self.active_bot.deal.opening_price
            delta = price * (self.active_bot.stop_loss / 100)
            self.active_bot.deal.stop_loss_price = price - (delta * direction)

        if self.active_bot.trailing:
            trailing_profit = self.active_bot.deal.opening_price * (
                1 + direction * (self.active_bot.trailing_profit / 100)
            )
            self.active_bot.deal.trailing_profit_price = trailing_profit
            self.active_bot.deal.trailing_stop_loss_price = 0
            self.active_bot.deal.take_profit_price = 0
        else:
            take_profit_price = self.active_bot.deal.opening_price * (
                1 + direction * (self.active_bot.take_profit / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price

        self.active_bot.status = Status.active
        if direction == -1:
            self.active_bot.add_log("Bot re-activated (short)")
        else:
            self.active_bot.add_log("Bot re-activated")
        self.controller.save(self.active_bot)
        return self.active_bot

    def open_deal(
        self,
        progress: Callable[[int, str], None] | None = None,
        *,
        trigger_entry: bool = False,
    ) -> BotModel:
        if self.active_bot.status == Status.closed:
            return self.active_bot
        if progress:
            progress(35, "Preparing the futures entry")
        if (
            self.active_bot.dynamic_position_sizing
            and self.active_bot.recovery_params is not None
        ):
            raise BinbotErrors(
                "Dynamic position sizing and recovery are mutually exclusive"
            )
        base_order = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == DealType.base_order
            ),
            None,
        )

        if not base_order:
            if (
                self.active_bot.entry_mode == EntryMode.conditional_limit
                and self.active_bot.deal.entry_client_oid is None
                and not trigger_entry
            ):
                return ConditionalEntry(self).arm()
            if progress:
                progress(45, "Submitting the entry order")
            self.active_bot.add_log(
                f"Opening new future deal for {self.kucoin_symbol}..."
            )
            self.base_order()
            if self.active_bot.status in {Status.error, Status.completed} or (
                not self.active_bot.orders
                and self.active_bot.deal.entry_client_oid is None
            ):
                return self.active_bot
            if progress:
                progress(75, "Entry order submitted")

        # Entry not filled yet (opening_price == 0): leave the bot pending and
        # return. order_updates() will promote it to active once KuCoin confirms
        # the fill by calling open_deal() again, which will reach the branch below.
        if self.active_bot.deal.opening_price == 0:
            self.active_bot.status = Status.pending
            self.active_bot.add_log(
                "Entry order is live but not yet filled; bot set to pending."
            )
            self.controller.save(self.active_bot)
            if progress:
                progress(95, "Waiting for the exchange fill")
            return self.active_bot

        # Entry is filled (opening_price > 0): activate / reactivate.
        # Disarm any stale trail — parameters may have changed (e.g. Update Deal).
        self.active_bot.deal.trailing_stop_loss_price = 0
        self.active_bot = self.update_parameters()
        if self.active_bot.status != Status.completed:
            self.active_bot.status = Status.active
        self.controller.save(self.active_bot)
        if progress:
            progress(95, "Bot state saved")
        return self.active_bot
