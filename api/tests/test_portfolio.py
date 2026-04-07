from datetime import datetime, timedelta
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

    with patch(
        "portfolio.controller.BinanceApi.get_ui_klines",
        return_value=klines,
    ):
        response = client.get("/portfolio/benchmark-series")

    assert response.status_code == 200

    content = response.json()
    assert content["message"] == "Successfully retrieved benchmark series."
    assert content["data"]["series"] == {
        "fiat": [100.0, 110.0, 105.0],
        "btc": [95000.0, 96000.0, 97000.0],
        "dates": [balance_points[0][0], balance_points[1][0], balance_points[2][0]],
    }
    assert content["data"]["stats"]["pnl"] == -0.0477
    assert content["data"]["stats"]["sharpe"] == 7.1643
