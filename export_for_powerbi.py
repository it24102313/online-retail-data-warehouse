"""
Power BI Connection Helper
Exports all 5 warehouse tables to CSV so Power BI can import them
directly without needing the ODBC driver.
This is a backup method if ODBC connection fails.
"""
import sqlite3
import pandas as pd
import os

DB_PATH    = "online_retail_dw.db"
EXPORT_DIR = "powerbi_export"
os.makedirs(EXPORT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)

TABLES = ["dim_date","dim_customer","dim_product","dim_location","fact_sales"]

print("Exporting warehouse tables for Power BI...")
print("=" * 50)
for table in TABLES:
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    out = os.path.join(EXPORT_DIR, f"{table}.csv")
    df.to_csv(out, index=False)
    size_kb = os.path.getsize(out) / 1024
    print(f"  {table:<20} {len(df):>8,} rows  -> {out}  ({size_kb:.0f} KB)")

conn.close()
print("=" * 50)
print(f"\nAll tables exported to: {EXPORT_DIR}/")
print("In Power BI: Get Data -> Text/CSV -> import each file")
