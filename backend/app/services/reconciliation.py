from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.collections import PendingOnlinePayment
from app.models.ledger import CustomerLedger, LedgerTxnType
from app.models.masters import Customer
from app.models.reconciliation import (
    BankTransaction,
    PaymentIdentityMapping,
    PaymentReconciliation,
    ReconciliationAuditLog,
    ReconciliationStatus,
)
from app.services import accounting as acct
from app.services.accounting import post_journal_entry

AUTO_MATCH_THRESHOLD = Decimal("95")
SUGGESTED_THRESHOLD = Decimal("80")


def _find_best_match(
    db: Session, bank_txn: BankTransaction
) -> tuple[Decimal, int | None, int | None, str | None]:
    """Score every unresolved pending online payment against this bank
    transaction and return the best (score, pending_payment_id, customer_id,
    match_method).

    Verified payment identities (the learning system) take priority and can
    reach the auto-match tier on their own; everything else is scored from
    fuzzy name similarity (pg_trgm) plus an amount-match bonus, capped below
    the auto-match threshold unless the name similarity is close to perfect.
    """
    holder_name = bank_txn.account_holder_name or ""

    identity_match = db.execute(
        select(PaymentIdentityMapping).where(
            func.lower(PaymentIdentityMapping.identity_value) == func.lower(holder_name)
        )
    ).scalar_one_or_none()

    candidates = db.execute(
        select(
            PendingOnlinePayment.id,
            PendingOnlinePayment.customer_id,
            PendingOnlinePayment.amount,
            func.similarity(Customer.name, holder_name).label("sim"),
        )
        .join(Customer, Customer.id == PendingOnlinePayment.customer_id)
        .where(PendingOnlinePayment.resolved_at.is_(None))
    ).all()

    best: tuple[Decimal, int, int, str] | None = None
    for pending_id, customer_id, amount, similarity in candidates:
        amount_diff = abs(Decimal(amount) - Decimal(bank_txn.amount))
        amount_exact = amount_diff <= Decimal("0.01")
        amount_close = amount_diff <= Decimal(bank_txn.amount) * Decimal("0.02")

        if identity_match is not None and identity_match.customer_id == customer_id:
            score = Decimal("95") + (Decimal("5") if amount_exact else Decimal("0"))
            method = "verified_identity"
        else:
            score = Decimal(str(similarity)) * Decimal("70")
            if amount_exact:
                score += Decimal("25")
            elif amount_close:
                score += Decimal("10")
            method = "fuzzy_name+amount"

        score = min(score, Decimal("100"))
        if best is None or score > best[0]:
            best = (score, pending_id, customer_id, method)

    if best is None:
        return Decimal("0"), None, None, None
    return best


def resolve_match(db: Session, reconciliation: PaymentReconciliation, approved_by: int | None) -> None:
    """Mark the pending online payment as cleared and credit the customer
    ledger — the same ledger effect a cash collection gets immediately,
    just deferred until reconciliation confirms the transfer actually landed.
    """
    pending = db.get(PendingOnlinePayment, reconciliation.pending_payment_id)
    if pending is None:
        return
    pending.resolved_at = datetime.now(timezone.utc)

    prev_balance = db.execute(
        select(CustomerLedger.balance_after)
        .where(CustomerLedger.customer_id == pending.customer_id)
        .order_by(CustomerLedger.id.desc())
        .limit(1)
    ).scalar_one_or_none() or Decimal("0")

    db.add(
        CustomerLedger(
            customer_id=pending.customer_id,
            txn_type=LedgerTxnType.payment,
            reference_type="payment_collection",
            reference_id=pending.payment_collection_id,
            debit=Decimal("0"),
            credit=pending.amount,
            balance_after=prev_balance - pending.amount,
        )
    )

    post_journal_entry(
        db,
        entry_date=datetime.now(timezone.utc).date(),
        reference_type="payment_reconciliation",
        reference_id=reconciliation.id,
        narration="Online payment cleared via bank reconciliation",
        lines=[(acct.BANK, pending.amount, Decimal("0")), (acct.ACCOUNTS_RECEIVABLE, Decimal("0"), pending.amount)],
        created_by=approved_by,
    )

    # Learning system: reinforce an *existing* verified identity regardless of
    # who/what confirmed the match (that's just usage tracking on something a
    # human already vouched for). But only ever CREATE a new mapping — i.e.
    # extend trust to a name nobody has vetted yet — when a human actually
    # approved this specific match (approved_by is not None). Letting a
    # >=95%-confidence *algorithmic* auto-match mint a brand-new verified
    # identity would mean an unreviewed coincidence (right name-similarity +
    # amount) permanently seeds the trusted mapping table, which is exactly
    # what the spec's "Owner confirms X -> Y" learning model is meant to
    # prevent.
    bank_txn = db.get(BankTransaction, reconciliation.bank_transaction_id)
    holder_name = (bank_txn.account_holder_name or "").strip() if bank_txn else ""
    if holder_name:
        mapping = db.execute(
            select(PaymentIdentityMapping).where(
                func.lower(PaymentIdentityMapping.identity_value) == func.lower(holder_name)
            )
        ).scalar_one_or_none()
        if mapping is None:
            if approved_by is not None:
                db.add(
                    PaymentIdentityMapping(
                        customer_id=pending.customer_id,
                        identity_type="name",
                        identity_value=holder_name,
                        times_matched=1,
                        verified_by=approved_by,
                    )
                )
        else:
            mapping.times_matched += 1


def process_bank_transaction(db: Session, bank_txn: BankTransaction) -> PaymentReconciliation:
    """Score a freshly-imported credit transaction and file it into the
    right confidence tier, auto-resolving it immediately if the match is
    confident enough (see AUTO_MATCH_THRESHOLD)."""
    score, pending_id, customer_id, method = _find_best_match(db, bank_txn)

    if score >= AUTO_MATCH_THRESHOLD:
        status = ReconciliationStatus.auto_matched
    elif score >= SUGGESTED_THRESHOLD:
        status = ReconciliationStatus.suggested
    else:
        status = ReconciliationStatus.unmatched

    reconciliation = PaymentReconciliation(
        bank_transaction_id=bank_txn.id,
        pending_payment_id=pending_id,
        matched_customer_id=customer_id,
        confidence_score=score,
        match_method=method,
        status=status,
    )
    db.add(reconciliation)
    db.flush()

    db.add(
        ReconciliationAuditLog(
            reconciliation_id=reconciliation.id,
            previous_status=None,
            new_status=status,
            confidence_score=score,
        )
    )

    if status == ReconciliationStatus.auto_matched:
        reconciliation.approved_at = datetime.now(timezone.utc)
        resolve_match(db, reconciliation, approved_by=None)

    return reconciliation
