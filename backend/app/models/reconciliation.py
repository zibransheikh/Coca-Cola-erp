import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BankStatementImport(Base):
    __tablename__ = "bank_statement_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str]
    file_type: Mapped[str]
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    imported_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    imported_at: Mapped[datetime] = mapped_column(server_default=func.now())


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    __table_args__ = (
        CheckConstraint("direction IN ('credit', 'debit')"),
        Index("idx_bank_txn_import", "import_id"),
        Index(
            "idx_bank_txn_holder_trgm",
            "account_holder_name",
            postgresql_using="gin",
            postgresql_ops={"account_holder_name": "gin_trgm_ops"},
        ),
        Index(
            "idx_bank_txn_unignored_credits",
            "transaction_date",
            postgresql_where=text("direction = 'credit' AND is_ignored = false"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("bank_statement_imports.id"))
    transaction_date: Mapped[date] = mapped_column(Date)
    account_holder_name: Mapped[str | None]
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    reference_number: Mapped[str | None]
    narration: Mapped[str | None]
    direction: Mapped[str]
    is_ignored: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PaymentIdentityMapping(Base):
    __tablename__ = "payment_identity_mappings"
    __table_args__ = (
        CheckConstraint("identity_type IN ('name', 'upi_id', 'account_ref')"),
        UniqueConstraint("identity_type", "identity_value"),
        Index("idx_payment_identity_customer", "customer_id"),
        Index(
            "idx_payment_identity_value_trgm",
            "identity_value",
            postgresql_using="gin",
            postgresql_ops={"identity_value": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    identity_type: Mapped[str]
    identity_value: Mapped[str]
    times_matched: Mapped[int] = mapped_column(Integer, default=0)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ReconciliationStatus(str, enum.Enum):
    auto_matched = "auto_matched"
    suggested = "suggested"
    approved = "approved"
    rejected = "rejected"
    unmatched = "unmatched"


class PaymentReconciliation(Base):
    __tablename__ = "payment_reconciliations"
    __table_args__ = (
        Index("idx_reconciliation_status", "status"),
        Index("idx_reconciliation_bank_txn", "bank_transaction_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_transaction_id: Mapped[int] = mapped_column(ForeignKey("bank_transactions.id"))
    pending_payment_id: Mapped[int | None] = mapped_column(ForeignKey("pending_online_payments.id"))
    matched_customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    match_method: Mapped[str | None]
    status: Mapped[ReconciliationStatus] = mapped_column(
        SAEnum(ReconciliationStatus, name="reconciliation_status", create_type=False),
        default=ReconciliationStatus.unmatched,
    )
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ReconciliationAuditLog(Base):
    __tablename__ = "reconciliation_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    reconciliation_id: Mapped[int] = mapped_column(ForeignKey("payment_reconciliations.id"))
    previous_status: Mapped[ReconciliationStatus | None] = mapped_column(
        SAEnum(ReconciliationStatus, name="reconciliation_status", create_type=False)
    )
    new_status: Mapped[ReconciliationStatus] = mapped_column(
        SAEnum(ReconciliationStatus, name="reconciliation_status", create_type=False)
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(server_default=func.now())
