from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models import User
from app.models.collections import PaymentCollection, PaymentMode
from app.models.inventory import StockLedger, StockLocationType
from app.models.masters import Customer, Employee, Product, Warehouse
from app.models.sales import SalesInvoice, SalesInvoiceItem
from app.models.trips import Trip
from app.schemas.reports import (
    CollectionsSummaryOut,
    CustomerAgingRow,
    SalesByCustomerRow,
    SalesByProductRow,
    StockReportRow,
)
from app.schemas.trips import ChequeLogRow, CreditLogRow

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/stock", response_model=list[StockReportRow])
def stock_report(db: Session = Depends(get_db), _user: User = Depends(require_permission("can_view_reports"))):
    rows = db.execute(
        select(
            StockLedger.location_id,
            StockLedger.product_id,
            func.sum(StockLedger.quantity).label("quantity"),
        )
        .where(StockLedger.location_type == StockLocationType.warehouse)
        .group_by(StockLedger.location_id, StockLedger.product_id)
        .having(func.sum(StockLedger.quantity) != 0)
    ).all()

    warehouses = {w.id: w for w in db.execute(select(Warehouse)).scalars().all()}
    products = {p.id: p for p in db.execute(select(Product)).scalars().all()}

    result = []
    for warehouse_id, product_id, quantity in rows:
        warehouse = warehouses.get(warehouse_id)
        product = products.get(product_id)
        if warehouse is None or product is None:
            continue
        result.append(
            StockReportRow(
                warehouse_id=warehouse_id,
                warehouse_name=warehouse.name,
                product_id=product_id,
                sku=product.sku,
                name=product.name,
                unit=product.unit,
                quantity=quantity,
            )
        )
    return result


@router.get("/sales-by-product", response_model=list[SalesByProductRow])
def sales_by_product(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_view_reports")),
):
    query = (
        select(
            SalesInvoiceItem.product_id,
            func.sum(SalesInvoiceItem.quantity).label("total_quantity"),
            func.sum(SalesInvoiceItem.line_total).label("total_revenue"),
        )
        .join(SalesInvoice, SalesInvoice.id == SalesInvoiceItem.invoice_id)
        .group_by(SalesInvoiceItem.product_id)
    )
    if start_date:
        query = query.where(SalesInvoice.invoice_date >= start_date)
    if end_date:
        query = query.where(SalesInvoice.invoice_date < end_date)

    rows = db.execute(query).all()
    products = {p.id: p for p in db.execute(select(Product)).scalars().all()}

    result = []
    for product_id, total_quantity, total_revenue in rows:
        product = products.get(product_id)
        if product is None:
            continue
        result.append(
            SalesByProductRow(
                product_id=product_id,
                sku=product.sku,
                name=product.name,
                total_quantity=total_quantity,
                total_revenue=total_revenue,
            )
        )
    return result


@router.get("/sales-by-customer", response_model=list[SalesByCustomerRow])
def sales_by_customer(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_view_reports")),
):
    query = select(
        SalesInvoice.customer_id,
        func.count(SalesInvoice.id).label("invoice_count"),
        func.sum(SalesInvoice.total_amount).label("total_amount"),
    ).group_by(SalesInvoice.customer_id)
    if start_date:
        query = query.where(SalesInvoice.invoice_date >= start_date)
    if end_date:
        query = query.where(SalesInvoice.invoice_date < end_date)

    rows = db.execute(query).all()
    customers = {c.id: c for c in db.execute(select(Customer)).scalars().all()}

    result = []
    for customer_id, invoice_count, total_amount in rows:
        customer = customers.get(customer_id)
        if customer is None:
            continue
        result.append(
            SalesByCustomerRow(
                customer_id=customer_id,
                customer_name=customer.name,
                invoice_count=invoice_count,
                total_amount=total_amount,
            )
        )
    return result


@router.get("/collections-summary", response_model=CollectionsSummaryOut)
def collections_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_view_reports")),
):
    def total_for(mode: PaymentMode) -> Decimal:
        query = select(func.coalesce(func.sum(PaymentCollection.amount), 0)).where(
            PaymentCollection.payment_mode == mode
        )
        if start_date:
            query = query.where(PaymentCollection.collected_at >= start_date)
        if end_date:
            query = query.where(PaymentCollection.collected_at < end_date)
        return db.execute(query).scalar_one()

    cash_total = total_for(PaymentMode.cash)
    online_total = total_for(PaymentMode.online)
    credit_total = total_for(PaymentMode.credit)
    return CollectionsSummaryOut(
        cash_total=cash_total,
        online_total=online_total,
        credit_total=credit_total,
        grand_total=cash_total + online_total + credit_total,
    )


def _trip_money_log(db: Session, mode: PaymentMode):
    """Shared lookup behind the trip-credits and trip-cheques report rows —
    both are a flat log of shop/amount/mode entered directly on a trip
    (no invoice), just with a different payment_mode and (for cheques) two
    extra date columns."""
    entries = (
        db.execute(
            select(PaymentCollection)
            .where(PaymentCollection.payment_mode == mode, PaymentCollection.trip_id.is_not(None))
            .order_by(PaymentCollection.id.desc())
        )
        .scalars()
        .all()
    )
    trips = {t.id: t for t in db.execute(select(Trip)).scalars().all()}
    customers = {c.id: c for c in db.execute(select(Customer)).scalars().all()}
    employees = {e.id: e for e in db.execute(select(Employee)).scalars().all()}
    return entries, trips, customers, employees


@router.get("/trip-credits", response_model=list[CreditLogRow])
def trip_credits(db: Session = Depends(get_db), _user: User = Depends(require_permission("can_view_reports"))):
    """Every shop-level credit entered directly on a trip (no invoice) —
    see app/api/v1/trips.py::create_credit_entry. Distinct from
    /customer-aging, which buckets invoice-based outstanding by age; this is
    a flat log of who got credit, how much, on which trip, from which
    driver."""
    entries, trips, customers, employees = _trip_money_log(db, PaymentMode.credit)

    result = []
    for entry in entries:
        trip = trips.get(entry.trip_id)
        customer = customers.get(entry.customer_id)
        if trip is None or customer is None:
            continue
        driver = employees.get(trip.driver_id)
        result.append(
            CreditLogRow(
                id=entry.id,
                trip_id=entry.trip_id,
                customer_id=entry.customer_id,
                customer_name=customer.name,
                amount=entry.amount,
                status=entry.status.value,
                trip_date=trip.trip_date,
                driver_id=trip.driver_id,
                driver_name=driver.name if driver else "?",
            )
        )
    return result


@router.get("/trip-cheques", response_model=list[ChequeLogRow])
def trip_cheques(db: Session = Depends(get_db), _user: User = Depends(require_permission("can_view_reports"))):
    """Every cheque entered directly on a trip — see
    app/api/v1/trips.py::create_cheque_entry. Same shape as /trip-credits
    plus the two cheque-specific dates."""
    entries, trips, customers, employees = _trip_money_log(db, PaymentMode.cheque)

    result = []
    for entry in entries:
        trip = trips.get(entry.trip_id)
        customer = customers.get(entry.customer_id)
        if trip is None or customer is None:
            continue
        driver = employees.get(trip.driver_id)
        result.append(
            ChequeLogRow(
                id=entry.id,
                trip_id=entry.trip_id,
                customer_id=entry.customer_id,
                customer_name=customer.name,
                amount=entry.amount,
                status=entry.status.value,
                cheque_given_date=entry.cheque_given_date,
                cheque_deposit_date=entry.cheque_deposit_date,
                trip_date=trip.trip_date,
                driver_id=trip.driver_id,
                driver_name=driver.name if driver else "?",
            )
        )
    return result


@router.get("/customer-aging", response_model=list[CustomerAgingRow])
def customer_aging(db: Session = Depends(get_db), _user: User = Depends(require_permission("can_view_reports"))):
    # Outstanding = invoice total minus cash collections against it (credit
    # collections don't reduce outstanding — see app/api/v1/trips.py — and
    # online collections stay outstanding until Phase 2 reconciliation clears
    # them onto the ledger).
    invoices = db.execute(
        select(SalesInvoice.id, SalesInvoice.customer_id, SalesInvoice.invoice_date, SalesInvoice.total_amount)
    ).all()
    cash_by_invoice: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for invoice_id, amount in db.execute(
        select(PaymentCollection.invoice_id, PaymentCollection.amount).where(
            PaymentCollection.payment_mode == PaymentMode.cash, PaymentCollection.invoice_id.is_not(None)
        )
    ).all():
        cash_by_invoice[invoice_id] += amount

    today = datetime.now(timezone.utc).date()
    buckets: dict[int, dict[str, Decimal]] = defaultdict(
        lambda: {"0_30": Decimal("0"), "31_60": Decimal("0"), "61_90": Decimal("0"), "over_90": Decimal("0")}
    )
    for invoice_id, customer_id, invoice_date, total_amount in invoices:
        outstanding = total_amount - cash_by_invoice.get(invoice_id, Decimal("0"))
        if outstanding <= Decimal("0.01"):
            continue
        age_days = (today - invoice_date.date()).days
        bucket = buckets[customer_id]
        if age_days <= 30:
            bucket["0_30"] += outstanding
        elif age_days <= 60:
            bucket["31_60"] += outstanding
        elif age_days <= 90:
            bucket["61_90"] += outstanding
        else:
            bucket["over_90"] += outstanding

    customers = {c.id: c for c in db.execute(select(Customer)).scalars().all()}
    result = []
    for customer_id, bucket in buckets.items():
        customer = customers.get(customer_id)
        if customer is None:
            continue
        total_outstanding = bucket["0_30"] + bucket["31_60"] + bucket["61_90"] + bucket["over_90"]
        result.append(
            CustomerAgingRow(
                customer_id=customer_id,
                customer_name=customer.name,
                credit_limit=customer.credit_limit,
                current_0_30=bucket["0_30"],
                days_31_60=bucket["31_60"],
                days_61_90=bucket["61_90"],
                over_90=bucket["over_90"],
                total_outstanding=total_outstanding,
                over_limit=total_outstanding > customer.credit_limit if customer.credit_limit > 0 else False,
            )
        )
    return sorted(result, key=lambda r: r.total_outstanding, reverse=True)
