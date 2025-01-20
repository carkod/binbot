import os
from sqlalchemy import create_engine, pool
from sqlmodel import Session
from time import time
from typing import Annotated
from pydantic import BeforeValidator

# This allows testing/Github action dummy envs
db_url = f'postgresql://{os.getenv("POSTGRES_USER", "postgres")}:{os.getenv("POSTGRES_PASSWORD", "postgres")}@{os.getenv("POSTGRES_HOSTNAME", "localhost")}:{os.getenv("POSTGRES_PORT", 5432)}/{os.getenv("POSTGRES_DB", "postgres")}'
engine = create_engine(url=db_url, poolclass=pool.NullPool)


def get_session():
    with Session(engine).no_autoflush as session:
        yield session


def independent_session() -> Session:
    """
    Used outside of FastAPI context
    """
    return Session(engine)


def timestamp() -> float:
    return int(round(time() * 1000))


def _prepare_comma_seperated_float(value: str | float | int) -> float:
    if isinstance(value, str) or isinstance(value, int):
        return float(value)

    return value


Amount = Annotated[
    float,
    BeforeValidator(_prepare_comma_seperated_float),
]
