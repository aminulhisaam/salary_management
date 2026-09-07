from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Date, ForeignKey, Index, Integer, Numeric, Text, desc
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Salary(Base):
    __tablename__ = "salaries"
    __table_args__ = (
        Index(
            "ix_salaries_employee_id_effective_date",
            "employee_id",
            desc("effective_date"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(Text)
    effective_date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
