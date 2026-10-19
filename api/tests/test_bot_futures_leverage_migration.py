import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from api.alembic.versions import e8b2c4d6f0a1_add_bot_futures_leverage as migration


@pytest.mark.parametrize("existing_column", [False, True])
def test_bot_leverage_migration_backfills_symbol_defaults_and_replays(
    monkeypatch,
    existing_column,
):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE symbol (id TEXT PRIMARY KEY, futures_leverage INTEGER)")
        )
        connection.execute(
            text("INSERT INTO symbol VALUES ('XBTUSDTM', 3), ('ETHUSDTM', 5)")
        )
        connection.execute(
            text("CREATE TABLE bot (id TEXT PRIMARY KEY, pair TEXT, market_type TEXT)")
        )
        connection.execute(
            text(
                "INSERT INTO bot VALUES ('btc', 'XBTUSDTM', 'FUTURES'), "
                "('eth', 'ETHUSDTM', 'FUTURES'), ('unknown', 'MISSING', 'FUTURES'), "
                "('spot', 'XBTUSDTM', 'SPOT')"
            )
        )
        if existing_column:
            connection.execute(
                text("ALTER TABLE bot ADD COLUMN futures_leverage INTEGER")
            )
            # Explicit per-bot values survive a missing Alembic revision marker.
            connection.execute(
                text("UPDATE bot SET futures_leverage = 2 WHERE id = 'btc'")
            )

        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        migration.upgrade()
        assert connection.execute(
            text("SELECT id, futures_leverage FROM bot ORDER BY id")
        ).all() == [
            ("btc", 2 if existing_column else 3),
            ("eth", 5),
            ("spot", 1),
            ("unknown", 1),
        ]
        columns = {
            column["name"]: column for column in inspect(connection).get_columns("bot")
        }
        assert columns["futures_leverage"]["nullable"] is False
        connection.execute(text("INSERT INTO bot (id) VALUES ('new')"))
        assert (
            connection.execute(
                text("SELECT futures_leverage FROM bot WHERE id = 'new'")
            ).scalar_one()
            == 1
        )
        for invalid in (0, 6):
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "UPDATE bot SET futures_leverage = :leverage WHERE id = 'new'"
                    ),
                    {"leverage": invalid},
                )

        migration.downgrade()
        migration.downgrade()
        assert "futures_leverage" not in {
            column["name"] for column in inspect(connection).get_columns("bot")
        }
