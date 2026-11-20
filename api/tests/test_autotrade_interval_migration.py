import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from api.alembic.versions import (
    a9d38e21c6f4_remove_autotrade_candlestick_interval as migration,
)


@pytest.mark.parametrize("existing_column", [False, True])
@pytest.mark.parametrize("legacy_table", [False, True])
def test_interval_migration_preserves_settings_and_bot_intervals_on_replay(
    monkeypatch, existing_column, legacy_table
):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE bot (id TEXT PRIMARY KEY, candlestick_interval TEXT)")
        )
        connection.execute(text("INSERT INTO bot VALUES ('btc', 'one_hour')"))
        tables = ["autotrade", "test_autotrade"] if legacy_table else ["autotrade"]
        for table in tables:
            connection.execute(
                text(f"CREATE TABLE {table} (id TEXT PRIMARY KEY, fiat TEXT)")
            )
            connection.execute(
                text(f"INSERT INTO {table} VALUES ('autotrade_settings', 'USDT')")
            )
            if existing_column:
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN candlestick_interval TEXT")
                )

        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        migration.upgrade()
        for table in tables:
            assert connection.execute(text(f"SELECT * FROM {table}")).all() == [
                ("autotrade_settings", "USDT")
            ]
        assert connection.execute(text("SELECT * FROM bot")).all() == [
            ("btc", "one_hour")
        ]
        assert inspect(connection).has_table("test_autotrade") is legacy_table

        migration.downgrade()
        migration.downgrade()
        for table in tables:
            assert connection.execute(text(f"SELECT * FROM {table}")).all() == [
                ("autotrade_settings", "USDT", "fifteen_minutes")
            ]
