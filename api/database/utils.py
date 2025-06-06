import os
from sqlalchemy import create_engine, pool
from sqlmodel import Session
from time import time
from typing import Annotated, Any
from pydantic import BeforeValidator
from tools.round_numbers import round_timestamp

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


def timestamp() -> int:
    ts = time() * 1000
    rounded_ts = round_timestamp(ts)
    return rounded_ts


def ensure_float(value: Any) -> float:
    if isinstance(value, str) or isinstance(value, int):
        return float(value)

    return value


Amount = Annotated[
    float,
    BeforeValidator(ensure_float),
]
