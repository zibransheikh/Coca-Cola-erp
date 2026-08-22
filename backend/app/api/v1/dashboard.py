from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.trips import _cash_total
from app.db.session import get_db
from app.models import User
from app.models.collections import PaymentCollection, PaymentMode, PaymentStatus
from app.models.expenses import Expense, ExpenseStatus
from app.models.inventory import StockLedger, StockLocationType, StockTxnType
from app.models.masters import Product, ProductBatch, Route
from app.models.trips import Trip, TripStatus
from app.schemas.dashboard import (
    BestSellingProduct,
    DailyCollectionPoint,
    DailySalesPoint,
    DashboardSummaryOut,
    DashboardTrendsOut,
    RouteSalesTrendOut,
)

# Fixed-order categorical route cap: past this many routes, the rest fold
# into "Other" rather than growing the series count indefinitely (see the
# dataviz skill's categorical-palette rule — a 9th series is never a
# generated hue). "Other" itself isn't part of the 8-slot palette.
MAX_ROUTE_SERIES = 8
OTHER_ROUTE_LABEL = "Other"
NO_ROUTE_LABEL = "No Route"

# Named param is "period", never "range" — this module loops with the
# builtin range(), and a query param called `range` would shadow it.
PERIOD_DAYS: dict[str, int | None] = {
    "week": 7,
    "15d": 15,
    "month": 30,
    "year": 365,
    "all": None,  # no lower bound — start from the earliest trip on record
}

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _today_range() -> tuple[datetime, datetime]:
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _period_start_date(db: Session, period: str, today: date) -> date:
    if period not in PERIOD_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period '{period}' — expected one of {sorted(PERIOD_DAYS)}",
        )
    days = PERIOD_DAYS[period]
    if days is not None:
        return today - timedelta(days=days - 1)
    earliest = db.execute(select(func.min(Trip.trip_date))).scalar_one_or_none()
    return earliest if earliest is not None else today


def _stock_movement_rows(db: Session, start_date: date | None = None, end_date: date | None = None):
    """Raw (trip_date, product_id, product_name, quantity, value) rows behind
    every value-based sales figure on this dashboard — the same formula
    app/api/v1/trips.py::_compute_reconciliation uses per trip
    ((loaded − returned − damaged) × base_price), just not scoped to a single
    trip. load_in is already positive and return_/damage are already
    negative in the vehicle-side ledger, so raw signed quantity already
    nets out to "what was actually sold" — no sign-juggling needed.

    This exists because `today_sales`/`daily_sales`/`best_selling_products`
    used to read from `sales_invoices`, which stopped being populated once
    trips moved to the simplified cash/credit/online/cheque flow — those
    figures silently went stale (flat/zero) for any trip using the new flow,
    which is the bug this fixes."""
    query = (
        select(
            Trip.trip_date,
            StockLedger.product_id,
            Product.name,
            StockLedger.quantity,
            (StockLedger.quantity * Product.base_price).label("value"),
        )
        .select_from(StockLedger)
        .join(Trip, (Trip.id == StockLedger.location_id) & (StockLedger.location_type == StockLocationType.vehicle))
        .join(Product, Product.id == StockLedger.product_id)
        .where(StockLedger.txn_type.in_([StockTxnType.load_in, StockTxnType.return_, StockTxnType.damage]))
    )
    if start_date is not None:
        query = query.where(Trip.trip_date >= start_date)
    if end_date is not None:
        query = query.where(Trip.trip_date < end_date)
    return db.execute(query).all()


@router.get("/summary", response_model=DashboardSummaryOut)
def dashboard_summary(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    start, end = _today_range()
    today = start.date()

    today_sales = sum(
        (row.value for row in _stock_movement_rows(db, today, today + timedelta(days=1))), Decimal("0")
    )

    def collected_today(mode: PaymentMode) -> Decimal:
        return db.execute(
            select(func.coalesce(func.sum(PaymentCollection.amount), 0)).where(
                PaymentCollection.payment_mode == mode,
                PaymentCollection.collected_at >= start,
                PaymentCollection.collected_at < end,
            )
        ).scalar_one()

    online_today = collected_today(PaymentMode.online)

    today_trips = db.execute(select(Trip).where(Trip.trip_date == today)).scalars().all()
    cash_today = sum((_cash_total(trip) for trip in today_trips), Decimal("0"))

    # "Pending credits" = shop-level credit entries not yet marked repaid —
    # same figure the Reconciliation page's "Yet to be Paid" tab shows (see
    # reports.py::trip_credits). Credit given always writes a
    # payment_collections row (mode=credit) regardless of which flow created
    # it (old invoice-based or the current trip-level entries), so this
    # naturally covers both.
    pending_credits_total = db.execute(
        select(func.coalesce(func.sum(PaymentCollection.amount), 0)).where(
            PaymentCollection.payment_mode == PaymentMode.credit,
            PaymentCollection.status == PaymentStatus.pending,
        )
    ).scalar_one()

    vehicles_on_route = db.execute(
        select(func.count()).select_from(Trip).where(Trip.status == TripStatus.on_route)
    ).scalar_one()

    stock_rows = db.execute(
        select(StockLedger.product_id, StockLedger.batch_id, func.sum(StockLedger.quantity))
        .where(StockLedger.location_type == StockLocationType.warehouse)
        .group_by(StockLedger.product_id, StockLedger.batch_id)
        .having(func.sum(StockLedger.quantity) > 0)
    ).all()

    stock_by_product: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    batches_in_stock: list[tuple[int, int | None]] = []
    for product_id, batch_id, qty in stock_rows:
        stock_by_product[product_id] += qty
        if batch_id is not None:
            batches_in_stock.append((product_id, batch_id))

    warehouse_stock_products = len(stock_by_product)

    near_expiry_count = 0
    if batches_in_stock:
        cutoff = today + timedelta(days=30)
        batch_ids = [b for _, b in batches_in_stock]
        near_expiry_count = db.execute(
            select(func.count())
            .select_from(ProductBatch)
            .where(ProductBatch.id.in_(batch_ids), ProductBatch.expiry_date.is_not(None), ProductBatch.expiry_date <= cutoff)
        ).scalar_one()

    products_with_reorder = db.execute(
        select(Product.id, Product.reorder_level).where(Product.reorder_level > 0)
    ).all()
    low_stock_count = sum(
        1 for product_id, reorder_level in products_with_reorder if stock_by_product.get(product_id, Decimal("0")) <= reorder_level
    )

    daily_expenses = db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.status == ExpenseStatus.approved, Expense.expense_date == today
        )
    ).scalar_one()

    profit_today = today_sales - daily_expenses

    # "Sold" isn't tracked directly anymore (no per-invoice line items once a
    # trip uses the simplified flow) — inferred the same way expected sales
    # value is: whatever left the vehicle and wasn't returned or damaged.
    qty_by_product: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    name_by_product: dict[int, str] = {}
    for row in _stock_movement_rows(db, today.replace(day=1), None):
        qty_by_product[row.product_id] += row.quantity
        name_by_product[row.product_id] = row.name
    best_selling_rows = sorted(
        ((pid, name_by_product[pid], qty) for pid, qty in qty_by_product.items() if qty > 0),
        key=lambda r: r[2],
        reverse=True,
    )[:3]

    return DashboardSummaryOut(
        today_sales=today_sales,
        cash_collected_today=cash_today,
        online_collected_today=online_today,
        pending_credits_total=pending_credits_total,
        vehicles_on_route=vehicles_on_route,
        warehouse_stock_products=warehouse_stock_products,
        near_expiry_count=near_expiry_count,
        low_stock_count=low_stock_count,
        daily_expenses=daily_expenses,
        profit_today=profit_today,
        best_selling_products=[
            BestSellingProduct(product_id=pid, name=name, quantity=qty) for pid, name, qty in best_selling_rows
        ],
    )


@router.get("/trends", response_model=DashboardTrendsOut)
def dashboard_trends(
    period: str = Query("15d"), db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    today = datetime.now(timezone.utc).date()
    start_date = _period_start_date(db, period, today)
    days = (today - start_date).days + 1
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)

    sales_by_date: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in _stock_movement_rows(db, start_date, None):
        sales_by_date[row.trip_date] += row.value

    # Cash isn't a payment_collections row anymore (it's denomination counts
    # directly on trips — see trips.py::_cash_total), so it has to be
    # aggregated per trip_date separately from online/credit, which are
    # still real payment_collections rows regardless of which flow (old
    # invoice-based or current trip-level entries) created them.
    cash_by_date: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    for trip in db.execute(select(Trip).where(Trip.trip_date >= start_date)).scalars().all():
        cash_by_date[trip.trip_date] += _cash_total(trip)

    collection_rows = db.execute(
        select(func.date(PaymentCollection.collected_at), PaymentCollection.payment_mode, func.sum(PaymentCollection.amount))
        .where(PaymentCollection.collected_at >= start_dt, PaymentCollection.payment_mode != PaymentMode.cash)
        .group_by(func.date(PaymentCollection.collected_at), PaymentCollection.payment_mode)
    ).all()
    collections_by_date: dict[date, dict[str, Decimal]] = defaultdict(
        lambda: {"cash": Decimal("0"), "online": Decimal("0"), "credit": Decimal("0")}
    )
    for d, mode, total in collection_rows:
        if mode.value in ("online", "credit"):
            collections_by_date[d][mode.value] = total
    for d, cash_total in cash_by_date.items():
        collections_by_date[d]["cash"] = cash_total

    daily_sales = []
    daily_collections = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        daily_sales.append(DailySalesPoint(date=d, total=sales_by_date.get(d, Decimal("0"))))
        bucket = collections_by_date.get(d, {"cash": Decimal("0"), "online": Decimal("0"), "credit": Decimal("0")})
        daily_collections.append(
            DailyCollectionPoint(date=d, cash=bucket["cash"], online=bucket["online"], credit=bucket["credit"])
        )

    return DashboardTrendsOut(daily_sales=daily_sales, daily_collections=daily_collections)


@router.get("/route-sales-trend", response_model=RouteSalesTrendOut)
def route_sales_trend(
    period: str = Query("15d"), db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    """Per-route daily sales value, computed the same way trip reconciliation
    computes expected value — (loaded - returned - damaged) x base_price —
    not from sales_invoices, since trips using the simplified cash/credit/
    online flow never create one. load_in is already positive and
    return_/damage are already negative in the vehicle-side ledger (see
    app/api/v1/trips.py::update_stock_sheet), so summing raw signed quantity
    per trip/product and multiplying by base_price gives that figure
    directly, no sign-juggling needed."""
    today = datetime.now(timezone.utc).date()
    start_date = _period_start_date(db, period, today)
    days = (today - start_date).days + 1

    rows = db.execute(
        select(
            Trip.trip_date,
            Trip.route_id,
            Route.name,
            func.sum(StockLedger.quantity * Product.base_price),
        )
        .select_from(StockLedger)
        .join(Trip, (Trip.id == StockLedger.location_id) & (StockLedger.location_type == StockLocationType.vehicle))
        .join(Product, Product.id == StockLedger.product_id)
        .outerjoin(Route, Route.id == Trip.route_id)
        .where(
            StockLedger.txn_type.in_([StockTxnType.load_in, StockTxnType.return_, StockTxnType.damage]),
            Trip.trip_date >= start_date,
        )
        .group_by(Trip.trip_date, Trip.route_id, Route.name)
    ).all()

    def route_label(route_id: int | None, route_name: str | None) -> str:
        return route_name if route_id is not None and route_name else NO_ROUTE_LABEL

    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_date: dict[date, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    label_route_id: dict[str, int] = {}
    for trip_date, route_id, route_name, value in rows:
        label = route_label(route_id, route_name)
        totals[label] += value
        by_date[trip_date][label] += value
        # Sort key for stable color assignment below — route identity, not
        # day-to-day value ranking, decides which slot a route keeps (only
        # which routes make the top-N cut is value-based, not their order).
        label_route_id[label] = route_id if route_id is not None else 10**9

    # Which routes make the cut is by total value (busiest routes shown);
    # their on-screen ORDER (and therefore color slot) is by route id, so a
    # route doesn't jump color slots between requests just because its
    # ranking shifted — see the dataviz skill's "color follows the entity,
    # never its rank" rule.
    ranked_by_value = sorted(totals, key=lambda label: totals[label], reverse=True)
    kept_routes = sorted(ranked_by_value[:MAX_ROUTE_SERIES], key=lambda label: label_route_id[label])
    overflow_routes = set(ranked_by_value[MAX_ROUTE_SERIES:])
    route_names = kept_routes + ([OTHER_ROUTE_LABEL] if overflow_routes else [])

    points: list[dict[str, Any]] = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        point: dict[str, Any] = {"date": d.isoformat()}
        day_values = by_date.get(d, {})
        for label in kept_routes:
            point[label] = float(day_values.get(label, Decimal("0")))
        if overflow_routes:
            point[OTHER_ROUTE_LABEL] = float(sum((day_values.get(r, Decimal("0")) for r in overflow_routes), Decimal("0")))
        points.append(point)

    return RouteSalesTrendOut(route_names=route_names, points=points)
