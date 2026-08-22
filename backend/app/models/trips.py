import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TripStatus(str, enum.Enum):
    loading = "loading"
    on_route = "on_route"
    returned = "returned"
    closed = "closed"


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        Index("idx_trips_date", "trip_date"),
        Index("idx_trips_vehicle", "vehicle_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    trip_date: Mapped[date] = mapped_column(Date)
    status: Mapped[TripStatus] = mapped_column(
        SAEnum(TripStatus, name="trip_status", create_type=False), default=TripStatus.loading
    )
    opened_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    closed_at: Mapped[datetime | None]
    mismatch_notes: Mapped[str | None]
    cash_count_500: Mapped[int] = mapped_column(default=0)
    cash_count_200: Mapped[int] = mapped_column(default=0)
    cash_count_100: Mapped[int] = mapped_column(default=0)
    cash_count_50: Mapped[int] = mapped_column(default=0)
    cash_count_20: Mapped[int] = mapped_column(default=0)
    cash_count_10: Mapped[int] = mapped_column(default=0)
    cash_coins_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    # crates_out is NOT stored — it's computed from the stock sheet's loaded
    # quantity for unit='crate' products (see app/api/v1/trips.py::_crates_out),
    # so it can never drift from what was actually loaded.
    crates_in: Mapped[int] = mapped_column(default=0)  # empty crates the driver brought back


class TripStockCount(Base):
    __tablename__ = "trip_stock_counts"
    __table_args__ = (UniqueConstraint("trip_id", "product_id", "batch_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("product_batches.id"))
    returned_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    damaged_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    counted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
