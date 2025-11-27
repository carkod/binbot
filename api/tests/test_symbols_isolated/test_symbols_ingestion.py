"""
Tests for symbol ingestion functions to verify TRY symbols are excluded from Binance
"""
import pytest
from unittest.mock import patch
from databases.crud.symbols_crud import SymbolsCrud


@pytest.fixture
def mock_binance_exchange_info():
    """Mock Binance exchange info response with TRY symbols"""
    return {
        "symbols": [
            {
                "symbol": "BTCUSDC",
                "status": "TRADING",
                "baseAsset": "BTC",
                "quoteAsset": "USDC",
                "isMarginTradingAllowed": True,
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.00001"},
                    {"filterType": "NOTIONAL", "minNotional": "10.0"},
                ],
            },
            {
                "symbol": "BTCTRY",  # Should be excluded
                "status": "TRADING",
                "baseAsset": "BTC",
                "quoteAsset": "TRY",
                "isMarginTradingAllowed": True,
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.00001"},
                    {"filterType": "NOTIONAL", "minNotional": "10.0"},
                ],
            },
            {
                "symbol": "ETHTRY",  # Should be excluded
                "status": "TRADING",
                "baseAsset": "ETH",
                "quoteAsset": "TRY",
                "isMarginTradingAllowed": True,
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.00001"},
                    {"filterType": "NOTIONAL", "minNotional": "10.0"},
                ],
            },
            {
                "symbol": "ETHBTC",
                "status": "TRADING",
                "baseAsset": "ETH",
                "quoteAsset": "BTC",
                "isMarginTradingAllowed": True,
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": "0.000001"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.00001"},
                    {"filterType": "NOTIONAL", "minNotional": "0.0001"},
                ],
            },
        ]
    }


def test_binance_symbols_ingestion_excludes_try(
    create_symbol_test_tables, mock_binance_exchange_info
):
    """Test that binance_symbols_ingestion excludes symbols with TRY as quote asset"""
    with patch("databases.crud.symbols_crud.BinanceApi") as mock_api:
        mock_api.return_value.exchange_info.return_value = mock_binance_exchange_info

        crud = SymbolsCrud()
        crud.binance_symbols_ingestion()

        # Verify symbols were added correctly
        all_symbols = crud.get_all()
        symbol_ids = [s.id for s in all_symbols]

        # BTCUSDC and ETHBTC should be ingested (ETHBTC may already exist from fixtures)
        assert "BTCUSDC" in symbol_ids
        assert "ETHBTC" in symbol_ids

        # BTCTRY and ETHTRY should NOT be ingested
        assert "BTCTRY" not in symbol_ids
        assert "ETHTRY" not in symbol_ids


def test_etl_exchange_info_update_excludes_try(
    create_symbol_test_tables, mock_binance_exchange_info
):
    """Test that etl_exchange_info_update excludes symbols with TRY as quote asset"""
    with patch("databases.crud.symbols_crud.BinanceApi") as mock_api:
        mock_api.return_value.exchange_info.return_value = mock_binance_exchange_info

        crud = SymbolsCrud()
        crud.etl_exchange_info_update()

        # Verify symbols were added correctly
        all_symbols = crud.get_all()
        symbol_ids = [s.id for s in all_symbols]

        # BTCUSDC should be added (ETHBTC already exists in fixtures)
        assert "BTCUSDC" in symbol_ids
        assert "ETHBTC" in symbol_ids

        # BTCTRY and ETHTRY should NOT be ingested
        assert "BTCTRY" not in symbol_ids
        assert "ETHTRY" not in symbol_ids
