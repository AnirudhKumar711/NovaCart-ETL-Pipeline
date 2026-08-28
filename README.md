# NovaCart-ETL-Pipeline

A complete ETL (Extract, Transform, Load) pipeline built using Python, Pandas, SQLite, SQL, and Streamlit.

The project processes e-commerce data from multiple sources, validates and cleans the data, performs transformations and enrichment, creates analytics-ready datasets, loads the results into SQLite, and provides a Streamlit dashboard for business analysis.

---

## Project Overview

NovaCart is an e-commerce data processing project designed to demonstrate a complete ETL workflow.

The pipeline handles:

- Data ingestion from CSV, JSON, TSV, and log files
- Data cleaning and validation
- Duplicate detection and removal
- Referential integrity validation
- Missing-value handling
- Currency conversion
- Date standardization
- Product and customer enrichment
- Return processing
- Web-event processing
- Customer-level feature engineering
- Reject logging
- Pipeline logging
- SQLite database loading
- SQL-based business analysis
- Streamlit dashboard visualization

---

## Technology Stack

- Python 3
- Pandas
- NumPy
- SQLite
- SQL
- Streamlit
- Git / GitHub

---

## Project Structure

```text
NovaCart-ETL-Pipeline/
│
├── data/
│   ├── customers.json
│   ├── exchange_rates.json
│   ├── orders.csv
│   ├── products.csv
│   ├── returns.tsv
│   └── web_events.log
│
├── src/
│   ├── dashboard.py
│   ├── inspect_customers.py
│   ├── inspect_exchange_rates.py
│   ├── inspect_orders.py
│   ├── inspect_products.py
│   ├── pipeline.py
│   └── sql_queries.py
│
├── output/
│   ├── dim_customers.csv
│   ├── dim_products.csv
│   ├── fact_sales.csv
│   ├── feature_customers.csv
│   ├── novacart.db
│   ├── pipeline.log
│   └── reject_log.csv

----------------------------------------------------------------------------------------------------------------------------------------------
Source Data
Orders

orders.csv

Contains transaction-level information:

order_id
customer_id
product_id
quantity
amount
currency
order_date
Customers

customers.json

Contains customer information including:

customer_id
name
email
signup_date
address
is_premium

Nested address information is transformed into:

city
country
Products

products.csv

Contains:

product_id
product_name
category
unit_price
currency
Exchange Rates

exchange_rates.json

Contains currency conversion rates to USD.

Supported currencies:

USD
EUR
GBP
INR
Returns

returns.tsv

Used to determine whether an order was returned.

Web Events

web_events.log

Contains customer web activity:

timestamp
session
user
event
product

Events are normalized into:

timestamp
session_id
customer_id
event_type
product_id
ETL Pipeline
1. Extract

The pipeline reads data from:

CSV files
JSON files
TSV files
Web event log files

The datasets are initially inspected for:

Shape
Columns
Data types
Missing values
Duplicate records
2. Transform
Order ID Validation

Order IDs are trimmed and checked for duplicates.

Results:

Orders after cleaning: 900
Duplicate order IDs: 0
Customer ID Validation

Order customer IDs are validated against the customer dimension.

Invalid records are rejected instead of being silently removed.

Results:

Missing customer IDs: 53
Invalid customer IDs: 0
Quantity Validation

Orders must have:

quantity > 0

Invalid quantities include:

0
-1
-2

Rejected records:

37
Amount Validation

The pipeline checks for:

Missing amounts
Negative amounts

Results:

Missing amounts: 25
Negative amounts: 0
Currency Validation

Orders are validated against the supported currencies:

EUR
GBP
INR
USD

Invalid currency records:

0
Currency Conversion

Order amounts are converted to USD using:

amount_usd = amount × rate_to_usd

Product prices are also converted:

unit_price_usd = unit_price × rate_to_usd
Date Standardization

Multiple source date formats are converted into a consistent datetime format.

Examples:

2026-04-28
20/04/2026
03-20-2026

After conversion:

datetime64

Invalid or missing dates:

0
Product Validation

Order product IDs are validated against products.csv.

Results:

Products: 60
Invalid product IDs: 0

Product information is then joined with valid orders.

Country Standardization

Country values are mapped to canonical names.

Examples:

U.S.A → USA
United States → USA
United Kingdom → UK
IN → India
DE → Germany
Price Tier

Products are categorized based on their USD unit price:

low
medium
high

The price tier is included in both the product dimension and sales fact table.

Return Processing

Return information is joined with sales using a left join.

This produces:

is_returned

for every valid sale.

Data Quality / Reject Handling

Invalid records are stored separately in:

output/reject_log.csv

Final rejected records:

115

Breakdown:

Rejection Reason	Count
Missing customer ID	53
Quantity ≤ 0	37
Missing amount	25
Total	115

Valid sales:

785
Output Data Model
fact_sales

Central transaction fact table.

order_id
customer_id
product_id
quantity
amount
currency
amount_usd
order_date
price_tier
net_revenue
is_returned

Final size:

785 × 11
dim_customers

Standardized customer dimension.

customer_id
name
email_present
city
country
is_premium
signup_date

Final size:

120 × 7
dim_products

Standardized product dimension.

product_id
product_name
category
unit_price
currency
unit_price_usd
price_tier

Final size:

60 × 7
feature_customers

ML-ready customer-level feature table.

Model training is not included in the current project, but the feature dataset is prepared for future use.

customer_id
total_orders
total_spend_usd
avg_order_value
return_rate
days_since_last_order
sessions_count
cart_abandon_rate

Final size:

120 × 8
Web Event Features

Web events are used to generate customer-level behavioral features.

Sessions Count

Number of unique sessions for each customer.

Cart Abandonment Rate

Calculated using cart sessions and purchased cart sessions:

abandoned cart sessions
=
cart sessions - purchased cart sessions

cart abandonment rate
=
abandoned cart sessions / cart sessions

These features are merged into feature_customers.

Logging

The pipeline creates a separate execution log:

output/pipeline.log

This provides information about pipeline execution and processing stages.

SQLite Database

The final ETL outputs are loaded into:

output/novacart.db

The SQLite database contains:

fact_sales
dim_customers
dim_products
feature_customers
reject_log

The database is populated using Pandas to_sql().

SQL Analysis

Business metrics are calculated using SQL against the SQLite database.

Total Revenue
$345,603.53
Return Rate
13.38%
Revenue by Price Tier
Price Tier	Revenue
High	$319,833.50
Medium	$17,306.37
Low	$8,463.67
Revenue by Country

The country analysis uses a SQL JOIN between:

fact_sales
      ↓
dim_customers

Results:

Country	Revenue
USA	$112,218.42
Germany	$87,286.50
India	$76,882.93
UK	$69,215.68
Revenue Over Time

Revenue is aggregated by individual order date using SQL and displayed as a line chart.

Dashboard

The project includes a Streamlit dashboard.

Run:

streamlit run src/dashboard.py

The dashboard contains the five required views:

Total Revenue — KPI
Return Rate — KPI
Revenue by Price Tier — Bar Chart
Revenue by Country — Bar Chart
Revenue Over Time by Order Date — Line Chart

The dashboard reads from the SQLite database rather than directly from the source files.

SQL is responsible for the business aggregations.

Running the Project
1. Clone the repository
git clone https://github.com/AnirudhKumar711/NovaCart-ETL-Pipeline.git
cd NovaCart-ETL-Pipeline
2. Create a virtual environment
python3 -m venv venv
3. Activate the virtual environment

Linux/macOS:

source venv/bin/activate
4. Install dependencies
pip install pandas numpy streamlit
5. Run the ETL pipeline
python src/pipeline.py

This generates the processed datasets and SQLite database inside:

output/
6. Run SQL analysis
python src/sql_queries.py
7. Run the dashboard
streamlit run src/dashboard.py
Final Pipeline Flow

             SOURCE DATA
                  │
     ┌────────────┼────────────┐
     ↓            ↓            ↓
  Orders      Customers     Products
     │            │            │
     └────────────┼────────────┘
                  ↓
          DATA VALIDATION
                  │
        ┌─────────┴─────────┐
        ↓                   ↓
   Valid Records        Reject Log
        │
        ↓
    TRANSFORMATION
        │
   ┌────┼─────────────┐
   ↓    ↓             ↓
Currency Dates     Enrichment
   │    │             │
   └────┼─────────────┘
        ↓
   WEB EVENT FEATURES
        │
        ↓
   DATA MODELING
        │
   ┌────┼───────────────┐
   ↓    ↓       ↓       ↓
 fact  dim     dim    features
sales customers products customers
        │
        ↓
      SQLite
        │
        ↓
    SQL Analysis
        │
        ↓
 Streamlit Dashboard

Final Results
Clean orders       : 785
Rejected orders    : 115
Customers          : 120
Products           : 60
ML customers       : 120

The pipeline also performs final validation for:

Duplicate order IDs
Duplicate customer IDs
Duplicate product IDs
Missing calculated fields
Missing web features
Business rule compliance
Future Improvements

Potential extensions include:

Customer churn prediction
Machine learning model training
Additional dashboard filters
Product performance analysis
Customer segmentation
Automated pipeline scheduling
Cloud database deployment
Automated data-quality monitoring

Author-
Anirudh Kumar
│
├── .gitignore
└── README.md
