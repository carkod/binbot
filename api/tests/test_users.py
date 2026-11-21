from contextlib import contextmanager
from uuid import uuid4
from urllib.parse import quote
from unittest.mock import patch

import pytest
from pybinbot import UserRoles
from api.databases.crud.user_crud import UserTableCrud
from api.databases.tables.user_table import UserTable
from api.databases.utils import get_session
from api.main import app
from api.user.models.user import UserDetails, UserTokenData
from api.user.services.auth import decode_access_token, get_current_user
from fastapi.testclient import TestClient
from sqlmodel import Session, select


def allow_user_list_access():
    return {"sub": "test@example.com", "role": "admin"}


@pytest.fixture(autouse=True)
def user_route_dependencies(test_engine):
    original_session_override = app.dependency_overrides.get(get_session)
    original_decode_override = app.dependency_overrides.get(decode_access_token)

    @contextmanager
    def get_test_session_manager():
        with Session(test_engine) as session:
            yield session

    def get_test_session():
        with get_test_session_manager() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[decode_access_token] = allow_user_list_access

    yield

    if original_session_override:
        app.dependency_overrides[get_session] = original_session_override
    else:
        app.dependency_overrides.pop(get_session, None)

    if original_decode_override:
        app.dependency_overrides[decode_access_token] = original_decode_override
    else:
        app.dependency_overrides.pop(decode_access_token, None)


def add_user(session: Session, password: str = "secret123") -> UserTable:
    user = UserTable(
        email=f"user-{uuid4()}@example.com",
        password=password,
        role=UserRoles.user,
        full_name="Test User",
        username=f"user-{uuid4()}",
        description="Test description",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_user_details_defaults_match_user_table() -> None:
    details = UserDetails(email="defaults@example.com", password="secret123")
    table = UserTable(email="defaults@example.com", password="secret123")

    assert details.is_active == table.is_active
    assert details.role == table.role
    assert details.full_name == table.full_name
    assert details.username == table.username
    assert details.description == table.description
    assert type(details.created_at) is type(table.created_at)
    assert type(details.updated_at) is type(table.updated_at)


def test_get_users_does_not_return_password(client: TestClient, test_engine) -> None:
    with Session(test_engine) as session:
        user = add_user(session)

    response = client.get("/user")

    assert response.status_code == 200
    assert user.password not in response.text
    for item in response.json()["data"]:
        assert "password" not in item


def test_get_one_user_does_not_return_password(client: TestClient, test_engine) -> None:
    with Session(test_engine) as session:
        user = add_user(session)

    response = client.get(f"/user/{quote(user.email, safe='')}")

    assert response.status_code == 200
    assert user.password not in response.text
    assert "password" not in response.json()["data"]


def test_edit_user_preserves_password_when_omitted(
    client: TestClient, test_engine
) -> None:
    with Session(test_engine) as session:
        user = add_user(session)
        original_password = user.password

    response = client.put(
        "/user",
        json={
            "email": user.email,
            "full_name": "Updated User",
        },
    )

    assert response.status_code == 200
    assert "password" not in response.json()["data"]
    with Session(test_engine) as session:
        edited_user = session.exec(
            select(UserTable).where(UserTable.email == user.email)
        ).one()
        assert edited_user.full_name == "Updated User"
        assert edited_user.password == original_password


def test_edit_user_updates_password_when_supplied(
    client: TestClient, test_engine
) -> None:
    with Session(test_engine) as session:
        user = add_user(session)

    response = client.put(
        "/user",
        json={
            "email": user.email,
            "password": "updated123",
        },
    )

    assert response.status_code == 200
    assert "password" not in response.json()["data"]
    with Session(test_engine) as session:
        edited_user = session.exec(
            select(UserTable).where(UserTable.email == user.email)
        ).one()
        assert edited_user.password == "updated123"


def test_user_lookup_by_id_returns_matching_user(test_engine):
    with Session(test_engine) as session:
        user = add_user(session)
        result = UserTableCrud(session).get_one(id=str(user.id))

    assert result.id == user.id
    assert result.email == user.email


def test_inactive_user_cannot_log_in(client, test_engine):
    with Session(test_engine) as session:
        user = add_user(session)
        user.is_active = False
        session.add(user)
        session.commit()
        email = user.email

    with patch("api.databases.crud.user_crud.create_access_token") as create_token:
        response = client.post(
            "/user/login", data={"username": email, "password": "secret123"}
        )

    assert response.json()["error"] == 1
    create_token.assert_not_called()


@pytest.mark.parametrize(
    "role, expected_status", [(UserRoles.user, 403), (UserRoles.admin, 200)]
)
def test_register_user_requires_admin(client, role, expected_status):
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: UserTokenData(
        email="caller@example.com", role=role, expires_in=1732388868477
    )
    try:
        response = client.post(
            "/user/register",
            json={
                "email": f"new-{uuid4()}@example.com",
                "password": "secret123",
                "role": "admin",
            },
        )
    finally:
        if original is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = original

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json()["data"]["role"] == "admin"
