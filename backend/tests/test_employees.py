from datetime import date
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


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'employees.db'}"
    monkeypatch.setattr(settings, "database_url", database_url)
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")

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


def auth_headers(client: TestClient) -> dict[str, str]:
    client.post(
        "/auth/register",
        json={"email": "hr@example.com", "password": "correct-password"},
    )
    token = client.post(
        "/auth/login", json={"email": "hr@example.com", "password": "correct-password"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def employee_payload(number: int, **overrides) -> dict:
    payload = {
        "employee_code": f"EMP-{number:05d}",
        "first_name": "Ada" if number == 1 else f"Person{number}",
        "last_name": "Lovelace",
        "email": f"person{number}@example.com",
        "department": "Engineering",
        "country": "United States",
        "job_title": "Engineer",
        "band": "L3",
        "hire_date": "2022-01-01",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def create_employee(client: TestClient, headers: dict[str, str], number: int, **overrides) -> dict:
    response = client.post(
        "/employees", headers=headers, json=employee_payload(number, **overrides)
    )
    assert response.status_code == 201
    return response.json()


def test_list_supports_pagination_search_filters_and_correct_total(client: TestClient):
    headers = auth_headers(client)
    create_employee(client, headers, 1)
    create_employee(
        client,
        headers,
        2,
        first_name="Grace",
        department="Product",
        country="India",
        band="L5",
        status="inactive",
    )
    create_employee(client, headers, 3, department="Product", country="India", band="L5")

    first_page = client.get("/employees?limit=2&offset=0", headers=headers).json()
    second_page = client.get("/employees?limit=2&offset=2", headers=headers).json()
    assert first_page["total"] == 3
    assert len(first_page["items"]) == 2
    assert len(second_page["items"]) == 1
    assert client.get("/employees?search=lovel", headers=headers).json()["total"] == 3
    assert client.get("/employees?search=grace", headers=headers).json()["total"] == 1
    assert client.get("/employees?department=Product", headers=headers).json()["total"] == 2
    assert client.get("/employees?country=India", headers=headers).json()["total"] == 2
    assert client.get("/employees?band=L5", headers=headers).json()["total"] == 2
    assert client.get("/employees?status=inactive", headers=headers).json()["total"] == 1
    combined = client.get(
        "/employees?department=Product&country=India&band=L5&status=inactive",
        headers=headers,
    ).json()
    assert combined["total"] == 1
    assert combined["items"][0]["first_name"] == "Grace"


def test_detail_returns_employee_and_salary_history_or_404(client: TestClient):
    headers = auth_headers(client)
    employee = create_employee(client, headers, 1)
    salary = client.post(
        f"/employees/{employee['id']}/salaries",
        headers=headers,
        json={
            "amount": "85000.50",
            "currency": "USD",
            "effective_date": "2022-01-01",
            "reason": "hire",
        },
    )
    assert salary.status_code == 201

    detail = client.get(f"/employees/{employee['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["employee"]["id"] == employee["id"]
    assert detail.json()["salary_history"][0]["amount"] == "85000.50"
    assert client.get("/employees/99999", headers=headers).status_code == 404


def test_create_rejects_duplicates_invalid_reference_data_and_salary_fields(
    client: TestClient,
):
    headers = auth_headers(client)
    assert client.post("/employees", headers=headers, json=employee_payload(1)).status_code == 201
    assert (
        client.post(
            "/employees",
            headers=headers,
            json=employee_payload(2, email="person1@example.com"),
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/employees",
            headers=headers,
            json=employee_payload(3, department="Unknown"),
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/employees", headers=headers, json=employee_payload(3, country="Unknown")
        ).status_code
        == 422
    )
    assert (
        client.post("/employees", headers=headers, json=employee_payload(3, band="L99")).status_code
        == 422
    )
    assert (
        client.post(
            "/employees",
            headers=headers,
            json=employee_payload(3, current_salary_amount="99999.99"),
        ).status_code
        == 422
    )


def test_update_changes_profile_and_rejects_salary_fields(client: TestClient):
    headers = auth_headers(client)
    employee = create_employee(client, headers, 1)

    updated = client.patch(
        f"/employees/{employee['id']}",
        headers=headers,
        json={
            "first_name": "Ada Updated",
            "department": "Product",
            "status": "inactive",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["first_name"] == "Ada Updated"
    assert updated.json()["department"] == "Product"
    assert updated.json()["status"] == "inactive"
    assert (
        client.patch(
            f"/employees/{employee['id']}",
            headers=headers,
            json={"current_salary_amount": "12345.67"},
        ).status_code
        == 422
    )


def test_employee_routes_require_authentication(client: TestClient):
    payload = employee_payload(1)
    requests = [
        client.get("/employees"),
        client.get("/employees/1"),
        client.post("/employees", json=payload),
        client.patch("/employees/1", json={"first_name": "Unauthenticated"}),
        client.post(
            "/employees/1/salaries",
            json={
                "amount": "85000.50",
                "currency": "USD",
                "effective_date": date.today().isoformat(),
                "reason": "hire",
            },
        ),
        client.get("/employees/1/salaries"),
    ]
    assert all(response.status_code == 401 for response in requests)
