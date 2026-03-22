"""
database.py — Enhanced Database Layer
Retail/Product Business | 25 customers | 22 products | 120+ invoices | 12 months
"""
import sqlite3
import os
from contextlib import contextmanager
from datetime import date, timedelta
import random

DB_PATH = os.environ.get("DB_PATH", "ebilling.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with open(SCHEMA_PATH, "r") as f:
        sql = f.read()
    with get_db() as conn:
        conn.executescript(sql)
        _seed_config(conn)
        conn.commit()
    print("✅ Database initialized.")

def _seed_config(conn):
    defaults = [
        ("business_name",    "RetailHub India"),
        ("business_address", "42 Commercial Street, Bengaluru - 560001"),
        ("business_gstin",   "29AABCU9603R1ZX"),
        ("business_state",   "Karnataka"),
        ("currency_symbol",  "₹"),
        ("invoice_prefix",   "RH"),
        ("default_tax_rate", "18"),
        ("bank_name",        "HDFC Bank"),
        ("bank_account",     "50100123456789"),
        ("bank_ifsc",        "HDFC0001234"),
    ]
    for key, val in defaults:
        conn.execute("INSERT OR IGNORE INTO business_config(key,value) VALUES(?,?)", (key, val))

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

def next_invoice_number() -> str:
    cfg = get_config()
    prefix = cfg.get("invoice_prefix", "RH")
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM invoices").fetchone()
    num = (row["cnt"] or 0) + 1
    return f"{prefix}-{date.today().strftime('%Y%m')}-{num:04d}"

def seed_demo_data():
    with get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) AS c FROM customers").fetchone()["c"]
        if existing > 0:
            print("Demo data already exists. Skipping.")
            return

        # ── 25 CUSTOMERS ──────────────────────────────────────────────
        customers = [
            ("Amit Sharma",       "amit.sharma@gmail.com",      "9876543210", "MG Road",         "Bengaluru",   "Karnataka",     "560001", "29AABCU9603R1ZX"),
            ("Priya Nair",        "priya.nair@yahoo.com",       "9845012345", "Indiranagar",      "Bengaluru",   "Karnataka",     "560038", ""),
            ("Rahul Mehta",       "rahul.mehta@outlook.com",    "9765432100", "Bandra West",      "Mumbai",      "Maharashtra",   "400050", "27AAHCS1234P1Z5"),
            ("Sunita Patel",      "sunita.patel@gmail.com",     "9712345678", "CG Road",          "Ahmedabad",   "Gujarat",       "380006", "24AAACI1234F1ZR"),
            ("Mohammed Irfan",    "irfan@business.net",         "9900112233", "Hitech City",      "Hyderabad",   "Telangana",     "500081", "36AABCT1234C1ZP"),
            ("Kavitha Reddy",     "kavitha.r@company.org",      "9988776655", "Anna Nagar",       "Chennai",     "Tamil Nadu",    "600040", "33AABCK1234D1ZQ"),
            ("Vikram Singh",      "vikram.singh@corp.in",       "9654321098", "Sector 62",        "Noida",       "UP",            "201309", "09AADCS1234B1ZT"),
            ("Deepa Krishnan",    "deepa.k@enterprise.co",      "9543210987", "Whitefield",       "Bengaluru",   "Karnataka",     "560066", "29AAADP1234F1ZY"),
            ("Ravi Kumar",        "ravi.kumar@store.dev",       "9432109876", "Salt Lake",        "Kolkata",     "WB",            "700091", ""),
            ("Ananya Joshi",      "ananya.j@consulting.biz",    "9321098765", "Viman Nagar",      "Pune",        "Maharashtra",   "411014", "27AAACJ1234G1ZZ"),
            ("Sanjay Gupta",      "sanjay.g@retail.com",        "9210987654", "Connaught Place",  "New Delhi",   "Delhi",         "110001", "07AABCG1234H1ZX"),
            ("Meena Iyer",        "meena.iyer@shop.in",         "9109876543", "T Nagar",          "Chennai",     "Tamil Nadu",    "600017", "33AAAMI1234E1ZR"),
            ("Arjun Kapoor",      "arjun.k@trade.co",           "9098765432", "Koregaon Park",    "Pune",        "Maharashtra",   "411001", "27AAACK1234I1ZW"),
            ("Lakshmi Venkat",    "lakshmi.v@wholesale.net",    "8987654321", "Jubilee Hills",    "Hyderabad",   "Telangana",     "500033", "36AACLV1234J1ZV"),
            ("Nitin Agarwal",     "nitin.a@distribution.com",   "8876543210", "Civil Lines",      "Jaipur",      "Rajasthan",     "302006", "08AAACN1234K1ZU"),
            ("Pooja Desai",       "pooja.d@emporium.in",        "8765432109", "Navrangpura",      "Ahmedabad",   "Gujarat",       "380009", "24AAACP1234L1ZT"),
            ("Kiran Rao",         "kiran.rao@supplyco.org",     "8654321098", "JP Nagar",         "Bengaluru",   "Karnataka",     "560078", "29AAACKR1234M1ZS"),
            ("Suresh Babu",       "suresh.b@megastore.com",     "8543210987", "Mylapore",         "Chennai",     "Tamil Nadu",    "600004", "33AAACS1234N1ZR"),
            ("Divya Menon",       "divya.m@fashionhub.in",      "8432109876", "Karol Bagh",       "New Delhi",   "Delhi",         "110005", "07AAACDM1234O1ZQ"),
            ("Rohit Bansal",      "rohit.b@gadgetworld.co",     "8321098765", "Sector 18",        "Noida",       "UP",            "201301", "09AAACRB1234P1ZP"),
            ("Sneha Pillai",      "sneha.p@homeneeds.net",      "8210987654", "Ernakulam",        "Kochi",       "Kerala",        "682011", "32AAACSP1234Q1ZO"),
            ("Tarun Saxena",      "tarun.s@officepro.com",      "8109876543", "Hazratganj",       "Lucknow",     "UP",            "226001", "09AAACTS1234R1ZN"),
            ("Uma Shankar",       "uma.s@homestyle.in",         "8009876543", "Basavanagudi",     "Bengaluru",   "Karnataka",     "560004", "29AAACUS1234S1ZM"),
            ("Vijay Tiwari",      "vijay.t@stockmart.co",       "7998765432", "Lal Kothi",        "Jaipur",      "Rajasthan",     "302015", "08AAACVT1234T1ZL"),
            ("Yamini Reddy",      "yamini.r@freshmart.biz",     "7887654321", "Banjara Hills",    "Hyderabad",   "Telangana",     "500034", "36AAACYR1234U1ZK"),
        ]
        conn.executemany(
            "INSERT INTO customers(name,email,phone,address,city,state,pincode,gstin) VALUES(?,?,?,?,?,?,?,?)",
            customers
        )

        # ── 22 PRODUCTS (Retail/Product Business) ─────────────────────
        products = [
            # Electronics
            ("Wireless Bluetooth Speaker",  "Portable speaker with 20hr battery",   "Electronics",    2499, "pcs",   "84182100", 18.0, 0),
            ("USB-C Fast Charger 65W",      "GaN charger with multiple ports",       "Electronics",     899, "pcs",   "85044010", 18.0, 0),
            ("Smart LED Desk Lamp",         "Touch control, 3 color modes",          "Electronics",    1299, "pcs",   "94054090", 18.0, 0),
            ("Mechanical Keyboard",         "TKL layout, RGB backlight",             "Electronics",    3499, "pcs",   "84716041", 18.0, 0),
            ("Webcam 1080p HD",             "Plug and play, built-in mic",           "Electronics",    1899, "pcs",   "85258090", 18.0, 0),
            # Home & Kitchen
            ("Stainless Steel Water Bottle","1L double-wall insulated",              "Home & Kitchen",  599, "pcs",   "73239390", 12.0, 0),
            ("Non-stick Cookware Set",      "5-piece set with glass lids",           "Home & Kitchen", 2199, "set",   "73239100", 12.0, 0),
            ("Air Purifier HEPA Filter",    "Coverage up to 300 sq ft",             "Home & Kitchen", 5999, "pcs",   "84213990", 18.0, 0),
            ("Electric Kettle 1.5L",        "Auto shutoff, boil-dry protection",     "Home & Kitchen",  799, "pcs",   "85163100", 18.0, 0),
            # Office Supplies
            ("Premium A4 Paper Ream",       "500 sheets, 80 GSM",                    "Office Supplies", 399, "ream",  "48025590", 12.0, 0),
            ("Ergonomic Office Chair",      "Lumbar support, adjustable height",     "Office Supplies",8999, "pcs",   "94013010", 18.0, 0),
            ("Whiteboard 3x2 ft",           "Magnetic surface with marker tray",     "Office Supplies",1499, "pcs",   "96100000", 12.0, 0),
            ("Ink Cartridge Set",           "Compatible with HP/Canon printers",     "Office Supplies", 699, "set",   "84439990", 18.0, 0),
            # Fashion & Accessories
            ("Cotton Tote Bag",             "Reusable, 10kg capacity",               "Fashion",         249, "pcs",   "42021290", 5.0,  0),
            ("Leather Wallet",              "Genuine leather, RFID blocking",        "Fashion",        1199, "pcs",   "42023190", 12.0, 0),
            ("Stainless Watch",             "Minimalist design, 5ATM water resist",  "Fashion",        3999, "pcs",   "91021900", 18.0, 0),
            # Sports & Fitness
            ("Yoga Mat Premium",            "6mm thickness, non-slip surface",       "Sports & Fitness",799, "pcs",   "95069990", 18.0, 0),
            ("Resistance Bands Set",        "5 levels, latex-free",                  "Sports & Fitness",499, "set",   "95069990", 18.0, 0),
            ("Protein Shaker Bottle",       "700ml BPA-free with mixing ball",       "Sports & Fitness",349, "pcs",   "39241090", 18.0, 0),
            # Stationery
            ("Gel Pen Pack 10",             "0.5mm tip, smooth writing",             "Stationery",      199, "pack",  "96081000", 12.0, 0),
            ("Spiral Notebook A5",          "200 pages, ruled",                      "Stationery",      149, "pcs",   "48201000", 12.0, 0),
            ("Sticky Notes Pack",           "5 colors, 100 sheets each",             "Stationery",      299, "pack",  "48211000", 12.0, 0),
        ]
        conn.executemany(
            "INSERT INTO products(name,description,category,unit_price,unit,hsn_sac_code,tax_rate,is_service) VALUES(?,?,?,?,?,?,?,?)",
            products
        )

        # ── 120 INVOICES (12 months) ───────────────────────────────────
        today = date.today()
        random.seed(42)

        # Invoice patterns: more invoices in recent months, seasonal spikes
        invoice_plan = []

        # Month weights: festive season (Oct/Nov) gets more invoices
        month_data = [
            (365, 350, 6),   # month 12 ago: 6 invoices
            (335, 305, 7),
            (305, 275, 8),
            (275, 245, 9),
            (245, 215, 11),  # festive peak
            (215, 185, 13),  # festive peak
            (185, 155, 10),
            (155, 125, 9),
            (125, 95,  10),
            (95,  65,  11),
            (65,  35,  12),
            (35,  5,   12),  # current month: 12 invoices
        ]

        prod_catalog = list(range(1, 23))  # product ids 1-22
        cust_pool    = list(range(1, 26))  # customer ids 1-25

        # Karnataka customers (intra-state)
        karnataka_custs = [1, 2, 8, 17, 23]

        inv_idx = 1
        cfg = get_config()
        prefix = cfg.get("invoice_prefix", "RH")

        for (day_start, day_end, count) in month_data:
            for _ in range(count):
                days_ago    = random.randint(day_end, day_start)
                inv_date    = today - timedelta(days=days_ago)
                due_date    = inv_date + timedelta(days=30)
                cust_id     = random.choice(cust_pool)
                supply_type = "intra" if cust_id in karnataka_custs else "inter"

                # 2-4 items per invoice
                num_items = random.randint(2, 4)
                item_prods = random.sample(prod_catalog, num_items)
                items_list = [(p, random.randint(1, 5)) for p in item_prods]

                # Status: older invoices mostly paid, recent ones mixed
                if days_ago > 60:
                    status = random.choices(["paid","paid","paid","cancelled"], weights=[85,5,5,5])[0]
                elif days_ago > 30:
                    status = random.choices(["paid","sent","overdue"], weights=[70,20,10])[0]
                else:
                    status = random.choices(["paid","sent","draft"], weights=[50,35,15])[0]

                inv_num  = f"{prefix}-{inv_date.strftime('%Y%m')}-{inv_idx:04d}"
                subtotal = total_tax = cgst_sum = sgst_sum = igst_sum = 0.0
                line_rows = []

                for (prod_id, qty) in items_list:
                    p = conn.execute("SELECT * FROM products WHERE id=?", (prod_id,)).fetchone()
                    if not p:
                        continue
                    price    = p["unit_price"]
                    rate     = p["tax_rate"]
                    line_sub = round(price * qty, 2)
                    tax_amt  = round(line_sub * rate / 100, 2)
                    if supply_type == "intra":
                        cgst = sgst = round(tax_amt / 2, 2); igst = 0.0
                    else:
                        cgst = sgst = 0.0; igst = tax_amt
                    line_total = round(line_sub + tax_amt, 2)
                    subtotal  += line_sub;  total_tax += tax_amt
                    cgst_sum  += cgst;      sgst_sum  += sgst;  igst_sum += igst
                    line_rows.append((prod_id, p["name"], qty, price, rate, line_sub, cgst, sgst, igst, line_total))

                total_amount = round(subtotal + total_tax, 2)

                conn.execute(
                    """INSERT INTO invoices
                       (invoice_number,customer_id,invoice_date,due_date,status,supply_type,
                        subtotal,cgst_amount,sgst_amount,igst_amount,total_tax,total_amount)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (inv_num, cust_id, inv_date.isoformat(), due_date.isoformat(),
                     status, supply_type, round(subtotal,2), round(cgst_sum,2),
                     round(sgst_sum,2), round(igst_sum,2), round(total_tax,2), total_amount)
                )
                inv_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                for row in line_rows:
                    conn.execute(
                        """INSERT INTO invoice_items
                           (invoice_id,product_id,description,quantity,unit_price,tax_rate,
                            line_subtotal,cgst,sgst,igst,line_total)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (inv_id, row[0], row[1], row[2], row[3], row[4],
                         row[5], row[6], row[7], row[8], row[9])
                    )
                inv_idx += 1

        conn.commit()
    print("✅ Enhanced retail demo data seeded — 25 customers, 22 products, 120+ invoices!")


def seed_provision_products():
    """Seed provision shop products if not already present."""
    with get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) AS c FROM products WHERE category IN ('Grains & Flour','Dal & Pulses','Cooking Oil','Sugar & Salt','Spices','Beverages','Biscuits & Snacks','Personal Care','Dairy')").fetchone()["c"]
        if existing > 0:
            print("Provision products already exist. Skipping.")
            return

        provision_products = [
            # Grains & Flour
            ("Basmati Rice 1kg",        "Premium long grain basmati",        "Grains & Flour",   85,   "kg",    "10063090", 5.0,  0),
            ("Sona Masoori Rice 1kg",   "Daily use rice",                    "Grains & Flour",   55,   "kg",    "10063090", 5.0,  0),
            ("Wheat Atta 1kg",           "Whole wheat flour",                 "Grains & Flour",   45,   "kg",    "11010000", 5.0,  0),
            ("Maida 1kg",               "Refined wheat flour",               "Grains & Flour",   40,   "kg",    "11010000", 5.0,  0),
            ("Rava / Sooji 500g",       "Semolina for upma, halwa",          "Grains & Flour",   28,   "pkt",   "11010000", 5.0,  0),
            ("Poha 500g",               "Flattened rice",                    "Grains & Flour",   32,   "pkt",   "10064000", 5.0,  0),
            # Dal & Pulses
            ("Toor Dal 1kg",            "Split pigeon peas",                 "Dal & Pulses",     110,  "kg",    "07134000", 5.0,  0),
            ("Chana Dal 1kg",           "Split chickpeas",                   "Dal & Pulses",     95,   "kg",    "07132000", 5.0,  0),
            ("Moong Dal 1kg",           "Split green gram",                  "Dal & Pulses",     115,  "kg",    "07135000", 5.0,  0),
            ("Masoor Dal 500g",         "Red lentils",                       "Dal & Pulses",     60,   "pkt",   "07134000", 5.0,  0),
            ("Rajma 500g",              "Kidney beans",                      "Dal & Pulses",     75,   "pkt",   "07133200", 5.0,  0),
            # Cooking Oil
            ("Sunflower Oil 1L",        "Refined sunflower oil",             "Cooking Oil",      145,  "ltr",   "15121100", 5.0,  0),
            ("Coconut Oil 500ml",       "Pure coconut oil",                  "Cooking Oil",      135,  "btl",   "15131100", 5.0,  0),
            ("Mustard Oil 1L",          "Kachi ghani mustard oil",           "Cooking Oil",      155,  "ltr",   "15141100", 5.0,  0),
            ("Groundnut Oil 1L",        "Cold pressed groundnut oil",        "Cooking Oil",      180,  "ltr",   "15081000", 5.0,  0),
            # Sugar & Salt
            ("Sugar 1kg",              "Refined white sugar",               "Sugar & Salt",      50,   "kg",    "17011400", 5.0,  0),
            ("Rock Salt 1kg",          "Sendha namak",                      "Sugar & Salt",      35,   "kg",    "25010010", 0.0,  0),
            ("Iodized Salt 1kg",       "Table salt",                        "Sugar & Salt",      20,   "kg",    "25010090", 0.0,  0),
            ("Jaggery 500g",           "Pure cane jaggery",                 "Sugar & Salt",      45,   "pkt",   "17029010", 5.0,  0),
            # Spices
            ("Turmeric Powder 100g",   "Pure haldi powder",                 "Spices",            25,   "pkt",   "09103010", 5.0,  0),
            ("Red Chilli Powder 100g", "Kashmiri chilli powder",            "Spices",            35,   "pkt",   "09042210", 5.0,  0),
            ("Coriander Powder 100g",  "Dhania powder",                     "Spices",            22,   "pkt",   "09092110", 5.0,  0),
            ("Cumin Seeds 100g",       "Jeera",                             "Spices",            30,   "pkt",   "09093100", 5.0,  0),
            ("Garam Masala 50g",       "Mixed spice blend",                 "Spices",            40,   "pkt",   "09109100", 12.0, 0),
            ("Mustard Seeds 100g",     "Rai / sarson seeds",                "Spices",            18,   "pkt",   "12079910", 5.0,  0),
            # Beverages
            ("Tata Tea Premium 250g",  "Black tea leaves",                  "Beverages",         90,   "pkt",   "09024090", 5.0,  0),
            ("Bru Coffee 50g",         "Instant coffee",                    "Beverages",         85,   "pkt",   "21011100", 12.0, 0),
            ("Horlicks 500g",          "Health drink powder",               "Beverages",        220,   "jar",   "19011000", 12.0, 0),
            ("Boost 500g",             "Chocolate malt drink",              "Beverages",        230,   "jar",   "19011000", 12.0, 0),
            ("Complan 200g",           "Nutrition drink powder",            "Beverages",        135,   "pkt",   "19011000", 12.0, 0),
            # Biscuits & Snacks
            ("Parle-G Biscuits 800g",  "Glucose biscuits family pack",      "Biscuits & Snacks",  65,  "pkt",   "19053100", 18.0, 0),
            ("Good Day Cashew 200g",   "Butter cashew biscuits",            "Biscuits & Snacks",  40,  "pkt",   "19053100", 18.0, 0),
            ("Lays Classic 80g",       "Salted potato chips",               "Biscuits & Snacks",  20,  "pkt",   "20051000", 12.0, 0),
            ("Haldirams Mixture 200g", "Namkeen mixed snack",               "Biscuits & Snacks",  50,  "pkt",   "21069099", 12.0, 0),
            ("Monaco Biscuits 200g",   "Salted crackers",                   "Biscuits & Snacks",  35,  "pkt",   "19053100", 18.0, 0),
            # Personal Care
            ("Lifebuoy Soap 100g",     "Germ protection soap",              "Personal Care",      28,  "pcs",   "34011110", 18.0, 0),
            ("Dove Soap 100g",         "Moisturizing beauty bar",           "Personal Care",      55,  "pcs",   "34011110", 18.0, 0),
            ("Clinic Plus Shampoo 80ml","Anti-dandruff shampoo",            "Personal Care",      65,  "btl",   "33051000", 18.0, 0),
            ("Surf Excel 500g",        "Washing powder",                    "Personal Care",      85,  "pkt",   "34022090", 18.0, 0),
            ("Colgate 200g",           "Toothpaste strong teeth",           "Personal Care",      90,  "pcs",   "33061000", 18.0, 0),
            # Dairy
            ("Amul Milk 1L",           "Full cream milk",                   "Dairy",              60,  "ltr",   "04011000", 5.0,  0),
            ("Amul Butter 100g",       "Salted butter",                     "Dairy",              55,  "pcs",   "04051000", 12.0, 0),
            ("Amul Paneer 200g",       "Fresh cottage cheese",              "Dairy",              80,  "pcs",   "04063000", 12.0, 0),
            ("Curd 400g",              "Fresh set curd",                    "Dairy",              40,  "cup",   "04031000", 5.0,  0),
            ("Ghee 500ml",             "Pure cow ghee",                     "Dairy",             280,  "btl",   "04059000", 12.0, 0),
        ]
        conn.executemany(
            "INSERT INTO products(name,description,category,unit_price,unit,hsn_sac_code,tax_rate,is_service) VALUES(?,?,?,?,?,?,?,?)",
            provision_products
        )
        conn.commit()
    print(f"✅ {len(provision_products)} provision shop products added!")
