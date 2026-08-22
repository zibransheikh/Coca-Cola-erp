import csv
import io
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models import User
from app.models.collections import PendingOnlinePayment
from app.models.masters import Customer
from app.models.reconciliation import (
    BankStatementImport,
    BankTransaction,
    PaymentIdentityMapping,
    PaymentReconciliation,
    ReconciliationAuditLog,
    ReconciliationStatus,
)
from app.schemas.reconciliation import (
    BankStatementImportOut,
    BankTransactionOut,
    ManualMatchRequest,
    PaymentIdentityMappingCreate,
    PaymentIdentityMappingOut,
    ReconciliationOut,
)
from app.services.reconciliation import resolve_match, process_bank_transaction

router = APIRouter(tags=["reconciliation"])

REQUIRED_CSV_COLUMNS = {"transaction_date", "amount", "direction"}


class BankStatementUploadResult(BaseModel):
    import_: BankStatementImportOut
    transactions_imported: int
    ignored: int
    auto_matched: int
    suggested: int
    unmatched: int


@router.post(
    "/bank-statements/upload", response_model=BankStatementUploadResult, status_code=status.HTTP_201_CREATED
)
def upload_bank_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_reconcile_payment")),
):
    """Accepts a CSV bank statement (columns: transaction_date, amount,
    direction, account_holder_name, reference_number, narration). PDF/Excel
    parsing is a future enhancement — CSV covers the reconciliation logic
    end-to-end without pulling in a heavier parsing dependency.
    """
    raw = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    if reader.fieldnames is None or not REQUIRED_CSV_COLUMNS.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV must include columns: {', '.join(sorted(REQUIRED_CSV_COLUMNS))}",
        )

    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV has no data rows")

    dates = []
    parsed_rows = []
    for row in rows:
        try:
            txn_date = datetime.strptime(row["transaction_date"].strip(), "%Y-%m-%d").date()
            amount = Decimal(row["amount"].strip())
        except (ValueError, InvalidOperation, KeyError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not parse row: {row}. Dates must be YYYY-MM-DD, amount numeric.",
            )
        direction = row["direction"].strip().lower()
        if direction not in ("credit", "debit"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid direction: {direction}")
        dates.append(txn_date)
        parsed_rows.append(
            {
                "transaction_date": txn_date,
                "amount": amount,
                "direction": direction,
                "account_holder_name": (row.get("account_holder_name") or "").strip() or None,
                "reference_number": (row.get("reference_number") or "").strip() or None,
                "narration": (row.get("narration") or "").strip() or None,
            }
        )

    bank_import = BankStatementImport(
        file_name=file.filename or "upload.csv",
        file_type="csv",
        period_start=min(dates),
        period_end=max(dates),
        imported_by=user.id,
    )
    db.add(bank_import)
    db.flush()

    counts = {"ignored": 0, "auto_matched": 0, "suggested": 0, "unmatched": 0}
    for parsed in parsed_rows:
        is_ignored = parsed["direction"] == "debit"
        txn = BankTransaction(import_id=bank_import.id, is_ignored=is_ignored, **parsed)
        db.add(txn)
        db.flush()

        if is_ignored:
            counts["ignored"] += 1
            continue

        reconciliation = process_bank_transaction(db, txn)
        counts[reconciliation.status.value] += 1

    db.commit()
    db.refresh(bank_import)
    return BankStatementUploadResult(
        import_=bank_import,
        transactions_imported=len(parsed_rows),
        **counts,
    )


@router.get("/bank-statements", response_model=list[BankStatementImportOut])
def list_bank_statements(
    db: Session = Depends(get_db), _user: User = Depends(require_permission("can_reconcile_payment"))
):
    return db.execute(select(BankStatementImport).order_by(BankStatementImport.id.desc())).scalars().all()


@router.get("/bank-statements/{import_id}/transactions", response_model=list[BankTransactionOut])
def list_import_transactions(
    import_id: int, db: Session = Depends(get_db), _user: User = Depends(require_permission("can_reconcile_payment"))
):
    return (
        db.execute(select(BankTransaction).where(BankTransaction.import_id == import_id).order_by(BankTransaction.id))
        .scalars()
        .all()
    )


def _reconciliation_to_out(row) -> ReconciliationOut:
    reconciliation, bank_txn, customer_name = row
    return ReconciliationOut(
        id=reconciliation.id,
        bank_transaction_id=reconciliation.bank_transaction_id,
        pending_payment_id=reconciliation.pending_payment_id,
        matched_customer_id=reconciliation.matched_customer_id,
        matched_customer_name=customer_name,
        confidence_score=reconciliation.confidence_score,
        match_method=reconciliation.match_method,
        status=reconciliation.status.value,
        transaction_date=bank_txn.transaction_date,
        account_holder_name=bank_txn.account_holder_name,
        amount=bank_txn.amount,
        reference_number=bank_txn.reference_number,
        narration=bank_txn.narration,
    )


@router.get("/reconciliations", response_model=list[ReconciliationOut])
def list_reconciliations(
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_reconcile_payment")),
):
    query = (
        select(PaymentReconciliation, BankTransaction, Customer.name)
        .join(BankTransaction, BankTransaction.id == PaymentReconciliation.bank_transaction_id)
        .outerjoin(Customer, Customer.id == PaymentReconciliation.matched_customer_id)
        .order_by(PaymentReconciliation.id.desc())
    )
    if status_filter:
        query = query.where(PaymentReconciliation.status == ReconciliationStatus(status_filter))
    rows = db.execute(query).all()
    return [_reconciliation_to_out(row) for row in rows]


def _get_reconciliation_or_404(db: Session, reconciliation_id: int) -> PaymentReconciliation:
    reconciliation = db.get(PaymentReconciliation, reconciliation_id)
    if reconciliation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reconciliation not found")
    return reconciliation


@router.post("/reconciliations/{reconciliation_id}/approve", response_model=ReconciliationOut)
def approve_reconciliation(
    reconciliation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_reconcile_payment")),
):
    reconciliation = _get_reconciliation_or_404(db, reconciliation_id)
    if reconciliation.status != ReconciliationStatus.suggested:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only suggested matches can be approved")

    previous_status = reconciliation.status
    reconciliation.status = ReconciliationStatus.approved
    reconciliation.approved_by = user.id
    reconciliation.approved_at = datetime.now(timezone.utc)
    resolve_match(db, reconciliation, approved_by=user.id)
    db.add(
        ReconciliationAuditLog(
            reconciliation_id=reconciliation.id,
            previous_status=previous_status,
            new_status=reconciliation.status,
            confidence_score=reconciliation.confidence_score,
            changed_by=user.id,
        )
    )
    db.commit()

    row = db.execute(
        select(PaymentReconciliation, BankTransaction, Customer.name)
        .join(BankTransaction, BankTransaction.id == PaymentReconciliation.bank_transaction_id)
        .outerjoin(Customer, Customer.id == PaymentReconciliation.matched_customer_id)
        .where(PaymentReconciliation.id == reconciliation.id)
    ).one()
    return _reconciliation_to_out(row)


@router.post("/reconciliations/{reconciliation_id}/reject", response_model=ReconciliationOut)
def reject_reconciliation(
    reconciliation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_reconcile_payment")),
):
    reconciliation = _get_reconciliation_or_404(db, reconciliation_id)
    if reconciliation.status not in (ReconciliationStatus.suggested, ReconciliationStatus.unmatched):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only suggested or unmatched rows can be rejected"
        )

    previous_status = reconciliation.status
    reconciliation.status = ReconciliationStatus.rejected
    reconciliation.approved_by = user.id
    reconciliation.approved_at = datetime.now(timezone.utc)
    db.add(
        ReconciliationAuditLog(
            reconciliation_id=reconciliation.id,
            previous_status=previous_status,
            new_status=reconciliation.status,
            confidence_score=reconciliation.confidence_score,
            changed_by=user.id,
        )
    )
    db.commit()

    row = db.execute(
        select(PaymentReconciliation, BankTransaction, Customer.name)
        .join(BankTransaction, BankTransaction.id == PaymentReconciliation.bank_transaction_id)
        .outerjoin(Customer, Customer.id == PaymentReconciliation.matched_customer_id)
        .where(PaymentReconciliation.id == reconciliation.id)
    ).one()
    return _reconciliation_to_out(row)


@router.post("/reconciliations/{reconciliation_id}/manual-match", response_model=ReconciliationOut)
def manual_match_reconciliation(
    reconciliation_id: int,
    payload: ManualMatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_reconcile_payment")),
):
    reconciliation = _get_reconciliation_or_404(db, reconciliation_id)
    if reconciliation.status not in (ReconciliationStatus.unmatched, ReconciliationStatus.rejected):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only unmatched or rejected rows can be manually matched"
        )
    pending = db.get(PendingOnlinePayment, payload.pending_payment_id)
    if pending is None or pending.resolved_at is not None or pending.customer_id != payload.customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending payment not found, already resolved, or doesn't belong to that customer",
        )

    previous_status = reconciliation.status
    reconciliation.pending_payment_id = payload.pending_payment_id
    reconciliation.matched_customer_id = payload.customer_id
    reconciliation.match_method = "manual"
    reconciliation.status = ReconciliationStatus.approved
    reconciliation.approved_by = user.id
    reconciliation.approved_at = datetime.now(timezone.utc)
    resolve_match(db, reconciliation, approved_by=user.id)
    db.add(
        ReconciliationAuditLog(
            reconciliation_id=reconciliation.id,
            previous_status=previous_status,
            new_status=reconciliation.status,
            confidence_score=reconciliation.confidence_score,
            changed_by=user.id,
        )
    )
    db.commit()

    row = db.execute(
        select(PaymentReconciliation, BankTransaction, Customer.name)
        .join(BankTransaction, BankTransaction.id == PaymentReconciliation.bank_transaction_id)
        .outerjoin(Customer, Customer.id == PaymentReconciliation.matched_customer_id)
        .where(PaymentReconciliation.id == reconciliation.id)
    ).one()
    return _reconciliation_to_out(row)


@router.get("/payment-identities", response_model=list[PaymentIdentityMappingOut])
def list_payment_identities(
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("can_reconcile_payment")),
):
    query = select(PaymentIdentityMapping).order_by(PaymentIdentityMapping.id.desc())
    if customer_id is not None:
        query = query.where(PaymentIdentityMapping.customer_id == customer_id)
    return db.execute(query).scalars().all()


@router.post("/payment-identities", response_model=PaymentIdentityMappingOut, status_code=status.HTTP_201_CREATED)
def create_payment_identity(
    payload: PaymentIdentityMappingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_reconcile_payment")),
):
    mapping = PaymentIdentityMapping(
        customer_id=payload.customer_id,
        identity_type=payload.identity_type,
        identity_value=payload.identity_value,
        verified_by=user.id,
    )
    db.add(mapping)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This identity is already mapped")
    db.refresh(mapping)
    return mapping


@router.get("/customers/{customer_id}/pending-online-payments")
def list_customer_pending_payments(
    customer_id: int, db: Session = Depends(get_db), _user: User = Depends(require_permission("can_reconcile_payment"))
):
    rows = db.execute(
        select(PendingOnlinePayment)
        .where(PendingOnlinePayment.customer_id == customer_id, PendingOnlinePayment.resolved_at.is_(None))
        .order_by(PendingOnlinePayment.id)
    ).scalars().all()
    return [{"id": r.id, "amount": r.amount, "created_at": r.created_at} for r in rows]
