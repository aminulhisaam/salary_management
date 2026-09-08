from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, event, inspect, text

from app.config import settings
from app.models import Employee, Salary, User
from tests.db_support import database_url_for_tests, engine_options_for_tests, migrate_test_database


def test_initial_migration_creates_schema_and_supports_salary_references(tmp_path, monkeypatch):
    database_url = database_url_for_tests(tmp_path, "salary_management.db")
    monkeypatch.setattr(settings, "database_url", database_url)
    migrate_test_database(database_url)

    engine = create_engine(database_url, **engine_options_for_tests(database_url))

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    now = datetime(2026, 9, 7)
    with engine.begin() as connection:
        connection.execute(
            User.__table__.insert().values(
                email="hr@example.com",
                hashed_password="hashed-password",
                role="hr_admin",
                created_at=now,
            )
        )
        connection.execute(
            Employee.__table__.insert().values(
                employee_code="EMP-00001",
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.com",
                department="Engineering",
                country="India",
                job_title="Engineer",
                band="L5",
                hire_date=date(2020, 1, 1),
                status="active",
                current_salary_amount=Decimal("100000.00"),
                current_salary_currency="INR",
                current_salary_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        salary_result = connection.execute(
            Salary.__table__.insert().values(
                employee_id=1,
                amount=Decimal("100000.00"),
                currency="INR",
                effective_date=date(2020, 1, 1),
                reason="hire",
                created_by=1,
                created_at=now,
            )
        )
        connection.execute(
            Employee.__table__.update()
            .where(Employee.id == 1)
            .values(current_salary_id=salary_result.inserted_primary_key[0])
        )

        if database_url.startswith("sqlite"):
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []

    inspector = inspect(engine)
    foreign_keys = inspector.get_foreign_keys("salaries")
    assert {foreign_key["referred_table"] for foreign_key in foreign_keys} == {
        "employees",
        "users",
    }
    employee_foreign_keys = inspector.get_foreign_keys("employees")
    assert "salaries" in {foreign_key["referred_table"] for foreign_key in employee_foreign_keys}

    indexes = inspector.get_indexes("salaries")
    composite_index = next(
        index for index in indexes if index["name"] == "ix_salaries_employee_id_effective_date"
    )
    assert composite_index["column_names"] == ["employee_id", "effective_date"]

    if database_url.startswith("sqlite"):
        with engine.connect() as connection:
            index_xinfo = (
                connection.execute(text("PRAGMA index_xinfo('ix_salaries_employee_id_effective_date')"))
                .mappings()
                .all()
            )
        assert [row["desc"] for row in index_xinfo if row["key"] == 1] == [0, 1]
