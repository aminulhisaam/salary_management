import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from tests.db_support import database_url_for_tests, engine_options_for_tests, migrate_test_database


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_url = database_url_for_tests(tmp_path, "analytics.db")
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


def headers_and_seeded_dataset(client: TestClient) -> dict[str, str]:
    client.post("/auth/register", json={"email": "hr@example.com", "password": "correct-password"})
    token = client.post(
        "/auth/login", json={"email": "hr@example.com", "password": "correct-password"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    employees = [
        ("EMP-00001", "Engineering", "United States", "L3", "active", "100.00", "USD"),
        ("EMP-00002", "Engineering", "United States", "L4", "active", "300.00", "USD"),
        ("EMP-00003", "Engineering", "India", "L3", "active", "1000.00", "INR"),
        ("EMP-00004", "Sales", "United States", "L2", "active", "200.00", "USD"),
        ("EMP-00005", "HR", "United States", "L1", "inactive", "400.00", "USD"),
    ]
    for number, department, country, band, status, amount, currency in employees:
        employee = client.post(
            "/employees",
            headers=headers,
            json={
                "employee_code": number,
                "first_name": number,
                "last_name": "Employee",
                "email": f"{number.lower()}@example.com",
                "department": department,
                "country": country,
                "job_title": "Analyst",
                "band": band,
                "hire_date": "2020-01-01",
                "status": status,
            },
        ).json()
        salary = client.post(
            f"/employees/{employee['id']}/salaries",
            headers=headers,
            json={
                "amount": amount,
                "currency": currency,
                "effective_date": "2020-01-01",
                "reason": "hire",
            },
        )
        assert salary.status_code == 201
    return headers


def test_headcount_excludes_inactive_by_default_and_can_include_them(client: TestClient):
    headers = headers_and_seeded_dataset(client)
    default = client.get("/analytics/headcount", headers=headers).json()
    inclusive = client.get("/analytics/headcount?include_inactive=true", headers=headers).json()

    assert {item["group"]: item["count"] for item in default["by_department"]} == {
        "Engineering": 3,
        "Sales": 1,
    }
    assert {item["group"]: item["count"] for item in inclusive["by_department"]}["HR"] == 1


def test_salary_summary_and_range_keep_currencies_separate(client: TestClient):
    headers = headers_and_seeded_dataset(client)
    summary = client.get("/analytics/salary-summary", headers=headers)
    salary_range = client.get("/analytics/salary-range", headers=headers)

    assert summary.status_code == 200
    engineering = [
        item for item in summary.json()["by_department"] if item["group"] == "Engineering"
    ]
    assert engineering == [
        {"group": "Engineering", "currency": "INR", "average": "1000.00", "median": "1000.00"},
        {"group": "Engineering", "currency": "USD", "average": "200.00", "median": "200.00"},
    ]
    engineering_range = [
        item for item in salary_range.json()["by_department"] if item["group"] == "Engineering"
    ]
    assert engineering_range == [
        {"group": "Engineering", "currency": "INR", "minimum": "1000.00", "maximum": "1000.00"},
        {"group": "Engineering", "currency": "USD", "minimum": "100.00", "maximum": "300.00"},
    ]


def test_band_distribution_supports_filters(client: TestClient):
    headers = headers_and_seeded_dataset(client)
    overall = client.get("/analytics/band-distribution", headers=headers).json()
    engineering = client.get(
        "/analytics/band-distribution?department=Engineering", headers=headers
    ).json()
    india = client.get("/analytics/band-distribution?country=India", headers=headers).json()

    assert {item["band"]: item["count"] for item in overall["bands"]} == {"L2": 1, "L3": 2, "L4": 1}
    assert {item["band"]: item["count"] for item in engineering["bands"]} == {"L3": 2, "L4": 1}
    assert india["bands"] == [{"band": "L3", "count": 1}]


def test_analytics_routes_require_authentication(client: TestClient):
    responses = [
        client.get("/analytics/headcount"),
        client.get("/analytics/salary-summary"),
        client.get("/analytics/band-distribution"),
        client.get("/analytics/salary-range"),
    ]
    assert all(response.status_code == 401 for response in responses)
