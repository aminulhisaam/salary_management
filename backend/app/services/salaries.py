from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee, Salary


def add_salary_record(
    db: Session,
    employee: Employee,
    *,
    amount: Decimal,
    currency: str,
    effective_date: date,
    reason: str,
    created_by: int,
) -> Salary:
    """Append a salary and maintain the employee's denormalized current salary."""
    salary = Salary(
        employee_id=employee.id,
        amount=amount,
        currency=currency,
        effective_date=effective_date,
        reason=reason,
        created_by=created_by,
        created_at=datetime.now(UTC),
    )
    db.add(salary)
    db.flush()

    latest_salary = db.scalar(
        select(Salary)
        .where(Salary.employee_id == employee.id)
        .order_by(Salary.effective_date.desc(), Salary.id.desc())
        .limit(1)
    )
    if latest_salary is not None and latest_salary.id == salary.id:
        employee.current_salary_amount = salary.amount
        employee.current_salary_currency = salary.currency
        employee.current_salary_id = salary.id
        employee.updated_at = datetime.now(UTC)
    return salary
