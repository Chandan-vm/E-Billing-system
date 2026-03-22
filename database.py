"""
database.py — Database layer for E-Billing System
Handles: connection, schema init, seed data, query helpers
"""
import sqlite3
import os
from contextlib import contextmanager
from datetime import date, timedelta
import random

DB_PATH = os.environ.get("DB_PATH", "ebilling.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


# ─────────────────────────────────────────────
# Connection Management
# ─────────────────────────────────────────────

@contextmanager
def get_db():
    """Context manager: yields a connected, row-factory cursor."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create all tables, views, and indexes from schema.sql."""
    with open(SCHEMA_PATH, "r") as f:
        sql = f.read()
    with get_db() as conn:
        conn.executescript(sql)
        _seed_config(conn)
        conn.commit()
    print("✅ Database initialized.")


def _seed_config(conn):
    defaults = [
        ("business_name",   "My Business"),
        ("business_address","123 Main Street, City"),
        ("business_gstin",  "29AABCU9603R1ZX"),
        ("business_state",  "Karnataka"),
        ("currency_symbol", "₹"),
        ("invoice_prefix",  "INV"),
        ("default_tax_rate","18"),
        ("bank_name",       "State Bank of India"),
        ("bank_account",    "1234567890"),
        ("bank_ifsc",       "SBIN0001234"),
    ]
    for key, val in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO business_config(key,value) VALUES(?,?)",
            (key, val)
        )


# ─────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────

def get_config() -> dict:
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM business_config").fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_config(key: str, value: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO business_config(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
            (key, value)
        )
        conn.commit()


# ─────────────────────────────────────────────
# Invoice Number Generator
# ─────────────────────────────────────────────

def next_invoice_number() -> str:
    cfg = get_config()
    prefix = cfg.get("invoice_prefix", "INV")
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM invoices"
        ).fetchone()
    num = (row["cnt"] or 0) + 1
    return f"{prefix}-{date.today().strftime('%Y%m')}-{num:04d}"


# ─────────────────────────────────────────────
# Sample / Demo Data Seeder
# ─────────────────────────────────────────────

def seed_demo_data():
    """Insert realistic demo data for portfolio demonstration."""
    with get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) AS c FROM customers").fetchone()["c"]
        if existing > 0:
            print("Demo data already exists. Skipping.")
            return

        # --- Customers ---
        customers = [
            ("Rajesh Sharma",     "rajesh@techcorp.in",     "9876543210", "Koramangala",   "Bengaluru",  "Karnataka", "560034", "29AABCU9603R1ZX"),
            ("Priya Nair",        "priya@designstudio.com", "9845012345", "Indiranagar",   "Bengaluru",  "Karnataka", "560038", ""),
            ("Arun Mehta",        "arun@startupx.io",       "9765432100", "Bandra West",   "Mumbai",     "Maharashtra","400050","27AAHCS1234P1Z5"),
            ("Sunita Patel",      "sunita@retailco.com",    "9712345678", "C.G. Road",     "Ahmedabad",  "Gujarat",   "380006", "24AAACI1234F1ZR"),
            ("Mohammed Irfan",    "irfan@logistics.net",    "9900112233", "Hitech City",   "Hyderabad",  "Telangana", "500081", "36AABCT1234C1ZP"),
            ("Kavitha Reddy",     "kavitha@edu.org",        "9988776655", "Anna Nagar",    "Chennai",    "Tamil Nadu","600040","33AABCK1234D1ZQ"),
            ("Vikram Singh",      "vikram@manufact.in",     "9654321098", "Sector 62",     "Noida",      "UP",        "201309", "09AADCS1234B1ZT"),
            ("Deepa Krishnan",    "deepa@pharma.co",        "9543210987", "Whitefield",    "Bengaluru",  "Karnataka", "560066", "29AAADP1234F1ZY"),
            ("Ravi Kumar",        "ravi@freelance.dev",     "9432109876", "Salt Lake",     "Kolkata",    "WB",        "700091", ""),
            ("Ananya Joshi",      "ananya@consulting.biz",  "9321098765", "Viman Nagar",   "Pune",       "Maharashtra","411014","27AAACJ1234G1ZZ"),
        ]
        conn.executemany(
            "INSERT INTO customers(name,email,phone,address,city,state,pincode,gstin) VALUES(?,?,?,?,?,?,?,?)",
            customers
        )

        # --- Products ---
        products = [
            ("Web Development",     "Full-stack web app development", "Services",  45000, "project", "998314", 18.0, 1),
            ("UI/UX Design",        "User interface design package",  "Services",  25000, "project", "998312", 18.0, 1),
            ("SEO Package",         "3-month SEO optimization",       "Services",  15000, "month",   "998361", 18.0, 1),
            ("Domain Registration", "Annual domain name registration","Products",    899, "year",    "847160", 18.0, 0),
            ("SSL Certificate",     "1-year SSL certificate",         "Products",   2500, "year",    "847160", 18.0, 0),
            ("Cloud Hosting",       "VPS cloud hosting per month",    "Services",   3500, "month",   "998315", 18.0, 1),
            ("Content Writing",     "Blog / copywriting per article", "Services",   2000, "article", "998391", 18.0, 1),
            ("Social Media Mgmt",   "Monthly social media management","Services",  12000, "month",   "998369", 18.0, 1),
            ("Logo Design",         "Brand logo with source files",   "Services",   8000, "project", "998312", 18.0, 1),
            ("Annual Maintenance",  "Software maintenance contract",  "Services",  36000, "year",    "998314", 18.0, 1),
            ("Email Marketing",     "Bulk email campaign setup",      "Services",   5000, "campaign","998369", 18.0, 1),
            ("Data Analytics Report","Custom BI/analytics report",    "Services",  20000, "report",  "998314", 18.0, 1),
        ]
        conn.executemany(
            "INSERT INTO products(name,description,category,unit_price,unit,hsn_sac_code,tax_rate,is_service) VALUES(?,?,?,?,?,?,?,?)",
            products
        )

        # --- Invoices (6 months of historical data) ---
        today = date.today()
        inv_data = [
            # (customer_id, days_ago, status, items: [(product_id, qty)])
            (1, 180, "paid",     [(1,1),(2,1)]),
            (2, 170, "paid",     [(9,1),(7,3)]),
            (3, 160, "paid",     [(1,1),(6,3)]),
            (4, 155, "paid",     [(8,2),(11,1)]),
            (5, 145, "paid",     [(1,1),(3,1)]),
            (1, 140, "paid",     [(10,1),(5,2)]),
            (6, 130, "paid",     [(12,1),(7,5)]),
            (7, 120, "paid",     [(1,1),(4,2)]),
            (8, 115, "paid",     [(2,1),(6,2)]),
            (2, 110, "paid",     [(8,1),(11,2)]),
            (3, 100, "paid",     [(3,3),(6,1)]),
            (9, 95,  "paid",     [(7,4),(9,1)]),
            (10,90,  "paid",     [(12,1),(1,1)]),
            (1, 85,  "paid",     [(2,1),(10,1)]),
            (4, 80,  "paid",     [(8,1),(3,2)]),
            (5, 75,  "paid",     [(1,1),(6,2)]),
            (6, 70,  "paid",     [(11,3),(7,2)]),
            (7, 65,  "paid",     [(4,3),(5,1)]),
            (2, 60,  "paid",     [(1,1),(2,1)]),
            (8, 55,  "paid",     [(12,2),(6,1)]),
            (3, 50,  "paid",     [(9,1),(3,1)]),
            (1, 45,  "paid",     [(8,2),(11,1)]),
            (9, 40,  "paid",     [(1,1),(6,3)]),
            (10,35,  "paid",     [(7,3),(2,1)]),
            (4, 30,  "sent",     [(12,1),(10,1)]),
            (5, 25,  "sent",     [(3,2),(8,1)]),
            (6, 20,  "sent",     [(1,1),(6,1)]),
            (2, 15,  "sent",     [(2,1),(9,1)]),
            (1, 10,  "sent",     [(11,2),(4,1)]),
            (7,  5,  "draft",    [(12,1),(7,2)]),
        ]

        cfg = get_config()
        prefix = cfg.get("invoice_prefix", "INV")

        for idx, (cust_id, days_ago, status, items) in enumerate(inv_data, 1):
            inv_date = today - timedelta(days=days_ago)
            due_date = inv_date + timedelta(days=30)
            inv_num  = f"{prefix}-{inv_date.strftime('%Y%m')}-{idx:04d}"

            # Determine supply type (intra=Karnataka, inter=other states)
            cust_row = conn.execute("SELECT state FROM customers WHERE id=?", (cust_id,)).fetchone()
            supply = "intra" if cust_row and cust_row["state"] == "Karnataka" else "inter"

            subtotal = total_tax = cgst_sum = sgst_sum = igst_sum = 0.0
            line_rows = []

            for (prod_id, qty) in items:
                p = conn.execute("SELECT * FROM products WHERE id=?", (prod_id,)).fetchone()
                if not p:
                    continue
                price     = p["unit_price"]
                rate      = p["tax_rate"]
                line_sub  = round(price * qty, 2)
                tax_amt   = round(line_sub * rate / 100, 2)

                if supply == "intra":
                    cgst = sgst = round(tax_amt / 2, 2)
                    igst = 0.0
                else:
                    cgst = sgst = 0.0
                    igst = tax_amt

                line_total = round(line_sub + tax_amt, 2)

                subtotal  += line_sub
                total_tax += tax_amt
                cgst_sum  += cgst
                sgst_sum  += sgst
                igst_sum  += igst

                line_rows.append((None, prod_id, p["name"], qty, price, rate, line_sub, cgst, sgst, igst, line_total))

            total_amount = round(subtotal + total_tax, 2)

            conn.execute(
                """INSERT INTO invoices
                   (invoice_number,customer_id,invoice_date,due_date,status,supply_type,
                    subtotal,cgst_amount,sgst_amount,igst_amount,total_tax,total_amount)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (inv_num, cust_id, inv_date.isoformat(), due_date.isoformat(),
                 status, supply, round(subtotal,2), round(cgst_sum,2),
                 round(sgst_sum,2), round(igst_sum,2), round(total_tax,2), total_amount)
            )
            inv_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            for row in line_rows:
                conn.execute(
                    """INSERT INTO invoice_items
                       (invoice_id,product_id,description,quantity,unit_price,tax_rate,
                        line_subtotal,cgst,sgst,igst,line_total)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (inv_id, row[1], row[2], row[3], row[4], row[5],
                     row[6], row[7], row[8], row[9], row[10])
                )

        conn.commit()
    print("✅ Demo data seeded successfully.")
