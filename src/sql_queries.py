import sqlite3

DB_PATH = "output/novacart.db"

connection = sqlite3.connect(DB_PATH)


# ============================================================
# 1. TOTAL REVENUE
# ============================================================

query = """
SELECT SUM(net_revenue) AS total_revenue
FROM fact_sales;
"""

result = connection.execute(query).fetchone()

print("===== TOTAL REVENUE =====")
print(f"Total Revenue: ${result[0]:,.2f}")


# ============================================================
# 2. RETURN RATE
# ============================================================

query = """
SELECT
    AVG(is_returned) AS return_rate
FROM fact_sales;
"""

result = connection.execute(query).fetchone()

print("\n===== RETURN RATE =====")
print(f"Return Rate: {result[0] * 100:.2f}%")

# ============================================================
# 3. REVENUE BY PRICE TIER
# ============================================================

query = """
SELECT
    price_tier,
    SUM(net_revenue) AS revenue
FROM fact_sales
GROUP BY price_tier
ORDER BY revenue DESC;
"""

result = connection.execute(query).fetchall()

print("\n===== REVENUE BY PRICE TIER =====")

for row in result:
    print(f"{row[0]}: ${row[1]:,.2f}")
# ============================================================
# 4. REVENUE BY COUNTRY
# ============================================================

query = """
SELECT
    c.country,
    SUM(f.net_revenue) AS revenue
FROM fact_sales AS f
JOIN dim_customers AS c
    ON f.customer_id = c.customer_id
GROUP BY c.country
ORDER BY revenue DESC;
"""

result = connection.execute(query).fetchall()

print("\n===== REVENUE BY COUNTRY =====")

for row in result:
    print(f"{row[0]}: ${row[1]:,.2f}")

# ============================================================
# 5. REVENUE OVER TIME
# ============================================================

query = """
SELECT
    strftime('%Y-%m', order_date) AS month,
    SUM(net_revenue) AS revenue
FROM fact_sales
GROUP BY month
ORDER BY month;
"""

result = connection.execute(query).fetchall()

print("\n===== REVENUE OVER TIME =====")

for row in result:
    print(f"{row[0]}: ${row[1]:,.2f}")
connection.close()