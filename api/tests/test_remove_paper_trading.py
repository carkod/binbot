"""Retiring simulation must not remove real trading data or expose old routes."""

from itertools import product

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlmodel import SQLModel

from api.alembic.versions import d7e8f9a0b1c2_remove_paper_trading as migration
from api.main import app


@pytest.mark.parametrize(
    "paper,orders,settings", list(product([False, True], repeat=3))
)
def test_removal_replays_on_full_partial_and_already_migrated_schema(
    monkeypatch, paper, orders, settings
):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        connection.execute(text("CREATE TABLE deal (id TEXT PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE bot (id TEXT PRIMARY KEY, deal_id TEXT REFERENCES deal(id))"
            )
        )
        connection.execute(text("CREATE TABLE autotrade (id TEXT PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE exchange_order (id TEXT, bot_id TEXT REFERENCES bot(id))"
            )
        )
        connection.execute(
            text("INSERT INTO deal VALUES ('live'), ('shared'), ('paper'), ('unowned')")
        )
        connection.execute(
            text("INSERT INTO bot VALUES ('a', 'live'), ('b', 'shared')")
        )
        connection.execute(text("INSERT INTO exchange_order VALUES ('order', 'a')"))
        connection.execute(text("INSERT INTO autotrade VALUES ('autotrade_settings')"))
        if paper:
            connection.execute(
                text(
                    "CREATE TABLE paper_trading (id TEXT PRIMARY KEY, deal_id TEXT REFERENCES deal(id))"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO paper_trading VALUES ('p', 'paper'), ('s', 'shared'), ('n', NULL)"
                )
            )
        if orders:
            # A partially removed schema may still have the child table.
            reference = " REFERENCES paper_trading(id)" if paper else ""
            connection.execute(
                text(f"CREATE TABLE fake_order (paper_trading_id TEXT{reference})")
            )
            connection.execute(text("INSERT INTO fake_order VALUES ('p')"))
        if settings:
            connection.execute(text("CREATE TABLE test_autotrade (id TEXT)"))
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )

        migration.upgrade()
        migration.upgrade()

        assert set(inspect(connection).get_table_names()) == {
            "deal",
            "bot",
            "exchange_order",
            "autotrade",
        }
        expected_deals = {"live", "shared", "unowned"}
        if not paper:
            # Without ownership information, do not guess which deals to delete.
            expected_deals.add("paper")
        assert (
            set(connection.execute(text("SELECT id FROM deal")).scalars())
            == expected_deals
        )
        assert connection.execute(text("SELECT COUNT(*) FROM bot")).scalar() == 2
        assert (
            connection.execute(text("SELECT id FROM exchange_order")).scalar()
            == "order"
        )
        assert (
            connection.execute(text("SELECT id FROM autotrade")).scalar()
            == "autotrade_settings"
        )


def test_removed_routes_and_models_are_not_registered():
    paths = app.openapi()["paths"]
    assert not any("paper-trading" in path for path in paths)
    assert "/bot" in paths
    assert "/autotrade-settings/bots" in paths
    assert {"paper_trading", "fake_order", "test_autotrade"}.isdisjoint(
        SQLModel.metadata.tables
    )


def test_downgrade_does_not_pretend_to_restore_deleted_history():
    with pytest.raises(RuntimeError, match="irreversible"):
        migration.downgrade()
