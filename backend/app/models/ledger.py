import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class LedgerTxnType(str, enum.Enum):
    invoice = "invoice"
    payment = "payment"
    credit_note = "credit_note"
    debit_note = "debit_note"


class CustomerLedger(Base):
    __tablename__ = "customer_ledger"
    __table_args__ = (Index("idx_customer_ledger_customer", "customer_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    txn_type: Mapped[LedgerTxnType] = mapped_column(SAEnum(LedgerTxnType, name="ledger_txn_type", create_type=False))
    reference_type: Mapped[str]
    reference_id: Mapped[int]
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
