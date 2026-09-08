from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Employee, Salary
from tests.db_support import database_url_for_tests, engine_options_for_tests, migrate_test_database

CSV_HEADER = (
    "employee_code,first_name,last_name,email,department,country,job_title,band,"
    "hire_date,status,salary_amount,salary_currency,effective_date\n"
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_url = database_url_for_tests(tmp_path, "import.db")
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
        yield test_client, session_local
    app.dependency_overrides.clear()
    engine.dispose()


def auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/auth/register", json={"email": "hr@example.com", "password": "correct-password"})
    token = client.post(
        "/auth/login", json={"email": "hr@example.com", "password": "correct-password"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def csv_row(number: int, **overrides) -> str:
    row = {
        "employee_code": f"IMP-{number:05d}",
        "first_name": "Ada",
        "last_name": f"Person{number}",
        "email": f"person{number}@example.com",
        "department": "Engineering",
        "country": "United States",
        "job_title": "Engineer",
        "band": "L3",
        "hire_date": "2022-01-01",
        "status": "active",
        "salary_amount": "85000.50",
        "salary_currency": "USD",
        "effective_date": "2022-01-01",
    }
    row.update(overrides)
    return ",".join(row[column] for column in CSV_HEADER.strip().split(",")) + "\n"


def upload(client: TestClient, headers: dict[str, str], content: str):
    return client.post(
        "/employees/import",
        headers=headers,
        files={"file": ("employees.csv", BytesIO(content.encode()), "text/csv")},
    )


def employee_count(session_local) -> int:
    with session_local() as session:
        return session.scalar(select(func.count()).select_from(Employee)) or 0


def test_valid_csv_imports_employees_and_initial_salaries(client):
    test_client, session_local = client
    response = upload(test_client, auth_headers(test_client), CSV_HEADER + csv_row(1) + csv_row(2))

    assert response.status_code == 201
    assert response.json() == {
        "rows_processed": 2,
        "rows_imported": 2,
        "rows_rejected": [],
        "error": None,
    }
    with session_local() as session:
        employees = session.scalars(select(Employee).order_by(Employee.employee_code)).all()
        assert len(employees) == 2
        assert all(employee.current_salary_amount == 85000.50 for employee in employees)
        assert all(employee.current_salary_currency == "USD" for employee in employees)
        assert all(employee.current_salary_id is not None for employee in employees)
        assert session.scalar(select(func.count()).select_from(Salary)) == 2


def test_invalid_department_rejects_entire_file_without_writes(client):
    test_client, session_local = client
    response = upload(
        test_client,
        auth_headers(test_client),
        CSV_HEADER + csv_row(1) + csv_row(2, department="Enginering"),
    )

    assert response.status_code == 422
    assert response.json()["rows_imported"] == 0
    assert response.json()["rows_rejected"] == [
        {"row": 3, "message": "department 'Enginering' is not in the canonical list"}
    ]
    assert employee_count(session_local) == 0


def test_existing_email_rejects_file(client):
    test_client, session_local = client
    headers = auth_headers(test_client)
    assert upload(test_client, headers, CSV_HEADER + csv_row(1)).status_code == 201

    response = upload(test_client, headers, CSV_HEADER + csv_row(2, email="person1@example.com"))

    assert response.status_code == 422
    assert response.json()["rows_rejected"] == [
        {"row": 2, "message": "email 'person1@example.com' is already in use"}
    ]
    assert employee_count(session_local) == 1


def test_duplicate_email_in_file_rejects_file(client):
    test_client, session_local = client
    response = upload(
        test_client,
        auth_headers(test_client),
        CSV_HEADER + csv_row(1) + csv_row(2, email="person1@example.com"),
    )

    assert response.status_code == 422
    assert response.json()["rows_rejected"] == [
        {"row": 3, "message": "email 'person1@example.com' is duplicated in this file"}
    ]
    assert employee_count(session_local) == 0


def test_missing_required_column_is_rejected_before_row_processing(client):
    test_client, session_local = client
    content = CSV_HEADER.replace("salary_amount,", "") + csv_row(1).replace("85000.50,", "", 1)

    response = upload(test_client, auth_headers(test_client), content)

    assert response.status_code == 422
    assert response.json()["error"] == "Missing required columns: salary_amount"
    assert response.json()["rows_processed"] == 0
    assert employee_count(session_local) == 0
