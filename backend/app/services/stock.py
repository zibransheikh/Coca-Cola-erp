from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inventory import StockLedger, StockLocationType, StockTxnType


def write_ledger_entry(
    db: Session,
    *,
    location_type: StockLocationType,
    location_id: int,
    product_id: int,
    batch_id: int | None,
    txn_type: StockTxnType,
    quantity: Decimal,
    reference_type: str,
    reference_id: int,
    created_by: int | None,
) -> StockLedger:
    entry = StockLedger(
        location_type=location_type,
        location_id=location_id,
        product_id=product_id,
        batch_id=batch_id,
        txn_type=txn_type,
        quantity=quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by=created_by,
    )
    db.add(entry)
    return entry


def stock_quantity(
    db: Session,
    *,
    location_type: StockLocationType,
    location_id: int,
    product_id: int,
    batch_id: int | None = None,
) -> Decimal:
    """Current on-hand quantity for a product (optionally batch) at a location."""
    query = select(func.coalesce(func.sum(StockLedger.quantity), 0)).where(
        StockLedger.location_type == location_type,
        StockLedger.location_id == location_id,
        StockLedger.product_id == product_id,
    )
    if batch_id is not None:
        query = query.where(StockLedger.batch_id == batch_id)
    return db.execute(query).scalar_one()


def location_stock_levels(db: Session, *, location_type: StockLocationType, location_id: int):
    """All products/batches with non-zero stock at a location."""
    query = (
        select(
            StockLedger.product_id,
            StockLedger.batch_id,
            func.sum(StockLedger.quantity).label("quantity"),
        )
        .where(StockLedger.location_type == location_type, StockLedger.location_id == location_id)
        .group_by(StockLedger.product_id, StockLedger.batch_id)
        .having(func.sum(StockLedger.quantity) != 0)
    )
    return db.execute(query).all()
