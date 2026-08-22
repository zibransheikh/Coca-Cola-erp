import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ExpenseCategoryGroup(str, enum.Enum):
    vehicle = "vehicle"
    business = "business"


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"
    __table_args__ = (CheckConstraint("category_group IN ('vehicle', 'business')"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    category_group: Mapped[str]


class ExpenseStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("idx_expenses_vehicle", "vehicle_id"),
        Index("idx_expenses_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("expense_categories.id"))
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    expense_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str | None]
    status: Mapped[ExpenseStatus] = mapped_column(
        SAEnum(ExpenseStatus, name="expense_status", create_type=False), default=ExpenseStatus.pending
    )
    submitted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
