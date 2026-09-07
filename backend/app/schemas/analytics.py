from decimal import Decimal

from pydantic import BaseModel


class CountBreakdown(BaseModel):
    group: str
    count: int


class HeadcountResponse(BaseModel):
    by_department: list[CountBreakdown]
    by_country: list[CountBreakdown]


class SalarySummaryBreakdown(BaseModel):
    group: str
    currency: str
    average: Decimal
    median: Decimal


class SalarySummaryResponse(BaseModel):
    by_department: list[SalarySummaryBreakdown]
    by_country: list[SalarySummaryBreakdown]


class BandBreakdown(BaseModel):
    band: str
    count: int


class BandDistributionResponse(BaseModel):
    bands: list[BandBreakdown]


class SalaryRangeBreakdown(BaseModel):
    group: str
    currency: str
    minimum: Decimal
    maximum: Decimal


class SalaryRangeResponse(BaseModel):
    by_department: list[SalaryRangeBreakdown]
    by_country: list[SalaryRangeBreakdown]
