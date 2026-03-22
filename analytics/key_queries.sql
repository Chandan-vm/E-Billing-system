-- ============================================================
-- E-BILLING SYSTEM — KEY ANALYTICS SQL QUERIES
-- For Portfolio: Demonstrates DA/BA SQL skills
-- ============================================================

-- ──────────────────────────────────────────────────────────
-- 1. KPI SUMMARY (Multi-metric CTE aggregation)
-- Skill: CTEs, subqueries, conditional aggregation
-- ──────────────────────────────────────────────────────────
WITH paid_invoices AS (
    SELECT * FROM invoices WHERE status IN ('paid','sent')
),
base AS (
    SELECT
        COUNT(*)                        AS total_invoices,
        SUM(total_amount)               AS total_revenue,
        AVG(total_amount)               AS avg_invoice_value,
        COUNT(DISTINCT customer_id)     AS unique_customers
    FROM paid_invoices
),
repeat_cust AS (
    SELECT COUNT(*) AS repeat_count
    FROM (
        SELECT customer_id FROM paid_invoices
        GROUP BY customer_id HAVING COUNT(*) > 1
    )
)
SELECT
    b.*,
    r.repeat_count,
    ROUND(r.repeat_count * 100.0 / NULLIF(b.unique_customers,0), 1) AS repeat_rate_pct,
    ROUND(b.total_revenue / NULLIF(b.unique_customers,0), 2)        AS arpu
FROM base b, repeat_cust r;


-- ──────────────────────────────────────────────────────────
-- 2. MONTH-OVER-MONTH REVENUE GROWTH
-- Skill: Window functions, LAG, time series
-- ──────────────────────────────────────────────────────────
WITH monthly AS (
    SELECT
        strftime('%Y-%m', invoice_date) AS period,
        SUM(total_amount)               AS revenue
    FROM invoices WHERE status IN ('paid','sent')
    GROUP BY period
)
SELECT
    period,
    revenue,
    LAG(revenue) OVER (ORDER BY period)  AS prev_month_revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY period)) /
        NULLIF(LAG(revenue) OVER (ORDER BY period), 0) * 100, 1
    ) AS mom_growth_pct
FROM monthly
ORDER BY period DESC;


-- ──────────────────────────────────────────────────────────
-- 3. TOP PRODUCTS — REVENUE SHARE (Percentage contribution)
-- Skill: Window functions, PARTITION, revenue share calc
-- ──────────────────────────────────────────────────────────
SELECT
    p.name                              AS product,
    p.category,
    COUNT(DISTINCT ii.invoice_id)       AS invoice_count,
    SUM(ii.quantity)                    AS total_qty,
    SUM(ii.line_subtotal)               AS product_revenue,
    ROUND(SUM(ii.line_subtotal) * 100.0 /
        SUM(SUM(ii.line_subtotal)) OVER (), 1) AS revenue_share_pct,
    RANK() OVER (ORDER BY SUM(ii.line_subtotal) DESC) AS revenue_rank
FROM invoice_items ii
JOIN products p     ON ii.product_id = p.id
JOIN invoices inv   ON ii.invoice_id = inv.id
WHERE inv.status IN ('paid','sent')
GROUP BY p.id, p.name, p.category
ORDER BY product_revenue DESC;


-- ──────────────────────────────────────────────────────────
-- 4. RFM CUSTOMER SEGMENTATION
-- Skill: CASE WHEN, DATE functions, customer scoring
-- ──────────────────────────────────────────────────────────
SELECT
    c.name,
    c.city,
    COUNT(DISTINCT inv.id)          AS frequency,
    ROUND(SUM(inv.total_amount), 2) AS monetary,
    MAX(inv.invoice_date)           AS last_purchase,
    CAST(julianday('now') - julianday(MAX(inv.invoice_date)) AS INT) AS recency_days,
    -- Segment logic
    CASE
        WHEN COUNT(DISTINCT inv.id) >= 5                                              THEN 'VIP'
        WHEN COUNT(DISTINCT inv.id) >= 3                                              THEN 'Loyal'
        WHEN COUNT(DISTINCT inv.id) >= 2                                              THEN 'Returning'
        WHEN CAST(julianday('now') - julianday(MAX(inv.invoice_date)) AS INT) > 90   THEN 'At-Risk'
        ELSE 'New'
    END AS segment
FROM customers c
JOIN invoices inv ON c.id = inv.customer_id AND inv.status IN ('paid','sent')
GROUP BY c.id
ORDER BY monetary DESC;


-- ──────────────────────────────────────────────────────────
-- 5. CUSTOMER LIFETIME VALUE + COHORT
-- Skill: GROUP BY, aggregation, joins
-- ──────────────────────────────────────────────────────────
SELECT
    c.id,
    c.name,
    strftime('%Y-%m', MIN(inv.invoice_date))  AS acquisition_month,
    COUNT(DISTINCT inv.id)                    AS total_orders,
    SUM(inv.total_amount)                     AS lifetime_value,
    AVG(inv.total_amount)                     AS avg_order_value,
    MAX(inv.invoice_date)                     AS last_active,
    CAST(julianday('now') - julianday(MIN(inv.invoice_date)) AS INT) AS customer_age_days
FROM customers c
JOIN invoices inv ON c.id = inv.customer_id
WHERE inv.status IN ('paid','sent')
GROUP BY c.id, c.name
ORDER BY lifetime_value DESC;


-- ──────────────────────────────────────────────────────────
-- 6. GST GSTR-1 SUMMARY (India Compliance)
-- Skill: Conditional aggregation, supply type split
-- ──────────────────────────────────────────────────────────
SELECT
    strftime('%Y-%m', invoice_date)                 AS tax_period,
    supply_type,
    COUNT(*)                                         AS invoice_count,
    SUM(subtotal)                                    AS taxable_value,
    SUM(CASE WHEN supply_type='intra' THEN cgst_amount ELSE 0 END) AS cgst,
    SUM(CASE WHEN supply_type='intra' THEN sgst_amount ELSE 0 END) AS sgst,
    SUM(CASE WHEN supply_type='inter' THEN igst_amount ELSE 0 END) AS igst,
    SUM(total_tax)                                   AS total_gst_collected
FROM invoices
WHERE status IN ('paid','sent')
GROUP BY tax_period, supply_type
ORDER BY tax_period DESC;


-- ──────────────────────────────────────────────────────────
-- 7. AGING ANALYSIS — RECEIVABLES AGEING
-- Skill: Date arithmetic, CASE bucketing
-- ──────────────────────────────────────────────────────────
SELECT
    inv.invoice_number,
    c.name AS customer,
    inv.invoice_date,
    inv.due_date,
    inv.total_amount,
    CAST(julianday('now') - julianday(inv.due_date) AS INT) AS days_past_due,
    CASE
        WHEN julianday('now') <= julianday(inv.due_date)       THEN 'Current'
        WHEN julianday('now') - julianday(inv.due_date) <= 30  THEN '1-30 Days'
        WHEN julianday('now') - julianday(inv.due_date) <= 60  THEN '31-60 Days'
        WHEN julianday('now') - julianday(inv.due_date) <= 90  THEN '61-90 Days'
        ELSE '90+ Days'
    END AS aging_bucket
FROM invoices inv
JOIN customers c ON inv.customer_id = c.id
WHERE inv.status IN ('sent','overdue')
ORDER BY days_past_due DESC;


-- ──────────────────────────────────────────────────────────
-- 8. WEEKLY SALES TREND
-- Skill: Time granularity, strftime
-- ──────────────────────────────────────────────────────────
SELECT
    strftime('%Y-W%W', invoice_date) AS week,
    COUNT(*)                          AS invoices,
    SUM(total_amount)                 AS weekly_revenue,
    AVG(total_amount)                 AS avg_order_value
FROM invoices
WHERE status IN ('paid','sent')
  AND invoice_date >= date('now', '-56 days')
GROUP BY week
ORDER BY week ASC;


-- ──────────────────────────────────────────────────────────
-- 9. PRODUCT-CUSTOMER CROSS ANALYSIS
-- Skill: Many-to-many joins, pivot-ready output
-- ──────────────────────────────────────────────────────────
SELECT
    c.name       AS customer,
    p.name       AS product,
    p.category,
    SUM(ii.quantity)        AS qty_purchased,
    SUM(ii.line_subtotal)   AS total_spend
FROM customers c
JOIN invoices inv       ON c.id = inv.customer_id AND inv.status IN ('paid','sent')
JOIN invoice_items ii  ON inv.id = ii.invoice_id
JOIN products p        ON ii.product_id = p.id
GROUP BY c.id, p.id
ORDER BY total_spend DESC;


-- ──────────────────────────────────────────────────────────
-- 10. CUMULATIVE REVENUE (Running Total)
-- Skill: Window functions, running aggregates
-- ──────────────────────────────────────────────────────────
SELECT
    invoice_date,
    invoice_number,
    total_amount,
    SUM(total_amount) OVER (ORDER BY invoice_date, id ROWS UNBOUNDED PRECEDING) AS cumulative_revenue,
    COUNT(*) OVER (ORDER BY invoice_date, id ROWS UNBOUNDED PRECEDING)           AS invoice_count_running
FROM invoices
WHERE status IN ('paid','sent')
ORDER BY invoice_date, id;
