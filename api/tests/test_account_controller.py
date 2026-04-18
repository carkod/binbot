from types import SimpleNamespace
from unittest.mock import MagicMock

from account.controller import ConsolidatedAccounts
from databases.tables.autotrade_table import AutotradeTable
from pybinbot import ExchangeId


def test_get_total_deposit_includes_paginated_crypto_and_bank_transfer_entries():
    controller = ConsolidatedAccounts.__new__(ConsolidatedAccounts)
    controller.fiat = "USDT"
    controller.autotrade_settings = AutotradeTable(exchange_id=ExchangeId.KUCOIN)
    controller._historical_rate_cache = {}

    ledger_page = SimpleNamespace(
        total_page=1,
        items=[
            SimpleNamespace(
                currency="EUR",
                amount="100",
                account_type="MAIN",
                biz_type="Fiat Deposit",
                direction="in",
                created_at=1_700_000_000_000,
            ),
            SimpleNamespace(
                currency="EUR",
                amount="50",
                account_type="TRADE",
                biz_type="Transfer in",
                direction="in",
                created_at=1_700_000_000_000,
            ),
        ],
    )
    controller.kucoin_api = MagicMock()
    controller.kucoin_api.get_spot_ledger.return_value = ledger_page
    controller.kucoin_api.get_ui_klines.return_value = [
        [0, "0", "0", "0", "0.8", "0", 0, "0"]
    ]

    assert controller.get_total_deposit() == 125.0

    controller.kucoin_api.get_spot_ledger.assert_called_once_with(
        current_page=1,
        page_size=ConsolidatedAccounts.PAGINATION_PAGE_SIZE,
    )
    controller.kucoin_api.get_ticker_price.assert_not_called()
