import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AccountType(str, enum.Enum):
    asset = "asset"
    liability = "liability"
    equity = "equity"
    income = "income"
    expense = "expense"


class ChartOfAccount(Base):
    __tablename__ = "chart_of_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    account_type: Mapped[AccountType] = mapped_column(SAEnum(AccountType, name="account_type", create_type=False))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("chart_of_accounts.id"))


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date)
    reference_type: Mapped[str | None]
    reference_id: Mapped[int | None]
    narration: Mapped[str | None]
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    lines: Mapped[list["JournalEntryLine"]] = relationship()


class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"
    __table_args__ = (
        CheckConstraint("debit = 0 OR credit = 0"),
        Index("idx_jel_entry", "journal_entry_id"),
        Index("idx_jel_account", "account_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    journal_entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("chart_of_accounts.id"))
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
