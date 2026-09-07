from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_code: Mapped[str] = mapped_column(Text, unique=True)
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text, unique=True)
    department: Mapped[str] = mapped_column(Text, index=True)
    country: Mapped[str] = mapped_column(Text, index=True)
    job_title: Mapped[str] = mapped_column(Text)
    band: Mapped[str] = mapped_column(Text, index=True)
    hire_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text)
    current_salary_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    current_salary_currency: Mapped[str | None] = mapped_column(Text)
    current_salary_id: Mapped[int | None] = mapped_column(ForeignKey("salaries.id"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
