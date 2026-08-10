import pytest
from pybinbot import ExchangeId

from api.databases.crud.symbols_crud import SymbolsCrud
from api.databases.tables.symbol_exchange_table import SymbolExchangeTable
from api.databases.tables.symbol_table import SymbolTable
from api.grid_ladders.base_lifecycle import BaseLifecycle
from api.grid_ladders.lifecycle import GridLadderLifecycle
from api.tools.utils import coerce_millisecond_timestamp


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (123, 123),
        (123.9, 123),
        ("123", 123),
        ("invalid", None),
        (None, None),
    ],
)
def test_coerce_millisecond_timestamp(value: object, expected: int | None) -> None:
    assert coerce_millisecond_timestamp(value) == expected


def test_symbol_price_precision_prefers_requested_exchange() -> None:
    symbol = SymbolTable(
        id="ADAUSDTM",
        exchange_values=[
            SymbolExchangeTable(
                exchange_id=ExchangeId.BINANCE,
                symbol_id="ADAUSDTM",
                price_precision=3,
            ),
            SymbolExchangeTable(
                exchange_id=ExchangeId.KUCOIN,
                symbol_id="ADAUSDTM",
                price_precision=5,
            ),
        ],
    )

    assert SymbolsCrud.get_price_precision(symbol, ExchangeId.KUCOIN) == 5


def test_symbol_price_precision_falls_back_to_first_exchange() -> None:
    symbol = SymbolTable(
        id="ADAUSDTM",
        exchange_values=[
            SymbolExchangeTable(
                exchange_id=ExchangeId.BINANCE,
                symbol_id="ADAUSDTM",
                price_precision=3,
            )
        ],
    )

    assert SymbolsCrud.get_price_precision(symbol, ExchangeId.KUCOIN) == 3
    assert (
        SymbolsCrud.get_price_precision(SymbolTable(id="EMPTY"), ExchangeId.KUCOIN)
        is None
    )


def test_grid_ladder_lifecycle_inherits_low_level_mechanics() -> None:
    assert issubclass(GridLadderLifecycle, BaseLifecycle)
    assert "_has_open_exposure" not in GridLadderLifecycle.__dict__
