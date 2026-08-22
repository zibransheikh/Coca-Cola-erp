from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting import ChartOfAccount, JournalEntry, JournalEntryLine

# Default chart of accounts (see app/seed.py). Deliberately small: expenses
# all post to one generic account rather than a per-category account (no
# expense_categories -> chart_of_accounts mapping exists), and purchases are
# treated as always-on-credit (no per-purchase payment-method tracking
# exists yet). Both are documented simplifications, not oversights — see
# docs/database-design.md / memory for the reasoning.
CASH = "1000"
BANK = "1010"
ACCOUNTS_RECEIVABLE = "1100"
INVENTORY = "1200"
ACCOUNTS_PAYABLE = "2000"
GST_OUTPUT_TAX_PAYABLE = "2100"
OWNERS_EQUITY = "3000"
SALES_REVENUE = "4000"
OPERATING_EXPENSES = "5000"


def _account_id(db: Session, code: str) -> int:
    account_id = db.execute(select(ChartOfAccount.id).where(ChartOfAccount.code == code)).scalar_one_or_none()
    if account_id is None:
        raise ValueError(f"Chart of accounts is missing required account {code!r} — run the seed script")
    return account_id


def post_journal_entry(
    db: Session,
    *,
    entry_date: date,
    reference_type: str,
    reference_id: int,
    narration: str,
    lines: list[tuple[str, Decimal, Decimal]],
    created_by: int | None,
) -> JournalEntry:
    """Post a balanced double-entry journal entry. `lines` is a list of
    (account_code, debit, credit) tuples — exactly one of debit/credit should
    be nonzero per line, matching the DB's own CHECK constraint. Does not
    commit; the caller's existing transaction covers this alongside whatever
    business event triggered it (invoice, collection, purchase, expense).
    """
    total_debit = sum((d for _, d, _ in lines), Decimal("0"))
    total_credit = sum((c for _, _, c in lines), Decimal("0"))
    if total_debit != total_credit:
        raise ValueError(f"Journal entry does not balance: debit {total_debit} != credit {total_credit}")

    entry = JournalEntry(
        entry_date=entry_date,
        reference_type=reference_type,
        reference_id=reference_id,
        narration=narration,
        created_by=created_by,
    )
    db.add(entry)
    db.flush()

    for account_code, debit, credit in lines:
        db.add(
            JournalEntryLine(
                journal_entry_id=entry.id,
                account_id=_account_id(db, account_code),
                debit=debit,
                credit=credit,
            )
        )

    return entry
