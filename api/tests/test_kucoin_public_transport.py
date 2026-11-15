"""Anonymous KuCoin requests used by streaming discovery and WebSocket setup."""

from unittest.mock import Mock, patch

import pytest
from requests import HTTPError

from streaming.shared.kucoin_futures import public_request


@pytest.mark.parametrize(
    "path,method,data",
    [
        ("/api/v1/bullet-public", "POST", {"token": "temporary-public-token"}),
        ("/api/v1/contracts/active", "GET", [{"symbol": "SOLUSDTM"}]),
    ],
)
def test_public_requests_return_data_without_account_credentials(path, method, data):
    response = Mock()
    response.json.return_value = {"code": "200000", "data": data}
    with patch(
        "streaming.shared.kucoin_futures.requests.request", return_value=response
    ) as request:
        assert public_request(path, method) == data
    request.assert_called_once_with(
        method, "https://api-futures.kucoin.com" + path, timeout=20
    )
    response.raise_for_status.assert_called_once()


def test_exchange_error_code_is_rejected_even_with_successful_http_status():
    response = Mock()
    response.json.return_value = {"code": "429000", "msg": "Too many requests"}
    with patch(
        "streaming.shared.kucoin_futures.requests.request", return_value=response
    ):
        with pytest.raises(ValueError, match="429000"):
            public_request("/api/v1/bullet-public", "POST")


def test_http_errors_propagate_to_collector_retry():
    response = Mock()
    response.raise_for_status.side_effect = HTTPError("Service unavailable")
    with patch(
        "streaming.shared.kucoin_futures.requests.request", return_value=response
    ):
        with pytest.raises(HTTPError, match="Service unavailable"):
            public_request("/api/v1/contracts/active")
