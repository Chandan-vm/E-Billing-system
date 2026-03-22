"""
app.py — Flask Backend for E-Billing System
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
import io
from datetime import date, timedelta
from database import get_db, init_db, seed_demo_data, next_invoice_number, get_config, set_config
import analytics as da

app = Flask(__name__)
app.secret_key = "ebilling_secret_2024"
app.jinja_env.filters['enumerate'] = enumerate
app.jinja_env.globals['abs'] = abs

_initialized = False

@app.before_request
def startup():
    global _initialized
    if not _initialized:
        init_db()
        seed_demo_data()
        _initialized = True

@app.context_processor
def inject_config():
    return dict(cfg=get_config())

@app.route("/")
def index():
    kpi      = da.get_kpi_summary()
    trend    = da.get_monthly_revenue_trend(6)
    top_p    = da.get_top_products(5)
    segs     = da.get_customer_segment_summary()
    statuses = da.get_invoice_status_summary()
    return render_template("index.html", kpi=kpi,
        trend=trend.to_dict("records") if not trend.empty else [],
        top_products=top_p.to_dict("records") if not top_p.empty else [],
        segments=segs.to_dict("records") if not segs.empty else [],
        statuses=statuses)

@app.route("/settings", methods=["GET","POST"])
def settings():
    if request.method == "POST":
        for key, val in request.form.items():
            set_config(key, val)
        flash("Settings saved!", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html")

@app.route("/products")
def products():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM products WHERE is_active=1 ORDER BY category,name").fetchall()
    return render_template("products.html", products=[dict(r) for r in rows])

@app.route("/products/add", methods=["GET","POST"])
def add_product():
    if request.method == "POST":
        f = request.form
        with get_db() as conn:
            conn.execute("INSERT INTO products(name,description,category,unit_price,unit,hsn_sac_code,tax_rate,is_service) VALUES(?,?,?,?,?,?,?,?)",
                (f["name"],f.get("description",""),f.get("category","General"),float(f["unit_price"]),
                 f.get("unit","unit"),f.get("hsn_sac_code",""),float(f.get("tax_rate",18)),int(f.get("is_service",0))))
            conn.commit()
        flash(f"Product '{f['name']}' added!", "success")
        return redirect(url_for("products"))
    return render_template("product_form.html", product=None, action="Add")

@app.route("/products/edit/<int:pid>", methods=["GET","POST"])
def edit_product(pid):
    if request.method == "POST":
        f = request.form
        with get_db() as conn:
            conn.execute("UPDATE products SET name=?,description=?,category=?,unit_price=?,unit=?,hsn_sac_code=?,tax_rate=?,is_service=? WHERE id=?",
                (f["name"],f.get("description",""),f.get("category","General"),float(f["unit_price"]),
                 f.get("unit","unit"),f.get("hsn_sac_code",""),float(f.get("tax_rate",18)),int(f.get("is_service",0)),pid))
            conn.commit()
        flash("Product updated!", "success")
        return redirect(url_for("products"))
    with get_db() as conn:
        p = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    return render_template("product_form.html", product=dict(p), action="Edit")

@app.route("/products/delete/<int:pid>", methods=["POST"])
def delete_product(pid):
    with get_db() as conn:
        conn.execute("UPDATE products SET is_active=0 WHERE id=?", (pid,))
        conn.commit()
    flash("Product removed.", "info")
    return redirect(url_for("products"))

@app.route("/customers")
def customers():
    df = da.get_customer_segments()
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
    cust_list = [dict(r) for r in rows]
    seg_map = {}
    if not df.empty:
        for _, row in df.iterrows():
            seg_map[row["name"]] = row["segment"]
    for c in cust_list:
        c["segment"] = seg_map.get(c["name"], "New")
    return render_template("customers.html", customers=cust_list)

@app.route("/customers/add", methods=["GET","POST"])
def add_customer():
    if request.method == "POST":
        f = request.form
        with get_db() as conn:
            conn.execute("INSERT INTO customers(name,email,phone,address,city,state,pincode,gstin) VALUES(?,?,?,?,?,?,?,?)",
                (f["name"],f.get("email",""),f.get("phone",""),f.get("address",""),f.get("city",""),f.get("state",""),f.get("pincode",""),f.get("gstin","")))
            conn.commit()
        flash(f"Customer '{f['name']}' added!", "success")
        return redirect(url_for("customers"))
    return render_template("customer_form.html", customer=None)

@app.route("/customers/edit/<int:cid>", methods=["GET","POST"])
def edit_customer(cid):
    if request.method == "POST":
        f = request.form
        with get_db() as conn:
            conn.execute("UPDATE customers SET name=?,email=?,phone=?,address=?,city=?,state=?,pincode=?,gstin=? WHERE id=?",
                (f["name"],f.get("email",""),f.get("phone",""),f.get("address",""),f.get("city",""),f.get("state",""),f.get("pincode",""),f.get("gstin",""),cid))
            conn.commit()
        flash("Customer updated!", "success")
        return redirect(url_for("customers"))
    with get_db() as conn:
        c = conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
    return render_template("customer_form.html", customer=dict(c))

@app.route("/invoices")
def invoices():
    status_filter = request.args.get("status","all")
    sql = "SELECT inv.*, c.name AS customer_name FROM invoices inv JOIN customers c ON inv.customer_id=c.id"
    params = []
    if status_filter != "all":
        sql += " WHERE inv.status=?"; params.append(status_filter)
    sql += " ORDER BY inv.invoice_date DESC"
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return render_template("invoices.html", invoices=[dict(r) for r in rows], status_filter=status_filter)

@app.route("/invoices/create", methods=["GET","POST"])
def create_invoice():
    if request.method == "POST":
        f = request.form
        customer_id = int(f["customer_id"])
        invoice_date = f.get("invoice_date", date.today().isoformat())
        due_date     = f.get("due_date", (date.today()+timedelta(days=30)).isoformat())
        supply_type  = f.get("supply_type","intra")
        notes        = f.get("notes","")
        inv_num      = next_invoice_number()
        product_ids  = request.form.getlist("product_id[]")
        descriptions = request.form.getlist("description[]")
        quantities   = request.form.getlist("quantity[]")
        unit_prices  = request.form.getlist("unit_price[]")
        tax_rates_l  = request.form.getlist("tax_rate[]")
        subtotal = total_tax = cgst_sum = sgst_sum = igst_sum = 0.0
        items = []
        for i in range(len(descriptions)):
            if not descriptions[i]: continue
            qty=float(quantities[i]); price=float(unit_prices[i]); rate=float(tax_rates_l[i]) if tax_rates_l[i] else 18.0
            pid=int(product_ids[i]) if product_ids[i] else None
            lsub=round(qty*price,2); tax_a=round(lsub*rate/100,2)
            if supply_type=="intra": cgst=sgst=round(tax_a/2,2); igst=0.0
            else: cgst=sgst=0.0; igst=tax_a
            ltot=round(lsub+tax_a,2)
            subtotal+=lsub; total_tax+=tax_a; cgst_sum+=cgst; sgst_sum+=sgst; igst_sum+=igst
            items.append((pid,descriptions[i],qty,price,rate,lsub,cgst,sgst,igst,ltot))
        total_amount=round(subtotal+total_tax,2)
        status="sent" if f.get("action")=="send" else "draft"
        with get_db() as conn:
            conn.execute("INSERT INTO invoices(invoice_number,customer_id,invoice_date,due_date,status,supply_type,subtotal,cgst_amount,sgst_amount,igst_amount,total_tax,total_amount,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (inv_num,customer_id,invoice_date,due_date,status,supply_type,round(subtotal,2),round(cgst_sum,2),round(sgst_sum,2),round(igst_sum,2),round(total_tax,2),total_amount,notes))
            inv_id=conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            for it in items:
                conn.execute("INSERT INTO invoice_items(invoice_id,product_id,description,quantity,unit_price,tax_rate,line_subtotal,cgst,sgst,igst,line_total) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(inv_id,*it))
            conn.commit()
        flash(f"Invoice {inv_num} created!", "success")
        return redirect(url_for("view_invoice", inv_id=inv_id))
    with get_db() as conn:
        customers_list = conn.execute("SELECT id,name FROM customers ORDER BY name").fetchall()
        products_list  = conn.execute("SELECT id,name,unit_price,tax_rate,unit FROM products WHERE is_active=1 ORDER BY name").fetchall()
    return render_template("invoice_create.html",
        customers=[dict(c) for c in customers_list], products=[dict(p) for p in products_list],
        inv_num=next_invoice_number(), today=date.today().isoformat(), due=(date.today()+timedelta(days=30)).isoformat())

@app.route("/invoices/<int:inv_id>")
def view_invoice(inv_id):
    with get_db() as conn:
        inv = conn.execute("SELECT inv.*,c.name AS cname,c.email,c.phone,c.address,c.city,c.state,c.pincode,c.gstin AS cgstin FROM invoices inv JOIN customers c ON inv.customer_id=c.id WHERE inv.id=?",(inv_id,)).fetchone()
        items = conn.execute("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id",(inv_id,)).fetchall()
    return render_template("invoice_view.html", inv=dict(inv), items=[dict(i) for i in items])

@app.route("/invoices/<int:inv_id>/status/<string:new_status>", methods=["POST"])
def update_invoice_status(inv_id, new_status):
    if new_status in {"draft","sent","paid","overdue","cancelled"}:
        with get_db() as conn:
            conn.execute("UPDATE invoices SET status=? WHERE id=?",(new_status,inv_id)); conn.commit()
        flash(f"Invoice marked as {new_status}.", "success")
    return redirect(url_for("view_invoice", inv_id=inv_id))

@app.route("/analytics")
def analytics():
    kpi=da.get_kpi_summary(); trend=da.get_monthly_revenue_trend(6)
    top_p=da.get_top_products(8); segs=da.get_customer_segments()
    seg_sum=da.get_customer_segment_summary(); top_c=da.get_top_customers(8)
    gst=da.get_gst_summary(); overdue=da.get_outstanding_receivables()
    cat_bkdn=da.get_category_breakdown()
    return render_template("analytics.html", kpi=kpi,
        trend=trend.to_dict("records") if not trend.empty else [],
        top_products=top_p.to_dict("records") if not top_p.empty else [],
        segments=segs.to_dict("records") if not segs.empty else [],
        seg_summary=seg_sum.to_dict("records") if not seg_sum.empty else [],
        top_customers=top_c.to_dict("records") if not top_c.empty else [],
        gst_summary=gst.to_dict("records") if not gst.empty else [],
        overdue=overdue.to_dict("records") if not overdue.empty else [],
        categories=cat_bkdn.to_dict("records") if not cat_bkdn.empty else [])

@app.route("/api/product/<int:pid>")
def api_product(pid):
    with get_db() as conn:
        p = conn.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
    return jsonify(dict(p)) if p else ({},404)

@app.route("/api/analytics/kpi")
def api_kpi():
    return jsonify(da.get_kpi_summary())

def _csv_response(df, filename):
    buf=io.StringIO(); df.to_csv(buf,index=False)
    return send_file(io.BytesIO(buf.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name=filename)

@app.route("/export/invoices")
def export_invoices():  return _csv_response(da.export_invoice_detail(), "invoice_detail.csv")

@app.route("/export/products")
def export_products():  return _csv_response(da.export_product_performance(), "product_performance.csv")

@app.route("/export/customers")
def export_customers(): return _csv_response(da.export_customer_insights(), "customer_insights.csv")

@app.route("/export/gst")
def export_gst():       return _csv_response(da.get_gst_summary(), "gst_report.csv")

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
