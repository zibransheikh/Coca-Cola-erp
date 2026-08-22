from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.collections import PaymentMode
from app.models.trips import TripStatus


# ---- Trip ----
class TripCreate(BaseModel):
    vehicle_id: int
    driver_id: int
    route_id: int | None = None
    warehouse_id: int
    trip_date: date


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    driver_id: int
    route_id: int | None
    warehouse_id: int
    trip_date: date
    status: TripStatus
    opened_at: datetime
    closed_at: datetime | None
    mismatch_notes: str | None
    cash_count_500: int
    cash_count_200: int
    cash_count_100: int
    cash_count_50: int
    cash_count_20: int
    cash_count_10: int
    cash_coins_amount: Decimal


# ---- Crates (glass-bottle returnables): crates_out is NOT user-entered —
# it's derived from the stock sheet's loaded quantity for every unit='crate'
# product, so it can never drift from what was actually loaded (see
# app/api/v1/trips.py::_crates_out). crates_in (empty crates the driver
# brought back) has no other data source, so that one stays a manual count;
# the difference is what should match the day's crate-based sales.
class CratesOut(BaseModel):
    crates_out: Decimal
    crates_in: int


class CratesUpdate(BaseModel):
    crates_in: int = 0


# ---- Cash count: driver counts Indian currency notes by denomination at
# day-close instead of entering a lump cash figure — the total is derived,
# never entered directly, so it can't drift from the note counts. Online
# payments are NOT part of this — they're per-shop entries below, since
# (unlike cash) each one has a specific payer to match against a bank
# statement later.
class CashCountUpdate(BaseModel):
    cash_count_500: int = 0
    cash_count_200: int = 0
    cash_count_100: int = 0
    cash_count_50: int = 0
    cash_count_20: int = 0
    cash_count_10: int = 0
    cash_coins_amount: Decimal = Decimal("0")


# ---- Credit & online entries: per-shop money given/received on a trip,
# entered directly instead of via a formal invoice — both reuse
# payment_collections (invoice_id left null) since that table was already
# designed for exactly this: "shop, amount, mode. Nothing more."
class MoneyEntryCreate(BaseModel):
    customer_id: int
    amount: Decimal


class MoneyEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    trip_id: int | None
    customer_id: int
    amount: Decimal
    status: str
    collected_at: datetime


class MoneyEntryStatusUpdate(BaseModel):
    paid: bool


# ---- Cheque entries: same idea as credit/online, but a cheque carries two
# dates instead of just an amount — when the shop handed it over, and the
# date it can actually be taken to the bank (cheques are frequently
# post-dated, so these two are rarely the same day).
class ChequeEntryCreate(BaseModel):
    customer_id: int
    amount: Decimal
    cheque_given_date: date
    cheque_deposit_date: date


class ChequeEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    trip_id: int | None
    customer_id: int
    amount: Decimal
    status: str
    cheque_given_date: date | None
    cheque_deposit_date: date | None
    collected_at: datetime


class CreditLogRow(BaseModel):
    id: int
    trip_id: int
    customer_id: int
    customer_name: str
    amount: Decimal
    status: str
    trip_date: date
    driver_id: int
    driver_name: str


class ChequeLogRow(BaseModel):
    id: int
    trip_id: int
    customer_id: int
    customer_name: str
    amount: Decimal
    status: str
    cheque_given_date: date | None
    cheque_deposit_date: date | None
    trip_date: date
    driver_id: int
    driver_name: str


# ---- Stock sheet: one editable row per product covering the whole trip —
# loaded/returned/damaged all live together, no separate load/depart/count
# stages. Submitting is idempotent: values are the new totals, not deltas to
# add: see app/api/v1/trips.py::update_stock_sheet.
class StockSheetRowIn(BaseModel):
    product_id: int
    loaded_quantity: Decimal = Decimal("0")
    returned_quantity: Decimal = Decimal("0")
    damaged_quantity: Decimal = Decimal("0")


class StockSheetRequest(BaseModel):
    rows: list[StockSheetRowIn]


class StockSheetRowOut(BaseModel):
    product_id: int
    sku: str
    name: str
    unit: str
    base_price: Decimal
    warehouse_available: Decimal
    loaded_quantity: Decimal
    returned_quantity: Decimal
    damaged_quantity: Decimal


# ---- Sales Invoice ----
class InvoiceItemCreate(BaseModel):
    product_id: int
    batch_id: int | None = None
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal = Decimal("0")


class InvoiceCreate(BaseModel):
    customer_id: int
    items: list[InvoiceItemCreate]


class InvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    batch_id: int | None
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_number: str
    trip_id: int
    customer_id: int
    invoice_date: datetime
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: str
    items: list[InvoiceItemOut]


# ---- Collections ----
class CollectionCreate(BaseModel):
    payment_mode: PaymentMode
    amount: Decimal


class CollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int | None
    customer_id: int
    amount: Decimal
    payment_mode: PaymentMode
    status: str
    collected_at: datetime


# ---- Reconciliation ----
# Value-based, not invoice-based: instead of requiring an invoice per sale,
# expected revenue for the day is inferred from stock movement (loaded minus
# returned minus damaged, valued at each product's base price) and compared
# against what the driver actually reports bringing back (counted cash +
# credit given + online amount). Sold quantity/"missing stock" can no longer
# be verified independently once invoices aren't required — any shortfall
# shows up as a money difference instead, which is exactly the check this
# feature exists for.
class ReconciliationProductRow(BaseModel):
    product_id: int
    sku: str
    name: str
    loaded: Decimal
    returned: Decimal
    damaged: Decimal
    expected_value: Decimal


class ReconciliationOut(BaseModel):
    products: list[ReconciliationProductRow]
    expected_sales_value: Decimal
    cash_collected: Decimal
    online_collected: Decimal
    credit_given: Decimal
    cheque_given: Decimal
    total_collected: Decimal
    money_difference: Decimal
    clean: bool

    @property
    def is_clean(self) -> bool:
        return self.clean


class TripCloseRequest(BaseModel):
    override_notes: str | None = None
