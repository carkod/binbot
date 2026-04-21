from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlmodel import Session

from databases.tables.account_balances import ConsolidatedBalancesTable


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
        [balance_points[0][0] - 1, "0", "0", "0", "95000", "0", balance_points[0][0]],
        [balance_points[1][0] - 1, "0", "0", "0", "96000", "0", balance_points[1][0]],
        [balance_points[2][0] - 1, "0", "0", "0", "97000", "0", balance_points[2][0]],
    ]

    with (
        patch(
            "portfolio.controller.BinanceApi.get_ui_klines",
            return_value=klines,
        ),
        patch(
            "portfolio.controller.BinanceApi.get_ticker_price",
            return_value=98000.0,
        ),
        patch(
            "portfolio.controller.ConsolidatedAccounts.get_balance",
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
    assert content["data"]["series"]["fiat"] == [100.0, 110.0, 105.0, 125.0]
    assert content["data"]["series"]["btc"] == [95000.0, 96000.0, 97000.0, 98000.0]
    assert content["data"]["series"]["dates"][:3] == [
        balance_points[0][0],
        balance_points[1][0],
        balance_points[2][0],
    ]
    assert len(content["data"]["series"]["dates"]) == 4
    assert content["data"]["stats"]["pnl"] == 0.16
    assert content["data"]["stats"]["sharpe"] == 16.0555
    assert content["data"]["stats"]["btc_sharpe"] == 2246.155
