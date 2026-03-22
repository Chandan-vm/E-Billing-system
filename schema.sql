-- ============================================================
-- E-BILLING SYSTEM — RELATIONAL DATABASE SCHEMA
-- Designed for: Data Analytics + Business Intelligence
-- Compatible: SQLite (dev) / PostgreSQL (prod)
-- ============================================================

-- 1. BUSINESS CONFIGURATION (multi-tenant ready)
CREATE TABLE IF NOT EXISTS business_config (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT NOT NULL UNIQUE,
    value       TEXT NOT NULL,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. CUSTOMERS
CREATE TABLE IF NOT EXISTS customers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE,
    phone       TEXT,
    address     TEXT,
    city        TEXT,
    state       TEXT,
    pincode     TEXT,
    gstin       TEXT,                          -- GST registration number
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. PRODUCTS / SERVICES
CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    description     TEXT,
    category        TEXT,
    unit_price      REAL NOT NULL CHECK(unit_price >= 0),
    unit            TEXT DEFAULT 'unit',       -- pcs, hrs, kg, etc.
    hsn_sac_code    TEXT,                      -- HSN (goods) / SAC (services)
    tax_rate        REAL DEFAULT 18.0,         -- GST %
    is_service      INTEGER DEFAULT 0,         -- 0=product, 1=service
    is_active       INTEGER DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. INVOICES (header)
CREATE TABLE IF NOT EXISTS invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number  TEXT NOT NULL UNIQUE,
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    invoice_date    DATE NOT NULL DEFAULT (date('now')),
    due_date        DATE,
    status          TEXT DEFAULT 'draft' CHECK(status IN ('draft','sent','paid','overdue','cancelled')),
    supply_type     TEXT DEFAULT 'intra' CHECK(supply_type IN ('intra','inter')),   -- for GST
    subtotal        REAL NOT NULL DEFAULT 0,
    cgst_amount     REAL DEFAULT 0,
    sgst_amount     REAL DEFAULT 0,
    igst_amount     REAL DEFAULT 0,
    total_tax       REAL DEFAULT 0,
    total_amount    REAL NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. INVOICE LINE ITEMS
CREATE TABLE IF NOT EXISTS invoice_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id      INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id      INTEGER REFERENCES products(id),
    description     TEXT NOT NULL,
    quantity        REAL NOT NULL DEFAULT 1 CHECK(quantity > 0),
    unit_price      REAL NOT NULL CHECK(unit_price >= 0),
    tax_rate        REAL DEFAULT 18.0,
    line_subtotal   REAL NOT NULL,
    cgst            REAL DEFAULT 0,
    sgst            REAL DEFAULT 0,
    igst            REAL DEFAULT 0,
    line_total      REAL NOT NULL
);

-- ============================================================
-- ANALYTICS VIEWS — Pre-built for DA/BI use cases
-- ============================================================

-- Monthly Revenue Summary
CREATE VIEW IF NOT EXISTS vw_monthly_revenue AS
SELECT
    strftime('%Y', invoice_date)  AS year,
    strftime('%m', invoice_date)  AS month,
    strftime('%Y-%m', invoice_date) AS year_month,
    COUNT(*)                       AS invoice_count,
    SUM(subtotal)                  AS gross_revenue,
    SUM(total_tax)                 AS total_tax_collected,
    SUM(total_amount)              AS net_revenue,
    AVG(total_amount)              AS avg_invoice_value
FROM invoices
WHERE status != 'cancelled'
GROUP BY year_month;

-- Product Performance View
CREATE VIEW IF NOT EXISTS vw_product_performance AS
SELECT
    p.id,
    p.name                          AS product_name,
    p.category,
    p.unit_price,
    COUNT(ii.id)                    AS times_sold,
    SUM(ii.quantity)                AS total_qty_sold,
    SUM(ii.line_subtotal)           AS total_revenue,
    AVG(ii.unit_price)              AS avg_selling_price,
    SUM(ii.line_total)              AS revenue_with_tax
FROM products p
LEFT JOIN invoice_items ii ON p.id = ii.product_id
LEFT JOIN invoices inv ON ii.invoice_id = inv.id AND inv.status != 'cancelled'
GROUP BY p.id, p.name, p.category, p.unit_price;

-- Customer Insights View
CREATE VIEW IF NOT EXISTS vw_customer_insights AS
SELECT
    c.id,
    c.name                          AS customer_name,
    c.email,
    c.city,
    COUNT(DISTINCT inv.id)          AS total_invoices,
    SUM(inv.total_amount)           AS lifetime_value,
    AVG(inv.total_amount)           AS avg_order_value,
    MAX(inv.invoice_date)           AS last_purchase_date,
    MIN(inv.invoice_date)           AS first_purchase_date,
    CASE
        WHEN COUNT(DISTINCT inv.id) >= 5 THEN 'VIP'
        WHEN COUNT(DISTINCT inv.id) >= 2 THEN 'Returning'
        ELSE 'New'
    END                             AS customer_segment
FROM customers c
LEFT JOIN invoices inv ON c.id = inv.customer_id AND inv.status != 'cancelled'
GROUP BY c.id, c.name, c.email, c.city;

-- Invoice Detail View (flattened for export/Power BI)
CREATE VIEW IF NOT EXISTS vw_invoice_detail AS
SELECT
    inv.invoice_number,
    inv.invoice_date,
    inv.status,
    c.name      AS customer_name,
    c.email     AS customer_email,
    c.city,
    c.gstin     AS customer_gstin,
    p.name      AS product_name,
    p.category,
    p.hsn_sac_code,
    ii.quantity,
    ii.unit_price,
    ii.tax_rate,
    ii.line_subtotal,
    ii.cgst,
    ii.sgst,
    ii.igst,
    ii.line_total,
    inv.total_amount AS invoice_total
FROM invoices inv
JOIN customers c    ON inv.customer_id = c.id
JOIN invoice_items ii ON ii.invoice_id = inv.id
LEFT JOIN products p  ON ii.product_id = p.id;

-- ============================================================
-- INDEXES for query performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_invoices_date        ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoices_customer    ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status      ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_items_invoice        ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_items_product        ON invoice_items(product_id);
