from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import Integer, Numeric, cast, func, or_, select

from app.dependencies import DbSession, get_current_user
from app.models import Employee, User
from app.schemas.analytics import (
    BandDistributionResponse,
    HeadcountResponse,
    SalaryRangeResponse,
    SalarySummaryResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])
CurrentUser = Annotated[User, Depends(get_current_user)]


def active_employee_filter(include_inactive: bool) -> list:
    return [] if include_inactive else [Employee.status == "active"]


def salary_summary(db: DbSession, group_column) -> list[dict]:
    filters = [Employee.status == "active", Employee.current_salary_amount.is_not(None)]
    ranked = (
        select(
            group_column.label("group"),
            Employee.current_salary_currency.label("currency"),
            Employee.current_salary_amount.label("amount"),
            func.row_number()
            .over(
                partition_by=(group_column, Employee.current_salary_currency),
                order_by=Employee.current_salary_amount,
            )
            .label("row_number"),
            func.count()
            .over(partition_by=(group_column, Employee.current_salary_currency))
            .label("group_count"),
        )
        .where(*filters)
        .subquery()
    )
    lower_middle = cast((ranked.c.group_count + 1) // 2, Integer)
    upper_middle = cast((ranked.c.group_count + 2) // 2, Integer)
    statement = (
        select(
            ranked.c.group,
            ranked.c.currency,
            cast(func.avg(ranked.c.amount), Numeric(12, 2)).label("average"),
            cast(
                func.avg(ranked.c.amount).filter(
                    or_(ranked.c.row_number == lower_middle, ranked.c.row_number == upper_middle)
                ),
                Numeric(12, 2),
            ).label("median"),
        )
        .group_by(ranked.c.group, ranked.c.currency)
        .order_by(ranked.c.group, ranked.c.currency)
    )
    return [dict(row._mapping) for row in db.execute(statement)]


def salary_ranges(db: DbSession, group_column) -> list[dict]:
    statement = (
        select(
            group_column.label("group"),
            Employee.current_salary_currency.label("currency"),
            func.min(Employee.current_salary_amount).label("minimum"),
            func.max(Employee.current_salary_amount).label("maximum"),
        )
        .where(Employee.status == "active", Employee.current_salary_amount.is_not(None))
        .group_by(group_column, Employee.current_salary_currency)
        .order_by(group_column, Employee.current_salary_currency)
    )
    return [dict(row._mapping) for row in db.execute(statement)]


@router.get("/headcount", response_model=HeadcountResponse)
def get_headcount(
    db: DbSession, _: CurrentUser, include_inactive: bool = False
) -> HeadcountResponse:
    filters = active_employee_filter(include_inactive)
    return HeadcountResponse(
        by_department=[
            dict(row._mapping)
            for row in db.execute(
                select(Employee.department.label("group"), func.count(Employee.id).label("count"))
                .where(*filters)
                .group_by(Employee.department)
                .order_by(Employee.department)
            )
        ],
        by_country=[
            dict(row._mapping)
            for row in db.execute(
                select(Employee.country.label("group"), func.count(Employee.id).label("count"))
                .where(*filters)
                .group_by(Employee.country)
                .order_by(Employee.country)
            )
        ],
    )


@router.get("/salary-summary", response_model=SalarySummaryResponse)
def get_salary_summary(db: DbSession, _: CurrentUser) -> SalarySummaryResponse:
    return SalarySummaryResponse(
        by_department=salary_summary(db, Employee.department),
        by_country=salary_summary(db, Employee.country),
    )


@router.get("/band-distribution", response_model=BandDistributionResponse)
def get_band_distribution(
    db: DbSession,
    _: CurrentUser,
    department: str | None = None,
    country: str | None = None,
) -> BandDistributionResponse:
    filters = [Employee.status == "active"]
    if department:
        filters.append(Employee.department == department)
    if country:
        filters.append(Employee.country == country)
    statement = (
        select(Employee.band, func.count(Employee.id).label("count"))
        .where(*filters)
        .group_by(Employee.band)
        .order_by(Employee.band)
    )
    return BandDistributionResponse(
        bands=[{"band": row.band, "count": row.count} for row in db.execute(statement)]
    )


@router.get("/salary-range", response_model=SalaryRangeResponse)
def get_salary_range(db: DbSession, _: CurrentUser) -> SalaryRangeResponse:
    return SalaryRangeResponse(
        by_department=salary_ranges(db, Employee.department),
        by_country=salary_ranges(db, Employee.country),
    )
