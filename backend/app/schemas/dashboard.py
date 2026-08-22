from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class BestSellingProduct(BaseModel):
    product_id: int
    name: str
    quantity: Decimal


class DashboardSummaryOut(BaseModel):
    today_sales: Decimal
    cash_collected_today: Decimal
    online_collected_today: Decimal
    pending_credits_total: Decimal
    vehicles_on_route: int
    warehouse_stock_products: int
    near_expiry_count: int
    low_stock_count: int
    daily_expenses: Decimal
    profit_today: Decimal
    best_selling_products: list[BestSellingProduct]


class DailySalesPoint(BaseModel):
    date: date
    total: Decimal


class DailyCollectionPoint(BaseModel):
    date: date
    cash: Decimal
    online: Decimal
    credit: Decimal


class DashboardTrendsOut(BaseModel):
    daily_sales: list[DailySalesPoint]
    daily_collections: list[DailyCollectionPoint]


# ---- Route sales trend: one line per route, value-based (same formula as
# trip reconciliation: (loaded-returned-damaged) x base_price), not
# invoice-based, so it stays meaningful for trips that never create an
# invoice. `points` is pre-pivoted server-side — each dict is one date with a
# key per route name — so the chart component doesn't need to reshape data.
class RouteSalesTrendOut(BaseModel):
    route_names: list[str]
    points: list[dict[str, Any]]
