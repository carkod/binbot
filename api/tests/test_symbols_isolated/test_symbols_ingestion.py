"""
Tests for symbol ingestion functions to verify TRY symbols are excluded from Binance
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session, select
from api.databases.symbols_etl import SymbolDataEtl
from api.databases.tables.symbol_exchange_table import SymbolExchangeTable
from api.databases.tables.symbol_table import SymbolTable


@pytest.fixture(autouse=True)
def _patch_symbol_crud_apis(monkeypatch):
    from types import SimpleNamespace

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


def test_upsert_exchange_link_refreshes_stale_multiplier(create_symbol_test_tables):
    """
    A futures contract multiplier left at the migration's 1.0 backfill must be
    corrected to the exchange's real value on re-ingestion, otherwise every
    notional and PnL figure derived from it stays silently wrong.
    """
    with Session(create_symbol_test_tables) as session:
        session.add(SymbolTable(id="DASHUSDTM", quote_asset="USDT", base_asset="DASH"))
        session.add(
            SymbolExchangeTable(
                symbol_id="DASHUSDTM",
                exchange_id="kucoin",
                min_notional=5,
                price_precision=3,
                qty_precision=1,
                is_margin_trading_allowed=False,
                multiplier=1.0,
            )
        )
        session.commit()

        SymbolDataEtl().upsert_exchange_link(
            session,
            symbol="DASHUSDTM",
            exchange_id="kucoin",
            min_notional=99,
            price_precision=8,
            qty_precision=8,
            quote_asset="USDT",
            base_asset="DASH",
            is_margin_trading_allowed=True,
            multiplier=0.01,
        )
        session.commit()

        links = session.exec(
            select(SymbolExchangeTable).where(
                SymbolExchangeTable.symbol_id == "DASHUSDTM"
            )
        ).all()

        assert len(links) == 1
        assert links[0].multiplier == 0.01
        # Insert-only columns must not be rewritten by a refresh
        assert links[0].min_notional == 5
        assert links[0].price_precision == 3
        assert links[0].is_margin_trading_allowed is False


def test_upsert_exchange_link_without_multiplier_keeps_stored_value(
    create_symbol_test_tables,
):
    """
    Spot/margin ingestion reports no contract multiplier, so it must leave a
    stored futures multiplier untouched rather than resetting it to 1.0.
    """
    with Session(create_symbol_test_tables) as session:
        session.add(SymbolTable(id="ZENUSDTM", quote_asset="USDT", base_asset="ZEN"))
        session.add(
            SymbolExchangeTable(
                symbol_id="ZENUSDTM",
                exchange_id="kucoin",
                min_notional=5,
                price_precision=3,
                qty_precision=1,
                is_margin_trading_allowed=False,
                multiplier=0.1,
            )
        )
        session.commit()

        SymbolDataEtl().upsert_exchange_link(
            session,
            symbol="ZENUSDTM",
            exchange_id="kucoin",
            min_notional=5,
            price_precision=3,
            qty_precision=1,
            quote_asset="USDT",
            base_asset="ZEN",
            is_margin_trading_allowed=True,
        )
        session.commit()

        link = session.exec(
            select(SymbolExchangeTable).where(
                SymbolExchangeTable.symbol_id == "ZENUSDTM"
            )
        ).one()

        assert link.multiplier == 0.1
