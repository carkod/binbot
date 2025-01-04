import os
from sqlalchemy import create_engine
from sqlmodel import Session
from time import time

# This allows testing/Github action dummy envs
db_url = f'postgresql://{os.getenv("POSTGRES_USER", "postgres")}:{os.getenv("POSTGRES_PASSWORD", "postgres")}@{os.getenv("POSTGRES_HOSTNAME", "localhost")}:{os.getenv("POSTGRES_PORT", 5432)}/{os.getenv("POSTGRES_DB", "postgres")}'
engine = create_engine(url=db_url, pool_size=20, max_overflow=0)


def get_session():
    with Session(engine) as session:
        yield session


def independent_session() -> Session:
    """
    Used outside of FastAPI context
    """
    return Session(engine)


def timestamp() -> float:
    return int(round(time() * 1000))
