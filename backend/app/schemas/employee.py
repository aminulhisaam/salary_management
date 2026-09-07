from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

EmployeeStatus = Literal["active", "inactive"]


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_code: str
    first_name: str
    last_name: str
    email: str
    department: str
    country: str
    job_title: str
    band: str
    hire_date: date
    status: EmployeeStatus = "active"


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    department: str | None = None
    country: str | None = None
    job_title: str | None = None
    band: str | None = None
    hire_date: date | None = None
    status: EmployeeStatus | None = None


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    department: str
    country: str
    job_title: str
    band: str
    hire_date: date
    status: str
    current_salary_amount: Decimal | None
    current_salary_currency: str | None
    current_salary_id: int | None
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int
    limit: int
    offset: int


class ImportRowError(BaseModel):
    row: int
    message: str


class EmployeeImportResponse(BaseModel):
    rows_processed: int
    rows_imported: int
    rows_rejected: list[ImportRowError]
    error: str | None = None
