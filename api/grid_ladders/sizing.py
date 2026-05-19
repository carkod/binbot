from dataclasses import dataclass
from typing import Protocol

from pybinbot import round_numbers


class GridMarginSizer(Protocol):
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

        min_contract_step = self.lot_size or 1
        per_contract_margin = self.required_margin_for_contracts(
            min_contract_step, price
        )
        if per_contract_margin <= 0:
            return 0

        contracts = round_numbers(
            (available_balance / per_contract_margin) * min_contract_step,
            self.qty_precision,
        )

        while (
            contracts > 0
            and self.required_margin_for_contracts(contracts, price) > available_balance
        ):
            contracts = round_numbers(contracts - min_contract_step, self.qty_precision)

        return int(contracts)
