import pandas as pd


# ============================================================
# 1. READ RAW CUSTOMER DATA
# ============================================================

customers = pd.read_json("data/customers.json")


# ============================================================
# 2. INSPECT RAW DATA
# ============================================================

print("===== FIRST 5 ROWS =====")
print(customers.head())

print("\n===== SHAPE =====")
print(customers.shape)

print("\n===== COLUMNS =====")
print(customers.columns)

print("\n===== DATA TYPES =====")
print(customers.dtypes)

print("\n===== MISSING VALUES =====")
print(customers.isna().sum())

print("\n===== DUPLICATE CUSTOMER IDs =====")
print(customers["customer_id"].duplicated().sum())


# ============================================================
# 3. FLATTEN ADDRESS
# ============================================================

address_data = pd.json_normalize(customers["address"])[
    ["city", "country"]
]

print("\n===== FLATTENED ADDRESS =====")
print(address_data.head())


# ============================================================
# 4. COMBINE CUSTOMER DATA WITH ADDRESS
# ============================================================

customers = pd.concat(
    [
        customers.drop(columns=["address"]),
        address_data
    ],
    axis=1
)

print("\n===== AFTER FLATTENING ADDRESS =====")
print(customers.head())


# ============================================================
# 5. CREATE EMAIL_PRESENT
# ============================================================

customers["email_present"] = customers["email"].notna()


# ============================================================
# 6. STANDARDISE COUNTRY
# ============================================================

country_mapping = {
    "U.S.A": "USA",
    "United States": "USA",
    "USA": "USA",
    "UK": "UK",
    "United Kingdom": "UK",
    "IN": "India",
    "India": "India",
    "DE": "Germany",
    "Germany": "Germany"
}

customers["country"] = customers["country"].replace(
    country_mapping
)


# ============================================================
# 7. CREATE DIM_CUSTOMERS
# ============================================================

dim_customers = customers[
    [
        "customer_id",
        "name",
        "email_present",
        "city",
        "country",
        "is_premium",
        "signup_date"
    ]
]


# ============================================================
# 8. VALIDATE DIM_CUSTOMERS
# ============================================================

print("\n===== DIM_CUSTOMERS =====")
print(dim_customers.head())

print("\n===== DIM_CUSTOMERS SHAPE =====")
print(dim_customers.shape)

print("\n===== DIM_CUSTOMERS COLUMNS =====")
print(dim_customers.columns)

print("\n===== MISSING VALUES =====")
print(dim_customers.isna().sum())

print("\n===== DUPLICATE CUSTOMER IDs =====")
print(
    dim_customers["customer_id"].duplicated().sum()
)