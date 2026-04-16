from fastapi.testclient import TestClient
from pybinbot import UserRoles
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
from uuid import UUID
from contextlib import contextmanager
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from user.models.user import UserTokenData
from user.services.auth import get_current_user
from databases.utils import get_session
from databases.tables.autotrade_table import AutotradeTable
from databases.tables.bot_table import BotTable
from databases.tables.deal_table import DealTable
from main import app

# The import below is required to register all models for SQLModel metadata. Do not remove!
import databases.tables  # noqa: F401

from tests.fixtures.symbol_fixtures import (
    get_test_symbols,
    get_test_asset_indices,
    get_test_symbol_index_links,
)
from tests.fixtures.paper_trading import seed_paper_trading_defaults


# Global variable to store test engine for use in patches
_test_engine = None


@pytest.fixture(scope="module")
def vcr_config():
    cassette_dir = Path(__file__).parent / "cassettes"
    cassette_dir.mkdir(parents=True, exist_ok=True)
    return {
        "filter_headers": [
            ("X-MBX-APIKEY", "DUMMY"),
            ("authorization", "DUMMY"),
        ],
        "filter_query_parameters": [
            ("timestamp", "DUMMY"),
            ("signature", "DUMMY"),
        ],
        "cassette_library_dir": str(cassette_dir),
        "record_mode": "once",
        "match_on": ["method", "path", "query"],
    }


class MockAsyncBaseProducer:
    def __init__(self):
        pass

    def start_producer(self):
        producer = MagicMock()
        return producer

    def update_required(self, action):
        return action


# Ensure all tables are created before any tests run
@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    global _test_engine

    # Use in-memory SQLite database for tests instead of real PostgreSQL
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _test_engine = test_engine
    SQLModel.metadata.create_all(test_engine)

    # Override get_session to use test database
    @contextmanager
    def get_test_session_manager():
        with Session(test_engine) as session:
            yield session

    def get_test_session():
        with get_test_session_manager() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session

    # Patch independent_session to also use test database
    # This ensures AutotradeCrud() without session parameter uses test DB
    # IMPORTANT: Return a NEW session each time to avoid session conflicts
    # when different CRUD instances close their sessions
    def mock_independent_session():
        return Session(test_engine, expire_on_commit=False)

    # Seed test database with fixtures
    with Session(test_engine) as session:
        # Add mock autotrade settings
        mock_autotrade = AutotradeTable(
            id="autotrade_settings",
            base_order_size=15.0,
            test_autotrade=False,
            trailing_deviation=0.63,
            stop_loss=0.0,
            fiat="USDC",
            telegram_signals=True,
            close_condition="dynamic_trailing",
            autotrade=True,
            candlestick_interval="15m",
            updated_at=1732388868477.8518,
            trailing=True,
            trailing_profit=2.3,
            take_profit=2.3,
            max_request=500,
            max_active_autotrade_bots=1,
            exchange_id="binance",
        )
        session.add(mock_autotrade)

        # Create test deals for the bots
        test_deals = [
            DealTable(
                id=UUID("550e8400-e29b-41d4-a716-446655440001"),
                base_order_size=15.0,
                current_price=0.0,
                take_profit_price=0.0,
                trailing_stop_loss_price=0.0,
                trailing_profit_price=0.0,
                stop_loss_price=0.0,
                total_interests=0.0,
                total_commissions=0.0,
                margin_loan_id=0,
                margin_repay_id=0,
                opening_price=0.0,
                opening_qty=0.0,
                opening_timestamp=0,
                closing_price=0.0,
                closing_qty=0.0,
                closing_timestamp=0,
            ),
            DealTable(
                id=UUID("550e8400-e29b-41d4-a716-446655440002"),
                base_order_size=20.0,
                current_price=0.0,
                take_profit_price=0.0,
                trailing_stop_loss_price=0.0,
                trailing_profit_price=0.0,
                stop_loss_price=0.0,
                total_interests=0.0,
                total_commissions=0.0,
                margin_loan_id=0,
                margin_repay_id=0,
                opening_price=0.0,
                opening_qty=0.0,
                opening_timestamp=0,
                closing_price=0.0,
                closing_qty=0.0,
                closing_timestamp=0,
            ),
            DealTable(
                id=UUID("550e8400-e29b-41d4-a716-446655440003"),
                base_order_size=25.0,
                current_price=0.0,
                take_profit_price=0.0,
                trailing_stop_loss_price=0.0,
                trailing_profit_price=0.0,
                stop_loss_price=0.0,
                total_interests=0.0,
                total_commissions=0.0,
                margin_loan_id=0,
                margin_repay_id=0,
                opening_price=0.0,
                opening_qty=0.0,
                opening_timestamp=0,
                closing_price=0.0,
                closing_qty=0.0,
                closing_timestamp=0,
            ),
            DealTable(
                id=UUID("550e8400-e29b-41d4-a716-446655440004"),
                base_order_size=15.0,
                current_price=0.0,
                take_profit_price=0.0,
                trailing_stop_loss_price=0.0,
                trailing_profit_price=0.0,
                stop_loss_price=0.0,
                total_interests=0.0,
                total_commissions=0.0,
                margin_loan_id=0,
                margin_repay_id=0,
                opening_price=0.0,
                opening_qty=0.0,
                opening_timestamp=0,
                closing_price=0.0,
                closing_qty=0.0,
                closing_timestamp=0,
            ),
            DealTable(
                id=UUID("550e8400-e29b-41d4-a716-446655440005"),
                base_order_size=15.0,
                current_price=0.0,
                take_profit_price=0.0,
                trailing_stop_loss_price=0.0,
                trailing_profit_price=0.0,
                stop_loss_price=0.0,
                total_interests=0.0,
                total_commissions=0.0,
                margin_loan_id=0,
                margin_repay_id=0,
                opening_price=0.0,
                opening_qty=0.0,
                opening_timestamp=0,
                closing_price=0.0,
                closing_qty=0.0,
                closing_timestamp=0,
            ),
        ]
        for deal in test_deals:
            session.add(deal)

        # Add test bots
        test_bots = [
            BotTable(
                id=UUID("cff9e468-87ee-46fa-8678-17af132b8434"),
                pair="ADXUSDC",
                fiat="USDC",
                base_order_size=15,
                candlestick_interval="15m",
                close_condition="dynamic_trailing",
                cooldown=360,
                created_at=1733973560249.0,
                updated_at=1733973560249.0,
                dynamic_trailing=False,
                mode="manual",
                name="Test bot 1",
                status="inactive",
                stop_loss=3.0,
                take_profit=2.3,
                trailing=True,
                trailing_deviation=3.0,
                trailing_profit=0.0,
                position="long",
                deal=test_deals[0],
            ),
            BotTable(
                id=UUID("44db75ee-15c2-4a48-a346-4ffdc3ac5506"),
                pair="EPICUSDC",
                fiat="USDC",
                base_order_size=20,
                candlestick_interval="15m",
                close_condition="dynamic_trailing",
                cooldown=360,
                created_at=1733973560249.0,
                updated_at=1733973560249.0,
                dynamic_trailing=False,
                mode="manual",
                name="Test bot 2",
                status="inactive",
                stop_loss=3.0,
                take_profit=2.3,
                trailing=True,
                trailing_deviation=3.0,
                trailing_profit=0.0,
                position="long",
                deal=test_deals[1],
            ),
            BotTable(
                id=UUID("ebda4958-837c-4544-bf97-9bf449698152"),
                pair="ADAUSDC",
                fiat="USDC",
                base_order_size=25,
                candlestick_interval="15m",
                close_condition="dynamic_trailing",
                cooldown=360,
                created_at=1733973560249.0,
                updated_at=1733973560249.0,
                dynamic_trailing=False,
                mode="manual",
                name="Test bot 3",
                status="active",
                stop_loss=3.0,
                take_profit=2.3,
                trailing=True,
                trailing_deviation=3.0,
                trailing_profit=0.0,
                position="long",
                deal=test_deals[2],
            ),
            # Additional bots for deletion testing
            BotTable(
                id=UUID("00000000-0000-0000-0000-000000000001"),
                pair="TESTUSDC1",
                fiat="USDC",
                base_order_size=15,
                candlestick_interval="15m",
                close_condition="dynamic_trailing",
                cooldown=360,
                created_at=1733973560249.0,
                updated_at=1733973560249.0,
                dynamic_trailing=False,
                mode="manual",
                name="Test bot for deletion 1",
                status="inactive",
                stop_loss=3.0,
                take_profit=2.3,
                trailing=True,
                trailing_deviation=3.0,
                trailing_profit=0.0,
                position="long",
                deal=test_deals[3],
            ),
            BotTable(
                id=UUID("00000000-0000-0000-0000-000000000002"),
                pair="TESTUSDC2",
                fiat="USDC",
                base_order_size=15,
                candlestick_interval="15m",
                close_condition="dynamic_trailing",
                cooldown=360,
                created_at=1733973560249.0,
                updated_at=1733973560249.0,
                dynamic_trailing=False,
                mode="manual",
                name="Test bot for deletion 2",
                status="inactive",
                stop_loss=3.0,
                take_profit=2.3,
                trailing=True,
                trailing_deviation=3.0,
                trailing_profit=0.0,
                position="long",
                deal=test_deals[4],
            ),
        ]
        for bot in test_bots:
            session.add(bot)

        # Add paper trading bots via shared fixture helper
        seed_paper_trading_defaults(session, commit=False)

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

    # Start patching independent_session for the entire test session
    # Patch in all locations where it's imported
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
    patcher4 = patch(
        "databases.crud.bot_crud.get_session",
        new=get_test_session_manager,
    )
    patcher5 = patch(
        "databases.crud.asset_index_crud.independent_session",
        side_effect=mock_independent_session,
    )
    patcher6 = patch(
        "databases.crud.paper_trading_crud.independent_session",
        side_effect=mock_independent_session,
    )

    # Mock exchange API methods that are called during bot activation/deactivation
    mock_buy_order_response = {
        "symbol": "EPICUSDC",
        "orderId": 123456789,
        "price": "1.0",
        "origQty": "20.0",
        "status": "FILLED",
        "type": "MARKET",
        "side": "BUY",
        "timeInForce": "GTC",
        "transactTime": 1733973560249,
        "fills": [
            {
                "price": "1.0",
                "qty": "20.0",
                "commission": "0.015",
                "commissionAsset": "USDC",
            }
        ],
    }

    patcher7 = patch(
        "exchange_apis.binance.deals.spot_deal.BinanceSpotDeal.buy_order",
        return_value=mock_buy_order_response,
    )
    patcher8 = patch(
        "exchange_apis.binance.deals.spot_deal.BinanceSpotDeal.sell_order",
        return_value=mock_buy_order_response,
    )
    patcher9 = patch(
        "exchange_apis.binance.deals.spot_deal.BinanceSpotDeal.delete_order",
        return_value={"msg": "success"},
    )

    # Mock get_server_time to return an object with proper response structure
    mock_server_time_response = Mock()
    mock_server_time_response.headers = {"x-mbx-used-weight-1m": "1"}
    mock_server_time_response.json.return_value = {"serverTime": 1733973560249}

    patcher10 = patch(
        "pybinbot.apis.binance.base.BinanceApi.get_server_time",
        return_value=1733973560249,
    )

    # Mock additional exchange API methods
    patcher11 = patch(
        "exchange_apis.binance.account.BinanceAccount.get_single_spot_balance",
        return_value=100.0,
    )
    patcher12 = patch(
        "exchange_apis.binance.orders.BinanceOrderController.get_ticker_price",
        return_value=1.0,
    )

    # Mock ConsolidatedAccounts for account endpoints
    mock_consolidated_accounts = MagicMock()
    mock_consolidated_accounts.store_balance.return_value = {"USDC": 100.0}
    mock_consolidated_accounts.autotrade_settings.exchange_id.name = "binance"

    patcher13 = patch(
        "account.routes.ConsolidatedAccounts",
        return_value=mock_consolidated_accounts,
    )

    patcher1.start()
    patcher2.start()
    patcher3.start()
    patcher4.start()
    patcher5.start()
    patcher6.start()
    patcher7.start()
    patcher8.start()
    patcher9.start()
    patcher10.start()
    patcher11.start()
    patcher12.start()
    patcher13.start()

    yield test_engine

    # Clean up
    patcher1.stop()
    patcher2.stop()
    patcher3.stop()
    patcher4.stop()
    patcher5.stop()
    patcher6.stop()
    patcher7.stop()
    patcher8.stop()
    patcher9.stop()
    patcher10.stop()
    patcher11.stop()
    patcher12.stop()
    patcher13.stop()
    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture()
def paper_trading_table_fixture(create_test_tables):
    if _test_engine is not None:
        with Session(_test_engine) as session:
            seed_paper_trading_defaults(session)
    try:
        yield
    finally:
        if _test_engine is not None:
            with Session(_test_engine) as session:
                seed_paper_trading_defaults(session)


@pytest.fixture(scope="session")
def mock_lifespan():
    with patch("main.lifespan") as mock_lifespan:
        yield mock_lifespan


def override_get_current_user():
    return UserTokenData(
        email="test@example.com", role=UserRoles.admin, expires_in=1732388868477
    )


@pytest.fixture()
def client() -> TestClient:
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = override_get_current_user
    return client
