import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from tests.db_support import database_url_for_tests, engine_options_for_tests, migrate_test_database


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_url = database_url_for_tests(tmp_path, "salaries.db")
    monkeypatch.setattr("app.config.settings.database_url", database_url)
    migrate_test_database(database_url)
    engine = create_engine(database_url, **engine_options_for_tests(database_url))
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


def authenticated_employee(client: TestClient) -> tuple[dict[str, str], dict]:
    client.post(
        "/auth/register",
        json={"email": "hr@example.com", "password": "correct-password"},
    )
    token = client.post(
        "/auth/login", json={"email": "hr@example.com", "password": "correct-password"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    employee = client.post(
        "/employees",
        headers=headers,
        json={
            "employee_code": "EMP-00001",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "department": "Engineering",
            "country": "United States",
            "job_title": "Engineer",
            "band": "L4",
            "hire_date": "2020-01-01",
        },
    ).json()
    return headers, employee


def add_salary(
    client: TestClient,
    headers: dict[str, str],
    employee_id: int,
    amount: str,
    date: str,
):
    return client.post(
        f"/employees/{employee_id}/salaries",
        headers=headers,
        json={
            "amount": amount,
            "currency": "USD",
            "effective_date": date,
            "reason": "adjustment",
        },
    )


def test_salary_insert_preserves_history_and_updates_only_when_latest(
    client: TestClient,
):
    headers, employee = authenticated_employee(client)
    original = add_salary(client, headers, employee["id"], "85000.50", "2023-01-01")
    latest = add_salary(client, headers, employee["id"], "95000.50", "2024-01-01")
    backfill = add_salary(client, headers, employee["id"], "80000.50", "2022-01-01")

    assert original.status_code == 201
    assert latest.status_code == 201
    assert backfill.status_code == 201
    history = client.get(f"/employees/{employee['id']}/salaries", headers=headers).json()
    assert len(history) == 3
    assert [item["amount"] for item in history] == ["95000.50", "85000.50", "80000.50"]

    detail = client.get(f"/employees/{employee['id']}", headers=headers).json()["employee"]
    assert detail["current_salary_amount"] == "95000.50"
    assert detail["current_salary_currency"] == "USD"
    assert detail["current_salary_id"] == latest.json()["id"]


def test_salary_requires_existing_employee_and_matching_country_currency(
    client: TestClient,
):
    headers, employee = authenticated_employee(client)
    assert add_salary(client, headers, 99999, "85000.50", "2024-01-01").status_code == 404
    response = client.post(
        f"/employees/{employee['id']}/salaries",
        headers=headers,
        json={
            "amount": "85000.50",
            "currency": "INR",
            "effective_date": "2024-01-01",
            "reason": "adjustment",
        },
    )
    assert response.status_code == 422
