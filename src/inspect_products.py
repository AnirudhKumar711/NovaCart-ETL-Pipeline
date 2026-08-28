import pandas as pd


# ============================================================
# 1. READ PRODUCTS
# ============================================================

products = pd.read_csv(
    "data/products.csv",
    sep="|"
)

# ============================================================
# 2. BASIC INSPECTION
# ============================================================

print("===== FIRST 5 ROWS =====")

print(
    products.head()
)


print("\n===== SHAPE =====")

print(
    products.shape
)


print("\n===== COLUMNS =====")

print(
    products.columns
)


print("\n===== DATA TYPES =====")

print(
    products.dtypes
)


print("\n===== INFO =====")

print(
    products.info()
)


print("\n===== MISSING VALUES =====")

print(
    products.isna().sum()
)


print("\n===== DUPLICATE ROWS =====")

print(
    products.duplicated().sum()
)


print("\n===== DUPLICATE PRODUCT IDs =====")

print(
    products["product_id"].duplicated().sum()
)