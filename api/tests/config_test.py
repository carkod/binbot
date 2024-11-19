from typing import Generator
from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session
from api.database.api_db import get_session
from main import app

session = get_session

@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with session:
        yield session


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
