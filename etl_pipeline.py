"""
============================================================
Online Retail Data Warehouse - Complete ETL Pipeline
============================================================
Dataset  : Online Retail II (UCI ML Repository)
Target   : SQLite Data Warehouse (online_retail_dw.db)
Tools    : Python 3.x, pandas, openpyxl, sqlite3
============================================================
"""

import os
import json
import sqlite3
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DATA_DIR        = os.path.join(BASE_DIR, "data")
DB_PATH         = os.path.join(BASE_DIR, "online_retail_dw.db")
EXCEL_FILE      = os.path.join(DATA_DIR, "online_retail_II.xlsx")
CUSTOMER_CSV    = os.path.join(DATA_DIR, "customer_demographics.csv")
PRODUCT_JSON    = os.path.join(DATA_DIR, "product_categories.json")

print("=" * 60)
print("Online Retail ETL Pipeline Starting...")
print(f"Timestamp: {datetime.now()}")
print("=" * 60)

# ============================================================
# STEP 1: EXTRACT
# ============================================================
print("\n[EXTRACT] Reading source data...")

# Extract Sheet 1: 2009-2010
print("  -> Reading Excel Sheet 1 (2009-2010)...")
df_2009 = pd.read_excel(EXCEL_FILE, sheet_name="Year 2009-2010", dtype=str)
print(f"     Records loaded: {len(df_2009):,}")

# Extract Sheet 2: 2010-2011
print("  -> Reading Excel Sheet 2 (2010-2011)...")
df_2010 = pd.read_excel(EXCEL_FILE, sheet_name="Year 2010-2011", dtype=str)
print(f"     Records loaded: {len(df_2010):,}")

# Combine both sheets
df_raw = pd.concat([df_2009, df_2010], ignore_index=True)
raw_count = len(df_raw)
print(f"  -> Combined raw records: {raw_count:,}")

# Extract Customer Demographics CSV
print("  -> Reading Customer Demographics CSV...")
df_customers = pd.read_csv(CUSTOMER_CSV, dtype=str)
print(f"     Customer records: {len(df_customers):,}")

# Extract Product Categories JSON
print("  -> Reading Product Categories JSON...")
with open(PRODUCT_JSON, "r") as f:
    product_data = json.load(f)
df_products_ref = pd.DataFrame(product_data)
print(f"     Product reference records: {len(df_products_ref):,}")

# ============================================================
# STEP 2: TRANSFORM
# ============================================================
print("\n[TRANSFORM] Applying data transformations...")

df = df_raw.copy()

# --- 2.1 Rename columns to standard names ---
df.columns = ["invoice_no", "stock_code", "description",
              "quantity", "invoice_date", "unit_price",
              "customer_id", "country"]

# --- 2.2 Data Type Conversion ---
print("  -> Converting data types...")
df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
df["quantity"]     = pd.to_numeric(df["quantity"], errors="coerce")
df["unit_price"]   = pd.to_numeric(df["unit_price"], errors="coerce")
df["customer_id"]  = df["customer_id"].str.strip()
df["description"]  = df["description"].str.strip()
df["country"]      = df["country"].str.strip()
df["invoice_no"]   = df["invoice_no"].str.strip()
df["stock_code"]   = df["stock_code"].str.strip()

# --- 2.3 Missing Value Handling ---
print("  -> Handling missing values...")
before_null_drop = len(df)
df = df.dropna(subset=["customer_id", "invoice_date"])
df = df[df["customer_id"] != ""]
after_null_drop = len(df)
print(f"     Dropped {before_null_drop - after_null_drop:,} rows with null CustomerID/Date")

# Drop null descriptions
desc_null = df["description"].isna().sum()
df = df.dropna(subset=["description"])
print(f"     Dropped {desc_null:,} rows with null Description")

# --- 2.4 Remove Duplicates ---
print("  -> Removing duplicates...")
before_dedup = len(df)
df = df.drop_duplicates()
after_dedup = len(df)
print(f"     Removed {before_dedup - after_dedup:,} duplicate rows")

# --- 2.5 Handle Returns (negative quantities / 'C' invoices) ---
print("  -> Separating returns transactions...")
mask_returns = (df["quantity"] < 0) | (df["invoice_no"].str.startswith("C"))
df_returns = df[mask_returns].copy()
df = df[~mask_returns].copy()
print(f"     Sales records: {len(df):,}")
print(f"     Return records: {len(df_returns):,}")

# --- 2.6 Filter invalid unit prices ---
df = df[df["unit_price"] > 0]
df = df[df["quantity"] > 0]

# --- 2.7 Country Standardisation ---
print("  -> Standardising country names...")
country_map = {
    "EIRE": "Ireland",
    "RSA": "South Africa",
    "Channel Islands": "United Kingdom",
    "Unspecified": "Unknown",
    "European Community": "Unknown",
    "West Indies": "Caribbean"
}
df["country"] = df["country"].replace(country_map)
df_returns["country"] = df_returns["country"].replace(country_map)

# --- 2.8 Derived Attributes ---
print("  -> Creating derived attributes...")
df["total_amount"]  = df["quantity"] * df["unit_price"]
df["year"]          = df["invoice_date"].dt.year
df["month"]         = df["invoice_date"].dt.month
df["month_name"]    = df["invoice_date"].dt.strftime("%B")
df["day"]           = df["invoice_date"].dt.day
df["quarter"]       = df["invoice_date"].dt.quarter
df["weekday"]       = df["invoice_date"].dt.strftime("%A")
df["week_number"]   = df["invoice_date"].dt.isocalendar().week.astype(int)
df["is_weekend"]    = df["invoice_date"].dt.dayofweek.isin([5, 6]).astype(int)
df["date_id"]       = df["invoice_date"].dt.strftime("%Y%m%d").astype(int)

# --- 2.9 Data Enrichment: Merge Customer Demographics ---
print("  -> Enriching with customer demographics...")
df_customers.columns = ["customer_id", "segment", "region"]
df = df.merge(df_customers, on="customer_id", how="left")
df["segment"] = df["segment"].fillna("B2C")
df["region"]  = df["region"].fillna("Unknown")

# --- 2.10 Data Enrichment: Merge Product Categories ---
print("  -> Enriching with product categories...")
# Select only the columns we need (JSON now also contains description column)
prod_ref_cols = [c for c in df_products_ref.columns if c in
                 ["stock_code","category","subcategory","is_gift"]]
df_products_ref = df_products_ref[prod_ref_cols]
df = df.merge(df_products_ref, on="stock_code", how="left")
df["category"]    = df["category"].fillna("Home Decor")
df["subcategory"] = df["subcategory"].fillna("General")
df["is_gift"]     = df["is_gift"].fillna(0).astype(int)

print(f"\n  [TRANSFORM COMPLETE] Clean records: {len(df):,}")

# ============================================================
# STEP 3: BUILD DIMENSION DATAFRAMES
# ============================================================
print("\n[BUILD DIMENSIONS] Constructing dimension tables...")

# --- dim_date ---
print("  -> Building dim_date...")
date_records = df[["date_id", "invoice_date", "day", "month", "month_name",
                    "quarter", "year", "weekday", "week_number", "is_weekend"]].copy()
date_records = date_records.rename(columns={"invoice_date": "full_date"})
date_records["is_holiday"] = 0  # simplified; extend with UK holiday calendar
dim_date = date_records.drop_duplicates(subset=["date_id"]).reset_index(drop=True)
print(f"     dim_date rows: {len(dim_date):,}")

# --- dim_customer ---
print("  -> Building dim_customer...")
customer_records = df[["customer_id", "country", "segment", "region"]].copy()
customer_records = customer_records.drop_duplicates(subset=["customer_id"]).reset_index(drop=True)
customer_records.insert(0, "cust_sk", range(1, len(customer_records) + 1))
customer_records = customer_records.rename(columns={
    "customer_id": "customer_code",
    "cust_sk": "customer_sk"
})
# Build surrogate key mapping
cust_map = dict(zip(customer_records["customer_code"], customer_records["customer_sk"]))
print(f"     dim_customer rows: {len(customer_records):,}")

# --- dim_product ---
print("  -> Building dim_product...")
product_records = df[["stock_code", "description", "category", "subcategory", "is_gift"]].copy()
product_records = product_records.drop_duplicates(subset=["stock_code"]).reset_index(drop=True)
product_records.insert(0, "product_sk", range(1, len(product_records) + 1))
prod_map = dict(zip(product_records["stock_code"], product_records["product_sk"]))
print(f"     dim_product rows: {len(product_records):,}")

# --- dim_location ---
print("  -> Building dim_location...")
region_continent_map = {
    "Western Europe": "Europe", "Northern Europe": "Europe",
    "Southern Europe": "Europe", "Eastern Europe": "Europe",
    "North America": "North America", "South America": "South America",
    "Middle East": "Asia", "South Asia": "Asia",
    "East Asia": "Asia", "Southeast Asia": "Asia",
    "Oceania": "Oceania", "Africa": "Africa",
    "Unknown": "Unknown", "Caribbean": "Americas"
}
location_records = df[["country", "region"]].copy()
location_records = location_records.drop_duplicates().reset_index(drop=True)
location_records["continent"] = location_records["region"].map(region_continent_map).fillna("Unknown")
location_records.insert(0, "location_sk", range(1, len(location_records) + 1))
loc_map = dict(zip(zip(location_records["country"], location_records["region"]),
                   location_records["location_sk"]))
print(f"     dim_location rows: {len(location_records):,}")

# ============================================================
# STEP 4: BUILD FACT TABLE
# ============================================================
print("\n[BUILD FACT TABLE] Constructing fact_sales...")

fact = df[["invoice_no", "date_id", "customer_id", "stock_code",
           "country", "region", "quantity", "unit_price", "total_amount"]].copy()

# Map surrogate keys
fact["customer_sk"] = fact["customer_id"].map(cust_map)
fact["product_sk"]  = fact["stock_code"].map(prod_map)
fact["location_sk"] = [loc_map.get((c, r), None) for c, r in zip(fact["country"], fact["region"])]
fact["discount_amount"] = 0.0

fact_sales = fact[["invoice_no", "date_id", "customer_sk", "product_sk",
                    "location_sk", "quantity", "unit_price",
                    "total_amount", "discount_amount"]].copy()
fact_sales = fact_sales.dropna(subset=["customer_sk", "product_sk", "location_sk"])
fact_sales = fact_sales.rename(columns={
    "customer_sk": "customer_id",
    "product_sk":  "product_id",
    "location_sk": "location_id"
})
print(f"     fact_sales rows: {len(fact_sales):,}")

# ============================================================
# STEP 5: LOAD INTO SQLITE DATA WAREHOUSE
# ============================================================
print("\n[LOAD] Loading data into SQLite Data Warehouse...")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Execute schema
with open(os.path.join(BASE_DIR, "schema.sql"), "r") as f:
    schema_sql = f.read()
conn.executescript(schema_sql)
print("  -> Schema created/verified")

# Load dim_date
dim_date_load = dim_date[["date_id", "full_date", "day", "month", "month_name",
                            "quarter", "year", "weekday", "week_number",
                            "is_weekend", "is_holiday"]].copy()
dim_date_load["full_date"] = dim_date_load["full_date"].astype(str)
dim_date_load.to_sql("dim_date", conn, if_exists="replace", index=False)
print(f"  -> dim_date loaded: {len(dim_date_load):,} rows")

# Load dim_customer
dim_cust_load = customer_records.rename(columns={"customer_sk": "customer_id"})
dim_cust_load.to_sql("dim_customer", conn, if_exists="replace", index=False)
print(f"  -> dim_customer loaded: {len(dim_cust_load):,} rows")

# Load dim_product
dim_prod_load = product_records.rename(columns={"product_sk": "product_id"})
dim_prod_load.to_sql("dim_product", conn, if_exists="replace", index=False)
print(f"  -> dim_product loaded: {len(dim_prod_load):,} rows")

# Load dim_location
dim_loc_load = location_records.rename(columns={"location_sk": "location_id"})
dim_loc_load.to_sql("dim_location", conn, if_exists="replace", index=False)
print(f"  -> dim_location loaded: {len(dim_loc_load):,} rows")

# Load fact_sales
fact_sales.to_sql("fact_sales", conn, if_exists="replace", index=False)
print(f"  -> fact_sales loaded: {len(fact_sales):,} rows")

conn.commit()

# ============================================================
# STEP 6: VALIDATION
# ============================================================
print("\n[VALIDATION] Running post-load checks...")

checks = [
    ("dim_date row count",    "SELECT COUNT(*) FROM dim_date"),
    ("dim_customer row count","SELECT COUNT(*) FROM dim_customer"),
    ("dim_product row count", "SELECT COUNT(*) FROM dim_product"),
    ("dim_location row count","SELECT COUNT(*) FROM dim_location"),
    ("fact_sales row count",  "SELECT COUNT(*) FROM fact_sales"),
    ("NULL date_id in fact",  "SELECT COUNT(*) FROM fact_sales WHERE date_id IS NULL"),
    ("NULL customer in fact", "SELECT COUNT(*) FROM fact_sales WHERE customer_id IS NULL"),
    ("NULL product in fact",  "SELECT COUNT(*) FROM fact_sales WHERE product_id IS NULL"),
    ("Total Revenue",         "SELECT ROUND(SUM(total_amount),2) FROM fact_sales"),
    ("Total Orders",          "SELECT COUNT(DISTINCT invoice_no) FROM fact_sales"),
    ("Total Customers",       "SELECT COUNT(DISTINCT customer_id) FROM fact_sales"),
]

print(f"\n{'Check':<35} {'Result':>15}")
print("-" * 52)
for label, query in checks:
    result = cursor.execute(query).fetchone()[0]
    print(f"{label:<35} {str(result):>15}")

conn.close()
print("\n" + "=" * 60)
print("ETL Pipeline Completed Successfully!")
print(f"Database saved to: {DB_PATH}")
print("=" * 60)
