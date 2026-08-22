# Database Design — Distributor Management System

This document explains the schema in [`db/schema.sql`](../db/schema.sql) and the
reasoning behind its structure. It has been validated by running the DDL
end-to-end against a real PostgreSQL 16 instance (Docker), including a
functional test that confirms the append-only triggers actually reject writes.

See [`requirements.md`](requirements.md) for the full product spec this schema implements.

---

## 1. Conventions

| Concern | Choice | Why |
|---|---|---|
| Primary keys | `BIGINT GENERATED ALWAYS AS IDENTITY` | Single-tenant ERP, no need for UUID's unguessability; sequential IDs are cheaper to index and join. |
| Money | `NUMERIC(14,2)` everywhere | Engineering principle: decimal only, never float. |
| Quantities | `NUMERIC(14,3)` | Supports whole crates as well as fractional units (litres, kg). |
| Controlled vocabularies | Postgres `ENUM` types | Cheaper than a lookup table for values that rarely change (status, mode, direction); still enforced at the DB layer. |
| Timestamps | `TIMESTAMPTZ DEFAULT now()` | Avoids timezone ambiguity across warehouses/regions. |
| Fuzzy text matching | `pg_trgm` + trigram GIN indexes on customer names, bank account-holder names, and payment identities | Backs the reconciliation engine's "fuzzy name matching" requirement directly in SQL (`similarity()`, `%` operator) instead of pulling every row into application code. |

---

## 2. Why a single, polymorphic `stock_ledger`

The spec's core invariant is:

```
Loaded Stock = Sold + Returned + Damaged + Missing
```

This only holds if load-outs, sales, returns, and damages are all rows in the
**same** ledger, so the equation is a `SUM(quantity)` query rather than a
reconciliation across several disconnected tables. `stock_ledger` therefore
covers both warehouse and vehicle stock via `location_type` (`warehouse` |
`vehicle`) + `location_id` (a `warehouse_id` or `trip_id`), with a signed
`quantity` and a `txn_type` (`purchase`, `sale`, `return`, `damage`,
`adjustment`, `transfer_in/out`, `load_out`, `load_in`).

The table is **append-only** — enforced by a `BEFORE UPDATE OR DELETE` trigger
(`prevent_update_delete()`), not just application discipline. A correction is
always a new offsetting row, which preserves a full audit trail of what
actually happened, when. This was verified directly: attempting `UPDATE
stock_ledger SET quantity = 999 ...` against a live instance raises `ERROR:
UPDATE on stock_ledger is not permitted`.

The day-close check (`trips.status = 'closed'`) is an application-level
computation: sum `stock_ledger` by `txn_type` per trip, compare against
`trip_stock_counts` (the physical count), and block closing on mismatch unless
a manager overrides it (`trips.mismatch_notes` records the justification).

The same append-only pattern is applied to `customer_ledger` (the second
invariant — `Sales Value = Cash + Online + Credit` — is a similar `SUM` over
`debit`/`credit` rows) and to every financial/audit table listed in Section 6
below.

---

## 3. Why invoices are immutable

`sales_invoices` and `sales_invoice_items` carry the same
`prevent_update_delete()` trigger. Per the spec, "Invoices are immutable — no
delete operation exists." Corrections are modeled as new documents
(`credit_notes`, `debit_notes`) that reference the original invoice, exactly
like real-world GST accounting — never as an edit to history.

---

## 4. Collections & reconciliation: table responsibilities

This is the newest and most complex module, so each table's single
responsibility is spelled out:

| Table | Responsibility |
|---|---|
| `payment_collections` | What the driver actually records: shop, amount, mode (cash/credit/online). Nothing else — no timestamps, no account numbers, per the "driver workflow" requirement. |
| `pending_online_payments` | The subset of `payment_collections` where `payment_mode = 'online'`, tracked separately so the reconciliation engine has a clean queue to work against without filtering the whole collections table. |
| `bank_statement_imports` / `bank_transactions` | Raw import of a bank statement (PDF/Excel/CSV). Outgoing transactions are kept but flagged `is_ignored = TRUE` rather than discarded, so an import is always fully auditable against the source file. |
| `payment_identity_mappings` | The **learning system**. One customer can have many verified identities (personal account, wife's account, business account, multiple UPI IDs) — modeled as a one-to-many from `customers`, unique on `(identity_type, identity_value)`. Once an owner confirms "MOHAMMED SHAFI → ABC Stores," it's a permanent row here, and `times_matched` tracks reuse. |
| `payment_reconciliations` | One row per attempted match between a `bank_transaction` and a `pending_online_payment`, carrying `confidence_score` and `status` (`auto_matched` ≥95, `suggested` 80–95, `unmatched` <80, plus `approved`/`rejected` after owner review). |
| `reconciliation_audit_log` | Every status transition, who made it, and when — "nothing can be silently changed." Also immutable via trigger. |

The spec's Section 14 lists "Reconciliation Confidence" and "Learning History"
as if they were separate tables. They aren't modeled that way here —
`confidence_score` already lives on `payment_reconciliations`, and learning
history is just the append-only trail of `payment_identity_mappings` inserts
plus `reconciliation_audit_log`. Adding dedicated tables for these would
create two sources of truth for the same fact.

---

## 5. Accounting

Standard double-entry: `chart_of_accounts` → `journal_entries` →
`journal_entry_lines`, with a `CHECK (debit = 0 OR credit = 0)` constraint so a
single line can't be both. `cash_ledger` and `bank_ledger` are thinner,
purpose-built ledgers for the day-to-day cash/bank views the dashboard needs
without joining through the general ledger every time — they get reconciled
into `journal_entries` by the accounting close process, not modeled here since
that's application logic, not schema.

---

## 6. Tables locked by the append-only/immutability trigger

`prevent_update_delete()` is attached to:

- `stock_ledger`
- `customer_ledger`
- `sales_invoices`, `sales_invoice_items`
- `journal_entries`, `journal_entry_lines`
- `audit_logs`
- `reconciliation_audit_log`

Everything else (masters like `customers`, `products`, `vehicles`, and
workflow state like `trips`, `expenses`, `payment_reconciliations`) is
normally mutable, since those rows represent current state or an in-progress
approval workflow rather than historical fact.

---

## 7. Derived data kept as views, not tables

`customer_returnable_balances` (outstanding crates/bottles per customer) is a
plain SQL `VIEW` over `empties_transactions`, not a stored table — it's fully
derivable from the transaction log, so persisting it separately would risk
drift. The same reasoning applies to any "outstanding balance" figure
elsewhere in the system: compute it from the ledger, don't cache it in the
schema layer.

---

## 8. What's intentionally deferred

- **RLS / multi-tenancy** — not needed yet; this is a single-distributor
  deployment per the vision statement ("the system belongs entirely to the
  distributor"). If multi-branch/multi-tenant support is ever required, add a
  `tenant_id` column and RLS policies rather than redesigning tables.
- **Partitioning** `stock_ledger` / `customer_ledger` by date — worth doing
  once volume justifies it, but premature now.
- **Full-text/vector search for the AI chatbot** — Phase 3+ per the roadmap;
  the current schema only needs to support deterministic SQL reporting
  (Phase 1) and reconciliation (Phase 2).

---

## 9. Validation performed

```
docker run -d --name dms_schema_test -e POSTGRES_PASSWORD=test -p 55432:5432 postgres:16
docker exec -i dms_schema_test psql -U postgres -v ON_ERROR_STOP=1 < db/schema.sql
```

Applied with zero errors. Followed by a functional check: inserted a
warehouse, product, and a `stock_ledger` row, then confirmed `UPDATE
stock_ledger SET quantity = 999 ...` is rejected by the trigger as designed.
Container was torn down after validation.
