from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.employee import EmployeeResponse


class SalaryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(max_digits=12, decimal_places=2, gt=0)
    currency: str
    effective_date: date
    reason: str


class SalaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    amount: Decimal
    currency: str
    effective_date: date
    reason: str
    created_by: int
    created_at: datetime


class EmployeeDetailResponse(BaseModel):
    employee: EmployeeResponse
    salary_history: list[SalaryResponse]
