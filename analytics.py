"""
analytics.py — Data Analytics Engine for E-Billing System
==========================================================
All KPIs, aggregations, and business intelligence queries.
This module demonstrates SQL-driven analysis skills for a DA portfolio.
"""
import pandas as pd
from database import get_db


# ─────────────────────────────────────────────
# KPI Dashboard Metrics
# ─────────────────────────────────────────────

def get_kpi_summary() -> dict:
    """
    Core business KPIs — Total Revenue, Invoice Count, ARPU, Repeat Rate.
    DA Skill: Multi-metric aggregation with CTEs.
    """
    sql = """
    WITH paid_invoices AS (
        SELECT * FROM invoices WHERE status IN ('paid','sent')
    ),
    base AS (
        SELECT
            COUNT(*)                             AS total_invoices,
            COALESCE(SUM(total_amount), 0)       AS total_revenue,
            COALESCE(AVG(total_amount), 0)       AS avg_invoice_value,
            COUNT(DISTINCT customer_id)          AS unique_customers
        FROM paid_invoices
    ),
    repeat_customers AS (
        SELECT COUNT(*) AS repeat_count
        FROM (
            SELECT customer_id FROM paid_invoices
            GROUP BY customer_id HAVING COUNT(*) > 1
        )
    ),
    this_month AS (
        SELECT COALESCE(SUM(total_amount), 0) AS revenue
        FROM paid_invoices
        WHERE strftime('%Y-%m', invoice_date) = strftime('%Y-%m', 'now')
    ),
    last_month AS (
        SELECT COALESCE(SUM(total_amount), 0) AS revenue
        FROM paid_invoices
        WHERE strftime('%Y-%m', invoice_date) = strftime('%Y-%m', date('now','-1 month'))
    )
    SELECT
        b.total_invoices,
        b.total_revenue,
        b.avg_invoice_value,
        b.unique_customers,
        r.repeat_count,
        ROUND(CAST(r.repeat_count AS FLOAT) / NULLIF(b.unique_customers,0) * 100, 1) AS repeat_rate_pct,
        ROUND(b.total_revenue / NULLIF(b.unique_customers,0), 2) AS arpu,
        tm.revenue AS this_month_revenue,
        lm.revenue AS last_month_revenue,
        CASE
            WHEN lm.revenue > 0
            THEN ROUND((tm.revenue - lm.revenue) / lm.revenue * 100, 1)
            ELSE NULL
        END AS mom_growth_pct
    FROM base b, repeat_customers r, this_month tm, last_month lm
    """
    with get_db() as conn:
        row = conn.execute(sql).fetchone()
    return dict(row) if row else {}


# ─────────────────────────────────────────────
# Revenue Trend Analysis
# ─────────────────────────────────────────────

def get_monthly_revenue_trend(months: int = 6) -> pd.DataFrame:
    """
    Monthly revenue trend for last N months.
    DA Skill: Time-series aggregation, MoM growth calculation.
    """
    sql = """
    SELECT
        strftime('%Y-%m', invoice_date) AS period,
        strftime('%b %Y', invoice_date) AS label,
        COUNT(*)                         AS invoices,
        SUM(subtotal)                    AS gross_revenue,
        SUM(total_tax)                   AS tax_collected,
        SUM(total_amount)                AS net_revenue,
        AVG(total_amount)                AS avg_order_value
    FROM invoices
    WHERE status IN ('paid','sent')
      AND invoice_date >= date('now', ? || ' months')
    GROUP BY period
    ORDER BY period ASC
    """
    with get_db() as conn:
        df = pd.read_sql_query(sql, conn, params=(f"-{months}",))
    if not df.empty:
        df["mom_growth"] = df["net_revenue"].pct_change() * 100
        df["mom_growth"] = df["mom_growth"].round(1)
    return df


def get_weekly_revenue(weeks: int = 8) -> pd.DataFrame:
    """
    Weekly revenue for last N weeks.
    DA Skill: Week-over-week granularity analysis.
    """
    sql = """
    SELECT
        strftime('%Y-W%W', invoice_date) AS week,
        COUNT(*)                          AS invoices,
        SUM(total_amount)                 AS revenue
    FROM invoices
    WHERE status IN ('paid','sent')
      AND invoice_date >= date('now', ? || ' days')
    GROUP BY week
    ORDER BY week ASC
    """
    with get_db() as conn:
        return pd.read_sql_query(sql, conn, params=(f"-{weeks*7}",))


# ─────────────────────────────────────────────
# Product Performance
# ─────────────────────────────────────────────

def get_top_products(limit: int = 10) -> pd.DataFrame:
    """
    Top products by revenue, quantity, and frequency.
    DA Skill: Multi-dimension ranking, joins.
    """
    sql = """
    SELECT
        p.name                         AS product,
        p.category,
        COUNT(DISTINCT ii.invoice_id)  AS invoice_count,
        SUM(ii.quantity)               AS total_qty,
        SUM(ii.line_subtotal)          AS total_revenue,
        AVG(ii.unit_price)             AS avg_price,
        ROUND(SUM(ii.line_subtotal) * 100.0 /
            (SELECT SUM(subtotal) FROM invoices WHERE status IN('paid','sent')), 1) AS revenue_share_pct
    FROM invoice_items ii
    JOIN products p     ON ii.product_id = p.id
    JOIN invoices inv   ON ii.invoice_id = inv.id
    WHERE inv.status IN ('paid','sent')
    GROUP BY p.id, p.name, p.category
    ORDER BY total_revenue DESC
    LIMIT ?
    """
    with get_db() as conn:
        return pd.read_sql_query(sql, conn, params=(limit,))


def get_category_breakdown() -> pd.DataFrame:
    """Revenue breakdown by product category."""
    sql = """
    SELECT
        p.category,
        COUNT(DISTINCT ii.invoice_id) AS invoice_count,
        SUM(ii.line_subtotal)         AS revenue,
        ROUND(SUM(ii.line_subtotal)*100.0/
            (SELECT SUM(line_subtotal) FROM invoice_items ii2
             JOIN invoices inv2 ON ii2.invoice_id=inv2.id
             WHERE inv2.status IN('paid','sent')), 1) AS share_pct
    FROM invoice_items ii
    JOIN products p   ON ii.product_id = p.id
    JOIN invoices inv ON ii.invoice_id = inv.id
    WHERE inv.status IN ('paid','sent')
    GROUP BY p.category
    ORDER BY revenue DESC
    """
    with get_db() as conn:
        return pd.read_sql_query(sql, conn)


# ─────────────────────────────────────────────
# Customer Analytics
# ─────────────────────────────────────────────

def get_customer_segments() -> pd.DataFrame:
    """
    RFM-inspired customer segmentation.
    DA Skill: Segmentation logic, CASE statements, window functions.
    """
    sql = """
    SELECT
        c.name,
        c.city,
        COUNT(DISTINCT inv.id)          AS frequency,
        SUM(inv.total_amount)           AS monetary,
        MAX(inv.invoice_date)           AS last_purchase,
        CAST(julianday('now') - julianday(MAX(inv.invoice_date)) AS INTEGER) AS recency_days,
        CASE
            WHEN COUNT(DISTINCT inv.id) >= 5                              THEN 'VIP'
            WHEN COUNT(DISTINCT inv.id) >= 3                              THEN 'Loyal'
            WHEN COUNT(DISTINCT inv.id) >= 2                              THEN 'Returning'
            WHEN CAST(julianday('now') - julianday(MAX(inv.invoice_date)) AS INTEGER) > 90 THEN 'At-Risk'
            ELSE 'New'
        END AS segment
    FROM customers c
    JOIN invoices inv ON c.id = inv.customer_id
    WHERE inv.status IN ('paid','sent')
    GROUP BY c.id, c.name, c.city
    ORDER BY monetary DESC
    """
    with get_db() as conn:
        return pd.read_sql_query(sql, conn)


def get_customer_segment_summary() -> pd.DataFrame:
    """Aggregate segment counts and revenue."""
    df = get_customer_segments()
    if df.empty:
        return df
    return (
        df.groupby("segment")
          .agg(customers=("name","count"), total_revenue=("monetary","sum"))
          .reset_index()
          .sort_values("total_revenue", ascending=False)
    )


def get_top_customers(limit: int = 10) -> pd.DataFrame:
    """Top customers by lifetime value."""
    sql = """
    SELECT
        c.name,
        c.email,
        c.city,
        COUNT(DISTINCT inv.id)  AS invoices,
        SUM(inv.total_amount)   AS lifetime_value,
        AVG(inv.total_amount)   AS avg_order_value,
        MAX(inv.invoice_date)   AS last_purchase
    FROM customers c
    JOIN invoices inv ON c.id = inv.customer_id
    WHERE inv.status IN ('paid','sent')
    GROUP BY c.id
    ORDER BY lifetime_value DESC
    LIMIT ?
    """
    with get_db() as conn:
        return pd.read_sql_query(sql, conn, params=(limit,))


# ─────────────────────────────────────────────
# GST / Tax Analysis
# ─────────────────────────────────────────────

def get_gst_summary() -> pd.DataFrame:
    """
    GST liability summary — essential for India tax compliance.
    DA Skill: Tax aggregation by supply type, period.
    """
    sql = """
    SELECT
        strftime('%Y-%m', invoice_date) AS period,
        supply_type,
        COUNT(*)                         AS invoices,
        SUM(subtotal)                    AS taxable_value,
        SUM(cgst_amount)                 AS cgst,
        SUM(sgst_amount)                 AS sgst,
        SUM(igst_amount)                 AS igst,
        SUM(total_tax)                   AS total_gst
    FROM invoices
    WHERE status IN ('paid','sent')
    GROUP BY period, supply_type
    ORDER BY period DESC
    """
    with get_db() as conn:
        return pd.read_sql_query(sql, conn)


# ─────────────────────────────────────────────
# Status & Receivables
# ─────────────────────────────────────────────

def get_invoice_status_summary() -> list:
    sql = """
    SELECT status, COUNT(*) AS count, COALESCE(SUM(total_amount),0) AS total
    FROM invoices GROUP BY status ORDER BY total DESC
    """
    with get_db() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def get_outstanding_receivables() -> pd.DataFrame:
    """Overdue and sent-but-unpaid invoices."""
    sql = """
    SELECT
        inv.invoice_number,
        c.name AS customer,
        c.email,
        inv.invoice_date,
        inv.due_date,
        inv.total_amount,
        inv.status,
        CAST(julianday('now') - julianday(inv.due_date) AS INTEGER) AS days_overdue
    FROM invoices inv
    JOIN customers c ON inv.customer_id = c.id
    WHERE inv.status IN ('sent','overdue')
    ORDER BY inv.due_date ASC
    """
    with get_db() as conn:
        return pd.read_sql_query(sql, conn)


# ─────────────────────────────────────────────
# Export Helpers
# ─────────────────────────────────────────────

def export_invoice_detail() -> pd.DataFrame:
    """Full flattened invoice detail — ready for Power BI / Excel."""
    sql = "SELECT * FROM vw_invoice_detail ORDER BY invoice_date DESC"
    with get_db() as conn:
        return pd.read_sql_query(sql, conn)


def export_product_performance() -> pd.DataFrame:
    sql = "SELECT * FROM vw_product_performance ORDER BY total_revenue DESC"
    with get_db() as conn:
        return pd.read_sql_query(sql, conn)


def export_customer_insights() -> pd.DataFrame:
    sql = "SELECT * FROM vw_customer_insights ORDER BY lifetime_value DESC"
    with get_db() as conn:
        return pd.read_sql_query(sql, conn)
