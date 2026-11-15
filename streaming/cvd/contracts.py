"""Discover the active registered linear USDT contract universe."""

import math

from pybinbot import ExchangeId
from sqlalchemy import select
from sqlmodel import col

from api.databases.tables.symbol_exchange_table import SymbolExchangeTable
from api.databases.tables.symbol_table import SymbolTable
from api.databases.utils import engine
from streaming.shared.kucoin_futures import public_request


def discover_contracts(contracts: list[dict], registered: set[str]) -> dict[str, float]:
    result = {}
    for contract in contracts:
        if (
            contract.get("symbol") not in registered
            or contract.get("status") != "Open"
            or contract.get("settleCurrency") != "USDT"
            or contract.get("isInverse") is not False
        ):
            continue
        multiplier = float(contract["multiplier"])
        if not math.isfinite(multiplier) or multiplier <= 0:
            raise ValueError("Invalid contract multiplier")
        result[contract["symbol"]] = multiplier
    return result


def load_contracts() -> dict[str, float]:
    with engine.connect() as connection:
        registered = set(
            connection.execute(
                select(col(SymbolExchangeTable.symbol_id))
                .join(
                    SymbolTable,
                    col(SymbolTable.id) == col(SymbolExchangeTable.symbol_id),
                )
                .where(
                    col(SymbolExchangeTable.exchange_id) == ExchangeId.KUCOIN,
                    col(SymbolTable.active).is_(True),
                )
            ).scalars()
        )
    return discover_contracts(public_request("/api/v1/contracts/active"), registered)
