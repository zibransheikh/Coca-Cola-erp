import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PaymentMode(str, enum.Enum):
    cash = "cash"
    credit = "credit"
    online = "online"
    cheque = "cheque"


class PaymentStatus(str, enum.Enum):
    cleared = "cleared"
    awaiting_bank_verification = "awaiting_bank_verification"
    pending = "pending"  # credit given but not yet repaid by the shop


class PaymentCollection(Base):
    __tablename__ = "payment_collections"
    __table_args__ = (
        Index("idx_payment_collections_customer", "customer_id"),
        Index(
            "idx_payment_collections_status",
            "status",
            postgresql_where=text("status = 'awaiting_bank_verification'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("sales_invoices.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payment_mode: Mapped[PaymentMode] = mapped_column(SAEnum(PaymentMode, name="payment_mode", create_type=False))
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status", create_type=False), default=PaymentStatus.cleared
    )
    collected_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    collected_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # Cheque-mode only: when the shop handed over the cheque, and the date
    # it can actually be deposited at the bank (post-dated cheques are
    # common — these two dates are rarely the same).
    cheque_given_date: Mapped[date | None]
    cheque_deposit_date: Mapped[date | None]


class PendingOnlinePayment(Base):
    __tablename__ = "pending_online_payments"
    __table_args__ = (
        Index("idx_pending_online_unresolved", "customer_id", postgresql_where=text("resolved_at IS NULL")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_collection_id: Mapped[int] = mapped_column(ForeignKey("payment_collections.id"), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None]
