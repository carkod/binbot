import os

import pytest
from fastapi.testclient import TestClient


@pytest.mark.vcr(match_on=["method"])
def test_get_kucoin_futures_position_proxies_symbol(client: TestClient) -> None:
    symbol = os.getenv("KUCOIN_TEST_FUTURES_SYMBOL", "XBTUSDTM")

    response = client.get(f"/order/kucoin/futures/position/{symbol}")

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Position found!"
    assert "data" in content


@pytest.mark.vcr(match_on=["method"])
def test_get_kucoin_futures_order_proxies_order_id(client: TestClient) -> None:
    order_id = os.getenv(
        "KUCOIN_TEST_FUTURES_ORDER_ID",
        "450247517263708160",
    )

    response = client.get(f"/order/kucoin/futures/{order_id}")

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Order found!"
    assert "data" in content
