import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import object_session
from sqlmodel import Session
from contextlib import contextmanager
from collections.abc import Generator
from typing import Any


# Load env vars for Alembic
load_dotenv()


# This allows testing/Github action dummy envs
db_url = f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOSTNAME', 'localhost')}:{os.getenv('POSTGRES_PORT', 5432)}/{os.getenv('POSTGRES_DB', 'postgres')}"
engine = create_engine(
    url=db_url,
    pool_size=int(os.getenv("POSTGRES_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("POSTGRES_MAX_OVERFLOW", "5")),
    pool_timeout=int(os.getenv("POSTGRES_POOL_TIMEOUT", "30")),
    pool_recycle=int(os.getenv("POSTGRES_POOL_RECYCLE", "1800")),
    pool_pre_ping=True,
)


def get_session():
    with Session(engine) as session:
        with session.no_autoflush:
            yield session


def independent_session() -> Session:
    """
    Used outside of FastAPI context
    """
    return Session(engine)


@contextmanager
def get_db_session(session: Session | None = None) -> Generator[Session, None, None]:
    """
    Yields a session for CRUD code.

    If a session is passed in, the caller owns commit/rollback/close.
    Otherwise this creates a fresh session, commits on success, rolls back on
    exception, and always closes.
    """
    if session is not None:
        yield session
        return

    session = independent_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def detach_bot_graph(session: Session, bot: Any) -> None:
    """
    Detach a bot with its eagerly loaded deal and orders from a session.
    """
    deal = bot.deal
    orders = list(bot.orders)

    if deal is not None and object_session(deal) is session:
        session.expunge(deal)

    for order in orders:
        if object_session(order) is session:
            session.expunge(order)

    if object_session(bot) is session:
        session.expunge(bot)
