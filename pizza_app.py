from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Pizza Store Analytics",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# PROFESSIONAL BLACK THEME
# ============================================================
st.markdown("""
<style>
    .stApp {
        background: #050505;
        color: #F5F5F5;
    }

    [data-testid="stHeader"] {
        background: #050505;
    }

    [data-testid="stSidebar"] {
        background: #0B0B0B;
        border-right: 1px solid #242424;
    }

    [data-testid="stSidebar"] * {
        color: #E8E8E8;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    .hero {
        background: linear-gradient(135deg, #111111, #080808);
        border: 1px solid #292929;
        border-radius: 18px;
        padding: 28px 32px;
        margin-bottom: 22px;
    }

    .hero-title {
        font-size: 34px;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.8px;
    }

    .hero-subtitle {
        color: #A5A5A5;
        font-size: 15px;
        margin-top: 7px;
    }

    .metric-card {
        background: #101010;
        border: 1px solid #292929;
        border-radius: 16px;
        padding: 20px;
        min-height: 125px;
    }

    .metric-label {
        color: #9B9B9B;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    .metric-value {
        color: #FFFFFF;
        font-size: 30px;
        font-weight: 800;
        margin-top: 8px;
    }

    .section-title {
        font-size: 21px;
        font-weight: 750;
        color: #FFFFFF;
        margin: 28px 0 12px 0;
    }

    .section-caption {
        color: #8F8F8F;
        font-size: 13px;
        margin-bottom: 10px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #292929;
        border-radius: 12px;
        overflow: hidden;
    }

    .stButton > button {
        background: #151515;
        color: white;
        border: 1px solid #333333;
        border-radius: 9px;
    }

    .stButton > button:hover {
        border-color: #666666;
        color: white;
    }

    hr {
        border-color: #242424;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# LOCAL DATA FILES (CLOUD-SAFE)
# ============================================================
DATA_DIR = Path(__file__).parent


@st.cache_data
def load_data():
    """Load the exported Pizza Store tables from CSV files.

    The original dashboard used MySQL. For Streamlit Community Cloud,
    the exported tables are bundled with the app so no localhost
    database connection is required.
    """
    required = [
        "order_wise_details.csv",
        "pizza_sales.csv",
        "pizza_wise_details.csv",
        "pizza_order.csv",
    ]

    missing = [name for name in required if not (DATA_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(
            "Missing data file(s): " + ", ".join(missing)
        )

    order_df = pd.read_csv(DATA_DIR / "order_wise_details.csv", dtype=str)
    sales_df = pd.read_csv(DATA_DIR / "pizza_sales.csv", dtype=str)
    pizza_df = pd.read_csv(DATA_DIR / "pizza_wise_details.csv", dtype=str)
    order_map_df = pd.read_csv(DATA_DIR / "pizza_order.csv", dtype=str)

    # Match the original SQL INNER JOIN:
    # order_wise_details -> pizza_sales -> pizza_wise_details -> pizza_order
    df = order_df.merge(
        sales_df,
        on="order_id",
        how="inner",
        suffixes=("_order", "_sales"),
    )

    df = df.merge(
        pizza_df[["pizza_id", "pizza_name", "Qty", "ingredients"]],
        on="pizza_id",
        how="inner",
    )

    df = df.merge(
        order_map_df[["pizza_id", "order_id"]],
        on=["pizza_id", "order_id"],
        how="inner",
    )

    # Keep the same first-occurrence behavior as SELECT * with duplicate
    # column names in the original MySQL version.
    result = pd.DataFrame({
        "order_id": df["order_id"],
        "total_price": df["total_price_order"],
        "unique_pizza_count": df["unique_pizza_count"],
        "total_qty": df["total_qty"],
        "order_date": df["order_date_order"],
        "unit_price": df["unit_price_order"],
        "min_pizza_size": df["min_pizza_size"],
        "max_pizza_size": df["max_pizza_size"],
        "unique_category_count": df["unique_category_count"],
        "order_details_id": df["order_details_id"],
        "pizza_id": df["pizza_id"],
        "quantity": df["quantity"],
        "order_time": df["order_time"],
        "pizza_size": df["pizza_size"],
        "pizza_category": df["pizza_category"],
        "pizza_ingredients": df["pizza_ingredients"],
        "pizza_name": df["pizza_name"],
    })

    # Same conversions as the original dashboard.
    result["order_id"] = pd.to_numeric(result["order_id"], errors="coerce")
    result["total_price"] = pd.to_numeric(result["total_price"], errors="coerce")
    result["unique_pizza_count"] = pd.to_numeric(
        result["unique_pizza_count"], errors="coerce"
    )
    result["unit_price"] = pd.to_numeric(result["unit_price"], errors="coerce")
    result["quantity"] = pd.to_numeric(result["quantity"], errors="coerce")
    result["total_qty"] = (
        pd.to_numeric(result["total_qty"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    result["full_date"] = pd.to_datetime(
        result["order_date"].astype(str).str.strip()
        + " "
        + result["order_time"].astype(str).str.strip(),
        errors="coerce",
    )

    if result["full_date"].isna().all():
        raise ValueError(
            "Could not parse order_date and order_time into full_date."
        )

    result["total_sale"] = result["total_qty"] * result["total_price"]

    return result


# ============================================================
# CHART THEME
# ============================================================
def dark_chart(fig, height=390):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="#101010",
        plot_bgcolor="#101010",
        font=dict(color="#EAEAEA"),
        margin=dict(l=45, r=25, t=45, b=45),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#D0D0D0")
        ),
        xaxis=dict(
            gridcolor="#242424",
            zerolinecolor="#242424"
        ),
        yaxis=dict(
            gridcolor="#242424",
            zerolinecolor="#242424"
        )
    )
    return fig


# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="hero">
    <div class="hero-title">🍕 Pizza Store Analytics</div>
    <div class="hero-subtitle">
        Sales performance, order behavior, product mix and daily revenue insights
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# LOAD DATA
# ============================================================
try:
    pizza_df = load_data()
except Exception as e:
    st.error("Could not load the Pizza Store data.")
    st.code(str(e))
    st.info(
        "Make sure the four CSV files are present in the same folder as pizza_app.py."
    )
    st.stop()


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 🍕 Pizza Store")
    st.caption("Analytics Dashboard")
    st.divider()

    st.markdown("### Dashboard Filters")

    categories = sorted(
        pizza_df["pizza_category"].dropna().astype(str).unique().tolist()
    )

    selected_categories = st.multiselect(
        "Pizza Category",
        categories,
        default=categories
    )

    sizes = sorted(
        pizza_df["min_pizza_size"].dropna().astype(str).unique().tolist()
    )

    selected_sizes = st.multiselect(
        "Pizza Size",
        sizes,
        default=sizes
    )

    st.divider()

    if st.button("↻ Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


filtered_df = pizza_df[
    pizza_df["pizza_category"].astype(str).isin(selected_categories)
    & pizza_df["min_pizza_size"].astype(str).isin(selected_sizes)
].copy()

# Defensive conversion before any .dt accessor is used.
filtered_df.loc[:, "full_date"] = pd.to_datetime(
    filtered_df["full_date"], errors="coerce"
)

if filtered_df.empty:
    st.warning("No data available for the selected filters.")
    st.stop()


# ============================================================
# KPI CALCULATIONS
# ============================================================
total_orders = filtered_df["order_id"].nunique()
avg_price = filtered_df["total_price"].astype(float).mean()
avg_pizza_qty = filtered_df["unique_pizza_count"].astype(float).mean()
total_sales = filtered_df["total_sale"].sum()
total_qty = filtered_df["total_qty"].sum()


# ============================================================
# KPI CARDS
# ============================================================
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Total Orders</div>'
        f'<div class="metric-value">{total_orders:,.0f}</div></div>',
        unsafe_allow_html=True
    )

with k2:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Total Sales</div>'
        f'<div class="metric-value">{total_sales:,.0f}</div></div>',
        unsafe_allow_html=True
    )

with k3:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Average Price</div>'
        f'<div class="metric-value">{avg_price:,.2f}</div></div>',
        unsafe_allow_html=True
    )

with k4:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Avg Pizza Qty</div>'
        f'<div class="metric-value">{avg_pizza_qty:,.1f}</div></div>',
        unsafe_allow_html=True
    )

with k5:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Total Quantity</div>'
        f'<div class="metric-value">{total_qty:,.0f}</div></div>',
        unsafe_allow_html=True
    )


# ============================================================
# TOP ORDER DATES
# ============================================================
st.markdown('<div class="section-title">Top 5 Order Dates</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-caption">Dates with the highest number of orders</div>',
    unsafe_allow_html=True
)

top5_dates = (
    filtered_df.groupby("order_date")
    .agg({"order_date": "count"})
    .rename(columns={"order_date": "orders"})
    .sort_values("orders", ascending=False)
    .head(5)
    .reset_index()
)

fig_top_dates = px.bar(
    top5_dates,
    x="order_date",
    y="orders",
    title="Top 5 Dates by Orders",
    labels={"order_date": "Order Date", "orders": "Orders"}
)

fig_top_dates.update_traces(
    hovertemplate="Date: %{x}<br>Orders: %{y}<extra></extra>"
)

dark_chart(fig_top_dates, 400)
st.plotly_chart(fig_top_dates, use_container_width=True)


# ============================================================
# SIZE + HOURLY ANALYSIS
# ============================================================
left, right = st.columns(2)

with left:
    st.markdown('<div class="section-title">Pizza Size Performance</div>', unsafe_allow_html=True)

    pizza_size = (
        filtered_df.groupby("min_pizza_size")
        .agg({"total_qty": "sum"})
        .reset_index()
    )

    fig_size = px.bar(
        pizza_size,
        x="min_pizza_size",
        y="total_qty",
        title="Quantity Sold by Pizza Size",
        labels={
            "min_pizza_size": "Pizza Size",
            "total_qty": "Total Quantity"
        }
    )

    fig_size.update_traces(
        hovertemplate="Size: %{x}<br>Quantity: %{y}<extra></extra>"
    )

    dark_chart(fig_size, 390)
    st.plotly_chart(fig_size, use_container_width=True)

with right:
    st.markdown('<div class="section-title">Order Activity by Hour</div>', unsafe_allow_html=True)

    hour_orders = (
        filtered_df.assign(order_hour=filtered_df["full_date"].dt.hour)
        .groupby("order_hour", as_index=False)
        .agg(order_id=("order_id", "nunique"))
        .sort_values("order_hour")
    )

    fig_hour = px.bar(
        hour_orders,
        x="order_hour",
        y="order_id",
        title="Orders by Hour",
        labels={
            "order_hour": "Hour",
            "order_id": "Unique Orders"
        }
    )

    fig_hour.update_traces(
        hovertemplate="Hour: %{x}:00<br>Orders: %{y}<extra></extra>"
    )

    dark_chart(fig_hour, 390)
    st.plotly_chart(fig_hour, use_container_width=True)


# ============================================================
# CATEGORY PERFORMANCE
# ============================================================
st.markdown('<div class="section-title">Pizza Category Performance</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-caption">Average price, average quantity and unique orders by category</div>',
    unsafe_allow_html=True
)

pizza_table = (
    filtered_df.groupby("pizza_category")
    .agg({
        "total_price": "mean",
        "total_qty": "mean",
        "order_id": "nunique"
    })
    .reset_index()
)

pizza_table.columns = [
    "Pizza Category",
    "Average Price",
    "Average Quantity",
    "Unique Orders"
]

pizza_table["Average Price"] = pizza_table["Average Price"].round()
pizza_table["Average Quantity"] = pizza_table["Average Quantity"].round()
pizza_table["Unique Orders"] = pizza_table["Unique Orders"].round()

st.dataframe(
    pizza_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# DAILY SALES
# ============================================================
st.markdown('<div class="section-title">Daily Sales Trend</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-caption">Total sales generated by day of the month</div>',
    unsafe_allow_html=True
)

day_sale = (
    filtered_df.groupby(filtered_df["full_date"].dt.day)
    .agg({"total_sale": "sum"})
    .reset_index()
)

fig_sales = px.line(
    day_sale,
    x="full_date",
    y="total_sale",
    markers=True,
    title="Daily Sales",
    labels={
        "full_date": "Day",
        "total_sale": "Total Sales"
    }
)

fig_sales.update_traces(
    hovertemplate="Day: %{x}<br>Sales: %{y:,.2f}<extra></extra>"
)

dark_chart(fig_sales, 430)
st.plotly_chart(fig_sales, use_container_width=True)


# ============================================================
# FOOTER
# ============================================================
st.divider()

st.caption(
    f"Pizza Store Analytics • Showing {len(filtered_df):,} records • "
    f"{total_orders:,} unique orders"
)
