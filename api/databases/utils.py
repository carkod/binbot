import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool
from sqlmodel import Session

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
