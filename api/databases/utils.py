import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool
from sqlmodel import Session
from contextlib import contextmanager


# Load env vars for Alembic
load_dotenv()


# This allows testing/Github action dummy envs
db_url = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOSTNAME', 'localhost')}:{os.getenv('POSTGRES_PORT', 5432)}/{os.getenv('POSTGRES_DB', 'postgres')}"
engine = create_engine(url=db_url, poolclass=pool.NullPool)


def get_session():
    with Session(engine).no_autoflush as session:
        yield session


def independent_session() -> Session:
    """
    Used outside of FastAPI context
    """
    return Session(engine)


@contextmanager
def get_db_session():
    """
    Yields a fresh session. Commits on success, rolls back on exception, always closes.
    Uses your existing independent_session() factory so this integrates with your config.
    """
    session = independent_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
