from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.v1.crud_factory import make_crud_router
from app.db.session import get_db
from app.models import User
from app.models.accounting import AccountType, ChartOfAccount, JournalEntry, JournalEntryLine
from app.schemas.accounting import (
    BalanceSheetLineOut,
    BalanceSheetOut,
    ChartOfAccountCreate,
    ChartOfAccountOut,
    ChartOfAccountUpdate,
    GeneralLedgerRow,
    JournalEntryLineOut,
    JournalEntryOut,
    ManualJournalEntryCreate,
    PLLineOut,
    ProfitAndLossOut,
    TrialBalanceOut,
    TrialBalanceRow,
)
from app.services.accounting import post_journal_entry

chart_of_accounts_router = make_crud_router(
    model=ChartOfAccount,
    create_schema=ChartOfAccountCreate,
    update_schema=ChartOfAccountUpdate,
    out_schema=ChartOfAccountOut,
    prefix="/chart-of-accounts",
    tag="chart-of-accounts",
    write_permission="can_manage_accounting",
)

router = APIRouter(prefix="/accounting", tags=["accounting"])


def _journal_entry_to_out(entry: JournalEntry, accounts: dict[int, ChartOfAccount]) -> JournalEntryOut:
    return JournalEntryOut(
        id=entry.id,
        entry_date=entry.entry_date,
        reference_type=entry.reference_type,
        reference_id=entry.reference_id,
        narration=entry.narration,
        created_at=entry.created_at,
        lines=[
            JournalEntryLineOut(
                account_id=line.account_id,
                account_code=accounts[line.account_id].code,
                account_name=accounts[line.account_id].name,
                debit=line.debit,
                credit=line.credit,
            )
            for line in entry.lines
        ],
    )


@router.post("/journal-entries", response_model=JournalEntryOut, status_code=status.HTTP_201_CREATED)
def create_manual_journal_entry(
    payload: ManualJournalEntryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_manage_accounting")),
):
    if not payload.lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal entry must have at least one line")
    for line in payload.lines:
        if line.debit != 0 and line.credit != 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A line cannot have both debit and credit")

    accounts = {a.id: a for a in db.execute(select(ChartOfAccount)).scalars().all()}
    for line in payload.lines:
        if line.account_id not in accounts:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown account_id {line.account_id}")

    try:
        entry = JournalEntry(
            entry_date=payload.entry_date,
            reference_type="manual",
            reference_id=None,
            narration=payload.narration,
            created_by=user.id,
        )
        db.add(entry)
        db.flush()
        total_debit = sum((line.debit for line in payload.lines), Decimal("0"))
        total_credit = sum((line.credit for line in payload.lines), Decimal("0"))
        if total_debit != total_credit:
            raise ValueError(f"Journal entry does not balance: debit {total_debit} != credit {total_credit}")
        for line in payload.lines:
            db.add(
                JournalEntryLine(
                    journal_entry_id=entry.id,
                    account_id=line.account_id,
                    debit=line.debit,
                    credit=line.credit,
                )
            )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db.commit()
    entry = db.get(JournalEntry, entry.id)
    return _journal_entry_to_out(entry, accounts)


@router.get("/journal-entries", response_model=list[JournalEntryOut])
def list_journal_entries(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_view_reports")),
):
    query = select(JournalEntry).order_by(JournalEntry.id.desc())
    if start_date:
        query = query.where(JournalEntry.entry_date >= start_date)
    if end_date:
        query = query.where(JournalEntry.entry_date <= end_date)
    entries = db.execute(query).scalars().all()
    accounts = {a.id: a for a in db.execute(select(ChartOfAccount)).scalars().all()}
    return [_journal_entry_to_out(e, accounts) for e in entries]


@router.get("/general-ledger", response_model=list[GeneralLedgerRow])
def general_ledger(
    account_id: int = Query(...),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_view_reports")),
):
    query = (
        select(JournalEntryLine, JournalEntry)
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .where(JournalEntryLine.account_id == account_id)
        .order_by(JournalEntry.entry_date, JournalEntry.id)
    )
    if start_date:
        query = query.where(JournalEntry.entry_date >= start_date)
    if end_date:
        query = query.where(JournalEntry.entry_date <= end_date)

    rows = db.execute(query).all()
    running = Decimal("0")
    result = []
    for line, entry in rows:
        running += line.debit - line.credit
        result.append(
            GeneralLedgerRow(
                journal_entry_id=entry.id,
                entry_date=entry.entry_date,
                reference_type=entry.reference_type,
                reference_id=entry.reference_id,
                narration=entry.narration,
                debit=line.debit,
                credit=line.credit,
                running_balance=running,
            )
        )
    return result


@router.get("/trial-balance", response_model=TrialBalanceOut)
def trial_balance(
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_view_reports")),
):
    query = (
        select(
            ChartOfAccount.id,
            ChartOfAccount.code,
            ChartOfAccount.name,
            ChartOfAccount.account_type,
            func.coalesce(func.sum(JournalEntryLine.debit), 0),
            func.coalesce(func.sum(JournalEntryLine.credit), 0),
        )
        .outerjoin(JournalEntryLine, JournalEntryLine.account_id == ChartOfAccount.id)
        .outerjoin(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
    )
    if as_of:
        query = query.where((JournalEntry.entry_date.is_(None)) | (JournalEntry.entry_date <= as_of))
    query = query.group_by(ChartOfAccount.id, ChartOfAccount.code, ChartOfAccount.name, ChartOfAccount.account_type).order_by(
        ChartOfAccount.code
    )

    rows = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for account_id, code, name, account_type, debit_total, credit_total in db.execute(query).all():
        if debit_total == 0 and credit_total == 0:
            continue
        rows.append(
            TrialBalanceRow(
                account_id=account_id, code=code, name=name, account_type=account_type,
                debit_total=debit_total, credit_total=credit_total,
            )
        )
        total_debit += debit_total
        total_credit += credit_total

    return TrialBalanceOut(
        rows=rows, total_debit=total_debit, total_credit=total_credit, balanced=(total_debit == total_credit)
    )


def _account_net_balances(
    db: Session, account_type: AccountType, as_of: date | None, start_date: date | None = None
) -> list[tuple[ChartOfAccount, Decimal, Decimal]]:
    """Returns (account, debit_total, credit_total) for every account of the
    given type that has any postings in range."""
    query = (
        select(
            ChartOfAccount,
            func.coalesce(func.sum(JournalEntryLine.debit), 0),
            func.coalesce(func.sum(JournalEntryLine.credit), 0),
        )
        .join(JournalEntryLine, JournalEntryLine.account_id == ChartOfAccount.id)
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .where(ChartOfAccount.account_type == account_type)
    )
    if start_date:
        query = query.where(JournalEntry.entry_date >= start_date)
    if as_of:
        query = query.where(JournalEntry.entry_date <= as_of)
    query = query.group_by(ChartOfAccount.id).order_by(ChartOfAccount.code)
    return db.execute(query).all()


@router.get("/profit-and-loss", response_model=ProfitAndLossOut)
def profit_and_loss(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_view_reports")),
):
    income_rows = _account_net_balances(db, AccountType.income, end_date, start_date)
    expense_rows = _account_net_balances(db, AccountType.expense, end_date, start_date)

    income = [PLLineOut(code=a.code, name=a.name, amount=credit - debit) for a, debit, credit in income_rows]
    expenses = [PLLineOut(code=a.code, name=a.name, amount=debit - credit) for a, debit, credit in expense_rows]
    total_income = sum((line.amount for line in income), Decimal("0"))
    total_expenses = sum((line.amount for line in expenses), Decimal("0"))

    return ProfitAndLossOut(
        income=income,
        expenses=expenses,
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=total_income - total_expenses,
    )


@router.get("/balance-sheet", response_model=BalanceSheetOut)
def balance_sheet(
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_view_reports")),
):
    """Assets = Liabilities + Equity + Retained Earnings holds by construction
    of double-entry bookkeeping (every journal entry balances), even though
    there's no period-close step rolling net income into an equity account —
    `retained_earnings` here is simply all-time net income to date.
    """
    as_of = as_of or datetime.now(timezone.utc).date()

    asset_rows = _account_net_balances(db, AccountType.asset, as_of)
    liability_rows = _account_net_balances(db, AccountType.liability, as_of)
    equity_rows = _account_net_balances(db, AccountType.equity, as_of)
    income_rows = _account_net_balances(db, AccountType.income, as_of)
    expense_rows = _account_net_balances(db, AccountType.expense, as_of)

    assets = [BalanceSheetLineOut(code=a.code, name=a.name, amount=debit - credit) for a, debit, credit in asset_rows]
    liabilities = [
        BalanceSheetLineOut(code=a.code, name=a.name, amount=credit - debit) for a, debit, credit in liability_rows
    ]
    equity = [BalanceSheetLineOut(code=a.code, name=a.name, amount=credit - debit) for a, debit, credit in equity_rows]

    total_income = sum((credit - debit for _, debit, credit in income_rows), Decimal("0"))
    total_expense = sum((debit - credit for _, debit, credit in expense_rows), Decimal("0"))
    retained_earnings = total_income - total_expense

    total_assets = sum((line.amount for line in assets), Decimal("0"))
    total_liabilities = sum((line.amount for line in liabilities), Decimal("0"))
    total_equity = sum((line.amount for line in equity), Decimal("0"))

    return BalanceSheetOut(
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        retained_earnings=retained_earnings,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        balanced=(total_assets == total_liabilities + total_equity + retained_earnings),
    )
