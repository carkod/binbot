import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from main import app


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# def test_data_init(client: TestClient):
#     client.create_db_and_tables()
#     client.create_dummy_bot()
#     result = client.select_bot("BTCUSDT")

#     assert result.status_code == 200
#     assert result["pair"] == "BTCUSDT"
#     assert result["base_order_size"] == "15"
