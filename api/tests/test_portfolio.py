from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlmodel import Session

from api.databases.tables.account_balances import ConsolidatedBalancesTable
from api.portfolio.controller import PortfolioController


def test_get_benchmark_series(client: TestClient, create_test_tables) -> None:
    now = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=1)
    balance_points = [
        (int((now - timedelta(days=2)).timestamp() * 1000), 100.0),
        (int((now - timedelta(days=1)).timestamp() * 1000), 110.0),
        (int(now.timestamp() * 1000), 105.0),
    ]

    with Session(create_test_tables) as session:
        session.exec(delete(ConsolidatedBalancesTable))
        for balance_id, estimated_total_fiat in balance_points:
            session.add(
                ConsolidatedBalancesTable(
                    id=balance_id,
                    balances=[],
                    estimated_total_fiat=estimated_total_fiat,
                )
            )
        session.commit()

    klines = [
        [
            balance_points[0][0],
            "0",
            "0",
            "0",
            "95000",
            "0",
            balance_points[0][0] + 86_400_000,
        ],
        [
            balance_points[1][0],
            "0",
            "0",
            "0",
            "96000",
            "0",
            balance_points[1][0] + 86_400_000,
        ],
        [
            balance_points[2][0],
            "0",
            "0",
            "0",
            "97000",
            "0",
            balance_points[2][0] + 86_400_000,
        ],
    ]

    with (
        patch(
            "api.portfolio.controller.BinanceApi.get_ui_klines",
            return_value=klines,
        ),
        patch(
            "api.portfolio.controller.BinanceApi.get_ticker_price",
            return_value=98000.0,
        ),
        patch(
            "api.portfolio.controller.ConsolidatedAccounts.get_balance",
            return_value=SimpleNamespace(
                estimated_total_fiat=130.0,
                total_deposit=5.0,
            ),
        ),
    ):
        response = client.get("/portfolio/benchmark-series")

    assert response.status_code == 200

    content = response.json()
    assert content["message"] == "Successfully retrieved benchmark series."
    assert content["data"]["series"]["fiat"] == [100.0, 110.0, 105.0, 130.0]
    assert content["data"]["series"]["btc"] == [95000.0, 96000.0, 97000.0, 98000.0]
    assert content["data"]["series"]["dates"][:3] == [
        balance_points[0][0],
        balance_points[1][0],
        balance_points[2][0],
    ]
    assert len(content["data"]["series"]["dates"]) == 4
    assert content["data"]["stats"]["pnl"] == 0.238
    assert content["data"]["stats"]["sharpe"] == 16.0974
    assert content["data"]["stats"]["btc_sharpe"] == 2246.155


def test_benchmark_releases_read_transaction_before_exchange_request() -> None:
    controller = PortfolioController.__new__(PortfolioController)
    session = MagicMock()
    controller.session = session
    controller.balances_crud = MagicMock()
    controller.balances_crud.query_balance_series.return_value = [
        SimpleNamespace(id=1_700_000_000_000, estimated_total_fiat=100.0),
        SimpleNamespace(id=1_699_913_600_000, estimated_total_fiat=90.0),
    ]
    controller.benchmark_symbol = "BTC-USDT"
    controller.interval = "1day"
    controller.api = MagicMock()

    def get_ui_klines(**kwargs):
        session.rollback.assert_called_once_with()
        return [
            [
                1_699_913_600_000,
                "0",
                "0",
                "0",
                "100",
                "0",
                1_699_913_600_000 + 86_400_000,
            ],
            [
                1_700_000_000_000,
                "0",
                "0",
                "0",
                "110",
                "0",
                1_700_000_000_000 + 86_400_000,
            ],
        ]

    controller.api.get_ui_klines.side_effect = get_ui_klines

    with patch.object(controller, "_append_live_benchmark_point"):
        controller.map_balance_with_benchmark(
            start_date=1_699_913_600_000,
            end_date=1_700_000_000_000,
        )

    session.rollback.assert_called_once_with()


def test_benchmark_requests_candles_covering_newest_and_oldest_snapshot():
    controller = PortfolioController.__new__(PortfolioController)
    controller.session = MagicMock()
    newest = 1_728_648_000_000
    oldest = newest - 3 * 86_400_000
    controller.balances_crud = MagicMock()
    controller.balances_crud.query_balance_series.return_value = [
        SimpleNamespace(id=newest, estimated_total_fiat=100),
        SimpleNamespace(id=oldest, estimated_total_fiat=90),
    ]
    controller.benchmark_symbol = "BTCUSDT"
    controller.interval = "1d"
    controller.api = MagicMock()
    controller.api.get_ui_klines.return_value = []

    with patch.object(controller, "_append_live_benchmark_point"):
        controller.map_balance_with_benchmark(0, newest)

    controller.api.get_ui_klines.assert_called_once_with(
        symbol="BTCUSDT", interval="1d", limit=4, end_time=newest
    )


@pytest.mark.parametrize(
    "previous, current, expected", [(100, 110, 0.1), (100, 0, -1), (0, 10, 0)]
)
def test_portfolio_return_uses_previous_balance_and_handles_zero(
    previous, current, expected
):
    controller = PortfolioController.__new__(PortfolioController)
    controller.session = MagicMock()
    controller.balances_crud = MagicMock()
    controller.balances_crud.query_balance_series.return_value = [
        SimpleNamespace(id=1_700_000_000_000, estimated_total_fiat=previous)
    ]
    controller.benchmark_symbol = "BTCUSDT"
    controller.interval = "1d"
    controller.api = MagicMock()
    controller.api.get_ui_klines.return_value = []

    def append_live(**kwargs):
        kwargs["balances"].append(current)

    with patch.object(
        controller, "_append_live_benchmark_point", side_effect=append_live
    ):
        result = controller.map_balance_with_benchmark(0, 1_700_000_000_000)

    assert result.stats.pnl == expected


def test_benchmark_matches_candle_open_day_when_close_is_at_next_midnight():
    controller = PortfolioController.__new__(PortfolioController)
    midnight = 1_728_604_800_000
    candles = [[midnight, 0, 0, 0, 100, 0, midnight + 86_400_000]]

    assert controller._consolidate_dates(candles, midnight + 3_600_000) == 0
