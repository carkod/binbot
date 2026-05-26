import math
from dataclasses import dataclass
from typing import Protocol

from pybinbot import round_numbers


def round_price_to_precision(price: float, price_precision: int | None) -> float:
    if price <= 0 or price_precision is None:
        return price

    return float(round_numbers(price, price_precision))


class GridMarginSizer(Protocol):
    price_precision: int | None

    def required_margin_for_contracts(
        self, contracts: float, price: float
    ) -> float: ...

    def max_contracts_for_margin(
        self, available_balance: float, price: float
    ) -> int: ...


@dataclass
class KucoinGridMarginRules:
    futures_leverage: int
    qty_precision: int = 0
    multiplier: float = 1.0
    lot_size: float = 1.0
    taker_fee_rate: float = 0.0
    min_notional: float = 0.0
    price_precision: int | None = None

    def notional_for_contracts(self, contracts: float, price: float) -> float:
        return contracts * price * self.multiplier

    def required_margin_for_contracts(self, contracts: float, price: float) -> float:
        if contracts <= 0 or price <= 0:
            return 0.0

        notional = self.notional_for_contracts(contracts, price)
        initial_margin = notional / self.futures_leverage
        fees = 2 * notional * self.taker_fee_rate
        return round_numbers(initial_margin + fees, 8)

    def max_contracts_for_margin(self, available_balance: float, price: float) -> int:
        if available_balance <= 0 or price <= 0:
            return 0

        lot = self.lot_size or 1
        per_lot_margin = self.required_margin_for_contracts(lot, price)
        if per_lot_margin <= 0:
            return 0

        # Snap to a whole number of lots — KuCoin futures rejects partial lots.
        lots = math.floor(available_balance / per_lot_margin)
        contracts = lots * lot
        if contracts == 0:
            return 0

        # Reject below the exchange minimum notional.
        if self.min_notional > 0:
            notional = self.notional_for_contracts(contracts, price)
            if notional < self.min_notional:
                return 0

        return int(contracts)
