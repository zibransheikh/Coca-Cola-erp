from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models import User
from app.models.inventory import Purchase, PurchaseItem, StockAdjustment, StockLocationType, StockTxnType
from app.models.masters import Product, ProductBatch
from app.schemas.inventory import (
    PurchaseCreate,
    PurchaseOut,
    StockAdjustmentCreate,
    StockAdjustmentOut,
    StockLevelOut,
)
from app.services import accounting as acct
from app.services.accounting import post_journal_entry
from app.services.stock import location_stock_levels, write_ledger_entry

router = APIRouter(tags=["inventory"])


@router.get("/warehouses/{warehouse_id}/stock", response_model=list[StockLevelOut])
def get_warehouse_stock(
    warehouse_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    rows = location_stock_levels(db, location_type=StockLocationType.warehouse, location_id=warehouse_id)
    result = []
    for product_id, batch_id, quantity in rows:
        product = db.get(Product, product_id)
        batch = db.get(ProductBatch, batch_id) if batch_id else None
        result.append(
            StockLevelOut(
                product_id=product_id,
                sku=product.sku,
                name=product.name,
                unit=product.unit,
                batch_id=batch_id,
                batch_number=batch.batch_number if batch else None,
                quantity=quantity,
                base_price=product.base_price,
            )
        )
    return result


@router.post("/purchases", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
def create_purchase(
    payload: PurchaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_manage_inventory")),
):
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase must have at least one item")

    total_amount = sum((item.quantity * item.unit_cost for item in payload.items), Decimal("0"))
    purchase = Purchase(
        warehouse_id=payload.warehouse_id,
        supplier_name=payload.supplier_name,
        invoice_number=payload.invoice_number,
        purchase_date=payload.purchase_date,
        total_amount=total_amount,
        created_by=user.id,
    )
    db.add(purchase)
    db.flush()

    for item in payload.items:
        db.add(
            PurchaseItem(
                purchase_id=purchase.id,
                product_id=item.product_id,
                batch_id=item.batch_id,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
            )
        )
        write_ledger_entry(
            db,
            location_type=StockLocationType.warehouse,
            location_id=payload.warehouse_id,
            product_id=item.product_id,
            batch_id=item.batch_id,
            txn_type=StockTxnType.purchase,
            quantity=item.quantity,
            reference_type="purchase",
            reference_id=purchase.id,
            created_by=user.id,
        )

    if total_amount > 0:
        # Purchases are treated as on-credit-from-supplier (no per-purchase
        # payment-method tracking exists yet) — see app/services/accounting.py.
        post_journal_entry(
            db,
            entry_date=payload.purchase_date,
            reference_type="purchase",
            reference_id=purchase.id,
            narration=f"Purchase from {payload.supplier_name}",
            lines=[(acct.INVENTORY, total_amount, Decimal("0")), (acct.ACCOUNTS_PAYABLE, Decimal("0"), total_amount)],
            created_by=user.id,
        )

    db.commit()
    db.refresh(purchase)
    return purchase


@router.get("/purchases", response_model=list[PurchaseOut])
def list_purchases(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.execute(select(Purchase).options(selectinload(Purchase.items))).scalars().all()


@router.get("/purchases/{purchase_id}", response_model=PurchaseOut)
def get_purchase(purchase_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    purchase = db.get(Purchase, purchase_id, options=[selectinload(Purchase.items)])
    if purchase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found")
    return purchase


@router.post("/stock-adjustments", response_model=StockAdjustmentOut, status_code=status.HTTP_201_CREATED)
def create_stock_adjustment(
    payload: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_manage_inventory")),
):
    adjustment = StockAdjustment(
        warehouse_id=payload.warehouse_id,
        product_id=payload.product_id,
        batch_id=payload.batch_id,
        quantity=payload.quantity,
        reason=payload.reason,
        requested_by=user.id,
        approved_by=user.id,
    )
    db.add(adjustment)
    db.flush()

    write_ledger_entry(
        db,
        location_type=StockLocationType.warehouse,
        location_id=payload.warehouse_id,
        product_id=payload.product_id,
        batch_id=payload.batch_id,
        txn_type=StockTxnType.adjustment,
        quantity=payload.quantity,
        reference_type="stock_adjustment",
        reference_id=adjustment.id,
        created_by=user.id,
    )

    db.commit()
    db.refresh(adjustment)
    return adjustment


@router.get("/stock-adjustments", response_model=list[StockAdjustmentOut])
def list_stock_adjustments(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.execute(select(StockAdjustment)).scalars().all()
