from fastapi.testclient import TestClient
from main import app
from pytest import fixture
from tests.fixtures.mock_bot_table import mock_bot_data, mock_bot_data_superusdt


@fixture()
def client() -> TestClient:
    client = TestClient(app)
    return client


mock_id = "cff9e468-87ee-46fa-8678-17af132b8434"
mock_symbol = "ADXUSDC"


def test_get_one_by_id(client: TestClient):
    response = client.get(f"/bot/{mock_id}")

    assert response.status_code == 200
    content = response.json()
    # Check key fields instead of full equality due to UUID serialization
    assert content["data"]["pair"] == mock_bot_data["pair"]
    assert content["data"]["fiat"] == mock_bot_data["fiat"]
    assert content["data"]["fiat_order_size"] == mock_bot_data["fiat_order_size"]
    assert content["data"]["status"] == mock_bot_data["status"]


def test_get_one_by_symbol(client: TestClient):
    """
    Only ADAUSDC is active in the mock data
    """
    response = client.get(f"/bot/symbol/{mock_symbol}")

    assert response.status_code == 200
    content = response.json()
    # Check key fields instead of full equality due to UUID serialization
    assert content["data"]["pair"] == mock_bot_data["pair"]
    assert content["data"]["fiat"] == mock_bot_data["fiat"]
    assert content["data"]["fiat_order_size"] == mock_bot_data["fiat_order_size"]


def test_get_one_by_symbol_not_found(client: TestClient):
    """Test getting a bot by a symbol that doesn't exist"""
    non_existent_symbol = "NONEXISTENTUSDC"
    response = client.get(f"/bot/symbol/{non_existent_symbol}")

    assert response.status_code == 200
    content = response.json()
    assert content["error"] == 1
    assert "not found" in content["message"].lower()


def test_get_bots(client: TestClient):
    response = client.get("/bot")

    assert response.status_code == 200
    content = response.json()
    # Verify response structure
    assert isinstance(content["data"], list)
    assert len(content["data"]) > 0
    # Check first bot has expected fields
    assert "pair" in content["data"][0]
    assert "fiat" in content["data"][0]


def test_create_bot(client: TestClient):
    response = client.post("/bot", json=mock_bot_data_superusdt)

    assert response.status_code == 200
    content = response.json()
    # Check key fields instead of full equality due to UUID serialization
    assert content["data"]["pair"] == mock_bot_data_superusdt["pair"]
    assert content["data"]["fiat"] == mock_bot_data_superusdt["fiat"]
    assert (
        content["data"]["fiat_order_size"] == mock_bot_data_superusdt["fiat_order_size"]
    )


def test_edit_bot(client: TestClient):
    response = client.put(
        "/bot/cff9e468-87ee-46fa-8678-17af132b8434", json=mock_bot_data
    )

    assert response.status_code == 200
    content = response.json()
    # Check key fields instead of full equality due to UUID serialization
    assert content["data"]["pair"] == mock_bot_data["pair"]
    assert content["data"]["fiat"] == mock_bot_data["fiat"]
    assert content["data"]["fiat_order_size"] == mock_bot_data["fiat_order_size"]


def test_delete_bot(client: TestClient):
    # Use dedicated test bot IDs that won't affect other tests
    delete_ids = [
        "00000000-0000-0000-0000-000000000001",  # Test bot for deletion 1
        "00000000-0000-0000-0000-000000000002",  # Test bot for deletion 2
    ]
    # Send as multiple query parameters - FastAPI will parse them as a list
    response = client.delete(f"/bot?id={delete_ids[0]}&id={delete_ids[1]}")

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Sucessfully deleted bot."


def test_activate_by_id(client: TestClient):
    mock_activate_id = "44db75ee-15c2-4a48-a346-4ffdc3ac5506"
    response = client.get(f"/bot/activate/{mock_activate_id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"]["pair"] == "EPICUSDC"
    assert content["data"]["fiat"] == "USDC"
    assert content["data"]["fiat_order_size"] == 15


def test_deactivate(client: TestClient):
    deactivate_id = "ebda4958-837c-4544-bf97-9bf449698152"
    response = client.delete(f"/bot/deactivate/{deactivate_id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"]["pair"] == "ADAUSDC"
    assert content["data"]["fiat"] == "USDC"
    assert content["data"]["fiat_order_size"] == 15


def test_post_bot_errors_str(client: TestClient):
    """
    Test submitting bot errors with a single string
    """
    payload = {"errors": "failed to create bot"}

    response = client.post(f"/bot/errors/{mock_id}", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Errors posted successfully."


def test_post_bot_errors_list(client: TestClient):
    """
    Test submitting bot errors with a list of strings
    """
    payload = {"errors": ["failed to create bot", "failed to create deal"]}

    response = client.post(f"/bot/errors/{mock_id}", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Errors posted successfully."
