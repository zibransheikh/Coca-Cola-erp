from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.expenses import ExpenseCategoryGroup, ExpenseStatus


class ExpenseCategoryCreate(BaseModel):
    name: str
    category_group: ExpenseCategoryGroup


class ExpenseCategoryUpdate(BaseModel):
    name: str | None = None
    category_group: ExpenseCategoryGroup | None = None


class ExpenseCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category_group: str


class ExpenseCreate(BaseModel):
    category_id: int
    vehicle_id: int | None = None
    amount: Decimal
    expense_date: date
    description: str | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_id: int
    vehicle_id: int | None
    amount: Decimal
    expense_date: date
    description: str | None
    status: ExpenseStatus
    submitted_by: int | None
    approved_by: int | None
