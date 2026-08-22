import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    address: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    brand: Mapped[str | None]
    category: Mapped[str | None]
    unit: Mapped[str]
    volume_ml: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # for sorting/grouping by pack size
    hsn_code: Mapped[str | None]
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    base_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    is_returnable: Mapped[bool] = mapped_column(default=False)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ProductBatch(Base):
    __tablename__ = "product_batches"
    __table_args__ = (
        UniqueConstraint("product_id", "batch_number"),
        Index("idx_product_batches_expiry", "expiry_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    batch_number: Mapped[str]
    manufacture_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index("idx_customers_route", "route_id"),
        Index(
            "idx_customers_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    owner_name: Mapped[str | None]
    phone: Mapped[str | None]
    address: Mapped[str | None]
    gst_number: Mapped[str | None]
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id"))
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    credit_days: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    route: Mapped[Route | None] = relationship()


class EmployeeRole(str, enum.Enum):
    driver = "driver"
    helper = "helper"
    office = "office"
    other = "other"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    role: Mapped[EmployeeRole] = mapped_column(SAEnum(EmployeeRole, name="employee_role", create_type=False))
    phone: Mapped[str | None]
    joining_date: Mapped[date] = mapped_column(Date)
    monthly_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_number: Mapped[str] = mapped_column(unique=True)
    vehicle_type: Mapped[str | None]
    capacity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class VehicleDriverAssignment(Base):
    __tablename__ = "vehicle_driver_assignments"
    __table_args__ = (Index("idx_vda_vehicle", "vehicle_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id"))
    assigned_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(default=True)
