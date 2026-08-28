import json
import re
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
import logging

# ============================================================
# 1. PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = OUTPUT_DIR / "novacart.db"
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_FILE = OUTPUT_DIR / "pipeline.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)
ORDERS_FILE = DATA_DIR / "orders.csv"
CUSTOMERS_FILE = DATA_DIR / "customers.json"
PRODUCTS_FILE = DATA_DIR / "products.csv"
RETURNS_FILE = DATA_DIR / "returns.tsv"
EXCHANGE_RATES_FILE = DATA_DIR / "exchange_rates.json"
WEB_EVENTS_FILE = DATA_DIR / "web_events.log"


# ============================================================
# 2. LOAD SOURCE FILES
# ============================================================

print("\n" + "=" * 70)
print("LOADING SOURCE FILES")
print("=" * 70)

orders = pd.read_csv(ORDERS_FILE)
customers = pd.read_json(CUSTOMERS_FILE)
products = pd.read_csv(PRODUCTS_FILE, sep="|")
returns = pd.read_csv(RETURNS_FILE, sep="\t")

with open(EXCHANGE_RATES_FILE, "r") as file:
    exchange_data = json.load(file)

print("Orders:", orders.shape)
print("Customers:", customers.shape)
print("Products:", products.shape)
print("Returns:", returns.shape)
logger.info(
    "Source files loaded | orders=%s | customers=%s | products=%s | returns=%s",
    len(orders),
    len(customers),
    len(products),
    len(returns)
)

# ============================================================
# 3. PREPARE EXCHANGE RATES
# ============================================================

print("\n" + "=" * 70)
print("EXCHANGE RATES")
print("=" * 70)

rates_dict = exchange_data["rates"]

rates = pd.DataFrame(
    {
        "currency": list(rates_dict.keys()),
        "base": exchange_data["base"],
        "as_of": exchange_data["as_of"],
        "rate_to_usd": list(rates_dict.values()),
    }
)

print(rates)


# ============================================================
# 4. CLEAN ORDERS
# ============================================================

print("\n" + "=" * 70)
print("ORDER CLEANING")
print("=" * 70)

string_columns = [
    "order_id",
    "customer_id",
    "product_id",
    "currency",
    "order_date",
]

for column in string_columns:
    orders[column] = orders[column].astype("string").str.strip()


# Remove exact duplicate rows

raw_row_count = len(orders)

orders = orders.drop_duplicates().copy()

print("Raw rows:", raw_row_count)
print("Rows after duplicate removal:", len(orders))


# Remove duplicate order IDs

orders = orders.drop_duplicates(
    subset=["order_id"],
    keep="first"
).copy()

print(
    "Rows after duplicate order ID removal:",
    len(orders)
)


# ============================================================
# 5. REJECT LOG
# ============================================================

reject_log = pd.DataFrame(
    columns=list(orders.columns) + ["reject_reason"]
)


def reject_rows(data, mask, reason):

    global reject_log

    rejected = data.loc[mask].copy()

    if len(rejected) > 0:

        rejected["reject_reason"] = reason

        reject_log = pd.concat(
            [
                reject_log,
                rejected
            ],
            ignore_index=True
        )

    return data.loc[~mask].copy()


# ============================================================
# 6. CUSTOMER ID VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("CUSTOMER ID VALIDATION")
print("=" * 70)

customer_ids = set(
    customers["customer_id"]
    .astype(str)
    .str.strip()
)

missing_customer = orders["customer_id"].isna()

invalid_customer = (
    orders["customer_id"].notna()
    & ~orders["customer_id"].isin(customer_ids)
)

print(
    "Missing customer IDs:",
    missing_customer.sum()
)

print(
    "Invalid customer IDs:",
    invalid_customer.sum()
)

orders = reject_rows(
    orders,
    missing_customer,
    "missing customer_id"
)

orders = reject_rows(
    orders,
    invalid_customer,
    "invalid customer_id"
)


# ============================================================
# 7. QUANTITY VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("QUANTITY VALIDATION")
print("=" * 70)

invalid_quantity = orders["quantity"] <= 0

print(
    "Invalid quantity rows:",
    invalid_quantity.sum()
)

orders = reject_rows(
    orders,
    invalid_quantity,
    "quantity must be greater than 0"
)


# ============================================================
# 8. AMOUNT VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("AMOUNT VALIDATION")
print("=" * 70)

missing_amount = orders["amount"].isna()

negative_amount = orders["amount"] < 0

print(
    "Missing amount:",
    missing_amount.sum()
)

print(
    "Negative amount:",
    negative_amount.sum()
)

orders = reject_rows(
    orders,
    missing_amount,
    "missing amount"
)

orders = reject_rows(
    orders,
    negative_amount,
    "amount must not be negative"
)


# ============================================================
# 9. CURRENCY VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("CURRENCY VALIDATION")
print("=" * 70)

valid_currencies = rates["currency"].tolist()

invalid_currency = (
    ~orders["currency"].isin(valid_currencies)
)

print(
    "Valid currencies:",
    valid_currencies
)

print(
    "Invalid currency rows:",
    invalid_currency.sum()
)

orders = reject_rows(
    orders,
    invalid_currency,
    "invalid currency"
)


# ============================================================
# 10. ORDER DATE CONVERSION
# ============================================================

print("\n" + "=" * 70)
print("ORDER DATE CONVERSION")
print("=" * 70)

orders["order_date"] = pd.to_datetime(
    orders["order_date"],
    format="mixed",
    dayfirst=False,
    errors="coerce"
)

invalid_date = orders["order_date"].isna()

print(
    "Invalid / missing dates:",
    invalid_date.sum()
)

orders = reject_rows(
    orders,
    invalid_date,
    "invalid order_date"
)


# ============================================================
# 11. EXCHANGE RATE MERGE
# ============================================================

print("\n" + "=" * 70)
print("EXCHANGE RATE MERGE")
print("=" * 70)

orders = orders.merge(
    rates[
        [
            "currency",
            "rate_to_usd"
        ]
    ],
    on="currency",
    how="left",
    validate="many_to_one"
)

print(
    orders[
        [
            "order_id",
            "amount",
            "currency",
            "rate_to_usd"
        ]
    ].head(10)
)
logger.info(
    "Order validation completed | clean_orders=%s | rejected_orders=%s",
    len(orders),
    len(reject_log)
)

# ============================================================
# 12. AMOUNT USD
# ============================================================

orders["amount_usd"] = (
    orders["amount"]
    * orders["rate_to_usd"]
)

print("\n===== AMOUNT USD =====")

print(
    orders[
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
# 13. PRODUCT PROCESSING
# ============================================================

print("\n" + "=" * 70)
print("PRODUCT PROCESSING")
print("=" * 70)

products["product_id"] = (
    products["product_id"]
    .astype("string")
    .str.strip()
)

products["product_name"] = (
    products["product_name"]
    .astype("string")
    .str.strip()
)

products["category"] = (
    products["category"]
    .astype("string")
    .str.strip()
)

products["currency"] = (
    products["currency"]
    .astype("string")
    .str.strip()
)

products_for_merge = products[
    [
        "product_id",
        "product_name",
        "category",
        "unit_price",
        "currency"
    ]
].copy()

products_for_merge = products_for_merge.rename(
    columns={
        "currency": "product_currency"
    }
)

print("\n===== PRODUCTS FOR MERGE =====")

print(
    products_for_merge.head()
)


# ============================================================
# 14. PRODUCT ID VALIDATION
# ============================================================

product_ids = set(
    products["product_id"]
)

invalid_product = (
    ~orders["product_id"].isin(product_ids)
)

print("\n===== PRODUCT ID VALIDATION =====")

print(
    "Total product IDs:",
    len(product_ids)
)

print(
    "Invalid product ID rows:",
    invalid_product.sum()
)

orders = reject_rows(
    orders,
    invalid_product,
    "invalid product_id"
)


# ============================================================
# 15. PRODUCT MERGE
# ============================================================

orders = orders.merge(
    products_for_merge,
    on="product_id",
    how="left",
    validate="many_to_one"
)

print("\n===== AFTER PRODUCT MERGE =====")

print(
    orders[
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
# 16. UNIT PRICE USD
# ============================================================

product_rate_lookup = rates[
    [
        "currency",
        "rate_to_usd"
    ]
].rename(
    columns={
        "currency": "product_currency",
        "rate_to_usd": "product_rate_to_usd"
    }
)

orders = orders.merge(
    product_rate_lookup,
    on="product_currency",
    how="left",
    validate="many_to_one"
)

orders["unit_price_usd"] = (
    orders["unit_price"]
    * orders["product_rate_to_usd"]
)

print("\n===== UNIT PRICE USD =====")

print(
    orders[
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
# 17. PRICE TIER
# ============================================================

print("\n" + "=" * 70)
print("PRICE TIER")
print("=" * 70)

orders["price_tier"] = np.select(
    [
        orders["unit_price_usd"] < 50,
        orders["unit_price_usd"] < 100
    ],
    [
        "low",
        "medium"
    ],
    default="high"
)

print(
    orders[
        [
            "product_id",
            "product_name",
            "unit_price_usd",
            "price_tier"
        ]
    ].head(10)
)


# ============================================================
# 18. RETURNS
# ============================================================

print("\n" + "=" * 70)
print("RETURNS PROCESSING")
print("=" * 70)

print("\nReturns columns:")
print(returns.columns.tolist())

print("\nReturns sample:")
print(returns.head())

returns.columns = (
    returns.columns
    .astype(str)
    .str.strip()
)

returns["order_id"] = (
    returns["order_id"]
    .astype("string")
    .str.strip()
)


# ============================================================
# 19. IS RETURNED
# ============================================================

returned_order_ids = set(
    returns["order_id"].dropna()
)

orders["is_returned"] = (
    orders["order_id"]
    .isin(returned_order_ids)
)

print("\n===== RETURN STATUS =====")

print(
    orders[
        [
            "order_id",
            "is_returned"
        ]
    ].head(10)
)


# ============================================================
# 20. NET REVENUE
# ============================================================

orders["net_revenue"] = np.where(
    orders["is_returned"],
    0,
    orders["amount_usd"]
)


# ============================================================
# 21. FACT SALES
# ============================================================

print("\n" + "=" * 70)
print("BUILDING FACT_SALES")
print("=" * 70)

fact_sales = orders[
    [
        "order_id",
        "customer_id",
        "product_id",
        "quantity",
        "amount",
        "currency",
        "amount_usd",
        "order_date",
        "price_tier",
        "net_revenue",
        "is_returned"
    ]
].copy()

print("\n===== FACT_SALES =====")

print(
    fact_sales.head()
)

print(
    "\nShape:",
    fact_sales.shape
)
logger.info(
    "FACT_SALES created | rows=%s",
    len(fact_sales)
)

# ============================================================
# 22. DIM CUSTOMERS
# ============================================================

print("\n" + "=" * 70)
print("BUILDING DIM_CUSTOMERS")
print("=" * 70)

address = pd.json_normalize(
    customers["address"]
)

address = address[
    [
        "city",
        "country"
    ]
].copy()

dim_customers = customers[
    [
        "customer_id",
        "name",
        "email",
        "signup_date",
        "is_premium"
    ]
].copy()

dim_customers = pd.concat(
    [
        dim_customers.reset_index(drop=True),
        address.reset_index(drop=True)
    ],
    axis=1
)

dim_customers["email_present"] = (
    dim_customers["email"].notna()
)
logger.info(
    "DIM_CUSTOMERS created | rows=%s",
    len(dim_customers)
)

# Country standardisation

country_map = {
    "U.S.A": "USA",
    "USA": "USA",
    "United States": "USA",
    "United Kingdom": "UK",
    "UK": "UK",
    "India": "India",
    "IN": "India",
    "Germany": "Germany",
    "DE": "Germany"
}
dim_customers["country"] = (
    dim_customers["country"]
    .astype("string")
    .str.strip()
    .replace(country_map)
)

dim_customers["signup_date"] = pd.to_datetime(
    dim_customers["signup_date"],
    errors="coerce"
)

dim_customers = dim_customers[
    [
        "customer_id",
        "name",
        "email_present",
        "city",
        "country",
        "is_premium",
        "signup_date"
    ]
].copy()

print("\n===== DIM_CUSTOMERS =====")

print(
    dim_customers.head()
)

print(
    "\nShape:",
    dim_customers.shape
)

print(
    "\nColumns:",
    dim_customers.columns.tolist()
)


# ============================================================
# 23. PARSE WEB EVENTS
# ============================================================

print("\n" + "=" * 70)
print("WEB EVENTS")
print("=" * 70)

web_events = []


with open(
    WEB_EVENTS_FILE,
    "r",
    encoding="utf-8"
) as file:

    for line in file:

        line = line.strip()

        if not line:
            continue

        # ----------------------------------------------------
        # Example:
        #
        # 2026-05-26T18:53:34 |
        # session=s5261 |
        # user=C0021 |
        # event=checkout |
        # product=P0030
        # ----------------------------------------------------

        parts = [
            part.strip()
            for part in line.split("|")
        ]

        event_record = {}

        # First part is timestamp

        if len(parts) > 0:

            event_record["timestamp"] = parts[0]


        # Remaining parts are key=value

        for part in parts[1:]:

            if "=" in part:

                key, value = part.split(
                    "=",
                    1
                )

                event_record[key.strip()] = (
                    value.strip()
                )


        if event_record:
            web_events.append(
                event_record
            )


web_events = pd.DataFrame(
    web_events
)


print(
    "Web event rows:",
    len(web_events)
)

print(
    "Web event columns:",
    web_events.columns.tolist()
)

print("\n===== WEB EVENTS SAMPLE =====")

print(
    web_events.head(10)
)


# ============================================================
# 24. NORMALISE WEB EVENT COLUMNS
# ============================================================

if len(web_events) > 0:

    web_events["customer_id"] = (
        web_events["user"]
        .astype("string")
        .str.strip()
    )

    web_events["session_id"] = (
        web_events["session"]
        .astype("string")
        .str.strip()
    )

    web_events["event_type"] = (
        web_events["event"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    web_events["product_id"] = (
        web_events["product"]
        .astype("string")
        .str.strip()
    )


    web_events["timestamp"] = pd.to_datetime(
        web_events["timestamp"],
        errors="coerce"
    )


    print("\n===== NORMALISED WEB EVENTS =====")

    print(
        web_events[
            [
                "timestamp",
                "session_id",
                "customer_id",
                "event_type",
                "product_id"
            ]
        ].head(10)
    )


# ============================================================
# 25. WEB CUSTOMER FEATURES
# ============================================================

print("\n" + "=" * 70)
print("WEB CUSTOMER FEATURES")
print("=" * 70)


if (
    len(web_events) > 0
    and "customer_id" in web_events.columns
):

    # --------------------------------------------------------
    # Sessions count
    #
    # Number of unique sessions for each customer.
    # --------------------------------------------------------

    sessions = (
        web_events
        .groupby("customer_id")
        ["session_id"]
        .nunique()
        .reset_index(
            name="sessions_count"
        )
    )


    # --------------------------------------------------------
    # Identify sessions that contain add_to_cart
    # --------------------------------------------------------

    cart_sessions = (
        web_events[
            web_events["event_type"]
            == "add_to_cart"
        ]
        [
            [
                "customer_id",
                "session_id"
            ]
        ]
        .drop_duplicates()
    )


    # --------------------------------------------------------
    # Identify sessions that contain purchase
    # --------------------------------------------------------

    purchase_sessions = (
        web_events[
            web_events["event_type"]
            == "purchase"
        ]
        [
            [
                "customer_id",
                "session_id"
            ]
        ]
        .drop_duplicates()
    )


    # --------------------------------------------------------
    # Count carts and purchased carts
    # --------------------------------------------------------

    cart_counts = (
        cart_sessions
        .groupby("customer_id")
        .size()
        .reset_index(
            name="cart_sessions"
        )
    )


    purchased_cart_counts = (
        cart_sessions
        .merge(
            purchase_sessions,
            on=[
                "customer_id",
                "session_id"
            ],
            how="inner"
        )
        .groupby("customer_id")
        .size()
        .reset_index(
            name="purchased_cart_sessions"
        )
    )


    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    web_features = sessions.merge(
        cart_counts,
        on="customer_id",
        how="left"
    )

    web_features = web_features.merge(
        purchased_cart_counts,
        on="customer_id",
        how="left"
    )


    web_features[
        [
            "cart_sessions",
            "purchased_cart_sessions"
        ]
    ] = web_features[
        [
            "cart_sessions",
            "purchased_cart_sessions"
        ]
    ].fillna(0)


    # --------------------------------------------------------
    # Cart abandonment rate
    #
    # abandoned cart sessions =
    # cart sessions - purchased cart sessions
    #
    # rate =
    # abandoned / total cart sessions
    # --------------------------------------------------------

    web_features["cart_abandon_rate"] = np.where(
        web_features["cart_sessions"] > 0,

        (
            web_features["cart_sessions"]
            - web_features["purchased_cart_sessions"]
        )
        / web_features["cart_sessions"],

        0
    )


    web_features = web_features[
        [
            "customer_id",
            "sessions_count",
            "cart_abandon_rate"
        ]
    ]


else:

    web_features = pd.DataFrame(
        columns=[
            "customer_id",
            "sessions_count",
            "cart_abandon_rate"
        ]
    )


print("\n===== WEB FEATURES =====")

print(
    web_features.head(10)
)

print(
    "\nWeb feature rows:",
    len(web_features)
)


# ============================================================
# 26. CUSTOMER ORDER AGGREGATES
# ============================================================

print("\n" + "=" * 70)
print("CUSTOMER ORDER AGGREGATES")
print("=" * 70)

order_features = (
    fact_sales
    .groupby("customer_id")
    .agg(
        total_orders=(
            "order_id",
            "nunique"
        ),

        total_spend_usd=(
            "net_revenue",
            "sum"
        ),

        avg_order_value=(
            "net_revenue",
            "mean"
        ),

        returned_orders=(
            "is_returned",
            "sum"
        ),

        last_order_date=(
            "order_date",
            "max"
        )
    )
    .reset_index()
)


# Return rate

order_features["return_rate"] = np.where(
    order_features["total_orders"] > 0,

    order_features["returned_orders"]
    / order_features["total_orders"],

    0
)


# ============================================================
# 27. DAYS SINCE LAST ORDER
# ============================================================

reference_date = fact_sales["order_date"].max()

order_features["days_since_last_order"] = (
    reference_date
    - order_features["last_order_date"]
).dt.days


order_features = order_features[
    [
        "customer_id",
        "total_orders",
        "total_spend_usd",
        "avg_order_value",
        "return_rate",
        "days_since_last_order"
    ]
]


# ============================================================
# 28. FEATURE CUSTOMERS
# ============================================================

print("\n" + "=" * 70)
print("BUILDING FEATURE_CUSTOMERS")
print("=" * 70)


# Start from dim_customers.
#
# This guarantees exactly one row per customer,
# even if that customer has no orders or web events.

feature_customers = dim_customers[
    [
        "customer_id"
    ]
].copy()

logger.info(
    "FEATURE_CUSTOMERS created | rows=%s",
    len(feature_customers)
)
# ------------------------------------------------------------
# Add order features
# ------------------------------------------------------------

feature_customers = feature_customers.merge(
    order_features,
    on="customer_id",
    how="left",
    validate="one_to_one"
)


# ------------------------------------------------------------
# Add web features
# ------------------------------------------------------------

feature_customers = feature_customers.merge(
    web_features,
    on="customer_id",
    how="left",
    validate="one_to_one"
)


# ------------------------------------------------------------
# Customers without orders
# ------------------------------------------------------------

numeric_order_columns = [
    "total_orders",
    "total_spend_usd",
    "avg_order_value",
    "return_rate",
    "days_since_last_order"
]

for column in numeric_order_columns:

    feature_customers[column] = (
        feature_customers[column]
        .fillna(0)
    )


# ------------------------------------------------------------
# Customers without web activity
# ------------------------------------------------------------

feature_customers["sessions_count"] = (
    feature_customers["sessions_count"]
    .fillna(0)
)

feature_customers["cart_abandon_rate"] = (
    feature_customers["cart_abandon_rate"]
    .fillna(0)
)


# ------------------------------------------------------------
# Final ML-ready columns
# ------------------------------------------------------------

feature_customers = feature_customers[
    [
        "customer_id",
        "total_orders",
        "total_spend_usd",
        "avg_order_value",
        "return_rate",
        "days_since_last_order",
        "sessions_count",
        "cart_abandon_rate"
    ]
].copy()


print("\n===== FEATURE_CUSTOMERS =====")

print(
    feature_customers.head(10)
)

print(
    "\nShape:",
    feature_customers.shape
)


# ============================================================
# 29. REJECT LOG
# ============================================================

print("\n" + "=" * 70)
print("REJECT LOG")
print("=" * 70)

reject_log.to_csv(
    OUTPUT_DIR / "reject_log.csv",
    index=False
)

print(
    "Total rejected:",
    len(reject_log)
)

if len(reject_log) > 0:

    print(
        reject_log["reject_reason"]
        .value_counts()
    )


# ============================================================
# 30. BUILD DIM PRODUCTS
# ============================================================

print("\n" + "=" * 70)
print("BUILDING DIM_PRODUCTS")
print("=" * 70)


dim_products = products[
    [
        "product_id",
        "product_name",
        "category",
        "unit_price",
        "currency"
    ]
].copy()


dim_products = dim_products.merge(
    rates[
        [
            "currency",
            "rate_to_usd"
        ]
    ],
    on="currency",
    how="left",
    validate="many_to_one"
)


dim_products["unit_price_usd"] = (
    dim_products["unit_price"]
    * dim_products["rate_to_usd"]
)


dim_products["price_tier"] = np.select(
    [
        dim_products["unit_price_usd"] < 50,
        dim_products["unit_price_usd"] < 100
    ],
    [
        "low",
        "medium"
    ],
    default="high"
)


dim_products = dim_products[
    [
        "product_id",
        "product_name",
        "category",
        "unit_price",
        "currency",
        "unit_price_usd",
        "price_tier"
    ]
].copy()


print(
    dim_products.head()
)
logger.info(
    "DIM_PRODUCTS created | rows=%s",
    len(dim_products)
)

# ============================================================
# 31. SAVE OUTPUTS
# ============================================================

print("\n" + "=" * 70)
print("SAVING OUTPUTS")
print("=" * 70)


fact_sales.to_csv(
    OUTPUT_DIR / "fact_sales.csv",
    index=False
)

dim_customers.to_csv(
    OUTPUT_DIR / "dim_customers.csv",
    index=False
)

dim_products.to_csv(
    OUTPUT_DIR / "dim_products.csv",
    index=False
)

feature_customers.to_csv(
    OUTPUT_DIR / "feature_customers.csv",
    index=False
)

# ============================================================
# SQLITE DATABASE
# ============================================================

print("\n" + "=" * 70)
print("LOADING SQLITE DATABASE")
print("=" * 70)

connection = sqlite3.connect(DB_PATH)

fact_sales.to_sql(
    "fact_sales",
    connection,
    if_exists="replace",
    index=False
)

dim_customers.to_sql(
    "dim_customers",
    connection,
    if_exists="replace",
    index=False
)

dim_products.to_sql(
    "dim_products",
    connection,
    if_exists="replace",
    index=False
)

feature_customers.to_sql(
    "feature_customers",
    connection,
    if_exists="replace",
    index=False
)

reject_log.to_sql(
    "reject_log",
    connection,
    if_exists="replace",
    index=False
)

connection.close()

print("SQLite database created:")
print(DB_PATH)
# ============================================================
# 32. FINAL VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL VALIDATION")
print("=" * 70)


print(
    "\nFACT_SALES:",
    fact_sales.shape
)

print(
    "DIM_CUSTOMERS:",
    dim_customers.shape
)

print(
    "DIM_PRODUCTS:",
    dim_products.shape
)

print(
    "FEATURE_CUSTOMERS:",
    feature_customers.shape
)

print(
    "REJECT_LOG:",
    reject_log.shape
)


# ------------------------------------------------------------
# Columns
# ------------------------------------------------------------

print("\n===== FACT_SALES COLUMNS =====")

print(
    fact_sales.columns.tolist()
)


print("\n===== DIM_CUSTOMERS COLUMNS =====")

print(
    dim_customers.columns.tolist()
)


print("\n===== DIM_PRODUCTS COLUMNS =====")

print(
    dim_products.columns.tolist()
)


print("\n===== FEATURE_CUSTOMERS COLUMNS =====")

print(
    feature_customers.columns.tolist()
)


# ------------------------------------------------------------
# Duplicate checks
# ------------------------------------------------------------

print("\n===== DUPLICATE CHECKS =====")

print(
    "Duplicate fact order IDs:",
    fact_sales["order_id"].duplicated().sum()
)

print(
    "Duplicate customer IDs:",
    dim_customers["customer_id"].duplicated().sum()
)

print(
    "Duplicate product IDs:",
    dim_products["product_id"].duplicated().sum()
)

print(
    "Duplicate feature customer IDs:",
    feature_customers["customer_id"].duplicated().sum()
)


# ------------------------------------------------------------
# Business checks
# ------------------------------------------------------------

print("\n===== BUSINESS RULE CHECKS =====")

print(
    "Missing amount_usd:",
    fact_sales["amount_usd"].isna().sum()
)

print(
    "Missing price_tier:",
    fact_sales["price_tier"].isna().sum()
)

print(
    "Missing is_returned:",
    fact_sales["is_returned"].isna().sum()
)

print(
    "Missing unit_price_usd:",
    dim_products["unit_price_usd"].isna().sum()
)

print(
    "Missing product price_tier:",
    dim_products["price_tier"].isna().sum()
)


# ------------------------------------------------------------
# Web feature checks
# ------------------------------------------------------------

print("\n===== WEB FEATURE CHECKS =====")

print(
    "Missing sessions_count:",
    feature_customers["sessions_count"].isna().sum()
)

print(
    "Missing cart_abandon_rate:",
    feature_customers["cart_abandon_rate"].isna().sum()
)


# ============================================================
# 33. SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("PIPELINE COMPLETE")
print("=" * 70)

print(
    f"""
Clean orders       : {len(fact_sales)}
Rejected orders    : {len(reject_log)}
Customers          : {len(dim_customers)}
Products           : {len(dim_products)}
ML customers       : {len(feature_customers)}

Output directory:
{OUTPUT_DIR}
"""
)

print("Generated files:")

for file in sorted(OUTPUT_DIR.iterdir()):

    if file.is_file():

        print(
            " -",
            file.name
        )
        