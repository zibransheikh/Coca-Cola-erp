from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.accounting import AccountType


class ChartOfAccountCreate(BaseModel):
    code: str
    name: str
    account_type: AccountType
    parent_id: int | None = None


class ChartOfAccountUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None


class ChartOfAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    account_type: AccountType
    parent_id: int | None


class ManualJournalLineCreate(BaseModel):
    account_id: int
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")


class ManualJournalEntryCreate(BaseModel):
    entry_date: date
    narration: str
    lines: list[ManualJournalLineCreate]


class JournalEntryLineOut(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal


class JournalEntryOut(BaseModel):
    id: int
    entry_date: date
    reference_type: str | None
    reference_id: int | None
    narration: str | None
    created_at: datetime
    lines: list[JournalEntryLineOut]


class GeneralLedgerRow(BaseModel):
    journal_entry_id: int
    entry_date: date
    reference_type: str | None
    reference_id: int | None
    narration: str | None
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class TrialBalanceRow(BaseModel):
    account_id: int
    code: str
    name: str
    account_type: AccountType
    debit_total: Decimal
    credit_total: Decimal


class TrialBalanceOut(BaseModel):
    rows: list[TrialBalanceRow]
    total_debit: Decimal
    total_credit: Decimal
    balanced: bool


class PLLineOut(BaseModel):
    code: str
    name: str
    amount: Decimal


class ProfitAndLossOut(BaseModel):
    income: list[PLLineOut]
    expenses: list[PLLineOut]
    total_income: Decimal
    total_expenses: Decimal
    net_profit: Decimal


class BalanceSheetLineOut(BaseModel):
    code: str
    name: str
    amount: Decimal


class BalanceSheetOut(BaseModel):
    assets: list[BalanceSheetLineOut]
    liabilities: list[BalanceSheetLineOut]
    equity: list[BalanceSheetLineOut]
    retained_earnings: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    balanced: bool
