import pandas as pd


# ============================================================
# 1. READ EXCHANGE RATES
# ============================================================

rates = pd.read_json("data/exchange_rates.json")


# ============================================================
# 2. BASIC INSPECTION
# ============================================================

print("===== EXCHANGE RATES =====")
print(rates)

print("\n===== SHAPE =====")
print(rates.shape)

print("\n===== COLUMNS =====")
print(rates.columns)

print("\n===== DATA TYPES =====")
print(rates.dtypes)

print("\n===== MISSING VALUES =====")
print(rates.isna().sum())

print("\n===== DUPLICATE ROWS =====")
print(rates.duplicated().sum())