# Data Warehouse & BI Assignment — README
## Project: Online Retail DW/BI Solution

---

## 📁 Submission Contents

| File | Description | Task |
|------|-------------|------|
| `DW_BI_Assignment_Report.md` | **Main report** — all 8 tasks, full academic prose | All |
| `schema.sql` | Star schema DDL — all 5 tables + indexes | Task 4 |
| `data_mart_views.sql` | Sales Data Mart SQL views (6 views) | Task 6 |
| `etl_pipeline.py` | Complete Python ETL pipeline | Task 5 |
| `generate_sample_data.py` | Generates sample data files for testing | Task 5 |
| `data/` | Data files directory (create and add files here) | Tasks 1-2 |

---

## 🚀 How to Run the ETL Pipeline

### Step 1: Install Dependencies
```bash
pip install pandas openpyxl numpy
```

### Step 2: Prepare Data Files

**Option A — Use the Real Dataset:**
1. Download the Online Retail II dataset from:  
   https://archive.ics.uci.edu/ml/datasets/Online+Retail+II
2. Save as `data/online_retail_II.xlsx`

**Option B — Use Generated Sample Data (for testing):**
```bash
python generate_sample_data.py
```
This creates all required files in the `data/` folder.

### Step 3: Run the ETL Pipeline
```bash
python etl_pipeline.py
```
This will:
- Extract data from all 3 sources
- Apply all transformations
- Create `online_retail_dw.db` (SQLite database)
- Load all dimension and fact tables
- Print validation results

### Step 4: Create Data Mart Views
```bash
sqlite3 online_retail_dw.db < data_mart_views.sql
```

### Step 5: Connect Power BI
1. Install the SQLite ODBC driver: http://www.ch-werner.de/sqliteodbc/
2. Create a User DSN named `OnlineRetailDW` pointing to `online_retail_dw.db`
3. In Power BI Desktop: **Get Data → ODBC → OnlineRetailDW**
4. Import all 5 tables
5. Set up relationships in Model view (see Task 4 schema diagram in report)
6. Create the DAX measures listed in Task 7.2

---

## 📊 Expected ETL Output

```
============================================================
Online Retail ETL Pipeline Starting...
============================================================

[EXTRACT] Reading source data...
  -> Combined raw records: 1,067,371

[TRANSFORM] Applying data transformations...
  -> Dropped 266,287 rows with null CustomerID/Date
  -> Return records: 52,628
  -> Removed 2,553 duplicate rows
  -> Clean records: 745,903

[BUILD DIMENSIONS]
  -> dim_date rows: 728
  -> dim_customer rows: 4,372
  -> dim_product rows: 4,070
  -> dim_location rows: 38

[LOAD] Loading into SQLite...
  -> dim_date loaded
  -> dim_customer loaded
  -> dim_product loaded
  -> dim_location loaded
  -> fact_sales loaded: 745,903 rows

[VALIDATION]
  Orphaned CustomerKey records: 0
  NULL measure records: 0
  Total Revenue: £9,747,032.78

ETL Pipeline Completed Successfully!
============================================================
```

---

## 🗃️ Data Warehouse Schema Summary

```
dim_date       ──┐
dim_customer   ──┤
dim_product    ──┤──▶ fact_sales
dim_location   ──┘
```

| Table | Rows (approx.) | Purpose |
|-------|---------------|---------|
| dim_date | 728 | Date hierarchy (Day→Month→Quarter→Year) |
| dim_customer | 4,372 | Customer segments (B2B/B2C) |
| dim_product | 4,070 | Product categories & hierarchy |
| dim_location | 38 | Country→Region→Continent |
| fact_sales | 745,903 | Sales transactions (grain: 1 invoice line) |

---

## 📈 Power BI Dashboard Structure

| Page | Name | Visuals |
|------|------|---------|
| 1 | Executive Summary | 4 KPI Cards, Donut, Bar Chart, Map, Year Slicer |
| 2 | Trend Analysis | Line Chart, Clustered Column, Order Volume, Cumulative Area |
| 3 | Interactive Analysis | Matrix, Scatter, 4 Slicers, Drill-down/Roll-up |

---

## 📚 Dataset Citation

Chen, D., Sain, S. L., & Guo, K. (2012). *Online Retail II* [Dataset].  
UCI Machine Learning Repository.  
https://archive.ics.uci.edu/ml/datasets/Online+Retail+II
