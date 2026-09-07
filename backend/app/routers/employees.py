import csv
import io
import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession, get_current_user
from app.models import Employee, Salary, User
from app.reference_data import BANDS, COUNTRY_CURRENCIES, DEPARTMENTS, STATUSES
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeImportResponse,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
    ImportRowError,
)
from app.schemas.salary import EmployeeDetailResponse, SalaryCreate, SalaryResponse
from app.services.salaries import add_salary_record

router = APIRouter(prefix="/employees", tags=["employees"])
CurrentUser = Annotated[User, Depends(get_current_user)]
CSV_REQUIRED_COLUMNS = {
    "employee_code",
    "first_name",
    "last_name",
    "email",
    "department",
    "country",
    "job_title",
    "band",
    "hire_date",
    "salary_amount",
    "salary_currency",
    "effective_date",
}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_employee_reference_data(department: str, country: str, band: str) -> None:
    if department not in DEPARTMENTS:
        raise HTTPException(status_code=422, detail="Invalid department")
    if country not in COUNTRY_CURRENCIES:
        raise HTTPException(status_code=422, detail="Invalid country")
    if band not in BANDS:
        raise HTTPException(status_code=422, detail="Invalid band")


def get_employee_or_404(employee_id: int, db: DbSession) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


def import_error_response(
    *,
    rows_processed: int,
    row_errors: list[ImportRowError] | None = None,
    error: str | None = None,
) -> JSONResponse:
    response = EmployeeImportResponse(
        rows_processed=rows_processed,
        rows_imported=0,
        rows_rejected=row_errors or [],
        error=error,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=response.model_dump()
    )


def parse_import_row(
    row: dict[str, str], row_number: int
) -> tuple[dict | None, list[ImportRowError]]:
    errors: list[ImportRowError] = []
    values = {key: (value or "").strip() for key, value in row.items()}
    for column in CSV_REQUIRED_COLUMNS:
        if not values.get(column):
            errors.append(ImportRowError(row=row_number, message=f"{column} is required"))

    department = values.get("department", "")
    country = values.get("country", "")
    band = values.get("band", "")
    status_value = values.get("status") or "active"
    if department and department not in DEPARTMENTS:
        errors.append(
            ImportRowError(
                row=row_number, message=f"department '{department}' is not in the canonical list"
            )
        )
    if country and country not in COUNTRY_CURRENCIES:
        errors.append(
            ImportRowError(
                row=row_number, message=f"country '{country}' is not in the canonical list"
            )
        )
    if band and band not in BANDS:
        errors.append(
            ImportRowError(row=row_number, message=f"band '{band}' is not in the canonical list")
        )
    if status_value not in STATUSES:
        errors.append(
            ImportRowError(row=row_number, message="status must be 'active' or 'inactive'")
        )
    if values.get("email") and not EMAIL_PATTERN.fullmatch(values["email"]):
        errors.append(
            ImportRowError(row=row_number, message=f"email '{values['email']}' is invalid")
        )

    parsed_dates: dict[str, date] = {}
    for column in ("hire_date", "effective_date"):
        if values.get(column):
            try:
                parsed_dates[column] = date.fromisoformat(values[column])
            except ValueError:
                errors.append(
                    ImportRowError(row=row_number, message=f"{column} must use YYYY-MM-DD")
                )

    amount: Decimal | None = None
    if values.get("salary_amount"):
        try:
            amount = Decimal(values["salary_amount"])
            if not amount.is_finite() or amount <= 0:
                raise InvalidOperation
            decimal_places = max(0, -amount.as_tuple().exponent)
            digits = len(amount.as_tuple().digits)
            if decimal_places > 2 or digits > 12:
                raise InvalidOperation
        except InvalidOperation:
            errors.append(
                ImportRowError(
                    row=row_number, message="salary_amount must be a positive DECIMAL(12,2) value"
                )
            )

    currency = values.get("salary_currency", "").upper()
    if country in COUNTRY_CURRENCIES and currency and currency != COUNTRY_CURRENCIES[country]:
        errors.append(
            ImportRowError(
                row=row_number,
                message=f"salary_currency must be {COUNTRY_CURRENCIES[country]} for {country}",
            )
        )
    if errors:
        return None, errors
    return {
        "employee_code": values["employee_code"],
        "first_name": values["first_name"],
        "last_name": values["last_name"],
        "email": values["email"],
        "department": department,
        "country": country,
        "job_title": values["job_title"],
        "band": band,
        "hire_date": parsed_dates["hire_date"],
        "status": status_value,
        "salary_amount": amount,
        "salary_currency": currency,
        "effective_date": parsed_dates["effective_date"],
    }, []


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    db: DbSession,
    _: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: str | None = None,
    department: str | None = None,
    country: str | None = None,
    band: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> EmployeeListResponse:
    filters = []
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Employee.first_name.ilike(pattern),
                Employee.last_name.ilike(pattern),
                Employee.email.ilike(pattern),
            )
        )
    if department:
        filters.append(Employee.department == department)
    if country:
        filters.append(Employee.country == country)
    if band:
        filters.append(Employee.band == band)
    if status_filter:
        filters.append(Employee.status == status_filter)

    total = db.scalar(select(func.count()).select_from(Employee).where(*filters)) or 0
    employees = db.scalars(
        select(Employee).where(*filters).order_by(Employee.id).offset(offset).limit(limit)
    ).all()
    return EmployeeListResponse(items=employees, total=total, limit=limit, offset=offset)


@router.post("/import", response_model=EmployeeImportResponse, status_code=status.HTTP_201_CREATED)
async def import_employees(
    db: DbSession,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File(...)],
) -> EmployeeImportResponse | JSONResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        return import_error_response(rows_processed=0, error="Upload a CSV file")
    try:
        content = (await file.read()).decode("utf-8-sig")
    except UnicodeDecodeError:
        return import_error_response(rows_processed=0, error="CSV must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(content))
    fieldnames = set(reader.fieldnames or [])
    missing_columns = sorted(CSV_REQUIRED_COLUMNS - fieldnames)
    if missing_columns:
        return import_error_response(
            rows_processed=0,
            error=f"Missing required columns: {', '.join(missing_columns)}",
        )

    parsed_rows: list[dict] = []
    row_errors: list[ImportRowError] = []
    seen_emails: set[str] = set()
    seen_codes: set[str] = set()
    rows_processed = 0
    for row_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        rows_processed += 1
        parsed, errors = parse_import_row(row, row_number)
        row_errors.extend(errors)
        if parsed is None:
            continue
        parsed["row_number"] = row_number
        email_key = parsed["email"].lower()
        if email_key in seen_emails:
            row_errors.append(
                ImportRowError(
                    row=row_number, message=f"email '{parsed['email']}' is duplicated in this file"
                )
            )
        seen_emails.add(email_key)
        if parsed["employee_code"] in seen_codes:
            row_errors.append(
                ImportRowError(
                    row=row_number,
                    message=f"employee_code '{parsed['employee_code']}' is duplicated in this file",
                )
            )
        seen_codes.add(parsed["employee_code"])
        parsed_rows.append(parsed)

    existing_emails = set(
        db.scalars(
            select(Employee.email).where(Employee.email.in_([row["email"] for row in parsed_rows]))
        ).all()
    )
    existing_codes = set(
        db.scalars(
            select(Employee.employee_code).where(
                Employee.employee_code.in_([row["employee_code"] for row in parsed_rows])
            )
        ).all()
    )
    for parsed in parsed_rows:
        row_number = parsed["row_number"]
        if parsed["email"] in existing_emails:
            row_errors.append(
                ImportRowError(
                    row=row_number, message=f"email '{parsed['email']}' is already in use"
                )
            )
        if parsed["employee_code"] in existing_codes:
            row_errors.append(
                ImportRowError(
                    row=row_number,
                    message=f"employee_code '{parsed['employee_code']}' is already in use",
                )
            )
    if row_errors:
        return import_error_response(rows_processed=rows_processed, row_errors=row_errors)

    now = datetime.now(UTC)
    try:
        for row in parsed_rows:
            employee = Employee(
                employee_code=row["employee_code"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                email=row["email"],
                department=row["department"],
                country=row["country"],
                job_title=row["job_title"],
                band=row["band"],
                hire_date=row["hire_date"],
                status=row["status"],
                current_salary_amount=None,
                current_salary_currency=None,
                current_salary_id=None,
                created_at=now,
                updated_at=now,
            )
            db.add(employee)
            db.flush()
            add_salary_record(
                db,
                employee,
                amount=row["salary_amount"],
                currency=row["salary_currency"],
                effective_date=row["effective_date"],
                reason="hire",
                created_by=current_user.id,
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        return import_error_response(
            rows_processed=rows_processed,
            error="Import could not be committed; no rows were written",
        )
    return EmployeeImportResponse(
        rows_processed=rows_processed, rows_imported=len(parsed_rows), rows_rejected=[]
    )


@router.get("/{employee_id}", response_model=EmployeeDetailResponse)
def get_employee(employee_id: int, db: DbSession, _: CurrentUser) -> EmployeeDetailResponse:
    employee = get_employee_or_404(employee_id, db)
    salary_history = db.scalars(
        select(Salary)
        .where(Salary.employee_id == employee.id)
        .order_by(Salary.effective_date.desc(), Salary.id.desc())
    ).all()
    return EmployeeDetailResponse(employee=employee, salary_history=salary_history)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: DbSession, _: CurrentUser) -> Employee:
    validate_employee_reference_data(payload.department, payload.country, payload.band)
    now = datetime.now(UTC)
    employee = Employee(
        **payload.model_dump(),
        current_salary_amount=None,
        current_salary_currency=None,
        current_salary_id=None,
        created_at=now,
        updated_at=now,
    )
    db.add(employee)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An employee with this email already exists"
        ) from None
    db.refresh(employee)
    return employee


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int, payload: EmployeeUpdate, db: DbSession, _: CurrentUser
) -> Employee:
    employee = get_employee_or_404(employee_id, db)
    changes = payload.model_dump(exclude_unset=True)
    department = changes.get("department", employee.department)
    country = changes.get("country", employee.country)
    band = changes.get("band", employee.band)
    validate_employee_reference_data(department, country, band)

    for field, value in changes.items():
        setattr(employee, field, value)
    employee.updated_at = datetime.now(UTC)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An employee with this email already exists"
        ) from None
    db.refresh(employee)
    return employee


@router.post(
    "/{employee_id}/salaries",
    response_model=SalaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_salary(
    employee_id: int, payload: SalaryCreate, db: DbSession, current_user: CurrentUser
) -> Salary:
    employee = get_employee_or_404(employee_id, db)
    if payload.currency != COUNTRY_CURRENCIES[employee.country]:
        raise HTTPException(status_code=422, detail="Currency must match the employee's country")

    salary = add_salary_record(db, employee, **payload.model_dump(), created_by=current_user.id)

    db.commit()
    db.refresh(salary)
    return salary


@router.get("/{employee_id}/salaries", response_model=list[SalaryResponse])
def list_salary_history(employee_id: int, db: DbSession, _: CurrentUser) -> list[Salary]:
    employee = get_employee_or_404(employee_id, db)
    return db.scalars(
        select(Salary)
        .where(Salary.employee_id == employee.id)
        .order_by(Salary.effective_date.desc(), Salary.id.desc())
    ).all()
