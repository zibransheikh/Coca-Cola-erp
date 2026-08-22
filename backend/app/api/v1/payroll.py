from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models import User
from app.models.masters import Employee
from app.models.payroll import Attendance, AttendanceStatus, SalaryAdvance, SalaryPayment
from app.schemas.payroll import (
    AttendanceMarkRequest,
    AttendanceOut,
    PayrollSummaryRow,
    SalaryAdvanceCreate,
    SalaryAdvanceOut,
    SalaryPaymentCreate,
    SalaryPaymentOut,
)

router = APIRouter(prefix="/payroll", tags=["payroll"])


def _date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


@router.post("/attendance", response_model=list[AttendanceOut], status_code=status.HTTP_201_CREATED)
def mark_attendance(
    payload: AttendanceMarkRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_manage_payroll")),
):
    """Marks a whole date range at once (e.g. "on leave July 10-15") rather
    than one day at a time — upserts so re-marking a range (to fix a
    mistake) just overwrites the existing rows instead of erroring on the
    (employee_id, attendance_date) unique constraint."""
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date can't be before start_date")

    existing = {
        row.attendance_date: row
        for row in db.execute(
            select(Attendance).where(
                Attendance.employee_id == payload.employee_id,
                Attendance.attendance_date >= payload.start_date,
                Attendance.attendance_date <= payload.end_date,
            )
        ).scalars()
    }
    rows = []
    for d in _date_range(payload.start_date, payload.end_date):
        row = existing.get(d)
        if row is None:
            row = Attendance(employee_id=payload.employee_id, attendance_date=d, status=payload.status)
            db.add(row)
        else:
            row.status = payload.status
        rows.append(row)

    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


@router.get("/attendance", response_model=list[AttendanceOut])
def list_attendance(
    employee_id: int | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_manage_payroll")),
):
    query = select(Attendance)
    if employee_id is not None:
        query = query.where(Attendance.employee_id == employee_id)
    if start_date is not None:
        query = query.where(Attendance.attendance_date >= start_date)
    if end_date is not None:
        query = query.where(Attendance.attendance_date <= end_date)
    return db.execute(query.order_by(Attendance.attendance_date.desc())).scalars().all()


@router.post("/advances", response_model=SalaryAdvanceOut, status_code=status.HTTP_201_CREATED)
def create_advance(
    payload: SalaryAdvanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_manage_payroll")),
):
    if payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")
    advance = SalaryAdvance(
        employee_id=payload.employee_id,
        amount=payload.amount,
        advance_date=payload.advance_date,
        reason=payload.reason,
        approved_by=user.id,
    )
    db.add(advance)
    db.commit()
    db.refresh(advance)
    return advance


@router.get("/advances", response_model=list[SalaryAdvanceOut])
def list_advances(
    employee_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_manage_payroll")),
):
    query = select(SalaryAdvance)
    if employee_id is not None:
        query = query.where(SalaryAdvance.employee_id == employee_id)
    return db.execute(query.order_by(SalaryAdvance.advance_date.desc())).scalars().all()


def _payroll_row(db: Session, employee: Employee, period_start: date, period_end: date) -> PayrollSummaryRow:
    counts: dict[AttendanceStatus, int] = defaultdict(int)
    for row in db.execute(
        select(Attendance.status).where(
            Attendance.employee_id == employee.id,
            Attendance.attendance_date >= period_start,
            Attendance.attendance_date <= period_end,
        )
    ).scalars():
        counts[row] += 1

    # Advances are scoped to this period's advance_date — there's no
    # "already deducted" flag on salary_advances, so an advance is assumed
    # to be squared off within the same period it was given.
    advances_total = sum(
        (
            row.amount
            for row in db.execute(
                select(SalaryAdvance).where(
                    SalaryAdvance.employee_id == employee.id,
                    SalaryAdvance.advance_date >= period_start,
                    SalaryAdvance.advance_date <= period_end,
                )
            ).scalars()
        ),
        Decimal("0"),
    )

    payment = db.execute(
        select(SalaryPayment).where(
            SalaryPayment.employee_id == employee.id,
            SalaryPayment.period_start == period_start,
            SalaryPayment.period_end == period_end,
        )
    ).scalar_one_or_none()

    gross = employee.monthly_salary
    net_payable = gross - advances_total

    return PayrollSummaryRow(
        employee_id=employee.id,
        employee_name=employee.name,
        monthly_salary=gross,
        leave_days=counts.get(AttendanceStatus.leave, 0),
        half_days=counts.get(AttendanceStatus.half_day, 0),
        absent_days=counts.get(AttendanceStatus.absent, 0),
        advances_total=advances_total,
        net_payable=net_payable,
        paid=payment is not None,
        paid_at=payment.paid_at if payment else None,
        salary_payment_id=payment.id if payment else None,
    )


@router.get("/summary", response_model=list[PayrollSummaryRow])
def payroll_summary(
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_manage_payroll")),
):
    if period_end < period_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_end can't be before period_start")
    employees = db.execute(select(Employee).where(Employee.is_active).order_by(Employee.name)).scalars().all()
    return [_payroll_row(db, employee, period_start, period_end) for employee in employees]


@router.post("/pay", response_model=SalaryPaymentOut, status_code=status.HTTP_201_CREATED)
def pay_salary(
    payload: SalaryPaymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_manage_payroll")),
):
    employee = db.get(Employee, payload.employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    if payload.period_end < payload.period_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_end can't be before period_start")

    existing = db.execute(
        select(SalaryPayment).where(
            SalaryPayment.employee_id == payload.employee_id,
            SalaryPayment.period_start == payload.period_start,
            SalaryPayment.period_end == payload.period_end,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already paid for this period")

    row = _payroll_row(db, employee, payload.period_start, payload.period_end)
    payment = SalaryPayment(
        employee_id=payload.employee_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        gross_amount=row.monthly_salary,
        advances_deducted=row.advances_total,
        net_amount=row.net_payable,
        paid_at=datetime.now(timezone.utc),
        paid_by=user.id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/payments", response_model=list[SalaryPaymentOut])
def list_payments(
    employee_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_manage_payroll")),
):
    query = select(SalaryPayment)
    if employee_id is not None:
        query = query.where(SalaryPayment.employee_id == employee_id)
    return db.execute(query.order_by(SalaryPayment.paid_at.desc())).scalars().all()
