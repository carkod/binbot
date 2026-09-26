from importlib import import_module

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


baseline = import_module("api.alembic.versions.5be29ddb30b9_baseline")


def test_baseline_creates_legacy_schema_and_can_be_replayed(monkeypatch):
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(baseline, "op", operations)

        baseline.upgrade()
        baseline.upgrade()

        inspector = inspect(connection)
        assert set(inspector.get_table_names()) == {
            "asset_index",
            "autotrade",
            "balances",
            "binbot_user",
            "bot",
            "consolidated_balances",
            "deal",
            "exchange_order",
            "fake_order",
            "paper_trading",
            "staging_balances",
            "staging_consolidated_balances",
            "symbol",
            "symbol_exchange",
            "symbol_index_link",
            "test_autotrade",
        }

        deal_columns = {column["name"] for column in inspector.get_columns("deal")}
        assert "trailling_stop_loss_price" in deal_columns
        assert "trailing_stop_loss_price" not in deal_columns

        bot_columns = {column["name"] for column in inspector.get_columns("bot")}
        assert {"strategy", "trailling", "dynamic_trailling"} <= bot_columns
        assert {"position", "trailing", "dynamic_trailing"}.isdisjoint(bot_columns)

        order_columns = {
            column["name"]: column for column in inspector.get_columns("exchange_order")
        }
        assert "INT" in str(order_columns["order_id"]["type"]).upper()
