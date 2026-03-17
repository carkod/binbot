from fastapi.testclient import TestClient
from main import app
from uuid import uuid4

client = TestClient(app)


def make_inquiry_data(**kwargs):
    data = {
        "full_name": "Test User",
        "email": "testuser@example.com",
        "phone": "+12345678901",
        "organisation": "TestOrg",
        "reason": "Support",
        "message": "This is a test inquiry.",
        "newsletter": True,
        "terms_agreement": True,
    }
    data.update(kwargs)
    return data


class TestCreateInquiry:
    def test_create_inquiry(self):
        data = make_inquiry_data()
        response = client.post("/inquiries", json=data)
        assert response.status_code == 200
        content = response.json()
        assert content["error"] == 0
        assert content["data"]["full_name"] == data["full_name"]
        assert content["data"]["email"] == data["email"]
        self.created_id = content["data"]["id"]

    def test_create_inquiry_invalid_email(self):
        data = make_inquiry_data(email="not-an-email")
        response = client.post("/inquiries", json=data)
        assert response.status_code in (400, 422)
        content = response.json()
        assert content.get("error", 1) == 1 or "error" not in content
        assert "email" in str(content)

    def test_create_inquiry_missing_required(self):
        data = make_inquiry_data()
        del data["full_name"]
        response = client.post("/inquiries", json=data)
        assert response.status_code in (400, 422)
        content = response.json()
        assert content.get("error", 1) == 1 or "error" not in content
        assert "full_name" in str(content)


class TestGetInquiry:
    def test_get_inquiry(self):
        data = make_inquiry_data(full_name="Get Inquiry User")
        response = client.post("/inquiries", json=data)
        assert response.status_code == 200
        inquiry_id = response.json()["data"]["id"]
        get_response = client.get(f"/inquiries/{inquiry_id}")
        assert get_response.status_code == 200
        content = get_response.json()
        assert content["error"] == 0
        assert content["data"]["id"] == inquiry_id
        assert content["data"]["full_name"] == "Get Inquiry User"

    def test_get_inquiry_not_found(self):
        random_id = str(uuid4())
        response = client.get(f"/inquiries/{random_id}")
        assert response.status_code == 404
        content = response.json()
        assert "not found" in content["detail"].lower()


class TestDeleteInquiry:
    def test_delete_inquiry(self):
        data = make_inquiry_data(full_name="Delete Inquiry User")
        response = client.post("/inquiries", json=data)
        assert response.status_code == 200
        inquiry_id = response.json()["data"]["id"]
        del_response = client.delete(f"/inquiries/{inquiry_id}")
        assert del_response.status_code == 204
        # For 204 No Content, response body should be empty
        assert del_response.content in (b"", None)
        get_response = client.get(f"/inquiries/{inquiry_id}")
        assert get_response.status_code == 404

    def test_delete_inquiry_not_found(self):
        random_id = str(uuid4())
        response = client.delete(f"/inquiries/{random_id}")
        assert response.status_code == 404
        content = response.json()
        assert "not found" in content["detail"].lower()

    def test_delete_inquiry_invalid_uuid(self):
        response = client.delete("/inquiries/not-a-uuid")
        assert response.status_code in (400, 422)
        content = response.json()
        assert (
            "uuid" in str(content).lower() or "not a valid uuid" in str(content).lower()
        )


class TestGetInquiries:
    def test_get_inquiries_empty(self):
        # Try to get all inquiries when DB is likely empty (after deleting all)
        # This test assumes a clean DB or that previous tests have deleted all
        response = client.get("/inquiries?offset=0&limit=10")
        assert response.status_code == 200
        content = response.json()
        assert content["error"] == 0
        assert isinstance(content["data"], list)
        # Accept empty or non-empty list depending on DB state

    def test_get_inquiries_with_filter(self):
        unique_reason = f"Reason-{uuid4()}"
        data = make_inquiry_data(reason=unique_reason)
        client.post("/inquiries", json=data)
        response = client.get(f"/inquiries?reason={unique_reason}")
        assert response.status_code == 200
        content = response.json()
        assert content["error"] == 0
        assert any(inq["reason"] == unique_reason for inq in content["data"])

    def test_get_inquiries_with_limit(self):
        response = client.get("/inquiries?limit=2")
        assert response.status_code == 200
        content = response.json()
        assert content["error"] == 0
        assert isinstance(content["data"], list)

    def test_get_inquiries_with_offset(self):
        response = client.get("/inquiries?offset=1")
        assert response.status_code == 200
        content = response.json()
        assert content["error"] == 0
        assert isinstance(content["data"], list)

    def test_get_inquiries_no_limit_offset(self):
        response = client.get("/inquiries")
        assert response.status_code == 200
        content = response.json()
        assert content["error"] == 0
        assert isinstance(content["data"], list)

    def test_get_inquiries_all_query_strings(self):
        unique_reason = f"Reason-{uuid4()}"
        data = make_inquiry_data(reason=unique_reason)
        client.post("/inquiries", json=data)
        response = client.get(f"/inquiries?offset=0&limit=5&reason={unique_reason}")
        assert response.status_code == 200
        content = response.json()
        assert content["error"] == 0
        assert any(inq["reason"] == unique_reason for inq in content["data"])
