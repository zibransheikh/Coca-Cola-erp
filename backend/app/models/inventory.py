import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class StockLocationType(str, enum.Enum):
    warehouse = "warehouse"
    vehicle = "vehicle"


class StockTxnType(str, enum.Enum):
    purchase = "purchase"
    sale = "sale"
    return_ = "return"
    damage = "damage"
    adjustment = "adjustment"
    transfer_in = "transfer_in"
    transfer_out = "transfer_out"
    load_out = "load_out"
    load_in = "load_in"


class StockLedger(Base):
    __tablename__ = "stock_ledger"
    __table_args__ = (
        Index("idx_stock_ledger_location", "location_type", "location_id", "product_id"),
        Index("idx_stock_ledger_product_batch", "product_id", "batch_id"),
        Index("idx_stock_ledger_reference", "reference_type", "reference_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    location_type: Mapped[StockLocationType] = mapped_column(
        SAEnum(StockLocationType, name="stock_location_type", create_type=False)
    )
    location_id: Mapped[int]
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("product_batches.id"))
    txn_type: Mapped[StockTxnType] = mapped_column(
        SAEnum(
            StockTxnType,
            name="stock_txn_type",
            create_type=False,
            # `return` is a Python keyword, so the enum member is `return_` but
            # its value is "return" — send .value to Postgres, not .name.
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        )
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    reference_type: Mapped[str | None]
    reference_id: Mapped[int | None]
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    supplier_name: Mapped[str]
    invoice_number: Mapped[str | None]
    purchase_date: Mapped[date] = mapped_column(Date)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    items: Mapped[list["PurchaseItem"]] = relationship()


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("product_batches.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("product_batches.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    reason: Mapped[str]
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
