# DMS — Distributor Management System

Full spec: [docs/requirements.md](docs/requirements.md). Schema design rationale: [docs/database-design.md](docs/database-design.md).

## Status

**Phase 0 (foundation) is done:** Postgres schema, JWT auth, RBAC
(action-based permissions), audit logging, and a working login → dashboard
flow in the browser.

**Phase 1 (core ERP) is done.** Built and verified end-to-end (curl + a real
browser, including RBAC boundaries and unhappy paths):
- Master data: full CRUD (list/create/edit, soft-deactivate via `is_active`
  rather than hard delete) for Warehouses, Products, Routes, Customers,
  Employees, and Vehicles.
- Inventory: purchases (bring stock into a warehouse) and a live stock-level
  view, both derived from the append-only `stock_ledger`.
- The full van-sales trip lifecycle: create trip → load stock onto a vehicle
  → depart → create sales invoices → record collections (cash/credit/online)
  → submit end-of-day stock counts (returns/damage) → reconciliation check →
  close (blocked with a 409 + full breakdown on mismatch, unless a
  `can_close_day` holder supplies override notes). The core reconciliation
  invariants (`Loaded = Sold + Returned + Damaged + Missing` and
  `Sales = Cash + Online + Credit`) actually hold on real data.
- Expenses: categories + submit/approve/reject workflow, gated by
  `can_approve_expense`.
- Reports: warehouse stock, sales by product/customer, collections summary,
  and a customer credit-aging report (0-30/31-60/61-90/90+ day buckets vs.
  credit limit) — gated by `can_view_reports`.

**Phase 2 (finance) is done.** Built and verified end-to-end:
- Bank statement import (CSV) + the intelligent payment reconciliation
  engine — confidence-scored matching (verified identity > fuzzy name +
  amount), auto-clear ≥95%, suggested 80-95% for owner approval, manual
  match/reject below that, a permanent learning system (verified payment
  identities), and a full audit trail. Verified end-to-end with the spec's
  own example (a payment from "MOHAMMED SHAFI" manually matched to "ABC
  Stores" once, then auto-matching on the next import).
- Full double-entry accounting — chart of accounts, journal entries posted
  automatically from real business events (sales invoices, cash/online
  collections, purchases, approved expenses), plus manual entries for
  adjustments. Trial balance, P&L, general ledger, and balance sheet reports
  all verified to actually balance/reconcile on real operational data, not
  just sample data.

Also built (pulled forward from Phase 3 since it needed no new modules): the
real dashboard, replacing the Phase 0 placeholder.

**Phase 0-2 are now fully done.** Phase 3+ (AI chatbot, forecasting) is not
built yet, by explicit user decision to defer them — see the roadmap in
[docs/requirements.md](docs/requirements.md) (§17).

## Stack

- Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL, Python 3.11 (`backend/.venv`, managed with `uv`)
- Frontend: React + TypeScript + Vite + TailwindCSS v4 + shadcn/ui (Nova preset)
- Local dev infra: Docker Compose (Postgres 16, Redis 7)

## Running it locally

1. **Start Postgres/Redis:**
   ```bash
   docker compose up -d
   ```

2. **Backend** (from `backend/`):
   ```bash
   .venv/bin/alembic upgrade head          # applies db/schema.sql (already done once)
   .venv/bin/uvicorn app.main:app --reload --port 8000
   ```
   Env config lives in `backend/.env` (see `backend/.env.example` for the
   full list: `DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`) — the
   checked-in values are dev-only, not for production. `CORS_ORIGINS` is a
   comma-separated string (not a JSON list — keeps a plain `.env` value
   simple), read via `settings.cors_origin_list` in `app/main.py`; add your
   deployed frontend's real origin there once you have one, alongside
   `http://localhost:5173`.

   To (re)seed roles/permissions and an owner login:
   ```bash
   .venv/bin/python -m app.seed --owner-email you@example.com --owner-password yourpassword
   ```
   Seeded owner used during development: `owner@dms.local` / `owner12345`.

3. **Frontend** (from `frontend/`):
   ```bash
   npm run dev
   ```
   Visit http://localhost:5173 — the Vite dev server proxies `/api` to the
   backend on port 8000 (see `frontend/vite.config.ts`), so
   `frontend/.env.example`'s `VITE_API_URL` should stay **unset** for local
   dev. `lib/api.ts` builds its axios `baseURL` as `` `${VITE_API_URL ??
   ""}/api/v1` `` — unset, that's just `/api/v1` (relative, proxied); for a
   production build (Netlify or otherwise) where the frontend and backend
   aren't on the same origin, set `VITE_API_URL` to the backend's real base
   URL as a build-time env var. The token-refresh interceptor's raw
   `axios.post(...)` call (bypasses the `api` instance to avoid re-triggering
   the interceptor) uses the same `API_BASE` constant, so it doesn't silently
   keep pointing at a relative path if the rest of the app doesn't.

   **Two full environment pairs, not two databases plugged into one app**:
   local dev is frontend(:5173, proxy) → backend(:8000) → local Postgres;
   production is Netlify → wherever the backend actually runs → a *separate*
   production Postgres. The production database connects to the **backend**
   host — Netlify itself never holds a database connection, it only ever
   calls the backend's API over HTTP.

## Database

The physical schema is hand-designed and validated directly in
`db/schema.sql` (see the design doc for rationale — unified append-only stock
ledger, immutable invoices via triggers, the payment-reconciliation learning
system, etc.). It's applied via a single Alembic baseline migration
(`backend/alembic/versions/..._baseline_schema_from_db_schema_sql.py`) that
executes the file verbatim, so `db/schema.sql` stays the one source of truth
for the physical schema rather than being re-derived from ORM models.

**Schema changes after the baseline are real, incremental Alembic migrations**
— not edits to the baseline. The first one (`..._add_products_reorder_level.py`)
adds `products.reorder_level` (for the dashboard's low-stock card). When
generating one, `alembic revision --autogenerate` will always also propose
`drop_table`/`drop_index` for every table that has no ORM model yet (see
below) — **hand-edit the generated file down to just the real change** before
applying; those tables exist for real and must not be dropped. Update
`db/schema.sql` too, so it stays accurate for fresh installs.

Models exist so far for auth/RBAC/audit (`backend/app/models/auth.py`) and
master data — warehouses, products, product_batches, routes, customers,
employees, vehicles, vehicle_driver_assignments (`backend/app/models/masters.py`).
`Base.type_annotation_map` (in `app/db/session.py`) maps `int`→`BigInteger`,
`str`→`Text`, `datetime`→`TIMESTAMPTZ` so these models match `db/schema.sql`'s
actual column types exactly — check `alembic revision --autogenerate` reports
no diff for modeled tables before adding new ones (tables without models yet
will always show as "removed" in that diff; that's expected, not drift).
Later phases add models (and ordinary `alembic revision --autogenerate`
migrations) for the rest of the schema as those modules get built — see
[docs/database-design.md](docs/database-design.md) and the roadmap in
[docs/requirements.md](docs/requirements.md) (§17) for what's next.

## Master data API/UI pattern

Backend: `app/api/v1/crud_factory.py` generates a standard list/get/create/update
router for any master-data model (see `app/api/v1/masters.py` for the six
instantiations). No hard-delete route exists anywhere — master data is
deactivated via `is_active`, not deleted, since other tables hold foreign
keys into it.

Frontend: `components/MasterDataPage.tsx` + `components/EntityFormDialog.tsx`
render a table + add/edit dialog from a declarative `ResourceConfig` (see
`pages/ProductsPage.tsx` etc.). `pages/CustomersPage.tsx` shows the pattern
for a field that needs a dynamically-fetched select (route options).

**Search bars are client-side, not a new endpoint.** `MasterDataPage.tsx`
filters its already-fetched `items` against every configured column's raw
value (case-insensitive substring match) — covers Products and Customers
for free since both go through this component; no `ResourceConfig` changes
needed. The same plain-filter pattern was repeated locally, matched to what
each page actually shows, everywhere else a search made sense: Trips
(`pages/TripsPage.tsx`, matches resolved vehicle/driver/route names + date +
status, not raw foreign-key ids), Inventory (`pages/InventoryPage.tsx`,
matches the Current Stock table by SKU/product/batch), and both credit
views — Reports → "Current Credits" and Reconciliation → "Credits" (matches
shop/driver/trip date). None of this hits the network; it's a `useMemo`
filter over data already in state, so it stays instant regardless of list
size at this project's scale.

## Inventory & van-sales trip lifecycle

Backend: `app/services/stock.py` has the shared helpers (`write_ledger_entry`,
`stock_quantity`, `location_stock_levels`) every stock-moving endpoint uses —
`app/api/v1/inventory.py` (purchases, stock adjustments, warehouse stock view)
and `app/api/v1/trips.py` (trip lifecycle: stock sheet, invoices,
reconciliation, close). `app/api/v1/trips.py` also hosts a second router
(`invoices_router`, prefix `/invoices`) for the payment collection endpoints
— those aren't trip-scoped in the URL since an invoice ID is enough on its
own.

**Warehouse stock now carries value, not just quantity.** `StockLevelOut`
(`GET /warehouses/{id}/stock`) gained `base_price` (straight off the
product), and `InventoryPage.tsx`'s Current Stock table gained Unit Price
and Value (`quantity × base_price`) columns plus a "Total Stock Value in
Warehouse" figure below the table — summed over the *unfiltered* `stock`
list, so it stays the true warehouse total even while the search box above
narrows what's displayed. `TripDetailPage.tsx`'s Stock Sheet also got a
search box (filters by name/SKU) — purely a display filter over `sheet`
state; the save payload still submits every product's `editRows` entry
regardless of what's currently visible, so searching can't accidentally
drop a row from what gets saved.

**Trips have no explicit stage gating (as of 2026-07-23, redesigned per user
request) — just open/closed.** There used to be loading → on_route →
returned status transitions with a `depart` action gating invoices; that's
gone. `GET/PUT /trips/{id}/stock-sheet` is a single editable sheet — one row
per active product, three editable quantities (loaded/returned/damaged) —
covering the whole trip's stock movement, and it's genuinely **re-editable**:
submitted values are the new *totals*, not deltas to add, so resubmitting
unchanged values is a no-op and changing one only posts a ledger entry for
the difference (`app/api/v1/trips.py::update_stock_sheet` computes
`loaded_so_far`/`sold_so_far`/etc. from the ledger itself before diffing —
never trusts a cached "previous" value). Editing `loaded_quantity` downward
is rejected if it would go below `sold + returned + damaged` for that
product (can't un-load what's already been sold or counted). Invoices can be
created any time before the trip is closed — no depart step required.
`trip.status` still exists in the DB (the enum has `loading`/`on_route`/
`returned`/`closed`) but the app only ever uses `loading` (open) and
`closed` now — the other two values are vestigial, kept because dropping
enum values cleanly is more invasive than just not using them.

**Reconciliation is value-based, not invoice-based (as of 2026-07-23,
redesigned per user request)** — the driver isn't expected to key in every
sale. `_compute_reconciliation` in `app/api/v1/trips.py` infers expected
revenue from stock movement instead: for each product, `(loaded − returned −
damaged) × base_price`, summed across the stock sheet. That's compared
against what the driver actually reports bringing back for the whole trip:
- **Cash**, counted by Indian currency note denomination (₹500/200/100/50/
  20/10 counts + a lump coins amount) via `PUT /trips/{id}/cash-count` —
  fields live directly on `trips` (`cash_count_500` etc.), and the total is
  always derived (`_cash_total`), never entered directly, so it can't drift
  from the note counts.
- **Credit**, entered per shop directly on the trip (`POST /trips/{id}/
  credit-entries`, `{customer_id, amount}`) rather than via a formal
  invoice. This reuses `payment_collections` with `invoice_id` left null —
  that table's own schema comment already described exactly this use case
  ("shop, amount, mode. Nothing more."). Unlike the invoice flow (where the
  invoice's own debit already covers it), a credit entry here writes its own
  `customer_ledger` debit, since nothing else does. Deleting an entry
  (`DELETE .../credit-entries/{id}`) hard-deletes the `payment_collections`
  row (not append-only) but reverses the effect with a `credit_note`
  `customer_ledger` entry (append-only — can't edit/delete the original).
- **Online**, entered **per shop** (as of the same-day follow-up request)
  rather than as a lump figure — `POST/GET/DELETE /trips/{id}/online-entries`,
  same `{customer_id, amount}` shape as credit entries and the same
  `payment_collections`-with-null-`invoice_id` reuse. Unlike credit, an
  online entry *does* hook into the existing Phase 2 bank-statement
  reconciliation engine: it creates a `pending_online_payments` row too
  (`status: awaiting_bank_verification`), so a real incoming bank transfer
  can later be matched to it exactly like an invoice-based online
  collection. When that match resolves (`app/services/reconciliation.py::
  resolve_match`), the existing code already credits the ledger back — no
  change needed there. Deleting an online entry is blocked with 400 once its
  `pending_online_payments` row has `resolved_at` set (already confirmed by
  the bank reconciliation engine — removing it would leave that confirmation
  dangling).

`_create_money_entry`/`_list_money_entries`/`_delete_money_entry` in
`app/api/v1/trips.py` are the shared helpers behind both credit-entries and
online-entries (parameterized by `PaymentMode`) — the only real differences
are the `PaymentStatus` set and whether a `pending_online_payments` row gets
created/checked.

`ReconciliationOut.clean` is now one flag (previously `stock_clean` +
`money_clean`): without invoices, "sold" can't be independently verified
against stock movement anymore, so a stock shortfall and a money shortfall
show up identically as a nonzero `money_difference` — that conflation is the
explicit tradeoff for not requiring per-invoice entry. The stock sheet
dropped its `sold`/`missing` columns for the same reason (nothing populates
them without invoices); it now shows Loaded/Returned/Damaged only.

The old invoice + per-invoice-collection endpoints (`POST/GET .../invoices`,
`invoices_router`) are untouched and still callable via the API — they're
just no longer surfaced in the trip UI. `_compute_reconciliation` no longer
reads from them at all, so old and new data don't double-count.

The Reconciliation card also renders a combined shop-level breakdown table
(shop / mode / amount / status, merging credit-entries and online-entries)
directly under the summary numbers, so "who gave credit or paid online on
this trip" is visible without leaving the reconciliation view. Both the
Credit Given and Online Payments forms' shop `Select` include a "+ Add new
shop" option (`app/pages/TripDetailPage.tsx::ShopSelect`) that opens a small
dialog to create a customer (`POST /customers`, gated by the existing
`can_manage_masters` permission — same as the Customers page) inline and
auto-selects it, so a driver/manager never has to leave the trip page to
add a shop that isn't in the system yet.

A "Current Credits" report (`GET /reports/trip-credits`, Reports page →
"Current Credits" tab) lists every shop-level credit entry — shop, amount,
trip date, driver — across both the new trip-level flow and any old
invoice-based credit collections (both write `payment_collections` rows
with `payment_mode = credit`, so both show up). This is distinct from
`/reports/customer-aging`, which ages invoice-based outstanding by 30/60/90
days; this is a flat log, not a bucketed balance.

**Credit and online entries both have an explicit paid/pending status now**
(as of a later same-day follow-up), separate from `_compute_reconciliation`'s
running totals (which count an entry the moment it's given/received,
regardless of whether it's since been repaid/confirmed). `payment_status`
gained a third enum value, `pending` (Alembic can't run `ALTER TYPE ... ADD
VALUE` inside the same transaction that might use it, so that migration
wraps the `op.execute` in `op.get_context().autocommit_block()`) — credit
entries now default to `pending` instead of `cleared` on creation, and a
follow-up migration backfilled every *existing* credit-mode
`payment_collections` row from `cleared` to `pending`, since the old
`cleared` there only ever meant "this collection record needs no bank
verification," never "the shop has repaid this," and nothing else reads that
column for credit rows (outstanding balances live in `customer_ledger`, not
here) so the backfill is safe.

`PATCH /trips/{id}/credit-entries/{id}` and `.../online-entries/{id}` (body
`{paid: bool}`, shared logic in `_set_money_entry_paid`) let a manager flip
an entry between paid and pending by hand — moving `customer_ledger` the
same direction `resolve_match()` already does (credit on mark-paid, a
reversing debit on mark-pending), and for online entries also flipping
`pending_online_payments.resolved_at`. This is a genuine manual override of
the bank-reconciliation flow, not just a label — a deliberate simplification
is that it doesn't check whether an online entry was already cleared by a
*real* bank match before letting it be toggled back to pending.
`TripDetailPage.tsx`'s Credit Given and Online Payments tables both got a
Status column (`MoneyStatusBadge` — emerald "Paid" / amber "Pending" or
"Awaiting Bank Verification", not the shadcn Badge default variant, which is
brand red per [docs/database-design.md](docs/database-design.md)'s theme
notes) and a "Mark Paid"/"Mark Pending" button next to Remove.

The Reconciliation page (`pages/ReconciliationPage.tsx`, the bank-statement
matching page — not the per-trip reconciliation card) gained a "Credits"
tab: two tables, "Yet to be Paid" and "Paid", sourced from the same
`/reports/trip-credits` endpoint and filtered client-side by status, each
row with its own Mark Paid/Mark Pending button (same PATCH endpoints,
addressed via the row's `trip_id`). Marking a credit paid/pending here fails
with a clear error if the trip has since closed (the PATCH endpoints reject
writes on closed trips, same as every other trip-money endpoint).

Deliberately out of scope for this pass: the new trip-level cash/credit/
online entries don't post to the general ledger (`journal_entries`) the way
invoice creation and cash collection do (except online entries, indirectly,
once bank-reconciled — see above). Wiring cash and credit into the GL too
would need idempotent delta-based JE posting (since cash-count is
re-editable like the stock sheet) and wasn't part of what was asked for;
flagged here as a natural follow-up if full GL integration is wanted later.

**Two hard-won gotchas with the immutable/append-only tables** (see
[docs/database-design.md](docs/database-design.md) for why these tables are
locked down in the first place):
- You cannot `flush()` an INSERT to get a generated id and then set another
  column afterward (e.g. to embed the id in a formatted field) — the
  `prevent_update_delete()` trigger rejects the resulting UPDATE. Any
  generated value (like `sales_invoices.invoice_number`) has to be computed
  *before* the single INSERT.
- `HTTPException(detail={...})` in FastAPI does **not** go through the normal
  `jsonable_encoder` response path, so a raw `pydantic_model.model_dump()`
  containing `Decimal` fields (money/quantities) will crash with `TypeError:
  Object of type Decimal is not JSON serializable`. Use
  `model_dump(mode="json")` whenever a Pydantic model ends up inside an
  exception's `detail`.

Frontend: `pages/InventoryPage.tsx` (stock view + purchase entry with dynamic
line items) and `pages/TripDetailPage.tsx` — one flat page, no status-gated
sections. Cards, top to bottom: Stock Sheet (Excel-style table, all active
products as rows, Loaded/Returned/Damaged as editable inputs, single "Save
Stock Sheet" button), Cash Count (denomination inputs for ₹500/200/100/50/
20/10 notes + a coins amount, a live-computed total, "Save Cash Count"
button — online is no longer here, see below), Credit Given and Online
Payments (two structurally identical cards: a table of shop/amount[/status
for online]/Remove-button rows, plus an add-entry form of shop select +
amount + submit), Reconciliation (summary numbers, a combined shop-level
credit+online breakdown table, Clean/Mismatch badge), and Close Day. Both
shop `Select`s share a `ShopSelect` sub-component with a "+ Add new shop"
option that opens a small `Dialog` (name/owner/phone → `POST /customers`)
and auto-selects the newly created customer in whichever form triggered it.
Local edits are plain React state until saved, and each section re-syncs
from the server response after its own save, so it's safe to keep
correcting values. Only "trip is closed" disables editing (inputs become
read-only, add/remove actions and Close hide). A "← Back to Trips" button
sits at the top.

**Cheque is a fourth payment mode**, alongside cash/credit/online, added the
same way credit and online were: `payment_mode` gained a `'cheque'` value
(another `autocommit_block()` migration, same reason as the earlier
`'pending'` status addition), and `POST/GET/DELETE/PATCH /trips/{id}/
cheque-entries` reuse the exact `_create_money_entry`/`_list_money_entries`/
`_delete_money_entry`/`_set_money_entry_paid` helpers credit and online
already used — `_create_money_entry` grew an `extra_fields` dict parameter
so cheque's two extra columns (`cheque_given_date`, `cheque_deposit_date` —
post-dated cheques are common, so these are rarely the same day) can be set
without credit/online needing to know about them. A cheque defaults to
`pending` (same bucket as credit) and is marked `cleared` manually via the
same paid/pending toggle UI — there's no bank statement to auto-match it
against the way online payments can be. `_compute_reconciliation`'s
`total_collected` now sums cash + credit + online + cheque. Frontend: a
"Cheque Given" card structurally identical to Credit Given/Online Payments
but with two extra date inputs on the add-form and two extra columns
(Given Date, Bank Deposit Date) in the table; the Reconciliation card's
summary grid and combined shop-breakdown table both include cheque too.

**Crates (glass-bottle returnables) get simple trip-level counters**, not
the fuller per-customer/per-product `empties_transactions` design already
sketched in `db/schema.sql` (4 directions: issued_to_driver/
returned_by_driver/given_to_customer/collected_from_customer) — the ask was
simple aggregate counts ("crates out" vs "crates in," difference = crates
sold that day), so that's what's built; the richer per-shop empties ledger
stays available as a natural extension if per-customer tracking is ever
needed. **`crates_out` is not user-entered** (as of a same-day follow-up) —
`unit` was always free text (`'case'`/`'bottle'`/`'crate'` per the original
schema comment) and now `unit = 'crate'` is specifically *recognized*:
`_crates_out()` in `app/api/v1/trips.py` sums the stock sheet's loaded
quantity across every `unit='crate'` product for the trip (case-insensitive
match), so it can never drift from what was actually loaded — the `trips.
crates_out` column was dropped entirely (migration `db957068be64`) since
it's now purely derived. `crates_in` (empty crates the driver brings back)
has no other data source, so that one stays a manual count via `PUT /trips/
{id}/crates` (now just `{crates_in}` — `GET` returns both figures).
Frontend: the "Crates (Empties)" card shows Crates Out as a read-only field
that updates whenever the Stock Sheet is saved, Crates In as an editable
input, and a computed "Crates Sold (Out − In)" — still purely informational,
not folded into the money-based Clean/Mismatch check. **No product was
auto-assigned `unit='crate'`** — which SKUs are actually glass-bottle
returnables vs. PET/tetra/can wasn't reliable enough to guess at across the
59-product catalog, so that's left for whoever knows the real lineup to set
via the Products page's existing Unit field (already free-text/editable).

**Products sort by pack size, not alphabetically.** Added `products.
volume_ml` (nullable `NUMERIC(10,2)`) with a migration that also backfills
every existing product by matching its SKU's suffix (`150ML`, `200ML`, ...,
`-1L`, `-2L`, plus the bare `-300`/`-500` used by early ad-hoc test SKUs) —
see `SUFFIX_TO_ML` in that migration if a new pack size needs adding.
`make_crud_router` (`app/api/v1/crud_factory.py`) gained an optional
`order_by` list; the products router passes `[Product.volume_ml, Product.
name]`, and `_stock_sheet`'s query does the same, so both the Products page
and every trip's Stock Sheet list smallest-to-largest instead of
alphabetically. `ProductsPage.tsx` exposes `volume_ml` as a create/edit
field and a list column so it stays correct as new products get added.

**Closing a trip with a mismatch is a confirm dialog now, not a hard
block requiring typed notes.** The backend is unchanged — `POST /trips/{id}/
close` still 409s on a mismatch unless `override_notes` is truthy — but
`TripDetailPage.tsx` no longer makes the user type something to get past
that. Clicking "Close Trip": if `reconciliation.clean`, closes immediately;
otherwise it opens a "Reconciliation Mismatch" `Dialog` showing the actual
difference with **Yes, Close Anyway** / **No, Go Back**. Confirming sends
whatever's in the (now-optional) override notes textarea, or if that's
empty, an auto-generated note (`Closed with a mismatch of ₹{difference} —
confirmed by user`) — so the audit trail (`trips.mismatch_notes`) is never
blank, but nobody has to type anything for a routine ₹10–20 rounding gap.

## Expenses & reports

Backend: `app/api/v1/expenses.py` — `expense_categories` uses the same
`crud_factory` pattern as master data; `expenses` is a small custom
submit/approve/reject flow (`can_approve_expense` gates the decision
endpoints, submission itself just needs login). `app/api/v1/reports.py` is
read-only aggregation over existing tables (no new tables of its own) —
notably `customer_aging` computes per-invoice outstanding as
`invoice.total_amount - sum(cash collections against it)`, since a "credit"
payment_collection is a declaration, not an actual reduction (see the
payment_collections responsibility table above), and online collections stay
outstanding until Phase 2 reconciliation clears them onto the ledger.
Everything under `/reports` requires `can_view_reports`.

Frontend: `pages/ExpensesPage.tsx` (submit form + list with conditional
Approve/Reject buttons via `useAuth().hasPermission`) and
`pages/ReportsPage.tsx` (a `Tabs`-based page, one query per report on mount).

## Payment reconciliation engine

Backend: `app/services/reconciliation.py` is the matching engine —
`process_bank_transaction()` scores every unresolved `pending_online_payment`
against a freshly-imported credit transaction and files it into
auto_matched/suggested/unmatched (`AUTO_MATCH_THRESHOLD`/`SUGGESTED_THRESHOLD`
= 95/80). Scoring: a verified `payment_identity_mappings` hit is worth 95-100
on its own; otherwise it's `pg_trgm` name similarity (`func.similarity`,
max 70 points) plus an amount-match bonus (+25 exact, +10 within 2%) — so
pure fuzzy name matching alone can never reach auto-match, only
suggested-or-below, which is deliberate. `app/api/v1/reconciliation.py` wraps
this with CSV upload (`/bank-statements/upload` — outgoing/debit rows are
auto-ignored, not parsed for keywords), the reconciliation list/approve/
reject/manual-match endpoints, and `payment_identities` CRUD. Everything
requires `can_reconcile_payment` (seeded back in Phase 0).

**Real bug found and fixed by actually running the flow**: `resolve_match()`
originally created a *new* `payment_identity_mappings` row for **any**
confirmed match, including fully algorithmic auto-matches that no human ever
reviewed. That let an unreviewed coincidence (right fuzzy-name-similarity +
right amount, scoring ≥95 with no prior identity) permanently seed the
trusted mapping table — contradicting the spec's "Owner confirms X → Y"
learning model. Fixed: **reinforce** (increment `times_matched` on) an
*existing* mapping regardless of who/what confirmed the match, but only ever
**create** a new one when `approved_by` is a real user (i.e. `/approve` or
`/manual-match` was called by a human) — never from the automatic
`process_bank_transaction()` path. Verified the fix by reproducing the exact
failure (a fuzzy match scoring exactly 95 with no identity) and confirming no
mapping got minted, then confirming approve/manual-match still correctly
create one with `verified_by` set.

CSV format expected: `transaction_date` (YYYY-MM-DD), `amount`, `direction`
(credit/debit) required; `account_holder_name`, `reference_number`,
`narration` optional. PDF/Excel parsing is deferred — CSV exercises the full
matching/learning logic without a heavier parsing dependency.

Frontend: `pages/ReconciliationPage.tsx` — upload card + tabs, **Credits
first** (as of a later request — it's the tab people actually open most),
then Cheques, then the original four (Automatically Matched / Suggested
Matches / Unmatched / History) matching the spec's dashboard sections. Tab
*order* only depends on `TabsTrigger` order in `TabsList` — Radix doesn't
care about `TabsContent` position in the JSX, so the content blocks stayed
where they were rather than reshuffling the whole file. The Unmatched tab
includes a manual shop-and-payment picker (`GET /customers/{id}/
pending-online-payments` populates the second dropdown once a shop is
chosen).

**The Cheques tab is a second, independent view onto trip-level cheque
entries** — same underlying data `TripDetailPage.tsx`'s "Cheque Given" card
writes (`payment_collections` mode=cheque), surfaced here via a new
`GET /reports/trip-cheques` (shares a `_trip_money_log()` helper with
`/reports/trip-credits` in `app/api/v1/reports.py` — same trips/customers/
employees lookup, just a different `payment_mode` and, for cheques, two
extra date columns). This tab also has its own **Add Cheque** form, so a
cheque can be entered here directly instead of only from the trip page —
it needs a trip picker too (`GET /trips`, filtered client-side to
non-closed ones) since a cheque is always trip-scoped, then posts to the
same `POST /trips/{id}/cheque-entries` the trip page form uses. Whichever
page created it, both show the same row — there's only one source of
truth. Mark Paid/Pending here calls the same `PATCH .../cheque-entries/{id}`
endpoint as the trip page.

## Dashboard

Backend: `app/api/v1/dashboard.py` — `GET /dashboard/summary` (today's sales,
cash/online collected today, total pending credits, vehicles on route,
warehouse stock product count, near-expiry batch count, low-stock product
count, today's approved expenses, a simple profit proxy, top-3 best-sellers
this month) and `GET /dashboard/trends?days=N` (daily sales + daily
collections-by-mode series). Both require only login, not `can_view_reports`
— the dashboard is the post-login home page, so it shouldn't 403 a driver.
`profit_today` is `sales − approved expenses`, explicitly **not** full
COGS-based gross profit (no per-unit cost allocation exists yet) — labeled
as such in the UI so it isn't mistaken for real accounting profit.

**Real bug: the dashboard went stale after the trip-flow redesign, and
nobody updated it at the time.** `today_sales`/`daily_sales`/
`best_selling_products` originally read from `sales_invoices`, and
`pending_credits_total` from an invoice-vs-cash-collected aging calc — both
assumed every trip creates an invoice. Once trips moved to the simplified
cash/credit/online/cheque flow (no invoice required), those figures quietly
froze: any trip using the new flow contributed nothing to them, so the
charts looked flat/stale for exactly the trips people actually cared about,
while a handful of numbers left over from old test invoices sat there
looking like real, current data. Fixed by sourcing all of them from the
same place `_compute_reconciliation` and the Credits/Cheques report tabs
already do:
- `today_sales` / `daily_sales` / `best_selling_products` now come from a
  new `_stock_movement_rows()` helper — the same `(loaded − returned −
  damaged) × base_price` formula as trip reconciliation, summed across all
  trips for the period instead of one trip. `best_selling_products` sums
  raw signed quantity per product this month (still net of returns/damage)
  instead of `sales_invoice_items.quantity`.
- `cash_collected_today` and the `cash` series in `/trends` now sum
  `_cash_total(trip)` (imported straight from `app/api/v1/trips.py`) across
  trips for the period, since cash is denomination counts on `trips` now,
  not a `payment_collections` row.
- `pending_credits_total` is now `sum(payment_collections.amount) where
  payment_mode='credit' and status='pending'` — the exact same query behind
  the Reconciliation page's "Yet to be Paid" tab, so the two can't disagree.
- `online`/`credit` in `/trends` needed no change — both are still real
  `payment_collections` rows regardless of which flow (old invoice-based or
  current trip-level entries) created them.

Caught by the user noticing the graphs "weren't updating properly" and
confirmed by comparing `/dashboard/summary` before/after against known trip
data (`pending_credits_total` went from a stale 4642 to the correct 27778,
matching the Credits tab's own total exactly).

**Low stock needed a real schema change**: added `products.reorder_level`
(`NUMERIC(14,3) DEFAULT 0`; 0 = no alert configured) via the project's first
genuine incremental Alembic migration (see the Database section above for
the drop-table gotcha this ran into). A product's stock across all
warehouses at or below its `reorder_level` counts as low stock.

Frontend followed the `dataviz` skill's procedure (form → color → validate →
marks → interaction → accessibility, in that order — see
`references/` under the skill for the full method): KPI numbers are stat
tiles (`components/dashboard/StatTile.tsx`), not one-bar charts. The two
trend charts (`SalesTrendChart.tsx`, `CollectionsTrendChart.tsx`, built on
`recharts`) use the skill's validated categorical palette (`#2a78d6` blue /
`#eb6834` orange / `#1baf7a` aqua for cash/online/credit — checked with
`scripts/validate_palette.js`, which flagged aqua's contrast on a light
surface as a WARN), each with a legend, hover tooltips, and a collapsible
"View as table" fallback — the last of these isn't optional polish, it's the
skill's mandated mitigation for that contrast WARN. `StatTile` supports an
optional `tone` (`good`/`bad`) reserved for values with genuine direction
(Profit Today goes red when negative) — routine counters stay neutral ink.

**"Sales by Route" card** (`GET /dashboard/route-sales-trend?period=`,
`components/dashboard/RouteSalesTrendChart.tsx`) is a multi-line comparison,
one line per route. It's value-based like trip reconciliation — `(loaded −
returned − damaged) × base_price` per product, summed per route per day —
not `sales_invoices`-based, for the same reason the trip reconciliation
redesign moved off invoices: most trips don't create one anymore. Computed
with a single aggregate query (`StockLedger` joined to `Trip`/`Route`/
`Product`, filtered to `load_in`/`return_`/`damage`, grouped by date+route)
rather than looping `_compute_reconciliation` per trip. Uses the dataviz
skill's full 8-slot categorical palette (validated for line/bar adjacent-pair
use, not just the 3-slot subset the other two charts use) — routes are
capped at 8 series, with any beyond that folded into a gray "Other" line
(never a 9th generated hue, per the skill's rule). Series **order** (and
therefore color slot) is by route id, not by which route sold the most —
only *inclusion* in the top-8 is value-ranked — so a route's color doesn't
reshuffle across page loads just because its ranking did (the skill's
"color follows the entity, never its rank" rule).

**All three trend charts share one range selector** (as of a later
follow-up), replacing the old fixed `days=14` query param on both
`/dashboard/trends` and `/dashboard/route-sales-trend`. Both now take
`period` — one of `week`/`15d`/`month`/`year`/`all` — validated against a
`PERIOD_DAYS` dict in `dashboard.py` (400 on anything else). Named `period`
deliberately, not `range`: this module loops with Python's builtin
`range()`, and a query param called `range` would shadow it inside the
handler. `all` has no fixed day count — it resolves to `MIN(trips.trip_date)`
via a query, falling back to today if there are no trips yet, so "All Time"
always means "since the earliest trip on record," not some arbitrarily
large fixed window. `DashboardPage.tsx` has one `Select` driving all three
charts at once (Sales, Collections by Mode, Sales by Route) plus their
titles, rather than a per-chart control — matches how the user actually
asked for it ("the graphs... an option to change *its* range," singular).

**`AppLayout.tsx`'s sidebar and header are fixed**, not part of the
scrolling page: the sidebar is `fixed inset-y-0 left-0` with its own
`overflow-y-auto` (so a nav list taller than the viewport scrolls
independently), the content column has matching `pl-56` to offset it, and
the header is `sticky top-0`. Long pages (the trip detail page especially)
scroll under both without the nav disappearing.

## Accounting

Backend: `app/services/accounting.py` is the posting engine —
`post_journal_entry()` takes `(account_code, debit, credit)` tuples, verifies
they balance (raises if not), and writes a `JournalEntry` + `JournalEntryLine`
rows (doesn't commit; the caller's existing transaction covers it, same
pattern as `write_ledger_entry`/`resolve_match`). Wired into four existing
flows rather than requiring the frontend to do anything extra:
- `trips.py::create_invoice` → Dr Accounts Receivable, Cr Sales Revenue, Cr
  GST Output Tax Payable (if any)
- `trips.py::create_collection` (cash only) → Dr Cash, Cr Accounts Receivable
- `reconciliation.py::resolve_match` (online, once cleared) → Dr Bank, Cr
  Accounts Receivable
- `inventory.py::create_purchase` → Dr Inventory, Cr Accounts Payable
- `expenses.py::approve_expense` → Dr Operating Expenses, Cr Cash

**Deliberate simplifications, not oversights** (see `app/services/accounting.py`'s
module docstring): all expenses post to one generic "Operating Expenses"
account regardless of category (no `expense_categories` → `chart_of_accounts`
mapping exists), and purchases are always treated as on-credit-from-supplier
(no per-purchase payment-method tracking exists). Both are easy to extend
later without restructuring anything.

`app/api/v1/accounting.py`: `chart_of_accounts` CRUD via `crud_factory`
(`can_manage_accounting`), a manual journal-entry endpoint for adjustments
(same permission, rejects unbalanced entries with a 400), and four read
reports gated by `can_view_reports` — general ledger (per-account, with
running balance), trial balance, P&L, and balance sheet. The balance sheet
adds a `retained_earnings` line (all-time net income, since there's no
period-close step rolling it into equity) — this isn't a fudge factor, it's
an algebraic identity: for any set of balanced double-entry postings,
`Assets = Liabilities + Equity + (Income − Expenses)` always holds, which is
exactly why `balanced` came back `true` the first time this was tested
against real data, not by coincidence.

Frontend: `pages/ChartOfAccountsPage.tsx` (the usual `MasterDataPage`
pattern) and `pages/AccountingPage.tsx` — five tabs (Trial Balance, P&L,
Balance Sheet, General Ledger, Journal Entries), the last of which includes
the manual-entry form with dynamic debit/credit lines.

## Payroll

Backend: `app/models/payroll.py` (`Attendance`, `SalaryAdvance`,
`SalaryPayment`) and `app/api/v1/payroll.py`. **These three tables already
existed in `db/schema.sql` and in the actual database** — they were part of
the baseline migration (which runs `db/schema.sql` verbatim) but never had
SQLAlchemy models, so every subsequent `alembic revision --autogenerate`
flagged them as "not yet modeled" and proposed dropping them, a proposal
hand-stripped out of every migration since (see the Database section) —
confirmed zero-diff against `db/schema.sql` before writing a line of API
code, so this was purely wiring up existing schema, not a new migration.

- `POST /payroll/attendance` marks a **date range** at once (e.g. "on leave
  July 10–15"), not one day at a time — upserts one `attendance` row per day
  in the range, so re-marking the same range corrects a mistake instead of
  hitting the `(employee_id, attendance_date)` unique constraint.
- `POST /payroll/advances` records a salary advance (amount, date, reason).
- `GET /payroll/summary?period_start=&period_end=` — one row per active
  employee: `monthly_salary` (gross, from `employees.monthly_salary`,
  un-prorated — leave days are shown, not deducted, since nothing asked for
  proration), `leave_days`/`half_days`/`absent_days` (counted from
  `attendance` in the period), `advances_total` (sum of `salary_advances`
  with `advance_date` inside the period — there's no "already deducted"
  flag on that table, so an advance is assumed to be squared off within the
  same period it was given, matching how the original schema was designed),
  `net_payable` (gross − advances, intentionally allowed to go negative and
  shown in red rather than silently clamped to 0 — an employee owing money
  back is a real state the owner should see, not hide), and whether a
  `salary_payments` row already exists for that exact period.
- `POST /payroll/pay` computes gross/advances/net **server-side** (never
  trusts client-supplied amounts for a financial action) and rejects a
  second payment for the same `(employee_id, period_start, period_end)`
  with a 400 — same "can't double-process" guard used elsewhere (trip
  close, etc.).
- New `can_manage_payroll` permission, seeded to owner (full access already),
  manager, and accountant.

**Deliberately out of scope for this pass**: no journal-entry posting for
advances or salary payments — payroll isn't wired into
`app/services/accounting.py` at all yet, unlike expenses/purchases/invoices.
Consistent with how the trip-level cash/credit/cheque flow also skipped GL
integration: it wasn't asked for, and would need its own design (e.g. an
"Employee Advances" asset account to clear against at payment time). Easy
to add later without restructuring what's here.

Frontend: `pages/PayrollPage.tsx` — a period picker (defaults to the current
calendar month via a `monthBounds()` helper; **hit and fixed a real
timezone bug** where formatting the default dates with `.toISOString()`
silently shifted them back a day in any timezone behind UTC, e.g. the
"This Month" default showing Jun 30–Jul 30 instead of Jul 1–31 — fixed by
formatting from the `Date`'s local fields directly instead of normalizing
through UTC first), a Payroll Summary table with a per-row "Pay" button,
Mark Attendance/Leave and Salary Advance forms, and a Payment History table.
