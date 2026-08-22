import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class InvoiceStatus(str, enum.Enum):
    posted = "posted"
    cancelled = "cancelled"


class SalesInvoice(Base):
    __tablename__ = "sales_invoices"
    __table_args__ = (
        Index("idx_invoices_customer", "customer_id"),
        Index("idx_invoices_trip", "trip_id"),
        Index("idx_invoices_date", "invoice_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_number: Mapped[str] = mapped_column(unique=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    invoice_date: Mapped[datetime] = mapped_column(server_default=func.now())
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, name="invoice_status", create_type=False), default=InvoiceStatus.posted
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    items: Mapped[list["SalesInvoiceItem"]] = relationship()


class SalesInvoiceItem(Base):
    __tablename__ = "sales_invoice_items"
    __table_args__ = (
        Index("idx_invoice_items_invoice", "invoice_id"),
        Index("idx_invoice_items_product", "product_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("sales_invoices.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("product_batches.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
