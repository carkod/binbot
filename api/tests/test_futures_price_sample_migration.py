from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from api.alembic.versions import a0b1c2d3e4f5_add_futures_price_sample as migration


def test_futures_price_sample_migration_creates_and_replays(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        migration.upgrade()
        inspector = inspect(connection)
        assert inspector.has_table("futures_price_sample")
        assert {
            "source",
            "recorded_at",
            "symbol",
            "last_price",
            "price_change_percent",
            "turnover_24h",
        } <= {
            column["name"] for column in inspector.get_columns("futures_price_sample")
        }
        assert migration.INDEX in {
            index["name"] for index in inspector.get_indexes("futures_price_sample")
        }


def test_futures_price_sample_migration_repairs_partial_table(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("""
            CREATE TABLE futures_price_sample (
                id INTEGER PRIMARY KEY, source VARCHAR(32), recorded_at DATETIME,
                symbol VARCHAR(64), last_price FLOAT
            )
        """)
        )
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        migration.upgrade()
        inspector = inspect(connection)
        assert {"price_change_percent", "turnover_24h"} <= {
            column["name"] for column in inspector.get_columns("futures_price_sample")
        }
        assert migration.UNIQUE in {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("futures_price_sample")
        }
