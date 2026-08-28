import pandas as pd
import numpy as np

# ============================================================
# 1. READ RAW ORDERS DATA
# ============================================================

orders = pd.read_csv("data/orders.csv")

# ============================================================
# 2. INSPECT RAW DATA
# ============================================================

print("===== FIRST 5 ROWS =====")
print(orders.head())

print("\n===== SHAPE =====")
print(orders.shape)

print("\n===== COLUMNS =====")
print(orders.columns)

print("\n===== DATA TYPES =====")
print(orders.dtypes)

print("\n===== INFO =====")
orders.info()

print("\n===== MISSING VALUES =====")
print(orders.isna().sum())

print("\n===== DUPLICATE ROWS =====")
print(orders.duplicated().sum())


# ============================================================
# 3. ORDER ID ANALYSIS
# ============================================================

print("\n===== ORDER ID ANALYSIS =====")

print("Total order IDs:", len(orders["order_id"]))

print("Unique order IDs:", orders["order_id"].nunique())

print("\nDuplicate order IDs:")

duplicate_orders = orders[
    orders["order_id"].duplicated(keep=False)
].sort_values("order_id")

print(
    duplicate_orders[["order_id"]]
    .to_string(index=False)
)


# ============================================================
# 4. DUPLICATE ORDER DETAILS
# ============================================================

print("\n===== DUPLICATE ORDER DETAILS =====")

print(
    duplicate_orders.to_string(index=False)
)


# ============================================================
# 5. REMOVE EXACT DUPLICATE ROWS
# ============================================================

clean_orders = orders.drop_duplicates()

print("\n===== AFTER DUPLICATE REMOVAL =====")

print("Raw rows:", len(orders))

print(
    "Rows after removing duplicates:",
    len(clean_orders)
)

print(
    "Duplicate rows remaining:",
    clean_orders.duplicated().sum()
)


# ============================================================
# 6. CLEAN ORDER IDs
# ============================================================

clean_orders["order_id"] = (
    clean_orders["order_id"].str.strip()
)

print("\n===== ORDER ID AFTER TRIMMING =====")

print(
    "Unique order IDs:",
    clean_orders["order_id"].nunique()
)

print(
    "Duplicate order IDs after trimming:",
    clean_orders["order_id"].duplicated().sum()
)
# ============================================================
# 7. CUSTOMER ID REFERENTIAL VALIDATION
# ============================================================

# Read customer IDs from the customer dimension
customers = pd.read_json("data/customers.json")

valid_customer_ids = set(customers["customer_id"])


# Check whether each order customer_id exists
customer_id_valid = clean_orders["customer_id"].isin(
    valid_customer_ids
)


print("\n===== CUSTOMER ID VALIDATION =====")

print(
    "Missing customer IDs:",
    clean_orders["customer_id"].isna().sum()
)

print(
    "Invalid customer IDs:",
    (
        clean_orders["customer_id"].notna()
        & ~customer_id_valid
    ).sum()
)

# ============================================================
# 8. CREATE VALID AND REJECTED ORDERS
# ============================================================

# Valid order:
# customer_id is present AND exists in customers.json
valid_customer_mask = (
    clean_orders["customer_id"].notna()
    & customer_id_valid
)

# Rejected order:
# customer_id is missing
missing_customer_mask = (
    clean_orders["customer_id"].isna()
)


# Create valid orders
valid_orders = clean_orders[
    valid_customer_mask
].copy()


# Create rejected orders
rejected_orders = clean_orders[
    missing_customer_mask
].copy()


# Add rejection reason
rejected_orders["reject_reason"] = (
    "missing customer_id"
)


# ============================================================
# 9. VALIDATION SUMMARY
# ============================================================

print("\n===== VALID / REJECTED ORDERS =====")

print(
    "Total clean orders:",
    len(clean_orders)
)

print(
    "Valid orders:",
    len(valid_orders)
)

print(
    "Rejected orders:",
    len(rejected_orders)
)

print(
    "Rejected because of missing customer_id:",
    (
        rejected_orders["reject_reason"]
        == "missing customer_id"
    ).sum()
)


# ============================================================
# 10. SHOW REJECTED ORDERS
# ============================================================

print("\n===== REJECTED ORDERS =====")

print(
    rejected_orders[
        [
            "order_id",
            "customer_id",
            "product_id",
            "quantity",
            "amount",
            "currency",
            "order_date",
            "reject_reason"
        ]
    ].head(10)
)
# ============================================================
# 11. QUANTITY VALIDATION
# ============================================================

# Source:
# data/orders.csv
#
# Rule:
# quantity must be greater than 0

invalid_quantity_mask = (
    valid_orders["quantity"] <= 0
)

print("\n===== QUANTITY VALIDATION =====")

print(
    "Invalid quantity rows:",
    invalid_quantity_mask.sum()
)


# ============================================================
# 12. ADD INVALID QUANTITY ORDERS TO REJECTED ORDERS
# ============================================================

invalid_quantity_orders = valid_orders[
    invalid_quantity_mask
].copy()

invalid_quantity_orders["reject_reason"] = (
    "quantity must be greater than 0"
)


# Add them to the existing rejected orders
rejected_orders = pd.concat(
    [
        rejected_orders,
        invalid_quantity_orders
    ],
    ignore_index=True
)


# Keep only orders that passed quantity validation
valid_orders = valid_orders[
    ~invalid_quantity_mask
].copy()


# ============================================================
# 13. VALIDATION SUMMARY
# ============================================================

print("\n===== UPDATED VALID / REJECTED ORDERS =====")

print(
    "Valid orders remaining:",
    len(valid_orders)
)

print(
    "Total rejected orders:",
    len(rejected_orders)
)

print("\n===== REJECTION REASONS =====")

print(
    rejected_orders["reject_reason"].value_counts()
)
# ============================================================
# 14. AMOUNT VALIDATION
# ============================================================

# Source:
# data/orders.csv
#
# Rule:
# amount must be present and greater than or equal to 0

missing_amount_mask = (
    valid_orders["amount"].isna()
)

invalid_amount_mask = (
    valid_orders["amount"].notna()
    & (valid_orders["amount"] < 0)
)


print("\n===== AMOUNT VALIDATION =====")

print(
    "Missing amount:",
    missing_amount_mask.sum()
)

print(
    "Invalid negative amount:",
    invalid_amount_mask.sum()
)


# ============================================================
# 15. ADD INVALID AMOUNT ORDERS TO REJECTED ORDERS
# ============================================================

# Missing amount records
missing_amount_orders = valid_orders[
    missing_amount_mask
].copy()

missing_amount_orders["reject_reason"] = (
    "missing amount"
)


# Negative amount records
negative_amount_orders = valid_orders[
    invalid_amount_mask
].copy()

negative_amount_orders["reject_reason"] = (
    "amount must be greater than or equal to 0"
)


# Add both types to rejection log
rejected_orders = pd.concat(
    [
        rejected_orders,
        missing_amount_orders,
        negative_amount_orders
    ],
    ignore_index=True
)


# Keep only orders that passed amount validation
valid_orders = valid_orders[
    ~(
        missing_amount_mask
        | invalid_amount_mask
    )
].copy()


# ============================================================
# 16. UPDATED VALIDATION SUMMARY
# ============================================================

print("\n===== AFTER AMOUNT VALIDATION =====")

print(
    "Valid orders remaining:",
    len(valid_orders)
)

print(
    "Total rejected orders:",
    len(rejected_orders)
)

print("\n===== REJECTION REASONS =====")

print(
    rejected_orders["reject_reason"].value_counts()
)
# ============================================================
# 17. CURRENCY VALIDATION
# ============================================================

# Source 1:
# data/orders.csv
# Column: currency
#
# Source 2:
# data/exchange_rates.json
# Columns: currency, rate_to_usd
#
# Rule:
# Every order currency must have a matching
# currency in exchange_rates.json.


# ------------------------------------------------------------
# Read exchange rates
# ------------------------------------------------------------

rates = pd.read_json(
    "data/exchange_rates.json"
)


# ------------------------------------------------------------
# Convert currency index into a normal column
# ------------------------------------------------------------

rates = rates.reset_index()


# ------------------------------------------------------------
# Rename columns
# ------------------------------------------------------------

rates = rates.rename(
    columns={
        "index": "currency",
        "rates": "rate_to_usd"
    }
)


# ------------------------------------------------------------
# Inspect prepared exchange-rate table
# ------------------------------------------------------------

print("\n===== PREPARED EXCHANGE RATES =====")

print(rates)


# ============================================================
# 18. CURRENCY VALIDATION
# ============================================================

# Create a set containing the currencies
# available in exchange_rates.json

valid_currencies = set(
    rates["currency"]
)


# Check every currency in orders.csv
# against the currencies in exchange_rates.json

currency_valid = valid_orders["currency"].isin(
    valid_currencies
)


# Find currencies that are NOT supported

invalid_currency_mask = ~currency_valid


print("\n===== CURRENCY VALIDATION =====")

print(
    "Valid currencies:",
    sorted(valid_currencies)
)

print(
    "Invalid currency rows:",
    invalid_currency_mask.sum()
)


# ============================================================
# 19. SHOW INVALID CURRENCY ORDERS
# ============================================================

print("\n===== INVALID CURRENCY ORDERS =====")

print(
    valid_orders[
        invalid_currency_mask
    ][
        [
            "order_id",
            "customer_id",
            "product_id",
            "quantity",
            "amount",
            "currency",
            "order_date"
        ]
    ].to_string(index=False)
)


# ============================================================
# 20. MERGE EXCHANGE RATES
# ============================================================

# We already confirmed that all currencies are valid.
#
# Now bring rate_to_usd from exchange_rates.json
# into valid_orders.
#
# Join key:
# orders.csv currency
#        ↓
# exchange_rates.json currency

valid_orders = valid_orders.merge(
    rates[
        [
            "currency",
            "rate_to_usd"
        ]
    ],
    on="currency",
    how="left"
)


print("\n===== AFTER EXCHANGE RATE MERGE =====")

print(
    valid_orders[
        [
            "order_id",
            "amount",
            "currency",
            "rate_to_usd"
        ]
    ].head(10)
)


# ============================================================
# 21. CALCULATE AMOUNT_USD
# ============================================================

# Project rule:
#
# amount_usd = amount × rate_to_usd

valid_orders["amount_usd"] = (
    valid_orders["amount"]
    * valid_orders["rate_to_usd"]
)


print("\n===== AMOUNT USD =====")

print(
    valid_orders[
        [
            "order_id",
            "amount",
            "currency",
            "rate_to_usd",
            "amount_usd"
        ]
    ].head(10)
)
# ============================================================
# 22. ORDER DATE INSPECTION
# ============================================================

print("\n===== ORDER DATE BEFORE CONVERSION =====")

print(
    valid_orders[
        [
            "order_id",
            "order_date"
        ]
    ].head(20).to_string(index=False)
)

print("\n===== ORDER DATE DATA TYPE =====")

print(
    valid_orders["order_date"].dtype
)

print("\n===== UNIQUE DATE FORMATS / EXAMPLES =====")

print(
    valid_orders["order_date"]
    .dropna()
    .head(20)
    .to_string(index=False)
)
# ============================================================
# 23. CONVERT ORDER DATE
# ============================================================

valid_orders["order_date"] = pd.to_datetime(
    valid_orders["order_date"],
    format="mixed",
    errors="coerce"
)


print("\n===== ORDER DATE AFTER CONVERSION =====")

print(
    valid_orders[
        [
            "order_id",
            "order_date"
        ]
    ].head(20).to_string(index=False)
)

print("\n===== ORDER DATE DATA TYPE =====")

print(
    valid_orders["order_date"].dtype
)


print("\n===== INVALID / MISSING DATES =====")

print(
    valid_orders["order_date"].isna().sum()
)
# ============================================================
# 24. PRODUCT ID VALIDATION
# ============================================================

# Source 1:
# data/orders.csv
# Column: product_id
#
# Source 2:
# data/products.csv
# Column: product_id
#
# Rule:
# Every product_id in a valid order must exist
# in products.csv.


# ------------------------------------------------------------
# Read products.csv
# ------------------------------------------------------------

products = pd.read_csv(
    "data/products.csv",
    sep="|"
)


# ------------------------------------------------------------
# Create set of valid product IDs
# ------------------------------------------------------------

valid_product_ids = set(
    products["product_id"]
)


# ------------------------------------------------------------
# Check order product IDs
# ------------------------------------------------------------

product_id_valid = valid_orders["product_id"].isin(
    valid_product_ids
)


# ------------------------------------------------------------
# Find invalid product IDs
# ------------------------------------------------------------

invalid_product_mask = ~product_id_valid


print("\n===== PRODUCT ID VALIDATION =====")

print(
    "Total product IDs in products.csv:",
    len(valid_product_ids)
)

print(
    "Invalid product ID rows:",
    invalid_product_mask.sum()
)


# ============================================================
# 25. SHOW INVALID PRODUCT ORDERS
# ============================================================

print("\n===== INVALID PRODUCT ORDERS =====")

print(
    valid_orders[
        invalid_product_mask
    ][
        [
            "order_id",
            "customer_id",
            "product_id",
            "quantity",
            "amount",
            "currency",
            "order_date"
        ]
    ].to_string(index=False)
)
# ============================================================
# 26. PREPARE PRODUCT DATA FOR MERGE
# ============================================================

# products.csv was already loaded during validation.
#
# Rename product currency so it does not conflict with
# the order currency from orders.csv.

products_for_merge = products.rename(
    columns={
        "currency": "product_currency"
    }
)


print("\n===== PRODUCTS FOR MERGE =====")

print(
    products_for_merge[
        [
            "product_id",
            "product_name",
            "category",
            "unit_price",
            "product_currency"
        ]
    ].head()
)


# ============================================================
# 27. MERGE PRODUCT INFORMATION
# ============================================================

valid_orders = valid_orders.merge(
    products_for_merge[
        [
            "product_id",
            "product_name",
            "category",
            "unit_price",
            "product_currency"
        ]
    ],
    on="product_id",
    how="left"
)


print("\n===== AFTER PRODUCT MERGE =====")

print(
    valid_orders[
        [
            "order_id",
            "product_id",
            "product_name",
            "category",
            "unit_price",
            "product_currency",
            "currency",
            "amount_usd"
        ]
    ].head(10)
)
# ============================================================
# 28. CALCULATE UNIT PRICE USD
# ============================================================

# Product unit price comes from:
# data/products.csv
#
# Product currency comes from:
# data/products.csv
#
# Exchange rate comes from:
# data/exchange_rates.json
#
# Rule:
# unit_price_usd = unit_price × rate_to_usd


# Create a separate exchange-rate table for product currency

product_rates = rates[
    [
        "currency",
        "rate_to_usd"
    ]
].rename(
    columns={
        "currency": "product_currency"
    }
)


# Merge the product currency rate

valid_orders = valid_orders.merge(
    product_rates,
    on="product_currency",
    how="left"
)


# Calculate product unit price in USD

valid_orders["unit_price_usd"] = (
    valid_orders["unit_price"]
    * valid_orders["rate_to_usd_y"]
)


print("\n===== UNIT PRICE USD =====")

print(
    valid_orders[
        [
            "product_id",
            "product_name",
            "unit_price",
            "product_currency",
            "unit_price_usd"
        ]
    ].head(10)
)
# ============================================================
# 29. CREATE PRICE TIER
# ============================================================

# Source:
# unit_price_usd was calculated using:
# products.csv + exchange_rates.json
#
# Project Rule:
# low    -> unit_price_usd < 10
# medium -> 10 <= unit_price_usd < 100
# high   -> unit_price_usd >= 100


valid_orders["price_tier"] = np.select(
    [
        valid_orders["unit_price_usd"] < 10,
        valid_orders["unit_price_usd"] < 100
    ],
    [
        "low",
        "medium"
    ],
    default="high"
)


print("\n===== PRICE TIER =====")

print(
    valid_orders[
        [
            "product_id",
            "product_name",
            "unit_price_usd",
            "price_tier"
        ]
    ].head(10)
)
