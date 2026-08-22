from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BankStatementImportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_name: str
    file_type: str
    period_start: date | None
    period_end: date | None
    imported_at: datetime


class BankTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    import_id: int
    transaction_date: date
    account_holder_name: str | None
    amount: Decimal
    reference_number: str | None
    narration: str | None
    direction: str
    is_ignored: bool


class PaymentIdentityMappingCreate(BaseModel):
    customer_id: int
    identity_type: str
    identity_value: str


class PaymentIdentityMappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    identity_type: str
    identity_value: str
    times_matched: int
    verified_at: datetime


class ReconciliationOut(BaseModel):
    id: int
    bank_transaction_id: int
    pending_payment_id: int | None
    matched_customer_id: int | None
    matched_customer_name: str | None
    confidence_score: Decimal
    match_method: str | None
    status: str
    transaction_date: date
    account_holder_name: str | None
    amount: Decimal
    reference_number: str | None
    narration: str | None


class ManualMatchRequest(BaseModel):
    customer_id: int
    pending_payment_id: int
