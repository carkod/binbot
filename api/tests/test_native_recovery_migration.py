import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from api.alembic.versions import f6a81c2d490e_native_recovery_closes as migration


@pytest.mark.parametrize("partial", [False, True])
def test_native_recovery_migration_backfills_and_replays_partial_schema(
    monkeypatch, partial
):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE bot (id VARCHAR PRIMARY KEY,name VARCHAR,dynamic_position_sizing BOOLEAN NOT NULL,margin_short_reversal BOOLEAN NOT NULL,recovery_mode_id VARCHAR)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE recovery_bot_table (id VARCHAR PRIMARY KEY,reversal_path VARCHAR NOT NULL,source_contracts FLOAT NOT NULL,source_loss_fiat FLOAT NOT NULL,stop_loss_pct FLOAT NOT NULL,created_at FLOAT NOT NULL,updated_at FLOAT NOT NULL)"
            )
        )
        connection.execute(text("CREATE TABLE deal (id VARCHAR PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE exchange_order (id VARCHAR PRIMARY KEY)"))
        connection.execute(
            text(
                "INSERT INTO bot VALUES ('source','terminal',false,true,NULL),('sizing','terminal',true,true,NULL),('top','top_gainer_short',false,true,NULL),('off','terminal',false,false,NULL)"
            )
        )
        if partial:
            connection.execute(
                text("ALTER TABLE deal ADD COLUMN conditional_close_order JSON")
            )
            connection.execute(
                text("ALTER TABLE exchange_order ADD COLUMN client_oid VARCHAR")
            )
            connection.execute(
                text("ALTER TABLE recovery_bot_table ADD COLUMN source_bot_id CHAR(32)")
            )
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        migration.upgrade()
        rows: dict[str, str | None] = dict(
            connection.execute(text("SELECT id,recovery_mode_id FROM bot")).all()
        )
        assert rows["source"] is not None
        assert rows["sizing"] is None
        assert rows["top"] is not None
        assert rows["off"] is None
        assert (
            connection.execute(text("SELECT COUNT(*) FROM recovery_bot_table")).scalar()
            == 2
        )
        assert "margin_short_reversal" not in {
            c["name"] for c in inspect(connection).get_columns("bot")
        }
        assert {
            c["name"] for c in inspect(connection).get_columns("exchange_order")
        } >= {"client_oid", "requested_qty", "stop_price"}
        migration.downgrade()
        migration.upgrade()
        assert (
            connection.execute(text("SELECT COUNT(*) FROM recovery_bot_table")).scalar()
            == 2
        )


def test_migration_preserves_pending_trigger_metadata_and_disables_inflight_sizing_recovery(
    monkeypatch,
):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE bot (id VARCHAR PRIMARY KEY,name VARCHAR,dynamic_position_sizing BOOLEAN NOT NULL,margin_short_reversal BOOLEAN NOT NULL,recovery_mode_id VARCHAR,deal_id VARCHAR)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE recovery_bot_table (id VARCHAR PRIMARY KEY,reversal_path VARCHAR NOT NULL,source_contracts FLOAT NOT NULL,source_loss_fiat FLOAT NOT NULL,stop_loss_pct FLOAT NOT NULL,created_at FLOAT NOT NULL,updated_at FLOAT NOT NULL)"
            )
        )
        connection.execute(
            text("CREATE TABLE deal (id VARCHAR PRIMARY KEY, position_size_order JSON)")
        )
        connection.execute(
            text(
                "CREATE TABLE exchange_order (id VARCHAR PRIMARY KEY,status VARCHAR,deal_type VARCHAR,price FLOAT,qty FLOAT)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO deal VALUES ('pending','{\"client_oid\":\"sizing\"}'), ('ordinary','null')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO bot VALUES ('pending','terminal',false,true,NULL,'pending'),('ordinary','terminal',false,true,NULL,'ordinary')"
            )
        )
        connection.execute(
            text("INSERT INTO exchange_order VALUES ('stop','NEW','stop_loss',98,101)")
        )
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        migration.upgrade()
        assert (
            connection.execute(
                text("SELECT recovery_mode_id FROM bot WHERE id='pending'")
            ).scalar()
            is None
        )
        assert (
            connection.execute(
                text("SELECT recovery_mode_id FROM bot WHERE id='ordinary'")
            ).scalar()
            is not None
        )
        row = connection.execute(
            text(
                "SELECT qty,price,requested_qty,stop_price FROM exchange_order WHERE id='stop'"
            )
        ).one()
        assert tuple(row) == (0, 0, 101, 98)
