from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.payroll import AttendanceStatus


# ---- Attendance: marked as a date range (e.g. "on leave July 10-15"), not
# one day at a time — internally upserts one row per day in the range so
# correcting a mistake just means re-marking the same range.
class AttendanceMarkRequest(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    status: AttendanceStatus


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    attendance_date: date
    status: AttendanceStatus


# ---- Salary advances ----
class SalaryAdvanceCreate(BaseModel):
    employee_id: int
    amount: Decimal
    advance_date: date
    reason: str | None = None


class SalaryAdvanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    amount: Decimal
    advance_date: date
    reason: str | None
    approved_by: int | None
    created_at: datetime


# ---- Payroll summary: one row per employee for a given period. Advances
# are scoped to advance_date falling within the period — there's no
# "already deducted" flag on salary_advances, so an advance is assumed to be
# cleared within the same period it was taken (matches how the original
# schema was designed, and how a small distributor would actually run this:
# advances given this month get squared off this month's payroll).
class PayrollSummaryRow(BaseModel):
    employee_id: int
    employee_name: str
    monthly_salary: Decimal
    leave_days: int
    half_days: int
    absent_days: int
    advances_total: Decimal
    net_payable: Decimal
    paid: bool
    paid_at: datetime | None
    salary_payment_id: int | None


# ---- Salary payments (the actual "pay" action) ----
class SalaryPaymentCreate(BaseModel):
    employee_id: int
    period_start: date
    period_end: date


class SalaryPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    period_start: date
    period_end: date
    gross_amount: Decimal
    advances_deducted: Decimal
    net_amount: Decimal
    paid_at: datetime | None
    paid_by: int | None
