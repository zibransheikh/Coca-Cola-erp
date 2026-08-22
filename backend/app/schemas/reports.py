from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class StockReportRow(BaseModel):
    warehouse_id: int
    warehouse_name: str
    product_id: int
    sku: str
    name: str
    unit: str
    quantity: Decimal


class SalesByProductRow(BaseModel):
    product_id: int
    sku: str
    name: str
    total_quantity: Decimal
    total_revenue: Decimal


class SalesByCustomerRow(BaseModel):
    customer_id: int
    customer_name: str
    invoice_count: int
    total_amount: Decimal


class CollectionsSummaryOut(BaseModel):
    cash_total: Decimal
    online_total: Decimal
    credit_total: Decimal
    grand_total: Decimal


class CustomerAgingRow(BaseModel):
    customer_id: int
    customer_name: str
    credit_limit: Decimal
    current_0_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    over_90: Decimal
    total_outstanding: Decimal
    over_limit: bool
