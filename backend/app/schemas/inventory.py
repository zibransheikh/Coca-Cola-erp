from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StockLevelOut(BaseModel):
    product_id: int
    sku: str
    name: str
    unit: str
    batch_id: int | None
    batch_number: str | None
    quantity: Decimal
    base_price: Decimal


class PurchaseItemCreate(BaseModel):
    product_id: int
    batch_id: int | None = None
    quantity: Decimal
    unit_cost: Decimal


class PurchaseItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    batch_id: int | None
    quantity: Decimal
    unit_cost: Decimal


class PurchaseCreate(BaseModel):
    warehouse_id: int
    supplier_name: str
    invoice_number: str | None = None
    purchase_date: date
    items: list[PurchaseItemCreate]


class PurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    warehouse_id: int
    supplier_name: str
    invoice_number: str | None
    purchase_date: date
    total_amount: Decimal
    items: list[PurchaseItemOut]


class StockAdjustmentCreate(BaseModel):
    warehouse_id: int
    product_id: int
    batch_id: int | None = None
    quantity: Decimal
    reason: str


class StockAdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    warehouse_id: int
    product_id: int
    batch_id: int | None
    quantity: Decimal
    reason: str
