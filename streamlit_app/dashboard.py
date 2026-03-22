"""
streamlit_app/dashboard.py
===========================
Streamlit Analytics Dashboard for E-Billing System
Run: streamlit run streamlit_app/dashboard.py

Requirements: streamlit pandas plotly sqlite3
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from database import get_db, init_db, seed_demo_data, get_config
import analytics as da

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="BillFlow Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# Init DB
# ─────────────────────────────────────────────
@st.cache_resource
def init():
    init_db()
    seed_demo_data()
    return get_config()

cfg = init()

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background: #0d0f14; color: #e2e8f8; }
    .metric-card {
        background: #151821; border: 1px solid #2a2f42;
        border-radius: 6px; padding: 18px 20px; margin-bottom: 8px;
    }
    .metric-label { font-size: 11px; color: #7a84a3; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 26px; font-weight: 700; color: #e2e8f8; font-family: monospace; }
    .metric-delta { font-size: 12px; }
    h1,h2,h3 { color: #e2e8f8; }
    div[data-testid="metric-container"] {
        background: #151821; border: 1px solid #2a2f42;
        border-radius: 6px; padding: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"## ⚡ {cfg.get('business_name','BillFlow')}")
    st.markdown("**Analytics Dashboard**")
    st.divider()

    page = st.radio("Navigate", [
        "📊 Overview",
        "📈 Revenue Trends",
        "🛍️ Product Analytics",
        "👥 Customer Analytics",
        "🧾 GST Summary",
        "📋 Raw Data"
    ])

    st.divider()
    months = st.slider("Time Range (months)", 3, 12, 6)
    st.caption(f"Currency: {cfg.get('currency_symbol','₹')}")


SYM = cfg.get('currency_symbol', '₹')

# ─────────────────────────────────────────────
# Plotly theme
# ─────────────────────────────────────────────
PLOTLY_THEME = dict(
    template="plotly_dark",
    paper_bgcolor="#151821",
    plot_bgcolor="#151821",
    font=dict(family="IBM Plex Mono, monospace", color="#e2e8f8")
)


# ═════════════════════════════════════════════
# PAGE: OVERVIEW
# ═════════════════════════════════════════════
if page == "📊 Overview":
    st.title("📊 Business Overview")

    kpi = da.get_kpi_summary()
    if not kpi:
        st.warning("No data found. Please seed demo data.")
        st.stop()

    # KPI Row
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Revenue",    f"{SYM}{kpi.get('total_revenue',0):,.0f}")
    c2.metric("This Month",       f"{SYM}{kpi.get('this_month_revenue',0):,.0f}",
              delta=f"{kpi.get('mom_growth_pct') or 0:+.1f}% MoM")
    c3.metric("Avg Invoice",      f"{SYM}{kpi.get('avg_invoice_value',0):,.0f}")
    c4.metric("ARPU",             f"{SYM}{kpi.get('arpu',0):,.0f}")
    c5.metric("Customers",        f"{kpi.get('unique_customers',0)}")
    c6.metric("Repeat Rate",      f"{kpi.get('repeat_rate_pct',0)}%",
              delta=f"{kpi.get('repeat_count',0)} returning")

    st.divider()

    # Revenue trend + Status breakdown
    col1, col2 = st.columns([2, 1])

    with col1:
        trend = da.get_monthly_revenue_trend(months)
        if not trend.empty:
            fig = px.bar(trend, x="label", y="net_revenue",
                         title="Monthly Revenue",
                         labels={"label":"Month","net_revenue":f"Revenue ({SYM})"},
                         color="net_revenue",
                         color_continuous_scale=["#1c2a4a","#4f8ef7"],
                         **PLOTLY_THEME)
            fig.update_layout(showlegend=False, coloraxis_showscale=False, title_font_size=14)
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        with get_db() as conn:
            status_df = pd.read_sql_query(
                "SELECT status, COUNT(*) as count, SUM(total_amount) as total FROM invoices GROUP BY status",
                conn
            )
        if not status_df.empty:
            fig2 = px.pie(status_df, values="count", names="status",
                          title="Invoice Status",
                          color_discrete_sequence=["#34d97b","#4f8ef7","#7c5af0","#f05c5c","#7a84a3"],
                          **PLOTLY_THEME)
            fig2.update_layout(title_font_size=14)
            st.plotly_chart(fig2, use_container_width=True)

    # Top products bar
    top_p = da.get_top_products(8)
    if not top_p.empty:
        fig3 = px.bar(top_p.sort_values("total_revenue"),
                      x="total_revenue", y="product",
                      orientation="h",
                      title="Top Products by Revenue",
                      labels={"total_revenue":f"Revenue ({SYM})","product":""},
                      color="total_revenue",
                      color_continuous_scale=["#2a1f40","#7c5af0"],
                      **PLOTLY_THEME)
        fig3.update_layout(showlegend=False, coloraxis_showscale=False, title_font_size=14)
        st.plotly_chart(fig3, use_container_width=True)


# ═════════════════════════════════════════════
# PAGE: REVENUE TRENDS
# ═════════════════════════════════════════════
elif page == "📈 Revenue Trends":
    st.title("📈 Revenue Trends")

    trend = da.get_monthly_revenue_trend(months)

    if trend.empty:
        st.info("No data available yet.")
        st.stop()

    # Line chart: Revenue + Tax
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(name="Net Revenue", x=trend["label"], y=trend["net_revenue"],
                         marker_color="#4f8ef7", opacity=0.85), secondary_y=False)
    fig.add_trace(go.Scatter(name="Avg Order Value", x=trend["label"], y=trend["avg_order_value"],
                             mode="lines+markers", line=dict(color="#34d97b", width=2),
                             marker=dict(size=6)), secondary_y=True)
    fig.update_layout(title="Revenue vs Avg Order Value", **PLOTLY_THEME,
                      title_font_size=14, legend=dict(orientation="h", y=1.15))
    fig.update_yaxes(title_text=f"Revenue ({SYM})", secondary_y=False)
    fig.update_yaxes(title_text=f"Avg Order ({SYM})", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    # MoM Growth
    if "mom_growth" in trend.columns:
        fig2 = px.bar(trend.dropna(subset=["mom_growth"]),
                      x="label", y="mom_growth",
                      title="Month-over-Month Revenue Growth (%)",
                      labels={"label":"Month","mom_growth":"MoM Growth %"},
                      color="mom_growth",
                      color_continuous_scale=["#f05c5c","#34d97b"],
                      **PLOTLY_THEME)
        fig2.add_hline(y=0, line_dash="dash", line_color="#7a84a3")
        fig2.update_layout(coloraxis_showscale=False, title_font_size=14)
        st.plotly_chart(fig2, use_container_width=True)

    # Data table
    st.subheader("Monthly Revenue Table")
    st.dataframe(trend.rename(columns={
        "label":"Month","invoices":"# Invoices",
        "gross_revenue":f"Gross ({SYM})","total_tax":f"Tax ({SYM})",
        "net_revenue":f"Net Revenue ({SYM})","avg_order_value":f"AOV ({SYM})",
        "mom_growth":"MoM %"
    }).set_index("Month"), use_container_width=True)

    csv = trend.to_csv(index=False).encode()
    st.download_button("↓ Download Revenue CSV", csv, "monthly_revenue.csv", "text/csv")


# ═════════════════════════════════════════════
# PAGE: PRODUCTS
# ═════════════════════════════════════════════
elif page == "🛍️ Product Analytics":
    st.title("🛍️ Product Performance")

    top_p = da.get_top_products(20)
    cats  = da.get_category_breakdown()

    if top_p.empty:
        st.info("No product data yet.")
        st.stop()

    col1, col2 = st.columns([3,2])
    with col1:
        fig = px.bar(top_p.head(10).sort_values("total_revenue"),
                     x="total_revenue", y="product", orientation="h",
                     title="Top 10 Products by Revenue",
                     labels={"total_revenue":f"Revenue ({SYM})","product":""},
                     color="invoice_count", color_continuous_scale=["#1c2a4a","#4f8ef7"],
                     **PLOTLY_THEME)
        fig.update_layout(title_font_size=14, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not cats.empty:
            fig2 = px.pie(cats, values="revenue", names="category",
                          title="Revenue by Category",
                          color_discrete_sequence=["#4f8ef7","#7c5af0","#34d97b","#f5c842","#f0904a"],
                          **PLOTLY_THEME)
            fig2.update_layout(title_font_size=14)
            st.plotly_chart(fig2, use_container_width=True)

    # Scatter: Price vs Volume
    fig3 = px.scatter(top_p, x="avg_price", y="total_qty",
                      size="total_revenue", color="category",
                      hover_name="product",
                      title="Price vs Volume (bubble = revenue)",
                      labels={"avg_price":f"Avg Price ({SYM})","total_qty":"Qty Sold"},
                      **PLOTLY_THEME)
    fig3.update_layout(title_font_size=14)
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Full Product Table")
    st.dataframe(top_p.set_index("product"), use_container_width=True)
    st.download_button("↓ Download", top_p.to_csv(index=False).encode(), "products.csv")


# ═════════════════════════════════════════════
# PAGE: CUSTOMERS
# ═════════════════════════════════════════════
elif page == "👥 Customer Analytics":
    st.title("👥 Customer Analytics")

    segs    = da.get_customer_segments()
    seg_sum = da.get_customer_segment_summary()
    top_c   = da.get_top_customers(20)

    if segs.empty:
        st.info("No customer data yet.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(seg_sum.sort_values("total_revenue", ascending=False),
                     x="segment", y="total_revenue",
                     color="segment", title="Revenue by Segment",
                     labels={"segment":"Segment","total_revenue":f"Revenue ({SYM})"},
                     color_discrete_map={"VIP":"#7c5af0","Loyal":"#4f8ef7",
                                         "Returning":"#34d97b","New":"#7a84a3","At-Risk":"#f05c5c"},
                     **PLOTLY_THEME)
        fig.update_layout(showlegend=False, title_font_size=14)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.pie(seg_sum, values="customers", names="segment",
                      title="Customer Distribution",
                      color="segment",
                      color_discrete_map={"VIP":"#7c5af0","Loyal":"#4f8ef7",
                                          "Returning":"#34d97b","New":"#7a84a3","At-Risk":"#f05c5c"},
                      **PLOTLY_THEME)
        fig2.update_layout(title_font_size=14)
        st.plotly_chart(fig2, use_container_width=True)

    # Recency vs Monetary scatter
    if "recency_days" in segs.columns:
        fig3 = px.scatter(segs, x="recency_days", y="monetary",
                          color="segment", size="frequency",
                          hover_name="name",
                          title="RFM Map: Recency vs Monetary (bubble = frequency)",
                          labels={"recency_days":"Days Since Last Purchase",
                                  "monetary":f"Total Spend ({SYM})"},
                          color_discrete_map={"VIP":"#7c5af0","Loyal":"#4f8ef7",
                                              "Returning":"#34d97b","New":"#7a84a3","At-Risk":"#f05c5c"},
                          **PLOTLY_THEME)
        fig3.update_layout(title_font_size=14)
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Top Customers by LTV")
    st.dataframe(top_c.set_index("name"), use_container_width=True)
    st.download_button("↓ Download", top_c.to_csv(index=False).encode(), "customers.csv")


# ═════════════════════════════════════════════
# PAGE: GST
# ═════════════════════════════════════════════
elif page == "🧾 GST Summary":
    st.title("🧾 GST Report")

    gst = da.get_gst_summary()
    if gst.empty:
        st.info("No GST data yet.")
        st.stop()

    # Totals
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Taxable", f"{SYM}{gst['taxable_value'].sum():,.0f}")
    c2.metric("Total CGST",    f"{SYM}{gst['cgst'].sum():,.0f}")
    c3.metric("Total SGST",    f"{SYM}{gst['sgst'].sum():,.0f}")
    c4.metric("Total IGST",    f"{SYM}{gst['igst'].sum():,.0f}")

    st.divider()

    fig = px.bar(gst, x="period", y=["cgst","sgst","igst"],
                 title="GST Breakdown by Month",
                 labels={"value":f"Amount ({SYM})","period":"Period","variable":"Tax Type"},
                 barmode="stack",
                 color_discrete_map={"cgst":"#4f8ef7","sgst":"#7c5af0","igst":"#34d97b"},
                 **PLOTLY_THEME)
    fig.update_layout(title_font_size=14, legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("GSTR Data Table")
    st.dataframe(gst, use_container_width=True)
    st.download_button("↓ GST Report CSV", gst.to_csv(index=False).encode(), "gst_report.csv")


# ═════════════════════════════════════════════
# PAGE: RAW DATA
# ═════════════════════════════════════════════
elif page == "📋 Raw Data":
    st.title("📋 Raw Data Explorer")

    tab1, tab2, tab3 = st.tabs(["Invoices", "Products", "Customers"])

    with tab1:
        df = da.export_invoice_detail()
        st.write(f"**{len(df)} records**")
        st.dataframe(df, use_container_width=True)
        st.download_button("↓ Download", df.to_csv(index=False).encode(), "invoice_detail.csv")

    with tab2:
        df = da.export_product_performance()
        st.dataframe(df, use_container_width=True)
        st.download_button("↓ Download", df.to_csv(index=False).encode(), "product_performance.csv")

    with tab3:
        df = da.export_customer_insights()
        st.dataframe(df, use_container_width=True)
        st.download_button("↓ Download", df.to_csv(index=False).encode(), "customer_insights.csv")
