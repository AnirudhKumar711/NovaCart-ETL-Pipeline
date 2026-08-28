import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# 1. PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "output" / "novacart.db"


# ============================================================
# 2. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="NovaCart Sales Dashboard",
    page_icon="🛒",
    layout="wide"
)


# ============================================================
# 3. DATABASE CONNECTION
# ============================================================

connection = sqlite3.connect(DB_PATH)


# ============================================================
# 4. TITLE
# ============================================================

st.title("NovaCart Sales Dashboard")

st.write(
    "Sales performance and customer transaction analysis"
)


# ============================================================
# 5. TOTAL REVENUE
# ============================================================

revenue_query = """
SELECT
    SUM(net_revenue) AS total_revenue
FROM fact_sales;
"""

total_revenue = connection.execute(
    revenue_query
).fetchone()[0]


# ============================================================
# 6. RETURN RATE
# ============================================================

return_query = """
SELECT
    AVG(is_returned) AS return_rate
FROM fact_sales;
"""

return_rate = connection.execute(
    return_query
).fetchone()[0]


# ============================================================
# 7. KPI DISPLAY
# ============================================================

col1, col2 = st.columns(2)

with col1:
    st.metric(
        label="Total Revenue",
        value=f"${total_revenue:,.2f}"
    )

with col2:
    st.metric(
        label="Return Rate",
        value=f"{return_rate * 100:.2f}%"
    )


st.divider()


# ============================================================
# 8. REVENUE BY PRICE TIER
# ============================================================

price_tier_query = """
SELECT
    price_tier,
    SUM(net_revenue) AS revenue
FROM fact_sales
GROUP BY price_tier
ORDER BY revenue DESC;
"""

price_tier_df = pd.read_sql_query(
    price_tier_query,
    connection
)

st.subheader("Revenue by Price Tier")

st.bar_chart(
    price_tier_df,
    x="price_tier",
    y="revenue"
)


# ============================================================
# 9. REVENUE BY COUNTRY
# ============================================================

country_query = """
SELECT
    c.country,
    SUM(f.net_revenue) AS revenue
FROM fact_sales AS f
JOIN dim_customers AS c
    ON f.customer_id = c.customer_id
GROUP BY c.country
ORDER BY revenue DESC;
"""

country_df = pd.read_sql_query(
    country_query,
    connection
)

st.subheader("Revenue by Country")

st.bar_chart(
    country_df,
    x="country",
    y="revenue"
)


# ============================================================
# 10. REVENUE OVER TIME - DATE WISE
# ============================================================

time_query = """
SELECT
    DATE(order_date) AS order_date,
    SUM(net_revenue) AS revenue
FROM fact_sales
GROUP BY DATE(order_date)
ORDER BY DATE(order_date);
"""

time_df = pd.read_sql_query(
    time_query,
    connection
)

# Convert the date column to datetime
time_df["order_date"] = pd.to_datetime(
    time_df["order_date"]
)


st.subheader("Revenue Over Time")

st.line_chart(
    time_df,
    x="order_date",
    y="revenue"
)


# ============================================================
# 11. CLOSE DATABASE
# ============================================================

connection.close()