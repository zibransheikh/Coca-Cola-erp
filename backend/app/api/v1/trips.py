from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models import User
from app.models.collections import PaymentCollection, PaymentMode, PaymentStatus, PendingOnlinePayment
from app.models.inventory import StockLedger, StockLocationType, StockTxnType
from app.models.ledger import CustomerLedger, LedgerTxnType
from app.models.masters import Product
from app.models.sales import SalesInvoice, SalesInvoiceItem
from app.models.trips import Trip, TripStatus, TripStockCount
from app.schemas.trips import (
    CashCountUpdate,
    ChequeEntryCreate,
    ChequeEntryOut,
    CollectionCreate,
    CollectionOut,
    CratesOut,
    CratesUpdate,
    CreditLogRow,
    InvoiceCreate,
    InvoiceOut,
    MoneyEntryCreate,
    MoneyEntryOut,
    MoneyEntryStatusUpdate,
    ReconciliationOut,
    ReconciliationProductRow,
    StockSheetRequest,
    StockSheetRowOut,
    TripCloseRequest,
    TripCreate,
    TripOut,
)
from app.services import accounting as acct
from app.services.accounting import post_journal_entry
from app.services.stock import location_stock_levels, stock_quantity, write_ledger_entry

router = APIRouter(prefix="/trips", tags=["trips"])

RECONCILIATION_TOLERANCE = Decimal("0.01")


def _get_trip_or_404(db: Session, trip_id: int) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


def _latest_customer_balance(db: Session, customer_id: int) -> Decimal:
    row = db.execute(
        select(CustomerLedger.balance_after)
        .where(CustomerLedger.customer_id == customer_id)
        .order_by(CustomerLedger.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    return row if row is not None else Decimal("0")


@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    trip = Trip(
        vehicle_id=payload.vehicle_id,
        driver_id=payload.driver_id,
        route_id=payload.route_id,
        warehouse_id=payload.warehouse_id,
        trip_date=payload.trip_date,
        status=TripStatus.loading,
        opened_by=user.id,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("", response_model=list[TripOut])
def list_trips(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.execute(select(Trip).order_by(Trip.trip_date.desc(), Trip.id.desc())).scalars().all()


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(trip_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return _get_trip_or_404(db, trip_id)


def _vehicle_txn_totals(db: Session, trip_id: int, txn_type: StockTxnType) -> dict[int, Decimal]:
    """Positive total quantity moved for this txn_type at the vehicle for
    this trip, per product — load_in sums are naturally positive and
    sale/return/damage sums are naturally negative, so abs() normalizes
    both to "how much of this has happened so far"."""
    rows = db.execute(
        select(StockLedger.product_id, func.sum(StockLedger.quantity))
        .where(
            StockLedger.location_type == StockLocationType.vehicle,
            StockLedger.location_id == trip_id,
            StockLedger.txn_type == txn_type,
        )
        .group_by(StockLedger.product_id)
    ).all()
    return {product_id: abs(total) for product_id, total in rows}


def _stock_sheet(db: Session, trip: Trip) -> list[StockSheetRowOut]:
    products = (
        db.execute(select(Product).where(Product.is_active).order_by(Product.volume_ml, Product.name))
        .scalars()
        .all()
    )
    warehouse_stock = {
        product_id: quantity
        for product_id, _batch_id, quantity in location_stock_levels(
            db, location_type=StockLocationType.warehouse, location_id=trip.warehouse_id
        )
    }
    loaded = _vehicle_txn_totals(db, trip.id, StockTxnType.load_in)
    returned = _vehicle_txn_totals(db, trip.id, StockTxnType.return_)
    damaged = _vehicle_txn_totals(db, trip.id, StockTxnType.damage)

    rows = []
    for product in products:
        rows.append(
            StockSheetRowOut(
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                unit=product.unit,
                base_price=product.base_price,
                warehouse_available=warehouse_stock.get(product.id, Decimal("0")),
                loaded_quantity=loaded.get(product.id, Decimal("0")),
                returned_quantity=returned.get(product.id, Decimal("0")),
                damaged_quantity=damaged.get(product.id, Decimal("0")),
            )
        )
    return rows


@router.get("/{trip_id}/stock-sheet", response_model=list[StockSheetRowOut])
def get_stock_sheet(trip_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    trip = _get_trip_or_404(db, trip_id)
    return _stock_sheet(db, trip)


@router.put("/{trip_id}/stock-sheet", response_model=list[StockSheetRowOut])
def update_stock_sheet(
    trip_id: int, payload: StockSheetRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """One editable sheet for the whole trip: every row's loaded/returned/
    damaged quantities are the new TOTALS, not deltas to add — resubmitting
    the same values is a no-op, and changing a value only posts a ledger
    entry for the difference. This is what makes the grid safely re-editable
    instead of double-counting on every save."""
    trip = _get_trip_or_404(db, trip_id)
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip is closed")

    loaded_so_far = _vehicle_txn_totals(db, trip.id, StockTxnType.load_in)
    sold_so_far = _vehicle_txn_totals(db, trip.id, StockTxnType.sale)
    returned_so_far = _vehicle_txn_totals(db, trip.id, StockTxnType.return_)
    damaged_so_far = _vehicle_txn_totals(db, trip.id, StockTxnType.damage)

    for row in payload.rows:
        product = db.get(Product, row.product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown product_id {row.product_id}")

        cur_loaded = loaded_so_far.get(row.product_id, Decimal("0"))
        cur_sold = sold_so_far.get(row.product_id, Decimal("0"))
        cur_returned = returned_so_far.get(row.product_id, Decimal("0"))
        cur_damaged = damaged_so_far.get(row.product_id, Decimal("0"))

        floor = cur_sold + row.returned_quantity + row.damaged_quantity
        if row.loaded_quantity < floor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{product.name}: loaded quantity ({row.loaded_quantity}) can't be less than "
                f"sold + returned + damaged ({floor})",
            )

        load_delta = row.loaded_quantity - cur_loaded
        if load_delta > 0:
            available = stock_quantity(
                db, location_type=StockLocationType.warehouse, location_id=trip.warehouse_id, product_id=row.product_id
            )
            if load_delta > available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{product.name}: need {load_delta} more to load, only {available} available in warehouse",
                )
        if load_delta != 0:
            write_ledger_entry(
                db,
                location_type=StockLocationType.warehouse,
                location_id=trip.warehouse_id,
                product_id=row.product_id,
                batch_id=None,
                txn_type=StockTxnType.load_out,
                quantity=-load_delta,
                reference_type="trip",
                reference_id=trip.id,
                created_by=user.id,
            )
            write_ledger_entry(
                db,
                location_type=StockLocationType.vehicle,
                location_id=trip.id,
                product_id=row.product_id,
                batch_id=None,
                txn_type=StockTxnType.load_in,
                quantity=load_delta,
                reference_type="trip",
                reference_id=trip.id,
                created_by=user.id,
            )

        returned_delta = row.returned_quantity - cur_returned
        if returned_delta != 0:
            write_ledger_entry(
                db,
                location_type=StockLocationType.vehicle,
                location_id=trip.id,
                product_id=row.product_id,
                batch_id=None,
                txn_type=StockTxnType.return_,
                quantity=-returned_delta,
                reference_type="trip",
                reference_id=trip.id,
                created_by=user.id,
            )
            write_ledger_entry(
                db,
                location_type=StockLocationType.warehouse,
                location_id=trip.warehouse_id,
                product_id=row.product_id,
                batch_id=None,
                txn_type=StockTxnType.return_,
                quantity=returned_delta,
                reference_type="trip",
                reference_id=trip.id,
                created_by=user.id,
            )

        damaged_delta = row.damaged_quantity - cur_damaged
        if damaged_delta != 0:
            write_ledger_entry(
                db,
                location_type=StockLocationType.vehicle,
                location_id=trip.id,
                product_id=row.product_id,
                batch_id=None,
                txn_type=StockTxnType.damage,
                quantity=-damaged_delta,
                reference_type="trip",
                reference_id=trip.id,
                created_by=user.id,
            )

        existing_count = db.execute(
            select(TripStockCount).where(
                TripStockCount.trip_id == trip.id,
                TripStockCount.product_id == row.product_id,
                TripStockCount.batch_id.is_(None),
            )
        ).scalar_one_or_none()
        if existing_count:
            existing_count.returned_quantity = row.returned_quantity
            existing_count.damaged_quantity = row.damaged_quantity
            existing_count.counted_by = user.id
        else:
            db.add(
                TripStockCount(
                    trip_id=trip.id,
                    product_id=row.product_id,
                    batch_id=None,
                    returned_quantity=row.returned_quantity,
                    damaged_quantity=row.damaged_quantity,
                    counted_by=user.id,
                )
            )

    db.commit()
    return _stock_sheet(db, trip)


def _cash_total(trip: Trip) -> Decimal:
    return (
        trip.cash_count_500 * 500
        + trip.cash_count_200 * 200
        + trip.cash_count_100 * 100
        + trip.cash_count_50 * 50
        + trip.cash_count_20 * 20
        + trip.cash_count_10 * 10
        + trip.cash_coins_amount
    )


@router.put("/{trip_id}/cash-count", response_model=TripOut)
def update_cash_count(
    trip_id: int, payload: CashCountUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    trip = _get_trip_or_404(db, trip_id)
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip is closed")

    trip.cash_count_500 = payload.cash_count_500
    trip.cash_count_200 = payload.cash_count_200
    trip.cash_count_100 = payload.cash_count_100
    trip.cash_count_50 = payload.cash_count_50
    trip.cash_count_20 = payload.cash_count_20
    trip.cash_count_10 = payload.cash_count_10
    trip.cash_coins_amount = payload.cash_coins_amount
    db.commit()
    db.refresh(trip)
    return trip


def _crates_out(db: Session, trip_id: int) -> Decimal:
    """Crates loaded onto the vehicle this trip, summed across every
    unit='crate' product — not user-entered, so it can't drift from what the
    stock sheet actually says was loaded."""
    loaded = _vehicle_txn_totals(db, trip_id, StockTxnType.load_in)
    crate_product_ids = (
        db.execute(select(Product.id).where(func.lower(Product.unit) == "crate")).scalars().all()
    )
    return sum((loaded.get(pid, Decimal("0")) for pid in crate_product_ids), Decimal("0"))


@router.get("/{trip_id}/crates", response_model=CratesOut)
def get_crates(trip_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    trip = _get_trip_or_404(db, trip_id)
    return CratesOut(crates_out=_crates_out(db, trip_id), crates_in=trip.crates_in)


@router.put("/{trip_id}/crates", response_model=CratesOut)
def update_crates(
    trip_id: int, payload: CratesUpdate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    trip = _get_trip_or_404(db, trip_id)
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip is closed")

    trip.crates_in = payload.crates_in
    db.commit()
    return CratesOut(crates_out=_crates_out(db, trip_id), crates_in=trip.crates_in)


def _create_money_entry(
    db: Session,
    trip: Trip,
    payload: MoneyEntryCreate | ChequeEntryCreate,
    mode: PaymentMode,
    user: User,
    extra_fields: dict | None = None,
) -> PaymentCollection:
    """Per-shop credit given, online payment received, or cheque received on
    this trip, entered directly instead of via a formal invoice. Reuses
    payment_collections with invoice_id left null — that table's comment
    already describes exactly this: "shop, amount, mode. Nothing more."
    Writes a customer_ledger debit itself, since (unlike the invoice flow)
    there's no invoice already recording the outstanding amount. Online
    entries additionally create a pending_online_payments row so the
    existing bank-statement reconciliation engine can later confirm the
    transfer actually landed (crediting the ledger back at that point, via
    app/services/reconciliation.py::resolve_match) — credit and cheque
    entries settle by manual paid/pending toggle instead (see
    _set_money_entry_paid), since there's no bank statement to match a
    cheque against automatically. `extra_fields` sets cheque-only columns
    (cheque_given_date/cheque_deposit_date) without credit/online needing to
    know about them."""
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip is closed")
    if payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")

    entry = PaymentCollection(
        invoice_id=None,
        customer_id=payload.customer_id,
        trip_id=trip.id,
        amount=payload.amount,
        payment_mode=mode,
        status=PaymentStatus.awaiting_bank_verification if mode == PaymentMode.online else PaymentStatus.pending,
        collected_by=user.id,
        **(extra_fields or {}),
    )
    db.add(entry)
    db.flush()

    prev_balance = _latest_customer_balance(db, payload.customer_id)
    db.add(
        CustomerLedger(
            customer_id=payload.customer_id,
            txn_type=LedgerTxnType.invoice,
            reference_type="payment_collection",
            reference_id=entry.id,
            debit=payload.amount,
            credit=Decimal("0"),
            balance_after=prev_balance + payload.amount,
        )
    )
    if mode == PaymentMode.online:
        db.add(
            PendingOnlinePayment(
                payment_collection_id=entry.id,
                customer_id=payload.customer_id,
                amount=payload.amount,
            )
        )
    db.commit()
    db.refresh(entry)
    return entry


def _list_money_entries(db: Session, trip_id: int, mode: PaymentMode) -> list[PaymentCollection]:
    return (
        db.execute(
            select(PaymentCollection)
            .where(PaymentCollection.trip_id == trip_id, PaymentCollection.payment_mode == mode)
            .order_by(PaymentCollection.id)
        )
        .scalars()
        .all()
    )


def _delete_money_entry(db: Session, trip: Trip, entry_id: int, mode: PaymentMode) -> None:
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip is closed")

    entry = db.execute(
        select(PaymentCollection).where(
            PaymentCollection.id == entry_id,
            PaymentCollection.trip_id == trip.id,
            PaymentCollection.payment_mode == mode,
        )
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    if mode == PaymentMode.online:
        pending = db.execute(
            select(PendingOnlinePayment).where(PendingOnlinePayment.payment_collection_id == entry.id)
        ).scalar_one_or_none()
        if pending is not None and pending.resolved_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already confirmed via bank reconciliation — can't remove",
            )
        if pending is not None:
            db.delete(pending)
            db.flush()  # no ORM relationship links these, so the FK-respecting
            # delete order has to be forced explicitly rather than left to SQLAlchemy

    # customer_ledger is append-only, so undo by adding the reversing entry
    # rather than touching the original debit.
    prev_balance = _latest_customer_balance(db, entry.customer_id)
    db.add(
        CustomerLedger(
            customer_id=entry.customer_id,
            txn_type=LedgerTxnType.credit_note,
            reference_type="payment_collection",
            reference_id=entry.id,
            debit=Decimal("0"),
            credit=entry.amount,
            balance_after=prev_balance - entry.amount,
        )
    )
    db.delete(entry)
    db.commit()


def _unpaid_status(mode: PaymentMode) -> PaymentStatus:
    return PaymentStatus.awaiting_bank_verification if mode == PaymentMode.online else PaymentStatus.pending


def _set_money_entry_paid(db: Session, trip: Trip, entry_id: int, mode: PaymentMode, paid: bool) -> PaymentCollection:
    """Manual paid/pending toggle for a credit or online entry — lets a
    manager mark a shop's credit as repaid, or an online payment as received,
    without waiting on (or in place of) the slower bank-statement
    reconciliation engine. Moves customer_ledger the same direction
    resolve_match() would, so the outstanding balance stays correct either
    way this gets marked. For online entries this also flips
    pending_online_payments.resolved_at, so this is a genuine manual
    override of that flow, not just a cosmetic label — this is a
    deliberate simplification: it doesn't check whether the entry was
    already cleared by a real bank match, it just moves the flag."""
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip is closed")

    entry = db.execute(
        select(PaymentCollection).where(
            PaymentCollection.id == entry_id,
            PaymentCollection.trip_id == trip.id,
            PaymentCollection.payment_mode == mode,
        )
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    was_paid = entry.status == PaymentStatus.cleared
    if was_paid == paid:
        return entry

    prev_balance = _latest_customer_balance(db, entry.customer_id)
    if paid:
        db.add(
            CustomerLedger(
                customer_id=entry.customer_id,
                txn_type=LedgerTxnType.payment,
                reference_type="payment_collection",
                reference_id=entry.id,
                debit=Decimal("0"),
                credit=entry.amount,
                balance_after=prev_balance - entry.amount,
            )
        )
    else:
        db.add(
            CustomerLedger(
                customer_id=entry.customer_id,
                txn_type=LedgerTxnType.debit_note,
                reference_type="payment_collection",
                reference_id=entry.id,
                debit=entry.amount,
                credit=Decimal("0"),
                balance_after=prev_balance + entry.amount,
            )
        )

    if mode == PaymentMode.online:
        pending = db.execute(
            select(PendingOnlinePayment).where(PendingOnlinePayment.payment_collection_id == entry.id)
        ).scalar_one_or_none()
        if pending is not None:
            pending.resolved_at = datetime.now(timezone.utc) if paid else None

    entry.status = PaymentStatus.cleared if paid else _unpaid_status(mode)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{trip_id}/credit-entries", response_model=MoneyEntryOut, status_code=status.HTTP_201_CREATED)
def create_credit_entry(
    trip_id: int, payload: MoneyEntryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    trip = _get_trip_or_404(db, trip_id)
    return _create_money_entry(db, trip, payload, PaymentMode.credit, user)


@router.get("/{trip_id}/credit-entries", response_model=list[MoneyEntryOut])
def list_credit_entries(trip_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    _get_trip_or_404(db, trip_id)
    return _list_money_entries(db, trip_id, PaymentMode.credit)


@router.delete("/{trip_id}/credit-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credit_entry(
    trip_id: int, entry_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    trip = _get_trip_or_404(db, trip_id)
    _delete_money_entry(db, trip, entry_id, PaymentMode.credit)


@router.patch("/{trip_id}/credit-entries/{entry_id}", response_model=MoneyEntryOut)
def update_credit_entry_status(
    trip_id: int,
    entry_id: int,
    payload: MoneyEntryStatusUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    trip = _get_trip_or_404(db, trip_id)
    return _set_money_entry_paid(db, trip, entry_id, PaymentMode.credit, payload.paid)


@router.post("/{trip_id}/online-entries", response_model=MoneyEntryOut, status_code=status.HTTP_201_CREATED)
def create_online_entry(
    trip_id: int, payload: MoneyEntryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    trip = _get_trip_or_404(db, trip_id)
    return _create_money_entry(db, trip, payload, PaymentMode.online, user)


@router.get("/{trip_id}/online-entries", response_model=list[MoneyEntryOut])
def list_online_entries(trip_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    _get_trip_or_404(db, trip_id)
    return _list_money_entries(db, trip_id, PaymentMode.online)


@router.delete("/{trip_id}/online-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_online_entry(
    trip_id: int, entry_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    trip = _get_trip_or_404(db, trip_id)
    _delete_money_entry(db, trip, entry_id, PaymentMode.online)


@router.patch("/{trip_id}/online-entries/{entry_id}", response_model=MoneyEntryOut)
def update_online_entry_status(
    trip_id: int,
    entry_id: int,
    payload: MoneyEntryStatusUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    trip = _get_trip_or_404(db, trip_id)
    return _set_money_entry_paid(db, trip, entry_id, PaymentMode.online, payload.paid)


@router.post("/{trip_id}/cheque-entries", response_model=ChequeEntryOut, status_code=status.HTTP_201_CREATED)
def create_cheque_entry(
    trip_id: int, payload: ChequeEntryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    trip = _get_trip_or_404(db, trip_id)
    return _create_money_entry(
        db,
        trip,
        payload,
        PaymentMode.cheque,
        user,
        extra_fields={
            "cheque_given_date": payload.cheque_given_date,
            "cheque_deposit_date": payload.cheque_deposit_date,
        },
    )


@router.get("/{trip_id}/cheque-entries", response_model=list[ChequeEntryOut])
def list_cheque_entries(trip_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    _get_trip_or_404(db, trip_id)
    return _list_money_entries(db, trip_id, PaymentMode.cheque)


@router.delete("/{trip_id}/cheque-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cheque_entry(
    trip_id: int, entry_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    trip = _get_trip_or_404(db, trip_id)
    _delete_money_entry(db, trip, entry_id, PaymentMode.cheque)


@router.patch("/{trip_id}/cheque-entries/{entry_id}", response_model=ChequeEntryOut)
def update_cheque_entry_status(
    trip_id: int,
    entry_id: int,
    payload: MoneyEntryStatusUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    trip = _get_trip_or_404(db, trip_id)
    return _set_money_entry_paid(db, trip, entry_id, PaymentMode.cheque, payload.paid)


@router.post("/{trip_id}/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    trip_id: int, payload: InvoiceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    trip = _get_trip_or_404(db, trip_id)
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip is closed")
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice must have at least one item")

    for item in payload.items:
        available = stock_quantity(
            db,
            location_type=StockLocationType.vehicle,
            location_id=trip.id,
            product_id=item.product_id,
            batch_id=item.batch_id,
        )
        if item.quantity > available:
            product = db.get(Product, item.product_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough vehicle stock for {product.name if product else item.product_id}: "
                f"requested {item.quantity}, available {available}",
            )

    subtotal = Decimal("0")
    tax_amount = Decimal("0")
    line_totals = []
    for item in payload.items:
        line_subtotal = (item.quantity * item.unit_price).quantize(Decimal("0.01"))
        line_tax = (line_subtotal * item.tax_rate / Decimal("100")).quantize(Decimal("0.01"))
        subtotal += line_subtotal
        tax_amount += line_tax
        line_totals.append(line_subtotal + line_tax)
    total_amount = subtotal + tax_amount

    # sales_invoices is append-only (no UPDATE allowed, see db/schema.sql), so
    # the invoice_number has to be decided before the one and only INSERT —
    # it can't be patched in afterwards once the row has an id.
    next_seq = db.execute(select(func.count()).select_from(SalesInvoice)).scalar_one() + 1
    invoice = SalesInvoice(
        invoice_number=f"INV-{next_seq:06d}",
        trip_id=trip.id,
        customer_id=payload.customer_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        created_by=user.id,
    )
    db.add(invoice)
    db.flush()

    for item, line_total in zip(payload.items, line_totals):
        db.add(
            SalesInvoiceItem(
                invoice_id=invoice.id,
                product_id=item.product_id,
                batch_id=item.batch_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
                line_total=line_total,
            )
        )
        write_ledger_entry(
            db,
            location_type=StockLocationType.vehicle,
            location_id=trip.id,
            product_id=item.product_id,
            batch_id=item.batch_id,
            txn_type=StockTxnType.sale,
            quantity=-item.quantity,
            reference_type="sales_invoice",
            reference_id=invoice.id,
            created_by=user.id,
        )

    prev_balance = _latest_customer_balance(db, payload.customer_id)
    db.add(
        CustomerLedger(
            customer_id=payload.customer_id,
            txn_type=LedgerTxnType.invoice,
            reference_type="sales_invoice",
            reference_id=invoice.id,
            debit=total_amount,
            credit=Decimal("0"),
            balance_after=prev_balance + total_amount,
        )
    )

    je_lines = [(acct.ACCOUNTS_RECEIVABLE, total_amount, Decimal("0")), (acct.SALES_REVENUE, Decimal("0"), subtotal)]
    if tax_amount > 0:
        je_lines.append((acct.GST_OUTPUT_TAX_PAYABLE, Decimal("0"), tax_amount))
    post_journal_entry(
        db,
        entry_date=datetime.now(timezone.utc).date(),
        reference_type="sales_invoice",
        reference_id=invoice.id,
        narration=f"Sales invoice {invoice.invoice_number}",
        lines=je_lines,
        created_by=user.id,
    )

    db.commit()
    return db.execute(
        select(SalesInvoice).where(SalesInvoice.id == invoice.id).options(selectinload(SalesInvoice.items))
    ).scalar_one()


@router.get("/{trip_id}/invoices", response_model=list[InvoiceOut])
def list_trip_invoices(trip_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    _get_trip_or_404(db, trip_id)
    return (
        db.execute(
            select(SalesInvoice)
            .where(SalesInvoice.trip_id == trip_id)
            .options(selectinload(SalesInvoice.items))
            .order_by(SalesInvoice.id)
        )
        .scalars()
        .all()
    )


invoices_router = APIRouter(prefix="/invoices", tags=["trips"])


@invoices_router.post("/{invoice_id}/collections", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
def create_collection(
    invoice_id: int, payload: CollectionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    invoice = db.get(SalesInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    already_collected = db.execute(
        select(PaymentCollection.amount).where(PaymentCollection.invoice_id == invoice_id)
    ).scalars().all()
    if sum(already_collected, Decimal("0")) + payload.amount > invoice.total_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collections would exceed the invoice total",
        )

    status_value = (
        PaymentStatus.awaiting_bank_verification if payload.payment_mode == PaymentMode.online else PaymentStatus.cleared
    )
    collection = PaymentCollection(
        invoice_id=invoice_id,
        customer_id=invoice.customer_id,
        trip_id=invoice.trip_id,
        amount=payload.amount,
        payment_mode=payload.payment_mode,
        status=status_value,
        collected_by=user.id,
    )
    db.add(collection)
    db.flush()

    if payload.payment_mode == PaymentMode.cash:
        # Cash is settled the moment it's collected — credit the ledger now.
        prev_balance = _latest_customer_balance(db, invoice.customer_id)
        db.add(
            CustomerLedger(
                customer_id=invoice.customer_id,
                txn_type=LedgerTxnType.payment,
                reference_type="payment_collection",
                reference_id=collection.id,
                debit=Decimal("0"),
                credit=payload.amount,
                balance_after=prev_balance - payload.amount,
            )
        )
        post_journal_entry(
            db,
            entry_date=datetime.now(timezone.utc).date(),
            reference_type="payment_collection",
            reference_id=collection.id,
            narration=f"Cash collection against invoice {invoice.invoice_number}",
            lines=[(acct.CASH, payload.amount, Decimal("0")), (acct.ACCOUNTS_RECEIVABLE, Decimal("0"), payload.amount)],
            created_by=user.id,
        )
    elif payload.payment_mode == PaymentMode.online:
        # Stays outstanding on the customer ledger until Phase 2's bank
        # reconciliation confirms the transfer actually landed.
        db.add(
            PendingOnlinePayment(
                payment_collection_id=collection.id,
                customer_id=invoice.customer_id,
                amount=payload.amount,
            )
        )
    # payment_mode == credit: no ledger entry — the invoice's debit already
    # reflects this amount as outstanding.

    db.commit()
    db.refresh(collection)
    return collection


@invoices_router.get("/{invoice_id}/collections", response_model=list[CollectionOut])
def list_collections(invoice_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return (
        db.execute(select(PaymentCollection).where(PaymentCollection.invoice_id == invoice_id))
        .scalars()
        .all()
    )


def _compute_reconciliation(db: Session, trip: Trip) -> ReconciliationOut:
    """Expected revenue is inferred from stock movement (no per-invoice entry
    required): value of what left the vehicle and didn't come back as a
    return or a damage write-off, priced at each product's base price. That's
    compared against what the driver actually reports: counted cash + credit
    given to shops on this trip + a lump online amount. A mismatch here means
    either stock or money is unaccounted for — with no per-invoice detail,
    the two causes can no longer be told apart, which is the tradeoff for not
    making the driver key in every sale."""

    def sums_for(txn_type: StockTxnType) -> dict[int, Decimal]:
        rows = db.execute(
            select(StockLedger.product_id, func.sum(StockLedger.quantity))
            .where(
                StockLedger.location_type == StockLocationType.vehicle,
                StockLedger.location_id == trip.id,
                StockLedger.txn_type == txn_type,
            )
            .group_by(StockLedger.product_id)
        ).all()
        return {p: abs(q) for p, q in rows}

    loaded = sums_for(StockTxnType.load_in)
    returned = sums_for(StockTxnType.return_)
    damaged = sums_for(StockTxnType.damage)

    all_product_ids = set(loaded) | set(returned) | set(damaged)
    products_by_id = {p.id: p for p in db.execute(select(Product).where(Product.id.in_(all_product_ids))).scalars().all()}

    products: list[ReconciliationProductRow] = []
    expected_sales_value = Decimal("0")
    for product_id in sorted(all_product_ids):
        loaded_qty = loaded.get(product_id, Decimal("0"))
        returned_qty = returned.get(product_id, Decimal("0"))
        damaged_qty = damaged.get(product_id, Decimal("0"))
        product = products_by_id.get(product_id)
        base_price = product.base_price if product else Decimal("0")
        expected_value = (loaded_qty - returned_qty - damaged_qty) * base_price
        expected_sales_value += expected_value
        products.append(
            ReconciliationProductRow(
                product_id=product_id,
                sku=product.sku if product else "?",
                name=product.name if product else "?",
                loaded=loaded_qty,
                returned=returned_qty,
                damaged=damaged_qty,
                expected_value=expected_value,
            )
        )

    def money_total(mode: PaymentMode) -> Decimal:
        return db.execute(
            select(func.coalesce(func.sum(PaymentCollection.amount), 0)).where(
                PaymentCollection.trip_id == trip.id, PaymentCollection.payment_mode == mode
            )
        ).scalar_one()

    cash_collected = _cash_total(trip)
    online_collected = money_total(PaymentMode.online)
    credit_given = money_total(PaymentMode.credit)
    cheque_given = money_total(PaymentMode.cheque)
    total_collected = cash_collected + online_collected + credit_given + cheque_given
    money_difference = expected_sales_value - total_collected
    clean = abs(money_difference) <= RECONCILIATION_TOLERANCE

    return ReconciliationOut(
        products=products,
        expected_sales_value=expected_sales_value,
        cash_collected=cash_collected,
        online_collected=online_collected,
        credit_given=credit_given,
        cheque_given=cheque_given,
        total_collected=total_collected,
        money_difference=money_difference,
        clean=clean,
    )


@router.get("/{trip_id}/reconciliation", response_model=ReconciliationOut)
def get_reconciliation(trip_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    trip = _get_trip_or_404(db, trip_id)
    return _compute_reconciliation(db, trip)


@router.post("/{trip_id}/close", response_model=TripOut)
def close_trip(
    trip_id: int,
    payload: TripCloseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_close_day")),
):
    trip = _get_trip_or_404(db, trip_id)
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip is already closed")

    reconciliation = _compute_reconciliation(db, trip)
    if not reconciliation.is_clean and not payload.override_notes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Reconciliation mismatch — provide override_notes to close anyway",
                "reconciliation": reconciliation.model_dump(mode="json"),
            },
        )

    trip.status = TripStatus.closed
    trip.closed_by = user.id
    trip.closed_at = datetime.now(timezone.utc)
    trip.mismatch_notes = payload.override_notes if not reconciliation.is_clean else None

    db.commit()
    db.refresh(trip)
    return trip
