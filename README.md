# ⚡ BillFlow — E-Billing System
### Production-Quality Prototype | Data Analyst Portfolio Project

---

## 🗂️ Project Structure

```
ebilling/
├── app.py                    # Flask backend (all routes)
├── database.py               # DB layer: init, seed, helpers
├── analytics.py              # DA engine: all KPI queries (Pandas + SQL)
├── schema.sql                # Full relational schema + analytics views
├── requirements.txt
│
├── templates/                # HTML UI (Jinja2)
│   ├── base.html             # Layout, sidebar, nav
│   ├── index.html            # Dashboard
│   ├── analytics.html        # Full analytics page
│   ├── invoices.html         # Invoice list
│   ├── invoice_create.html   # Invoice builder (dynamic JS)
│   ├── invoice_view.html     # GST-compliant invoice print view
│   ├── products.html
│   ├── product_form.html
│   ├── customers.html
│   ├── customer_form.html
│   └── settings.html
│
├── streamlit_app/
│   └── dashboard.py          # Plotly-powered Streamlit BI dashboard
│
└── analytics/
    └── key_queries.sql       # 10 portfolio-ready SQL queries
```

---

## 🚀 Quick Start (Local)

```bash
# 1. Clone / navigate to project
cd ebilling

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run Flask app
python app.py
# → Open http://localhost:5000

# 5. Run Streamlit dashboard (separate terminal)
streamlit run streamlit_app/dashboard.py
# → Open http://localhost:8501
```

The app **auto-seeds 30 invoices, 10 customers, 12 products** on first launch.

---

## 🗄️ Database Schema

```
customers      → name, email, phone, city, state, gstin
products       → name, category, unit_price, tax_rate, hsn_sac_code
invoices       → invoice_number, customer_id, supply_type, subtotal, cgst, sgst, igst, total
invoice_items  → invoice_id, product_id, qty, unit_price, tax_rate, line_total
business_config→ key-value settings (business name, GSTIN, bank, etc.)
```

**Analytics Views (SQL):**
- `vw_monthly_revenue`      — aggregated monthly KPIs
- `vw_product_performance`  — sales per product
- `vw_customer_insights`    — LTV, segment, recency
- `vw_invoice_detail`       — flattened for Power BI / CSV export

---

## 📊 Data Analyst Skills Demonstrated

| Skill | Where |
|---|---|
| SQL aggregations + CTEs | `analytics.py`, `key_queries.sql` |
| Window functions (LAG, RANK, OVER) | `key_queries.sql` Q2, Q3, Q10 |
| Time-series trend analysis | Monthly/weekly revenue queries |
| Customer segmentation (RFM) | `get_customer_segments()` |
| KPI calculation (ARPU, MoM, LTV) | `get_kpi_summary()` |
| GST tax logic (CGST/SGST/IGST) | Invoice model + GST summary |
| Data export (CSV) | 4 export endpoints |
| BI visualization | Streamlit + Plotly charts |
| Relational schema design | `schema.sql` |

---

## 🔌 Power BI Setup

1. **Export CSVs** from `/export/invoices`, `/export/products`, `/export/customers`
2. In Power BI Desktop → **Get Data → Text/CSV**
3. Load all 3 files; create relationships:
   - `invoice_detail[customer_email]` → `customer_insights[email]`
   - `invoice_detail[product_name]` → `product_performance[product_name]`
4. **Build visuals:**
   - Line chart: `invoice_date` vs `net_revenue` (trend)
   - Bar chart: `product_name` vs `total_revenue` (top products)
   - Donut: `customer_segment` (segmentation)
   - Card: Total Revenue, ARPU, Repeat Rate
   - Table: Outstanding receivables (`status = sent`)
5. Add slicers for: Date range, Status, City, Category

**OR** connect directly to SQLite:
- Power BI → Get Data → **ODBC** → SQLite ODBC driver → `ebilling.db`
- All views (`vw_*`) appear as ready-to-use tables

---

## ☁️ Deployment

### Render.com (Free)
```bash
# 1. Push to GitHub
git init && git add . && git commit -m "init"
git remote add origin https://github.com/yourusername/ebilling.git
git push -u origin main

# 2. On Render: New Web Service → connect repo
# Build Command: pip install -r requirements.txt
# Start Command: gunicorn app:app
# Set env var: DB_PATH=/var/data/ebilling.db  (use Render disk)
```

### Railway.app
```bash
railway login
railway init
railway up
# Auto-detects Flask + Procfile
```

### Local Production
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

---

## 🧾 GST Compliance Notes

- **Intra-state supply**: CGST + SGST (each = tax_rate / 2)
- **Inter-state supply**: IGST (= full tax_rate)
- Supply type auto-detected or manually set per invoice
- All amounts: taxable value, CGST, SGST, IGST stored separately
- Export `/export/gst` → ready for GSTR-1 filing prep

---
