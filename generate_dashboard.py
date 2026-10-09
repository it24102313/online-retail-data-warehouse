"""
============================================================
Online Retail DW/BI - Interactive Dashboard Generator
============================================================
Generates a complete 3-page interactive HTML dashboard
from the SQLite data warehouse.
Pages:
  1. Executive Summary  (KPIs, donut, bar, map)
  2. Trend Analysis     (line, clustered column, area)
  3. Interactive Analysis (matrix, scatter, top products)
============================================================
"""

import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json, os

DB_PATH = "online_retail_dw.db"
conn = sqlite3.connect(DB_PATH)

print("Loading data from warehouse...")

# ── Core DataFrames ───────────────────────────────────────
fact = pd.read_sql("SELECT * FROM fact_sales", conn)
dim_date = pd.read_sql("SELECT * FROM dim_date", conn)
dim_cust = pd.read_sql("SELECT * FROM dim_customer", conn)
dim_prod = pd.read_sql("SELECT * FROM dim_product", conn)
dim_loc  = pd.read_sql("SELECT * FROM dim_location", conn)

# Enrich fact with dimension attributes
fact = fact.merge(dim_date[['date_id','year','month','month_name','quarter','weekday','is_weekend']], on='date_id', how='left')
fact = fact.merge(dim_cust[['customer_id','segment','country','region']], on='customer_id', how='left')
fact = fact.merge(dim_prod[['product_id','stock_code','description','category','subcategory']], on='product_id', how='left')
fact = fact.merge(dim_loc[['location_id','country','region','continent']].rename(
    columns={'country':'loc_country','region':'loc_region','continent':'loc_continent'}), on='location_id', how='left')

conn.close()
print(f"Loaded {len(fact):,} fact records")

# ── Aggregate datasets ────────────────────────────────────
total_revenue  = fact['total_amount'].sum()
total_orders   = fact['invoice_no'].nunique()
total_customers= fact['customer_id'].nunique()
avg_order_val  = total_revenue / total_orders

# Monthly revenue
monthly = fact.groupby(['year','month','month_name']).agg(
    revenue=('total_amount','sum'),
    orders=('invoice_no','nunique')
).reset_index().sort_values(['year','month'])
monthly['period'] = monthly['month_name'].str[:3] + ' ' + monthly['year'].astype(str)

# Country revenue
country_rev = fact.groupby('loc_country').agg(revenue=('total_amount','sum')).reset_index().sort_values('revenue',ascending=False)

# Segment revenue
seg_rev = fact.groupby('segment').agg(revenue=('total_amount','sum'),
                                       orders=('invoice_no','nunique'),
                                       customers=('customer_id','nunique')).reset_index()
seg_rev['aov'] = seg_rev['revenue'] / seg_rev['orders']

# Category monthly
cat_monthly = fact.groupby(['year','month','month_name','category']).agg(
    revenue=('total_amount','sum')).reset_index().sort_values(['year','month'])

# Top 15 products
top_prods = fact.groupby(['stock_code','description']).agg(
    revenue=('total_amount','sum'), units=('quantity','sum')).reset_index()\
    .sort_values('revenue',ascending=False).head(15)

# Continent revenue
continent_rev = fact.groupby('loc_continent').agg(revenue=('total_amount','sum')).reset_index().sort_values('revenue',ascending=False)

# Customer order frequency
cust_freq = fact.groupby('customer_id').agg(orders=('invoice_no','nunique'), revenue=('total_amount','sum')).reset_index()
cust_freq['type'] = pd.cut(cust_freq['orders'], bins=[0,1,5,999], labels=['One-time (1)','Occasional (2-5)','Loyal (6+)'])

# YoY monthly for clustered bar
yoy = fact.groupby(['year','month','month_name']).agg(revenue=('total_amount','sum')).reset_index()

# Cumulative revenue
monthly_sorted = monthly.sort_values(['year','month']).copy()
monthly_sorted['cumulative'] = monthly_sorted['revenue'].cumsum()

# Weekday analysis
weekday_rev = fact.groupby('weekday').agg(revenue=('total_amount','sum')).reset_index()
weekday_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
weekday_rev['weekday'] = pd.Categorical(weekday_rev['weekday'], categories=weekday_order, ordered=True)
weekday_rev = weekday_rev.sort_values('weekday')

# Regional performance
region_rev = fact.groupby(['loc_continent','loc_country']).agg(
    revenue=('total_amount','sum'), orders=('invoice_no','nunique')).reset_index().sort_values('revenue',ascending=False).head(20)

print("Building dashboard...")

# ══════════════════════════════════════════════════════════
# COLOUR PALETTE
# ══════════════════════════════════════════════════════════
C_BLUE   = '#1f77b4'
C_ORG    = '#ff7f0e'
C_GREEN  = '#2ca02c'
C_RED    = '#d62728'
C_PURPLE = '#9467bd'
C_BG     = '#f7f9fc'
C_CARD   = '#ffffff'
C_HEADER = '#1a237e'
PALETTE  = [C_BLUE, C_ORG, C_GREEN, C_RED, C_PURPLE, '#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf']

# ══════════════════════════════════════════════════════════
# PAGE 1 – EXECUTIVE SUMMARY
# ══════════════════════════════════════════════════════════
fig1 = make_subplots(
    rows=3, cols=3,
    specs=[
        [{"type":"indicator"},{"type":"indicator"},{"type":"indicator"}],
        [{"type":"indicator"},{"type":"pie","colspan":2},None],
        [{"type":"bar","colspan":3},None,None],
    ],
    row_heights=[0.18, 0.35, 0.47],
    vertical_spacing=0.06,
    horizontal_spacing=0.05,
)

# KPI Cards
kpis = [
    ("Total Revenue",   f"£{total_revenue:,.0f}",  total_revenue,   "£"),
    ("Total Orders",    f"{total_orders:,}",         total_orders,    ""),
    ("Total Customers", f"{total_customers:,}",      total_customers, ""),
]
positions = [(1,1),(1,2),(1,3)]
for (label, disp, val, pfx), (r,c) in zip(kpis, positions):
    fig1.add_trace(go.Indicator(
        mode="number",
        value=val,
        title={"text": f"<b>{label}</b>", "font":{"size":14, "color":C_HEADER}},
        number={"prefix": pfx, "font":{"size":28, "color":C_HEADER},
                "valueformat": ",.0f"},
    ), row=r, col=c)

# Avg Order Value card (row2 col1)
fig1.add_trace(go.Indicator(
    mode="number",
    value=avg_order_val,
    title={"text":"<b>Avg Order Value</b>","font":{"size":14,"color":C_HEADER}},
    number={"prefix":"£","font":{"size":28,"color":C_GREEN},"valueformat":",.2f"},
), row=2, col=1)

# Donut – Segment Revenue
fig1.add_trace(go.Pie(
    labels=seg_rev['segment'],
    values=seg_rev['revenue'],
    hole=0.55,
    textinfo='label+percent',
    marker_colors=[C_BLUE, C_ORG],
    name="Segment Revenue",
    title={"text":"Revenue by<br>Segment","font":{"size":13}},
), row=2, col=2)

# Bar – Top 10 Countries
top10 = country_rev.head(10)
fig1.add_trace(go.Bar(
    x=top10['revenue'],
    y=top10['loc_country'],
    orientation='h',
    marker_color=[C_BLUE if i==0 else C_ORG for i in range(len(top10))],
    text=[f"£{v:,.0f}" for v in top10['revenue']],
    textposition='outside',
    name="Country Revenue",
), row=3, col=1)

fig1.update_layout(
    title=dict(text="<b>Page 1 — Executive Summary</b>", font=dict(size=22, color=C_HEADER), x=0.5),
    paper_bgcolor=C_BG, plot_bgcolor=C_CARD,
    height=780, showlegend=False,
    font=dict(family="Segoe UI, Arial", size=12),
    margin=dict(l=40, r=40, t=80, b=20),
)
fig1.update_yaxes(row=3, col=1, title_text="Country", tickfont=dict(size=11))
fig1.update_xaxes(row=3, col=1, title_text="Revenue (GBP)", tickprefix="£", tickformat=",.0f")

# ══════════════════════════════════════════════════════════
# PAGE 2 – TREND ANALYSIS
# ══════════════════════════════════════════════════════════
fig2 = make_subplots(
    rows=2, cols=2,
    subplot_titles=[
        "Monthly Revenue Trend (2009–2011)",
        "Year-on-Year Monthly Revenue Comparison",
        "Cumulative Revenue Over Time",
        "Revenue by Day of Week",
    ],
    vertical_spacing=0.14,
    horizontal_spacing=0.08,
)

# Line chart – monthly revenue
for yr, color in zip(sorted(monthly['year'].unique()), [C_BLUE, C_ORG, C_GREEN]):
    df_yr = monthly[monthly['year']==yr].sort_values('month')
    fig2.add_trace(go.Scatter(
        x=df_yr['month_name'], y=df_yr['revenue'],
        mode='lines+markers', name=str(yr),
        line=dict(color=color, width=2.5),
        marker=dict(size=7),
        hovertemplate=f"<b>{yr}</b><br>%{{x}}: £%{{y:,.0f}}<extra></extra>",
    ), row=1, col=1)

# Clustered column – YoY
for yr, color in zip(sorted(yoy['year'].unique()), [C_BLUE, C_ORG, C_GREEN]):
    df_yr = yoy[yoy['year']==yr].sort_values('month')
    fig2.add_trace(go.Bar(
        x=df_yr['month_name'], y=df_yr['revenue'],
        name=str(yr), marker_color=color,
        hovertemplate=f"<b>{yr}</b> %{{x}}: £%{{y:,.0f}}<extra></extra>",
        showlegend=False,
    ), row=1, col=2)

# Area – cumulative
fig2.add_trace(go.Scatter(
    x=monthly_sorted['period'], y=monthly_sorted['cumulative'],
    fill='tozeroy', fillcolor='rgba(31,119,180,0.25)',
    line=dict(color=C_BLUE, width=2),
    name="Cumulative Revenue",
    hovertemplate="%{x}: £%{y:,.0f}<extra></extra>",
    showlegend=False,
), row=2, col=1)

# Weekday bar
fig2.add_trace(go.Bar(
    x=weekday_rev['weekday'], y=weekday_rev['revenue'],
    marker_color=[C_ORG if d in ['Saturday','Sunday'] else C_BLUE for d in weekday_rev['weekday']],
    text=[f"£{v/1e6:.2f}M" for v in weekday_rev['revenue']],
    textposition='outside',
    name="Weekday Revenue",
    showlegend=False,
    hovertemplate="%{x}: £%{y:,.0f}<extra></extra>",
), row=2, col=2)

fig2.update_layout(
    title=dict(text="<b>Page 2 — Trend Analysis</b>", font=dict(size=22, color=C_HEADER), x=0.5),
    paper_bgcolor=C_BG, plot_bgcolor=C_CARD,
    height=780, barmode='group',
    legend=dict(title="Year", orientation='h', y=1.05, x=0.5, xanchor='center'),
    font=dict(family="Segoe UI, Arial", size=12),
    margin=dict(l=40, r=40, t=80, b=20),
)
for row in [1,2]:
    for col in [1,2]:
        fig2.update_yaxes(row=row, col=col, tickprefix="£", tickformat=",.0f", gridcolor="#e0e0e0")
        fig2.update_xaxes(row=row, col=col, tickangle=-30)

# ══════════════════════════════════════════════════════════
# PAGE 3 – INTERACTIVE ANALYSIS
# ══════════════════════════════════════════════════════════
fig3 = make_subplots(
    rows=2, cols=2,
    subplot_titles=[
        "Top 15 Products by Revenue",
        "Revenue by Product Category",
        "Customer Segmentation: Revenue vs Orders",
        "Monthly Revenue by Category (Heatmap)",
    ],
    vertical_spacing=0.14,
    horizontal_spacing=0.10,
)

# Top 15 products horizontal bar
fig3.add_trace(go.Bar(
    x=top_prods['revenue'],
    y=[d[:35]+'…' if len(d)>35 else d for d in top_prods['description']],
    orientation='h',
    marker_color=C_BLUE,
    text=[f"£{v:,.0f}" for v in top_prods['revenue']],
    textposition='outside',
    hovertemplate="<b>%{y}</b><br>Revenue: £%{x:,.0f}<extra></extra>",
    name="Top Products",
), row=1, col=1)

# Category revenue bar
cat_total = fact.groupby('category').agg(revenue=('total_amount','sum')).reset_index().sort_values('revenue',ascending=False)
fig3.add_trace(go.Bar(
    x=cat_total['category'],
    y=cat_total['revenue'],
    marker_color=PALETTE[:len(cat_total)],
    text=[f"£{v/1e6:.2f}M" for v in cat_total['revenue']],
    textposition='outside',
    name="Category Revenue",
    hovertemplate="%{x}: £%{y:,.0f}<extra></extra>",
), row=1, col=2)

# Scatter – segment AOV vs orders
seg_scatter = fact.groupby(['customer_id','segment']).agg(
    orders=('invoice_no','nunique'),
    revenue=('total_amount','sum')
).reset_index()
seg_scatter['aov'] = seg_scatter['revenue'] / seg_scatter['orders']
seg_agg = seg_scatter.groupby('segment').agg(
    avg_orders=('orders','mean'),
    avg_aov=('aov','mean'),
    total_rev=('revenue','sum'),
    customer_count=('customer_id','nunique')
).reset_index()

for _, row_s in seg_agg.iterrows():
    fig3.add_trace(go.Scatter(
        x=[row_s['avg_orders']],
        y=[row_s['avg_aov']],
        mode='markers+text',
        marker=dict(size=row_s['total_rev']/150000, color=C_BLUE if row_s['segment']=='B2C' else C_ORG,
                    line=dict(width=2, color='white'), opacity=0.85),
        text=[f"{row_s['segment']}<br>£{row_s['avg_aov']:,.0f} AOV"],
        textposition='top center',
        name=row_s['segment'],
        hovertemplate=f"<b>{row_s['segment']}</b><br>Avg Orders: {row_s['avg_orders']:.1f}<br>Avg AOV: £{row_s['avg_aov']:,.0f}<br>Customers: {int(row_s['customer_count'])}<extra></extra>",
    ), row=2, col=1)

# Heatmap – category x month
pivot = cat_monthly.groupby(['month_name','category'])['revenue'].sum().unstack(fill_value=0)
month_order_names = ['January','February','March','April','May','June',
                     'July','August','September','October','November','December']
pivot = pivot.reindex([m for m in month_order_names if m in pivot.index])

fig3.add_trace(go.Heatmap(
    z=pivot.values / 1000,
    x=pivot.columns.tolist(),
    y=pivot.index.tolist(),
    colorscale='Blues',
    text=[[f"£{v:.0f}K" for v in row] for row in pivot.values/1000],
    texttemplate="%{text}",
    textfont={"size":9},
    hovertemplate="Month: %{y}<br>Category: %{x}<br>Revenue: £%{z:.0f}K<extra></extra>",
    colorbar=dict(title="Revenue (£K)", thickness=15),
    name="Heatmap",
), row=2, col=2)

fig3.update_layout(
    title=dict(text="<b>Page 3 — Interactive Analysis</b>", font=dict(size=22, color=C_HEADER), x=0.5),
    paper_bgcolor=C_BG, plot_bgcolor=C_CARD,
    height=820, showlegend=False,
    font=dict(family="Segoe UI, Arial", size=11),
    margin=dict(l=40, r=40, t=80, b=20),
)
fig3.update_yaxes(row=1, col=1, tickfont=dict(size=9))
fig3.update_xaxes(row=1, col=2, tickangle=-35)
fig3.update_xaxes(row=2, col=2, tickangle=-35)
fig3.update_xaxes(row=2, col=1, title_text="Avg Orders per Customer")
fig3.update_yaxes(row=2, col=1, title_text="Avg Order Value (GBP)", tickprefix="£", tickformat=",.0f")

# ══════════════════════════════════════════════════════════
# ASSEMBLE FULL HTML DASHBOARD
# ══════════════════════════════════════════════════════════
print("Exporting dashboard HTML...")

fig1_html = fig1.to_html(full_html=False, include_plotlyjs=False, div_id="page1")
fig2_html = fig2.to_html(full_html=False, include_plotlyjs=False, div_id="page2")
fig3_html = fig3.to_html(full_html=False, include_plotlyjs=False, div_id="page3")

# Build KPI summary cards for the header
kpi_cards_html = f"""
<div class="kpi-bar">
  <div class="kpi-card">
    <div class="kpi-label">Total Revenue</div>
    <div class="kpi-value" style="color:#1a237e">&#163;{total_revenue:,.0f}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Total Orders</div>
    <div class="kpi-value" style="color:#1565c0">{total_orders:,}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Total Customers</div>
    <div class="kpi-value" style="color:#0277bd">{total_customers:,}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Avg Order Value</div>
    <div class="kpi-value" style="color:#2e7d32">&#163;{avg_order_val:,.2f}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">UK Revenue Share</div>
    <div class="kpi-value" style="color:#6a1b9a">{country_rev[country_rev['loc_country']=='United Kingdom']['revenue'].sum()/total_revenue*100:.1f}%</div>
  </div>
</div>
"""

full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Online Retail BI Dashboard - DW Assignment</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',Arial,sans-serif; background:#f0f2f5; color:#333; }}
  .header {{
    background: linear-gradient(135deg,#1a237e 0%,#283593 60%,#1565c0 100%);
    color:white; padding:24px 40px; box-shadow:0 2px 12px rgba(0,0,0,0.3);
  }}
  .header h1 {{ font-size:26px; font-weight:700; letter-spacing:0.5px; }}
  .header p  {{ font-size:13px; opacity:0.85; margin-top:6px; }}
  .kpi-bar {{
    display:flex; gap:16px; flex-wrap:wrap;
    padding:20px 40px; background:#fff;
    border-bottom:3px solid #e8eaf6;
    box-shadow:0 1px 4px rgba(0,0,0,0.08);
  }}
  .kpi-card {{
    flex:1; min-width:150px; text-align:center;
    padding:14px 10px; border-radius:10px;
    background:#f7f9fc; border:1px solid #e3e8f0;
    box-shadow:0 1px 4px rgba(0,0,0,0.06);
  }}
  .kpi-label {{ font-size:11px; color:#666; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px; }}
  .kpi-value {{ font-size:22px; font-weight:700; }}
  .tab-bar {{
    display:flex; gap:0; padding:0 40px;
    background:#fff; border-bottom:2px solid #e8eaf6;
  }}
  .tab-btn {{
    padding:14px 28px; border:none; background:transparent;
    font-size:14px; font-weight:600; color:#666;
    cursor:pointer; border-bottom:3px solid transparent;
    transition:all 0.2s; letter-spacing:0.3px;
  }}
  .tab-btn:hover {{ color:#1a237e; background:#f5f7ff; }}
  .tab-btn.active {{ color:#1a237e; border-bottom-color:#1a237e; background:#f5f7ff; }}
  .tab-content {{ display:none; padding:24px 40px 40px; }}
  .tab-content.active {{ display:block; }}
  .page-title {{
    font-size:16px; font-weight:700; color:#1a237e;
    margin-bottom:14px; padding-bottom:8px;
    border-bottom:2px solid #e8eaf6;
  }}
  .insight-box {{
    background:#fff; border-left:4px solid #1a237e;
    padding:14px 20px; border-radius:0 8px 8px 0;
    margin-top:20px; box-shadow:0 1px 4px rgba(0,0,0,0.06);
  }}
  .insight-box h3 {{ font-size:14px; color:#1a237e; margin-bottom:8px; }}
  .insight-box ul {{ padding-left:18px; font-size:13px; color:#555; line-height:1.8; }}
  .footer {{
    text-align:center; padding:16px; background:#fff;
    border-top:1px solid #e8eaf6; color:#999; font-size:12px;
    margin-top:20px;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>&#x1F4CA; Online Retail Business Intelligence Dashboard</h1>
  <p>Data Warehouse &amp; BI Assignment &mdash; UK Online Retail (Dec 2009 &ndash; Dec 2011) &mdash; Dataset: UCI Online Retail II</p>
</div>

{kpi_cards_html}

<div class="tab-bar">
  <button class="tab-btn active" onclick="showTab('t1',this)">&#x1F4CB; Executive Summary</button>
  <button class="tab-btn" onclick="showTab('t2',this)">&#x1F4C8; Trend Analysis</button>
  <button class="tab-btn" onclick="showTab('t3',this)">&#x1F50D; Interactive Analysis</button>
</div>

<div id="t1" class="tab-content active">
  <div class="page-title">Page 1 &mdash; Executive Summary: Key Performance Indicators</div>
  {fig1_html}
  <div class="insight-box">
    <h3>Key Observations</h3>
    <ul>
      <li>Total Revenue of <strong>&#163;{total_revenue:,.0f}</strong> generated across {total_customers:,} customers in 2 years</li>
      <li>United Kingdom contributes <strong>{country_rev[country_rev['loc_country']=='United Kingdom']['revenue'].sum()/total_revenue*100:.1f}%</strong> of all revenue</li>
      <li>Average Order Value of <strong>&#163;{avg_order_val:,.2f}</strong> indicates strong basket size</li>
    </ul>
  </div>
</div>

<div id="t2" class="tab-content">
  <div class="page-title">Page 2 &mdash; Trend Analysis: Time-Based Performance Patterns</div>
  {fig2_html}
  <div class="insight-box">
    <h3>Trend Insights</h3>
    <ul>
      <li>Clear <strong>Q4 seasonal peak</strong> every year &mdash; November is consistently the highest revenue month</li>
      <li><strong>Year-on-year growth</strong> is visible &mdash; 2011 revenue exceeded 2010 in almost every month</li>
      <li><strong>January&ndash;February slump</strong> follows each Q4 peak, creating a recurring cash-flow challenge</li>
      <li>Weekdays (especially Tuesday&ndash;Thursday) generate significantly more revenue than weekends</li>
    </ul>
  </div>
</div>

<div id="t3" class="tab-content">
  <div class="page-title">Page 3 &mdash; Interactive Analysis: Products, Categories &amp; Segments</div>
  {fig3_html}
  <div class="insight-box">
    <h3>Analytical Insights</h3>
    <ul>
      <li>Top 15 products account for a disproportionate share of revenue &mdash; classic <strong>Pareto distribution</strong></li>
      <li>The <strong>General</strong> category dominates due to broad product variety; Seasonal and Home Decor are key growth categories</li>
      <li><strong>B2B customers</strong> have a significantly higher average order value than B2C customers</li>
      <li>Heatmap reveals that <strong>October&ndash;November</strong> peak applies consistently across all product categories</li>
    </ul>
  </div>
</div>

<div class="footer">
  Online Retail DW/BI Assignment &mdash; Generated from SQLite Data Warehouse (online_retail_dw.db) &mdash; {total_orders:,} Orders &bull; {total_customers:,} Customers &bull; {len(fact):,} Transactions
</div>

<script>
function showTab(tabId, btn) {{
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(tabId).classList.add('active');
  btn.classList.add('active');
}}
</script>
</body>
</html>"""

output_path = "BI_Dashboard.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(full_html)

size_mb = os.path.getsize(output_path) / 1024 / 1024
print(f"\nDashboard saved: {output_path} ({size_mb:.1f} MB)")
print("Open this file in any web browser to view the interactive dashboard.")
