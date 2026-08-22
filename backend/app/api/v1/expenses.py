from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.api.v1.crud_factory import make_crud_router
from app.db.session import get_db
from app.models import User
from app.models.expenses import Expense, ExpenseCategory, ExpenseStatus
from app.schemas.expenses import (
    ExpenseCategoryCreate,
    ExpenseCategoryOut,
    ExpenseCategoryUpdate,
    ExpenseCreate,
    ExpenseOut,
)
from app.services import accounting as acct
from app.services.accounting import post_journal_entry

expense_categories_router = make_crud_router(
    model=ExpenseCategory,
    create_schema=ExpenseCategoryCreate,
    update_schema=ExpenseCategoryUpdate,
    out_schema=ExpenseCategoryOut,
    prefix="/expense-categories",
    tag="expense-categories",
    write_permission="can_manage_masters",
)

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    expense = Expense(
        category_id=payload.category_id,
        vehicle_id=payload.vehicle_id,
        amount=payload.amount,
        expense_date=payload.expense_date,
        description=payload.description,
        submitted_by=user.id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("", response_model=list[ExpenseOut])
def list_expenses(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.execute(select(Expense).order_by(Expense.id.desc())).scalars().all()


def _get_expense_or_404(db: Session, expense_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.post("/{expense_id}/approve", response_model=ExpenseOut)
def approve_expense(
    expense_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("can_approve_expense"))
):
    expense = _get_expense_or_404(db, expense_id)
    if expense.status != ExpenseStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expense is not pending")
    expense.status = ExpenseStatus.approved
    expense.approved_by = user.id

    # All expenses post to one generic account regardless of category (no
    # expense_categories -> chart_of_accounts mapping exists yet) and are
    # assumed paid in cash immediately — see app/services/accounting.py.
    post_journal_entry(
        db,
        entry_date=expense.expense_date,
        reference_type="expense",
        reference_id=expense.id,
        narration=expense.description or "Expense",
        lines=[(acct.OPERATING_EXPENSES, expense.amount, Decimal("0")), (acct.CASH, Decimal("0"), expense.amount)],
        created_by=user.id,
    )

    db.commit()
    db.refresh(expense)
    return expense


@router.post("/{expense_id}/reject", response_model=ExpenseOut)
def reject_expense(
    expense_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("can_approve_expense"))
):
    expense = _get_expense_or_404(db, expense_id)
    if expense.status != ExpenseStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expense is not pending")
    expense.status = ExpenseStatus.rejected
    expense.approved_by = user.id
    db.commit()
    db.refresh(expense)
    return expense
