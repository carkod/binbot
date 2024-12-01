from sqlmodel import Session
from database.api_db import engine


def get_session():
    with Session(engine) as session:
        yield session

def independent_session() -> Session:
    """
    Used outside of FastAPI context
    """
    return Session(engine)
