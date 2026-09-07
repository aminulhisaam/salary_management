"""Populate a migrated database with deterministic demo data.

The script refuses to overwrite an existing employee dataset unless --force is
given. Force mode clears employees and salaries first, which is appropriate for
the local demo database before application CRUD exists.
"""

import argparse
import random
import sys
import time
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from faker import Faker
from sqlalchemy import create_engine, delete, func, select, update
from sqlalchemy.orm import Session, sessionmaker

BACKEND_PATH = Path(__file__).parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.config import settings  # noqa: E402
from app.models import Employee, Salary, User  # noqa: E402
from app.reference_data import BANDS, COUNTRY_CURRENCIES, DEPARTMENTS, STATUSES  # noqa: E402
from app.security import hash_password  # noqa: E402

EMPLOYEE_COUNT = 10_000
BATCH_SIZE = 500
RANDOM_SEED = 42
REFERENCE_DATE = date(2026, 9, 7)
CREATED_AT = datetime(2026, 9, 7, tzinfo=UTC)
DEMO_USERS = (
    ("hr.admin@acme.example", "demo-admin-42"),
    ("hr.manager@acme.example", "demo-manager-42"),
    ("hr.operations@acme.example", "demo-operations-42"),
)
BAND_WEIGHTS = (14, 22, 24, 18, 12, 7, 3)
BASE_SALARIES = {
    "USD": (48_000, 62_000, 80_000, 105_000, 140_000, 185_000, 240_000),
    "INR": (600_000, 800_000, 1_100_000, 1_500_000, 2_000_000, 2_800_000, 4_000_000),
    "GBP": (34_000, 44_000, 58_000, 75_000, 95_000, 125_000, 165_000),
    "EUR": (38_000, 48_000, 62_000, 80_000, 105_000, 135_000, 175_000),
    "SGD": (48_000, 62_000, 80_000, 105_000, 135_000, 175_000, 225_000),
    "BRL": (55_000, 72_000, 95_000, 125_000, 165_000, 215_000, 280_000),
}


def build_engine(database_url: str):
    options: dict = {}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **options)


def quantize_amount(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def make_salary_amount(currency: str, band: str) -> Decimal:
    base_amount = Decimal(BASE_SALARIES[currency][BANDS.index(band)])
    variation = Decimal(str(random.uniform(0.88, 1.12)))
    return quantize_amount(base_amount * variation)


def salary_event_count(hire_date: date) -> int:
    years_employed = (REFERENCE_DATE - hire_date).days / 365
    if years_employed < 1:
        return 0
    return random.choices((0, 1, 2, 3), weights=(18, 44, 27, 11), k=1)[0]


def create_demo_users(session: Session) -> dict[str, int]:
    user_ids: dict[str, int] = {}
    for email, password in DEMO_USERS:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                role="hr_admin",
                created_at=CREATED_AT,
            )
            session.add(user)
            session.flush()
        else:
            user.hashed_password = hash_password(password)
            user.role = "hr_admin"
        user_ids[email] = user.id
    session.commit()
    return user_ids


def clear_existing_seed_data(session: Session) -> None:
    session.execute(update(Employee).values(current_salary_id=None))
    session.execute(delete(Salary))
    session.execute(delete(Employee))
    session.commit()


def seed_database(force: bool = False) -> int:
    random.seed(RANDOM_SEED)
    Faker.seed(RANDOM_SEED)
    faker = Faker("en_US")
    engine = build_engine(settings.database_url)
    session_local = sessionmaker(bind=engine, autoflush=False)

    try:
        with session_local() as session:
            employee_count_query = select(func.count()).select_from(Employee)
            existing_employee_count = session.scalar(employee_count_query) or 0
            if existing_employee_count:
                if not force:
                    raise RuntimeError(
                        f"Database already contains {existing_employee_count} employees. "
                        "Re-run with --force to replace employee and salary seed data."
                    )
                print(
                    f"Warning: removing {existing_employee_count} employees and their salary "
                    "history "
                    "before re-seeding."
                )
                clear_existing_seed_data(session)

            demo_user_ids = create_demo_users(session)
            created_by = demo_user_ids[DEMO_USERS[0][0]]

            for number in range(1, EMPLOYEE_COUNT + 1):
                first_name = faker.first_name()
                last_name = faker.last_name()
                country = random.choice(tuple(COUNTRY_CURRENCIES))
                currency = COUNTRY_CURRENCIES[country]
                band = random.choices(BANDS, weights=BAND_WEIGHTS, k=1)[0]
                hire_date = REFERENCE_DATE - timedelta(days=random.randint(30, 8 * 365))
                latest_amount = make_salary_amount(currency, band)
                employee = Employee(
                    employee_code=f"EMP-{number:05d}",
                    first_name=first_name,
                    last_name=last_name,
                    email=f"{first_name.lower()}.{last_name.lower()}.{number}@acme.example",
                    department=random.choice(DEPARTMENTS),
                    country=country,
                    job_title=faker.job(),
                    band=band,
                    hire_date=hire_date,
                    status=random.choices(STATUSES, weights=(94, 6), k=1)[0],
                    current_salary_amount=latest_amount,
                    current_salary_currency=currency,
                    current_salary_id=None,
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                )
                session.add(employee)
                session.flush()

                latest_salary = Salary(
                    employee_id=employee.id,
                    amount=latest_amount,
                    currency=currency,
                    effective_date=hire_date,
                    reason="hire",
                    created_by=created_by,
                    created_at=CREATED_AT,
                )
                session.add(latest_salary)
                session.flush()

                event_count = salary_event_count(hire_date)
                event_spacing = (REFERENCE_DATE - hire_date).days // (event_count + 1)
                for event_number in range(event_count):
                    event_date = hire_date + timedelta(
                        days=event_spacing * (event_number + 1)
                    )
                    increase = Decimal(str(random.uniform(1.05, 1.16)))
                    reason = "promotion" if random.random() < 0.35 else "adjustment"
                    latest_amount = quantize_amount(latest_amount * increase)
                    latest_salary = Salary(
                        employee_id=employee.id,
                        amount=latest_amount,
                        currency=currency,
                        effective_date=event_date,
                        reason=reason,
                        created_by=created_by,
                        created_at=CREATED_AT,
                    )
                    session.add(latest_salary)
                    session.flush()

                employee.current_salary_amount = latest_amount
                employee.current_salary_currency = currency
                employee.current_salary_id = latest_salary.id

                if number % BATCH_SIZE == 0:
                    session.commit()
                    print(f"Seeded {number:,} employees")

            session.commit()
    finally:
        engine.dispose()

    return EMPLOYEE_COUNT


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the salary management database.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing employees and salaries before seeding.",
    )
    args = parser.parse_args()
    started_at = time.perf_counter()

    try:
        employee_count = seed_database(force=args.force)
    except RuntimeError as error:
        print(error)
        raise SystemExit(1) from error

    elapsed_seconds = time.perf_counter() - started_at
    print(f"Seeded {employee_count:,} employees in {elapsed_seconds:.2f} seconds.")
    print("Demo HR users:")
    for email, password in DEMO_USERS:
        print(f"  {email} / {password}")


if __name__ == "__main__":
    main()
