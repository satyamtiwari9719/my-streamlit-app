import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Pizza Store Analytics",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background: #050505; color: #F5F5F5; }
[data-testid="stSidebar"] { background: #0B0B0B; }
.block-container { max-width: 1500px; padding-top: 2rem; }
.hero {
    background: #111111; border: 1px solid #292929;
    border-radius: 18px; padding: 28px 32px; margin-bottom: 22px;
}
.hero-title { font-size: 34px; font-weight: 800; margin: 0; }
.hero-subtitle { color: #A5A5A5; font-size: 15px; margin-top: 7px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <div class="hero-title">🍕 Pizza Store Analytics</div>
    <div class="hero-subtitle">
        Sales performance, order behavior, product mix and daily revenue insights
    </div>
</div>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).parent

@st.cache_data
def load_data():
    # pizza_sales.csv already contains all fields needed by the dashboard,
    # including pizza_name, category, size, quantity, price, date and time.
    path = BASE_DIR / "pizza_sales.csv"
    if not path.exists():
        raise FileNotFoundError(
            "pizza_sales.csv was not found beside pizza_app.py."
        )

    df = pd.read_csv(path)

    required = [
        "order_id", "pizza_id", "quantity", "order_date", "order_time",
        "unit_price", "total_price", "pizza_size", "pizza_category", "pizza_name"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in pizza_sales.csv: {', '.join(missing)}")

    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["total_price"] = pd.to_numeric(df["total_price"], errors="coerce")

    df["full_date"] = pd.to_datetime(
        df["order_date"].astype(str).str.strip() + " " +
        df["order_time"].astype(str).str.strip(),
        errors="coerce"
    )

    return df.dropna(subset=["order_id"]).copy()

try:
    pizza_df = load_data()
except Exception as e:
    st.error("Could not load the Pizza Store data.")
    st.code(str(e))
    st.info("Make sure pizza_sales.csv is in the same GitHub folder as pizza_app.py.")
    st.stop()

with st.sidebar:
    st.markdown("## 🍕 Pizza Store")
    st.caption("Analytics Dashboard")
    st.divider()

    categories = sorted(pizza_df["pizza_category"].dropna().astype(str).unique())
    selected_categories = st.multiselect(
        "Pizza Category", categories, default=categories
    )

    sizes = sorted(pizza_df["pizza_size"].dropna().astype(str).unique())
    selected_sizes = st.multiselect(
        "Pizza Size", sizes, default=sizes
    )

    st.divider()
    if st.button("↻ Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

filtered_df = pizza_df[
    pizza_df["pizza_category"].astype(str).isin(selected_categories)
    & pizza_df["pizza_size"].astype(str).isin(selected_sizes)
].copy()

if filtered_df.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

total_orders = filtered_df["order_id"].nunique()
total_sales = filtered_df["total_price"].sum()
total_qty = filtered_df["quantity"].sum()
avg_price = filtered_df["unit_price"].mean()
avg_qty_per_order = total_qty / total_orders if total_orders else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Orders", f"{total_orders:,.0f}")
k2.metric("Total Sales", f"{total_sales:,.2f}")
k3.metric("Average Price", f"{avg_price:,.2f}")
k4.metric("Avg Pizza Qty / Order", f"{avg_qty_per_order:,.1f}")
k5.metric("Total Quantity", f"{total_qty:,.0f}")

st.subheader("Top 5 Order Dates")
top_dates = (
    filtered_df.groupby(filtered_df["full_date"].dt.date)["order_id"]
    .nunique()
    .sort_values(ascending=False)
    .head(5)
    .reset_index(name="orders")
)
top_dates.columns = ["order_date", "orders"]
fig = px.bar(top_dates, x="order_date", y="orders", title="Top 5 Dates by Orders")
fig.update_layout(template="plotly_dark", paper_bgcolor="#101010", plot_bgcolor="#101010")
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with left:
    st.subheader("Pizza Size Performance")
    size_df = filtered_df.groupby("pizza_size", as_index=False)["quantity"].sum()
    fig = px.bar(size_df, x="pizza_size", y="quantity", title="Quantity Sold by Pizza Size")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#101010", plot_bgcolor="#101010")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Order Activity by Hour")
    hour_df = (
        filtered_df.dropna(subset=["full_date"])
        .assign(order_hour=lambda x: x["full_date"].dt.hour)
        .groupby("order_hour")["order_id"]
        .nunique()
        .reset_index(name="orders")
    )
    fig = px.bar(hour_df, x="order_hour", y="orders", title="Orders by Hour")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#101010", plot_bgcolor="#101010")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Pizza Category Performance")
category_df = (
    filtered_df.groupby("pizza_category")
    .agg(
        Average_Price=("unit_price", "mean"),
        Average_Quantity=("quantity", "mean"),
        Unique_Orders=("order_id", "nunique"),
    )
    .reset_index()
)
category_df["Average_Price"] = category_df["Average_Price"].round(2)
category_df["Average_Quantity"] = category_df["Average_Quantity"].round(2)
st.dataframe(category_df, use_container_width=True, hide_index=True)

st.subheader("Top 10 Pizzas by Sales")
pizza_sales_df = (
    filtered_df.groupby("pizza_name", as_index=False)["total_price"]
    .sum()
    .sort_values("total_price", ascending=False)
    .head(10)
)
fig = px.bar(
    pizza_sales_df,
    x="total_price",
    y="pizza_name",
    orientation="h",
    title="Top 10 Pizzas by Sales",
)
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#101010",
    plot_bgcolor="#101010",
    yaxis={"categoryorder": "total ascending"},
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Daily Sales Trend")
daily_df = (
    filtered_df.dropna(subset=["full_date"])
    .assign(order_day=lambda x: x["full_date"].dt.date)
    .groupby("order_day", as_index=False)["total_price"]
    .sum()
)
fig = px.line(
    daily_df,
    x="order_day",
    y="total_price",
    markers=True,
    title="Daily Sales",
    labels={"order_day": "Date", "total_price": "Total Sales"},
)
fig.update_layout(template="plotly_dark", paper_bgcolor="#101010", plot_bgcolor="#101010")
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption(
    f"Pizza Store Analytics • Showing {len(filtered_df):,} records • "
    f"{total_orders:,} unique orders"
)
