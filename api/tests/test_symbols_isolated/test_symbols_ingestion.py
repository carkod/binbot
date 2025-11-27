"""
Tests for symbol ingestion functions to verify TRY symbols are excluded
"""
import pytest
from unittest.mock import Mock, patch
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


@pytest.fixture
def mock_kucoin_symbols():
    """Mock KuCoin symbols response with TRY symbols"""
    btc_usdc = Mock()
    btc_usdc.symbol = "BTC-USDC"
    btc_usdc.enable_trading = True
    btc_usdc.base_currency = "BTC"
    btc_usdc.quote_currency = "USDC"
    btc_usdc.is_margin_enabled = True
    btc_usdc.price_increment = "0.01"
    btc_usdc.base_increment = "0.00001"
    btc_usdc.base_min_size = "10.0"

    btc_try = Mock()  # Should be excluded
    btc_try.symbol = "BTC-TRY"
    btc_try.enable_trading = True
    btc_try.base_currency = "BTC"
    btc_try.quote_currency = "TRY"
    btc_try.is_margin_enabled = True
    btc_try.price_increment = "0.01"
    btc_try.base_increment = "0.00001"
    btc_try.base_min_size = "10.0"

    eth_try = Mock()  # Should be excluded
    eth_try.symbol = "ETH-TRY"
    eth_try.enable_trading = True
    eth_try.base_currency = "ETH"
    eth_try.quote_currency = "TRY"
    eth_try.is_margin_enabled = True
    eth_try.price_increment = "0.01"
    eth_try.base_increment = "0.00001"
    eth_try.base_min_size = "10.0"

    eth_btc = Mock()
    eth_btc.symbol = "ETH-BTC"
    eth_btc.enable_trading = True
    eth_btc.base_currency = "ETH"
    eth_btc.quote_currency = "BTC"
    eth_btc.is_margin_enabled = True
    eth_btc.price_increment = "0.000001"
    eth_btc.base_increment = "0.00001"
    eth_btc.base_min_size = "0.0001"

    response = Mock()
    response.data = [btc_usdc, btc_try, eth_try, eth_btc]
    return response


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


def test_kucoin_symbols_ingestion_excludes_try(
    create_symbol_test_tables, mock_kucoin_symbols
):
    """Test that kucoin_symbols_ingestion excludes symbols with TRY as quote asset"""
    with patch("databases.crud.symbols_crud.KucoinApi") as mock_api:
        mock_api.return_value.get_all_symbols.return_value = mock_kucoin_symbols

        crud = SymbolsCrud()
        crud.kucoin_symbols_ingestion()

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


def test_kucoin_symbols_updates_excludes_try(
    create_symbol_test_tables, mock_kucoin_symbols
):
    """Test that kucoin_symbols_updates excludes symbols with TRY as quote asset"""
    with patch("databases.crud.symbols_crud.KucoinApi") as mock_api:
        mock_api.return_value.get_all_symbols.return_value = mock_kucoin_symbols

        crud = SymbolsCrud()
        crud.kucoin_symbols_updates()

        # Verify symbols were added correctly
        all_symbols = crud.get_all()
        symbol_ids = [s.id for s in all_symbols]

        # BTCUSDC should be added (ETHBTC already exists in fixtures)
        assert "BTCUSDC" in symbol_ids
        assert "ETHBTC" in symbol_ids

        # BTCTRY and ETHTRY should NOT be ingested
        assert "BTCTRY" not in symbol_ids
        assert "ETHTRY" not in symbol_ids
