"""
Tests for symbol ingestion functions to verify TRY symbols are excluded from Binance
"""

from types import SimpleNamespace

import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session

from api.databases.symbols_etl import (
    SymbolDataEtl,
    _is_crypto_contract,
    _persistent_asset_class,
)
from api.databases.tables.symbol_table import SymbolTable
from pybinbot import ExchangeId, FuturesContractMarketData


@pytest.fixture(autouse=True)
def _patch_symbol_crud_apis(monkeypatch):
    class DummyKucoinFutures:
        def __init__(self, *args, **kwargs):
            pass

        def get_all_symbols(self):
            items = [
                SimpleNamespace(
                    symbol="BTC-USDC",
                    enable_trading=True,
                    st=False,
                    base_min_size="0.001",
                    price_increment="0.01",
                    base_increment="0.0001",
                    quote_currency="USDC",
                    base_currency="BTC",
                    is_margin_enabled=True,
                ),
                SimpleNamespace(
                    symbol="BTC-TRY",
                    enable_trading=True,
                    st=False,
                    base_min_size="0.001",
                    price_increment="0.01",
                    base_increment="0.0001",
                    quote_currency="TRY",
                    base_currency="BTC",
                    is_margin_enabled=True,
                ),
            ]
            return SimpleNamespace(data=items)

    monkeypatch.setattr(
        "api.databases.crud.symbols_crud.KucoinFutures", DummyKucoinFutures
    )


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
                "symbol": "ETHUSDC",
                "status": "TRADING",
                "baseAsset": "ETH",
                "quoteAsset": "USDC",
                "isMarginTradingAllowed": True,
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.00001"},
                    {"filterType": "NOTIONAL", "minNotional": "10.0"},
                ],
            },
        ]
    }


def test_binance_symbols_ingestion_excludes_try(
    create_symbol_test_tables, mock_binance_exchange_info
):
    """Test that binance_symbols_ingestion excludes symbols with TRY as quote asset"""
    with patch("api.databases.crud.symbols_crud.BinanceApi") as MockBinanceApi:
        # Create a mock instance
        mock_instance = MagicMock()
        mock_instance.exchange_info.return_value = mock_binance_exchange_info
        MockBinanceApi.return_value = mock_instance

        crud = SymbolDataEtl()
        crud.binance_symbols_ingestion()

        # Verify symbols were added correctly
        all_symbols = crud.get_all()
        symbol_ids = [s.id for s in all_symbols]

        # BTCUSDC and ETHUSDC should be ingested
        assert "BTCUSDC" in symbol_ids
        assert "ETHUSDC" in symbol_ids

        # BTCTRY and ETHTRY should NOT be ingested
        assert "BTCTRY" not in symbol_ids
        assert "ETHTRY" not in symbol_ids


def test_persistent_asset_class_requires_regime_and_direction_stability():
    persistent_range = [(day, "range", "down") for day in range(31)]
    persistent_downtrend = [
        (day, "trend", "up" if day < 9 else "down") for day in range(31)
    ]
    unstable_trend = [(day, "trend", "down" if day % 2 else "up") for day in range(31)]

    assert _persistent_asset_class(persistent_range) == "persistent_range"
    assert _persistent_asset_class(persistent_downtrend) == "persistent_downtrend"
    assert _persistent_asset_class(unstable_trend) == ""


def test_crypto_contract_filter_uses_sdk_contract_metadata():
    crypto = FuturesContractMarketData(
        symbol="INJUSDTM",
        status="Open",
        quote_currency="USDT",
        source_exchanges=["kucoin", "binance"],
        turnover_24h=1_000,
        multiplier=1,
        open_interest=1,
    )
    tradfi = FuturesContractMarketData(
        symbol="NVDAUSDTM",
        status="Open",
        quote_currency="USDT",
        source_exchanges=["finnhub", "binance_index"],
        turnover_24h=1_000,
        multiplier=1,
        open_interest=1,
    )
    private_equity_reference = FuturesContractMarketData(
        symbol="OPENAIUSDTM",
        status="Open",
        quote_currency="USDT",
        source_exchanges=["binance_mark_price"],
        turnover_24h=1_000,
        multiplier=1,
        open_interest=1,
    )
    production_symbols = {"INJUSDTM", "NVDAUSDTM", "OPENAIUSDTM"}

    assert _is_crypto_contract(crypto, production_symbols)
    assert not _is_crypto_contract(tradfi, production_symbols)
    assert not _is_crypto_contract(private_equity_reference, production_symbols)


def test_update_asset_classes_replaces_evaluated_and_preserves_fetch_failures(
    create_symbol_test_tables, monkeypatch
):
    with Session(create_symbol_test_tables) as session:
        gas = session.get(SymbolTable, "GASBTC")
        lrc_btc = session.get(SymbolTable, "LRCBTC")
        lrc_eth = session.get(SymbolTable, "LRCETH")
        assert gas is not None
        assert lrc_btc is not None
        assert lrc_eth is not None
        gas.asset_class = "persistent_downtrend"
        lrc_btc.asset_class = "persistent_uptrend"
        lrc_eth.asset_class = "persistent_range"
        session.add_all([gas, lrc_btc, lrc_eth])
        session.commit()

    etl = SymbolDataEtl()
    monkeypatch.setattr(
        etl,
        "classify_persistent_crypto_assets",
        lambda: (
            {"LRCBTC": "persistent_range"},
            {"LRCBTC"},
            {"GASBTC", "LRCBTC"},
        ),
    )

    classifications = etl.update_asset_classes()

    assert classifications == {"LRCBTC": "persistent_range"}
    with Session(create_symbol_test_tables) as session:
        gas = session.get(SymbolTable, "GASBTC")
        lrc_btc = session.get(SymbolTable, "LRCBTC")
        lrc_eth = session.get(SymbolTable, "LRCETH")
        assert gas is not None
        assert lrc_btc is not None
        assert lrc_eth is not None
        assert gas.asset_class == "persistent_downtrend"
        assert lrc_btc.asset_class == "persistent_range"
        assert lrc_eth.asset_class == ""


def test_kucoin_ingestion_runs_asset_classification(monkeypatch):
    etl = SymbolDataEtl()
    etl.autotrade_settings.exchange_id = ExchangeId.KUCOIN
    ingest_symbols = MagicMock()
    update_asset_classes = MagicMock()
    monkeypatch.setattr(etl, "kucoin_symbols_ingestion", ingest_symbols)
    monkeypatch.setattr(etl, "update_asset_classes", update_asset_classes)

    etl.etl_symbols_ingestion()

    ingest_symbols.assert_called_once_with()
    update_asset_classes.assert_called_once_with()
