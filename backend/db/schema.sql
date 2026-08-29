-- =============================================================================
-- Distributor Management System (DMS) — PostgreSQL Schema
-- =============================================================================
-- Conventions
--   * Surrogate keys: BIGINT GENERATED ALWAYS AS IDENTITY (fast, sequential, joins cheaply)
--   * Money:          NUMERIC(14,2) — never FLOAT/DOUBLE
--   * Quantities:     NUMERIC(14,3) — supports fractional units (litres, kg) and whole crates
--   * Timestamps:     TIMESTAMPTZ, defaulting to now()
--   * Append-only / immutable tables are locked with a trigger (see bottom of file)
--     so no ORM bug or ad-hoc query can silently mutate financial history.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy name matching for reconciliation
CREATE EXTENSION IF NOT EXISTS citext;    -- case-insensitive email uniqueness

-- =============================================================================
-- SECTION 1 — AUTH, RBAC, AUDIT
-- =============================================================================

CREATE TABLE users (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email           CITEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    phone           TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,          -- e.g. 'owner', 'manager', 'driver', 'accountant'
    description     TEXT
);

-- Action-based permissions, per Engineering Principles (can_close_day, can_approve_credit, ...)
CREATE TABLE permissions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,          -- e.g. 'can_close_day'
    description     TEXT
);

CREATE TABLE role_permissions (
    role_id         BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id   BIGINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE user_roles (
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE refresh_tokens (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL UNIQUE,
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ
);

-- Every important action recorded. Never updated or deleted.
CREATE TABLE audit_logs (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id),
    action           TEXT NOT NULL,                -- e.g. 'invoice.create', 'day.close', 'credit.approve'
    entity_type     TEXT NOT NULL,
    entity_id       BIGINT,
    before_data     JSONB,
    after_data      JSONB,
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);

-- =============================================================================
-- SECTION 2 — MASTER DATA
-- =============================================================================

CREATE TABLE warehouses (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            TEXT NOT NULL,
    address         TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE products (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku             TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    brand           TEXT,
    category        TEXT,
    unit            TEXT NOT NULL,                 -- e.g. 'case', 'bottle', 'crate'
    volume_ml       NUMERIC(10,2),                 -- pack size in ml, for sorting/grouping (e.g. 200ml, 1.5ltr = 1500)
    hsn_code        TEXT,
    gst_rate        NUMERIC(5,2) NOT NULL DEFAULT 0,
    base_price      NUMERIC(14,2) NOT NULL DEFAULT 0,
    is_returnable   BOOLEAN NOT NULL DEFAULT FALSE, -- crates/bottles with deposits
    deposit_amount  NUMERIC(14,2) NOT NULL DEFAULT 0,
    reorder_level   NUMERIC(14,3) NOT NULL DEFAULT 0, -- 0 = no low-stock alert configured
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE product_batches (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id      BIGINT NOT NULL REFERENCES products(id),
    batch_number    TEXT NOT NULL,
    manufacture_date DATE,
    expiry_date     DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_id, batch_number)
);
CREATE INDEX idx_product_batches_expiry ON product_batches(expiry_date);

CREATE TABLE routes (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE customers (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            TEXT NOT NULL,                 -- shop name
    owner_name      TEXT,
    phone           TEXT,
    address         TEXT,
    gst_number      TEXT,
    route_id        BIGINT REFERENCES routes(id),
    credit_limit    NUMERIC(14,2) NOT NULL DEFAULT 0,
    credit_days     INTEGER NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_customers_name_trgm ON customers USING gin (name gin_trgm_ops);
CREATE INDEX idx_customers_route ON customers(route_id);

CREATE TYPE employee_role AS ENUM ('driver', 'helper', 'office', 'other');

CREATE TABLE employees (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id),   -- nullable: not every worker logs in
    name            TEXT NOT NULL,
    role            employee_role NOT NULL,
    phone           TEXT,
    joining_date    DATE NOT NULL,
    monthly_salary  NUMERIC(14,2) NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE vehicles (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    registration_number TEXT NOT NULL UNIQUE,
    vehicle_type        TEXT,
    capacity            NUMERIC(14,3),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE vehicle_driver_assignments (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id      BIGINT NOT NULL REFERENCES vehicles(id),
    driver_id       BIGINT NOT NULL REFERENCES employees(id),
    route_id        BIGINT REFERENCES routes(id),
    assigned_date   DATE NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX idx_vda_vehicle ON vehicle_driver_assignments(vehicle_id);

-- =============================================================================
-- SECTION 3 — INVENTORY (append-only stock ledger)
-- =============================================================================

CREATE TYPE stock_location_type AS ENUM ('warehouse', 'vehicle');
CREATE TYPE stock_txn_type AS ENUM (
    'purchase', 'sale', 'return', 'damage', 'adjustment',
    'transfer_in', 'transfer_out', 'load_out', 'load_in'
);

-- Single source of truth for all quantity movement, warehouse or vehicle.
-- Never UPDATEd or DELETEd — corrections are new offsetting rows (see trigger below).
CREATE TABLE stock_ledger (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_type   stock_location_type NOT NULL,
    location_id     BIGINT NOT NULL,               -- warehouse_id or trip_id, per location_type
    product_id      BIGINT NOT NULL REFERENCES products(id),
    batch_id        BIGINT REFERENCES product_batches(id),
    txn_type        stock_txn_type NOT NULL,
    quantity        NUMERIC(14,3) NOT NULL,         -- signed: +in / -out
    reference_type  TEXT,                           -- e.g. 'sales_invoice', 'trip', 'purchase'
    reference_id    BIGINT,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_stock_ledger_location ON stock_ledger(location_type, location_id, product_id);
CREATE INDEX idx_stock_ledger_product_batch ON stock_ledger(product_id, batch_id);
CREATE INDEX idx_stock_ledger_reference ON stock_ledger(reference_type, reference_id);

CREATE TABLE purchases (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    warehouse_id    BIGINT NOT NULL REFERENCES warehouses(id),
    supplier_name   TEXT NOT NULL,
    invoice_number  TEXT,
    purchase_date   DATE NOT NULL,
    total_amount    NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE purchase_items (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    purchase_id     BIGINT NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    product_id      BIGINT NOT NULL REFERENCES products(id),
    batch_id        BIGINT REFERENCES product_batches(id),
    quantity        NUMERIC(14,3) NOT NULL,
    unit_cost       NUMERIC(14,2) NOT NULL
);

CREATE TABLE stock_adjustments (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    warehouse_id    BIGINT NOT NULL REFERENCES warehouses(id),
    product_id      BIGINT NOT NULL REFERENCES products(id),
    batch_id        BIGINT REFERENCES product_batches(id),
    quantity        NUMERIC(14,3) NOT NULL,         -- signed
    reason          TEXT NOT NULL,
    requested_by    BIGINT REFERENCES users(id),
    approved_by     BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE transfer_status AS ENUM ('pending', 'in_transit', 'completed', 'cancelled');

CREATE TABLE stock_transfers (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    from_warehouse_id   BIGINT NOT NULL REFERENCES warehouses(id),
    to_warehouse_id     BIGINT NOT NULL REFERENCES warehouses(id),
    status              transfer_status NOT NULL DEFAULT 'pending',
    created_by          BIGINT REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (from_warehouse_id <> to_warehouse_id)
);

CREATE TABLE stock_transfer_items (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transfer_id     BIGINT NOT NULL REFERENCES stock_transfers(id) ON DELETE CASCADE,
    product_id      BIGINT NOT NULL REFERENCES products(id),
    batch_id        BIGINT REFERENCES product_batches(id),
    quantity        NUMERIC(14,3) NOT NULL
);

-- =============================================================================
-- SECTION 4 — VEHICLES / VAN SALES TRIPS
-- =============================================================================

CREATE TYPE trip_status AS ENUM ('loading', 'on_route', 'returned', 'closed');

CREATE TABLE trips (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id      BIGINT NOT NULL REFERENCES vehicles(id),
    driver_id       BIGINT NOT NULL REFERENCES employees(id),
    route_id        BIGINT REFERENCES routes(id),
    warehouse_id    BIGINT NOT NULL REFERENCES warehouses(id), -- load-out origin
    trip_date       DATE NOT NULL,
    status          trip_status NOT NULL DEFAULT 'loading',
    opened_by       BIGINT REFERENCES users(id),
    opened_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_by       BIGINT REFERENCES users(id),
    closed_at       TIMESTAMPTZ,
    mismatch_notes  TEXT,                             -- required if reconciliation formula fails
    -- Denomination-counted cash (Indian currency notes) instead of per-invoice
    -- collection: driver counts notes at day-close, system totals them.
    cash_count_500  INTEGER NOT NULL DEFAULT 0,
    cash_count_200  INTEGER NOT NULL DEFAULT 0,
    cash_count_100  INTEGER NOT NULL DEFAULT 0,
    cash_count_50   INTEGER NOT NULL DEFAULT 0,
    cash_count_20   INTEGER NOT NULL DEFAULT 0,
    cash_count_10   INTEGER NOT NULL DEFAULT 0,
    cash_coins_amount NUMERIC(14,2) NOT NULL DEFAULT 0, -- mixed coins, entered as a lump value
    -- Online payments are per-shop entries in payment_collections (mode='online'),
    -- not a lump field here — same table credit entries use, see below.
    -- crates_out is NOT stored — computed from the stock sheet's loaded
    -- quantity for unit='crate' products, so it can't drift from reality.
    crates_in       INTEGER NOT NULL DEFAULT 0         -- empty crates the driver brought back
);
CREATE INDEX idx_trips_date ON trips(trip_date);
CREATE INDEX idx_trips_vehicle ON trips(vehicle_id);

-- End-of-day physical count entered by driver/manager, compared against
-- the stock_ledger derived figures (Loaded = Sold + Returned + Damaged + Missing).
CREATE TABLE trip_stock_counts (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id         BIGINT NOT NULL REFERENCES trips(id),
    product_id      BIGINT NOT NULL REFERENCES products(id),
    batch_id        BIGINT REFERENCES product_batches(id),
    returned_quantity  NUMERIC(14,3) NOT NULL DEFAULT 0,
    damaged_quantity   NUMERIC(14,3) NOT NULL DEFAULT 0,
    counted_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trip_id, product_id, batch_id)
);

-- =============================================================================
-- SECTION 5 — EMPTIES & RETURNABLES
-- =============================================================================

CREATE TYPE empties_direction AS ENUM ('issued_to_driver', 'returned_by_driver', 'given_to_customer', 'collected_from_customer');

CREATE TABLE empties_transactions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id         BIGINT REFERENCES trips(id),
    customer_id     BIGINT REFERENCES customers(id),
    product_id      BIGINT NOT NULL REFERENCES products(id), -- must have is_returnable = true
    direction       empties_direction NOT NULL,
    quantity        NUMERIC(14,3) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_empties_customer ON empties_transactions(customer_id);
CREATE INDEX idx_empties_trip ON empties_transactions(trip_id);

-- Derived view: outstanding empties per customer (given minus collected)
CREATE VIEW customer_returnable_balances AS
SELECT
    customer_id,
    product_id,
    SUM(CASE WHEN direction = 'given_to_customer' THEN quantity
             WHEN direction = 'collected_from_customer' THEN -quantity
             ELSE 0 END) AS outstanding_quantity
FROM empties_transactions
WHERE customer_id IS NOT NULL
GROUP BY customer_id, product_id;

-- =============================================================================
-- SECTION 6 — SALES / INVOICING (immutable)
-- =============================================================================

CREATE TYPE invoice_status AS ENUM ('posted', 'cancelled'); -- cancellation is via credit note, row itself never changes

CREATE TABLE sales_invoices (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_number  TEXT NOT NULL UNIQUE,
    trip_id         BIGINT NOT NULL REFERENCES trips(id),
    customer_id     BIGINT NOT NULL REFERENCES customers(id),
    invoice_date    TIMESTAMPTZ NOT NULL DEFAULT now(),
    subtotal        NUMERIC(14,2) NOT NULL,
    tax_amount      NUMERIC(14,2) NOT NULL,
    total_amount    NUMERIC(14,2) NOT NULL,
    status          invoice_status NOT NULL DEFAULT 'posted',
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_invoices_customer ON sales_invoices(customer_id);
CREATE INDEX idx_invoices_trip ON sales_invoices(trip_id);
CREATE INDEX idx_invoices_date ON sales_invoices(invoice_date);

CREATE TABLE sales_invoice_items (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_id      BIGINT NOT NULL REFERENCES sales_invoices(id),
    product_id      BIGINT NOT NULL REFERENCES products(id),
    batch_id        BIGINT REFERENCES product_batches(id),
    quantity        NUMERIC(14,3) NOT NULL,
    unit_price      NUMERIC(14,2) NOT NULL,
    tax_rate        NUMERIC(5,2) NOT NULL DEFAULT 0,
    line_total      NUMERIC(14,2) NOT NULL
);
CREATE INDEX idx_invoice_items_invoice ON sales_invoice_items(invoice_id);
CREATE INDEX idx_invoice_items_product ON sales_invoice_items(product_id);

-- Corrections to immutable invoices happen via credit/debit notes, never edits.
CREATE TABLE credit_notes (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    note_number     TEXT NOT NULL UNIQUE,
    invoice_id      BIGINT NOT NULL REFERENCES sales_invoices(id),
    reason          TEXT NOT NULL,
    amount          NUMERIC(14,2) NOT NULL,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE debit_notes (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    note_number     TEXT NOT NULL UNIQUE,
    invoice_id      BIGINT NOT NULL REFERENCES sales_invoices(id),
    reason          TEXT NOT NULL,
    amount          NUMERIC(14,2) NOT NULL,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- SECTION 7 — CUSTOMER LEDGER (append-only)
-- =============================================================================

CREATE TYPE ledger_txn_type AS ENUM ('invoice', 'payment', 'credit_note', 'debit_note');

CREATE TABLE customer_ledger (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id     BIGINT NOT NULL REFERENCES customers(id),
    txn_type        ledger_txn_type NOT NULL,
    reference_type  TEXT NOT NULL,
    reference_id    BIGINT NOT NULL,
    debit           NUMERIC(14,2) NOT NULL DEFAULT 0,  -- increases outstanding (invoice, debit note)
    credit          NUMERIC(14,2) NOT NULL DEFAULT 0,  -- decreases outstanding (payment, credit note)
    balance_after   NUMERIC(14,2) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_customer_ledger_customer ON customer_ledger(customer_id, created_at);

-- =============================================================================
-- SECTION 8 — COLLECTIONS & PAYMENT RECONCILIATION
-- =============================================================================

CREATE TYPE payment_mode AS ENUM ('cash', 'credit', 'online', 'cheque');
-- 'pending' = credit given but not yet repaid by the shop (see payment_collections
-- mode='credit' — repaid/pending status, distinct from online's bank-verification wait).
CREATE TYPE payment_status AS ENUM ('cleared', 'awaiting_bank_verification', 'pending');

-- What the driver records at point of sale/collection: shop, amount, mode. Nothing more.
CREATE TABLE payment_collections (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_id      BIGINT REFERENCES sales_invoices(id),
    customer_id     BIGINT NOT NULL REFERENCES customers(id),
    trip_id         BIGINT REFERENCES trips(id),
    amount          NUMERIC(14,2) NOT NULL,
    payment_mode    payment_mode NOT NULL,
    status          payment_status NOT NULL DEFAULT 'cleared',
    collected_by    BIGINT REFERENCES users(id),
    collected_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    cheque_given_date   DATE,  -- cheque mode only: when the shop handed it over
    cheque_deposit_date DATE   -- cheque mode only: date it can be deposited (post-dated cheques)
);
CREATE INDEX idx_payment_collections_customer ON payment_collections(customer_id);
CREATE INDEX idx_payment_collections_status ON payment_collections(status) WHERE status = 'awaiting_bank_verification';

-- Convenience subset: only online collections not yet reconciled. Kept as its own
-- table (rather than a filtered view) so the reconciliation engine can attach
-- match state without touching payment_collections.
CREATE TABLE pending_online_payments (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_collection_id BIGINT NOT NULL UNIQUE REFERENCES payment_collections(id),
    customer_id         BIGINT NOT NULL REFERENCES customers(id),
    amount              NUMERIC(14,2) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at         TIMESTAMPTZ            -- set once reconciled
);
CREATE INDEX idx_pending_online_unresolved ON pending_online_payments(customer_id) WHERE resolved_at IS NULL;

CREATE TABLE bank_statement_imports (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_name       TEXT NOT NULL,
    file_type       TEXT NOT NULL,              -- 'pdf' | 'excel' | 'csv'
    period_start    DATE,
    period_end      DATE,
    imported_by     BIGINT REFERENCES users(id),
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE bank_transactions (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_id           BIGINT NOT NULL REFERENCES bank_statement_imports(id),
    transaction_date    DATE NOT NULL,
    account_holder_name TEXT,                   -- raw name as it appears in the statement
    amount              NUMERIC(14,2) NOT NULL,
    reference_number    TEXT,
    narration           TEXT,
    direction           TEXT NOT NULL CHECK (direction IN ('credit', 'debit')),
    is_ignored          BOOLEAN NOT NULL DEFAULT FALSE, -- outgoing (fuel/salary/vendor/charges)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_bank_txn_import ON bank_transactions(import_id);
CREATE INDEX idx_bank_txn_holder_trgm ON bank_transactions USING gin (account_holder_name gin_trgm_ops);
CREATE INDEX idx_bank_txn_unignored_credits ON bank_transactions(transaction_date) WHERE direction = 'credit' AND is_ignored = FALSE;

-- One shop can have many verified payment identities (personal/wife's/business
-- accounts, multiple UPI IDs). This is the table the learning system writes to.
CREATE TABLE payment_identity_mappings (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id     BIGINT NOT NULL REFERENCES customers(id),
    identity_type   TEXT NOT NULL CHECK (identity_type IN ('name', 'upi_id', 'account_ref')),
    identity_value  TEXT NOT NULL,
    times_matched   INTEGER NOT NULL DEFAULT 0,
    verified_by     BIGINT REFERENCES users(id),
    verified_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (identity_type, identity_value)
);
CREATE INDEX idx_payment_identity_customer ON payment_identity_mappings(customer_id);
CREATE INDEX idx_payment_identity_value_trgm ON payment_identity_mappings USING gin (identity_value gin_trgm_ops);

CREATE TYPE reconciliation_status AS ENUM ('auto_matched', 'suggested', 'approved', 'rejected', 'unmatched');

CREATE TABLE payment_reconciliations (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bank_transaction_id BIGINT NOT NULL REFERENCES bank_transactions(id),
    pending_payment_id  BIGINT REFERENCES pending_online_payments(id),
    matched_customer_id BIGINT REFERENCES customers(id),
    confidence_score    NUMERIC(5,2) NOT NULL,     -- 0.00 - 100.00
    match_method        TEXT,                       -- e.g. 'verified_identity', 'fuzzy_name+amount'
    status              reconciliation_status NOT NULL DEFAULT 'unmatched',
    approved_by         BIGINT REFERENCES users(id),
    approved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_reconciliation_status ON payment_reconciliations(status);
CREATE INDEX idx_reconciliation_bank_txn ON payment_reconciliations(bank_transaction_id);

-- "Nothing can be silently changed" — every status transition is recorded.
CREATE TABLE reconciliation_audit_log (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reconciliation_id   BIGINT NOT NULL REFERENCES payment_reconciliations(id),
    previous_status     reconciliation_status,
    new_status          reconciliation_status NOT NULL,
    confidence_score    NUMERIC(5,2),
    changed_by          BIGINT REFERENCES users(id),
    changed_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- SECTION 9 — ACCOUNTING
-- =============================================================================

CREATE TYPE account_type AS ENUM ('asset', 'liability', 'equity', 'income', 'expense');

CREATE TABLE chart_of_accounts (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    account_type    account_type NOT NULL,
    parent_id       BIGINT REFERENCES chart_of_accounts(id)
);

CREATE TABLE journal_entries (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entry_date      DATE NOT NULL,
    reference_type  TEXT,
    reference_id    BIGINT,
    narration       TEXT,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE journal_entry_lines (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journal_entry_id BIGINT NOT NULL REFERENCES journal_entries(id),
    account_id      BIGINT NOT NULL REFERENCES chart_of_accounts(id),
    debit           NUMERIC(14,2) NOT NULL DEFAULT 0,
    credit          NUMERIC(14,2) NOT NULL DEFAULT 0,
    CHECK (debit = 0 OR credit = 0)   -- a line is either a debit or a credit, not both
);
CREATE INDEX idx_jel_entry ON journal_entry_lines(journal_entry_id);
CREATE INDEX idx_jel_account ON journal_entry_lines(account_id);

CREATE TABLE cash_ledger (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_date DATE NOT NULL,
    direction       TEXT NOT NULL CHECK (direction IN ('in', 'out')),
    amount          NUMERIC(14,2) NOT NULL,
    reference_type  TEXT,
    reference_id    BIGINT,
    description     TEXT,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE bank_ledger (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bank_transaction_id BIGINT REFERENCES bank_transactions(id),
    transaction_date    DATE NOT NULL,
    direction           TEXT NOT NULL CHECK (direction IN ('in', 'out')),
    amount              NUMERIC(14,2) NOT NULL,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- SECTION 10 — EXPENSES
-- =============================================================================

CREATE TABLE expense_categories (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    category_group  TEXT NOT NULL CHECK (category_group IN ('vehicle', 'business'))
);

CREATE TYPE expense_status AS ENUM ('pending', 'approved', 'rejected');

CREATE TABLE expenses (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id     BIGINT NOT NULL REFERENCES expense_categories(id),
    vehicle_id      BIGINT REFERENCES vehicles(id),  -- null for business expenses
    amount          NUMERIC(14,2) NOT NULL,
    expense_date    DATE NOT NULL,
    description     TEXT,
    status          expense_status NOT NULL DEFAULT 'pending',
    submitted_by    BIGINT REFERENCES users(id),
    approved_by     BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_expenses_vehicle ON expenses(vehicle_id);
CREATE INDEX idx_expenses_status ON expenses(status);

-- =============================================================================
-- SECTION 11 — LABOUR & PAYROLL
-- =============================================================================

CREATE TYPE attendance_status AS ENUM ('present', 'absent', 'half_day', 'leave');

CREATE TABLE attendance (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id     BIGINT NOT NULL REFERENCES employees(id),
    attendance_date DATE NOT NULL,
    status          attendance_status NOT NULL,
    UNIQUE (employee_id, attendance_date)
);

CREATE TABLE salary_advances (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id     BIGINT NOT NULL REFERENCES employees(id),
    amount          NUMERIC(14,2) NOT NULL,
    advance_date    DATE NOT NULL,
    reason          TEXT,
    approved_by     BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE salary_payments (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id         BIGINT NOT NULL REFERENCES employees(id),
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    gross_amount        NUMERIC(14,2) NOT NULL,
    advances_deducted   NUMERIC(14,2) NOT NULL DEFAULT 0,
    net_amount          NUMERIC(14,2) NOT NULL,
    paid_at             TIMESTAMPTZ,
    paid_by             BIGINT REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_salary_payments_employee ON salary_payments(employee_id);

-- =============================================================================
-- SECTION 12 — AI
-- =============================================================================

-- Read-only chatbot log. The assistant never writes to business tables; this
-- table only records the Q&A exchange for audit/analytics purposes.
CREATE TABLE ai_conversations (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id),
    question        TEXT NOT NULL,
    answer          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE forecast_results (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id              BIGINT REFERENCES products(id),
    forecast_type           TEXT NOT NULL,          -- 'demand', 'sales', 'inventory'
    forecast_date           DATE NOT NULL,
    predicted_value         NUMERIC(14,3) NOT NULL,
    confidence_interval_low  NUMERIC(14,3),
    confidence_interval_high NUMERIC(14,3),
    model_version           TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_forecast_product_date ON forecast_results(product_id, forecast_date);

-- Note: "Reconciliation Confidence" and "Learning History" from the spec are not
-- separate tables — they are payment_reconciliations.confidence_score and
-- payment_identity_mappings.times_matched / reconciliation_audit_log respectively.
-- Duplicating them would create two sources of truth for the same fact.

-- =============================================================================
-- SECTION 13 — INTEGRITY TRIGGERS (append-only / immutable enforcement)
-- =============================================================================

CREATE OR REPLACE FUNCTION prevent_update_delete() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION '% on % is not permitted: this table is append-only/immutable (row id=%)',
        TG_OP, TG_TABLE_NAME, COALESCE(OLD.id, NULL);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_stock_ledger_immutable
    BEFORE UPDATE OR DELETE ON stock_ledger
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_customer_ledger_immutable
    BEFORE UPDATE OR DELETE ON customer_ledger
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_sales_invoices_immutable
    BEFORE UPDATE OR DELETE ON sales_invoices
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_sales_invoice_items_immutable
    BEFORE UPDATE OR DELETE ON sales_invoice_items
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_journal_entries_immutable
    BEFORE UPDATE OR DELETE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_journal_entry_lines_immutable
    BEFORE UPDATE OR DELETE ON journal_entry_lines
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

CREATE TRIGGER trg_reconciliation_audit_log_immutable
    BEFORE UPDATE OR DELETE ON reconciliation_audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();

-- =============================================================================
-- SECTION 14 — updated_at maintenance for mutable master tables
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_warehouses_updated_at BEFORE UPDATE ON warehouses
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_employees_updated_at BEFORE UPDATE ON employees
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
