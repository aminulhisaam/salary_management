from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from alembic.config import Config
from app.config import settings
from app.database import get_db
from app.main import app
from app.security import create_access_token


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'auth.db'}"
    monkeypatch.setattr(settings, "database_url", database_url)

    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def register(client: TestClient, email: str = "hr@example.com"):
    return client.post("/auth/register", json={"email": email, "password": "correct-password"})


def login(
    client: TestClient,
    email: str = "hr@example.com",
    password: str = "correct-password",
):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_register_then_login_returns_access_token(client: TestClient):
    registration = register(client)

    assert registration.status_code == 201
    assert registration.json()["email"] == "hr@example.com"
    assert registration.json()["role"] == "hr_admin"
    assert "hashed_password" not in registration.json()

    authentication = login(client)

    assert authentication.status_code == 200
    assert authentication.json()["token_type"] == "bearer"
    assert authentication.json()["access_token"]


def test_register_rejects_duplicate_email(client: TestClient):
    assert register(client).status_code == 201

    duplicate = register(client)

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "A user with this email already exists"


def test_login_rejects_wrong_password(client: TestClient):
    register(client)

    response = login(client, password="wrong-password")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_rejects_unknown_email_without_distinguishing_it(client: TestClient):
    response = login(client, email="missing@example.com")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_me_rejects_a_missing_token(client: TestClient):
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_an_invalid_token(client: TestClient):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"})

    assert response.status_code == 401


def test_me_returns_the_authenticated_user(client: TestClient):
    registered_user = register(client).json()
    token = login(client).json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "id": registered_user["id"],
        "email": "hr@example.com",
        "role": "hr_admin",
        "created_at": registered_user["created_at"],
    }


def test_me_rejects_an_expired_token(client: TestClient):
    user_id = register(client).json()["id"]
    expired_token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})

    assert response.status_code == 401
