from unittest.mock import patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# The import below is required to register all models for SQLModel metadata. Do not remove!
import databases.tables  # noqa: F401
from databases.tables.autotrade_table import AutotradeTable
from databases.utils import get_session
from main import app
from tests.fixtures.symbol_fixtures import (
    get_test_asset_indices,
    get_test_symbol_index_links,
    get_test_symbols,
)

# Global variable to store test engine for use in patches
_test_engine_symbols = None


@pytest.fixture(scope="module", autouse=True)
def create_symbol_test_tables():
    """
    Completely isolated test database setup ONLY for symbol tests.
    This prevents interference from other test files.
    """
    global _test_engine_symbols

    # Use a separate in-memory SQLite database just for symbol tests
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _test_engine_symbols = test_engine
    SQLModel.metadata.create_all(test_engine)

    # Override get_session to use this isolated test database
    def get_test_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session

    # Patch independent_session to also use this isolated test database
    def mock_independent_session():
        return Session(test_engine, expire_on_commit=False)

    # Seed test database with fixtures
    with Session(test_engine) as session:
        # Add mock autotrade settings with exchange_id = "binance"
        mock_autotrade = AutotradeTable(
            id="autotrade_settings",
            base_order_size=15.0,
            test_autotrade=False,
            trailling_deviation=0.63,
            stop_loss=0.0,
            fiat="USDC",
            telegram_signals=True,
            close_condition="dynamic_trailling",
            autotrade=True,
            candlestick_interval="15m",
            updated_at=1732388868477.8518,
            trailling=True,
            trailling_profit=2.3,
            take_profit=2.3,
            max_request=500,
            max_active_autotrade_bots=1,
            exchange_id="binance",  # Fixed to binance for symbol tests
        )
        session.add(mock_autotrade)

        # Add asset indices
        for asset_index in get_test_asset_indices():
            session.add(asset_index)

        # Add symbols with their exchange values
        for symbol_data in get_test_symbols():
            session.add(symbol_data["symbol"])
            for exchange_value in symbol_data["exchange_values"]:
                session.add(exchange_value)

        # Add symbol-index links
        for link in get_test_symbol_index_links():
            session.add(link)

        session.commit()

    # Start patching independent_session for symbol tests only
    patcher1 = patch(
        "databases.utils.independent_session", side_effect=mock_independent_session
    )
    patcher2 = patch(
        "databases.crud.autotrade_crud.independent_session",
        side_effect=mock_independent_session,
    )
    patcher3 = patch(
        "databases.crud.symbols_crud.independent_session",
        side_effect=mock_independent_session,
    )
    patcher1.start()
    patcher2.start()
    patcher3.start()

    yield test_engine

    # Clean up
    patcher1.stop()
    patcher2.stop()
    patcher3.stop()
    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(test_engine)
