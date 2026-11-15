"""Single-owner checkpoints, restart recovery and seven-day retention."""

import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import Connection, Table, delete, select, text
from sqlalchemy.dialects.postgresql import insert

from api.databases.tables.cvd_table import SOURCE, CvdBucketTable, CvdMinuteTable
from api.databases.utils import engine
from streaming.cvd.flow import Bucket, Flow, LATE_SECONDS, Minute

LOCK_ID = 731840217


def acquire_owner(connection: Connection) -> None:
    if not connection.execute(
        text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_ID}
    ).scalar_one():
        raise RuntimeError("Another CVD collector owns this database")
    connection.commit()


def restore(connection: Connection, flow: Flow) -> None:
    bucket_table: Table = getattr(CvdBucketTable, "__table__")
    minute_table: Table = getattr(CvdMinuteTable, "__table__")
    cutoff = flow.started_ns // 60_000_000_000 * 60 - LATE_SECONDS
    with connection.begin():
        for row in connection.execute(
            select(minute_table).where(
                minute_table.c.source == SOURCE, minute_table.c.minute >= cutoff
            )
        ).mappings():
            flow.minutes[row["minute"]] = Minute({}, row["universe"])
        for row in connection.execute(
            select(bucket_table).where(
                bucket_table.c.source == SOURCE, bucket_table.c.minute >= cutoff
            )
        ).mappings():
            flow.last_trade_ns = max(flow.last_trade_ns, row["last_trade_ns"])
            flow.replay_cutoffs[row["symbol"]] = max(
                flow.replay_cutoffs.get(row["symbol"], 0), row["last_trade_ns"]
            )
            state = flow.minutes.get(row["minute"])
            if state is not None:
                # Restart uncertainty is permanent for these minutes.
                state.symbols[row["symbol"]] = Bucket(
                    row["multiplier"],
                    row["buy"],
                    row["sell"],
                    False,
                    row["last_trade_ns"],
                )


def persist(
    connection: Connection, snapshot: tuple[list[dict], list[dict]], now: float
) -> None:
    """Absolute replacement makes retries safe, including ambiguous commit results.

    This is the SAME physical connection holding the session advisory lock. Never
    reconnect/retry an invalidated connection: exit and let a new collector restore.
    """
    if connection.invalidated:
        raise RuntimeError("CVD database owner connection lost")
    with connection.begin():
        for model, rows in zip((CvdBucketTable, CvdMinuteTable), snapshot):
            table: Table = getattr(model, "__table__")
            keys = [c.name for c in table.primary_key]
            for offset in range(0, len(rows), 500):
                statement = insert(table).values(rows[offset : offset + 500])
                connection.execute(
                    statement.on_conflict_do_update(
                        index_elements=keys,
                        set_={
                            c.name: statement.excluded[c.name]
                            for c in table.columns
                            if c.name not in keys
                        },
                    )
                )
            connection.execute(
                delete(table).where(table.c.minute < int(now) // 60 * 60 - 7 * 86400)
            )


@asynccontextmanager
async def owner_connection():
    connection = await asyncio.to_thread(engine.connect)
    try:
        await asyncio.to_thread(acquire_owner, connection)
        yield connection
    finally:
        try:
            await asyncio.to_thread(connection.invalidate)
        finally:
            connection.close()
