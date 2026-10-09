-- ============================================================
-- Online Retail Data Warehouse - Star Schema DDL
-- Tool: SQLite
-- ============================================================

-- ============================================================
-- DIMENSION TABLES
-- ============================================================

-- Dimension: Date
CREATE TABLE IF NOT EXISTS dim_date (
    date_id       INTEGER PRIMARY KEY,   -- surrogate key (YYYYMMDD integer)
    full_date     DATE NOT NULL,
    day           INTEGER NOT NULL,
    month         INTEGER NOT NULL,
    month_name    TEXT NOT NULL,
    quarter       INTEGER NOT NULL,
    year          INTEGER NOT NULL,
    weekday       TEXT NOT NULL,
    week_number   INTEGER NOT NULL,
    is_weekend    INTEGER NOT NULL DEFAULT 0,  -- 1 = weekend, 0 = weekday
    is_holiday    INTEGER NOT NULL DEFAULT 0   -- 1 = UK public holiday
);

-- Dimension: Customer
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id   INTEGER PRIMARY KEY,   -- surrogate key
    customer_code TEXT NOT NULL,         -- original CustomerID from source
    country       TEXT,
    segment       TEXT,                  -- B2B / B2C
    region        TEXT
);

-- Dimension: Product
CREATE TABLE IF NOT EXISTS dim_product (
    product_id    INTEGER PRIMARY KEY,   -- surrogate key
    stock_code    TEXT NOT NULL,
    description   TEXT,
    category      TEXT,
    subcategory   TEXT,
    is_gift       INTEGER DEFAULT 0      -- 1 = gift item, 0 = non-gift
);

-- Dimension: Location
CREATE TABLE IF NOT EXISTS dim_location (
    location_id   INTEGER PRIMARY KEY,   -- surrogate key
    country       TEXT NOT NULL,
    region        TEXT,
    continent     TEXT
);

-- ============================================================
-- FACT TABLE
-- ============================================================

-- Fact: Sales (grain = one invoice line item)
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no     TEXT NOT NULL,        -- degenerate dimension
    date_id        INTEGER NOT NULL REFERENCES dim_date(date_id),
    customer_id    INTEGER NOT NULL REFERENCES dim_customer(customer_id),
    product_id     INTEGER NOT NULL REFERENCES dim_product(product_id),
    location_id    INTEGER NOT NULL REFERENCES dim_location(location_id),
    quantity       INTEGER NOT NULL,
    unit_price     REAL NOT NULL,
    total_amount   REAL NOT NULL,        -- derived: quantity * unit_price
    discount_amount REAL DEFAULT 0.0
);

-- ============================================================
-- RETURNS FACT TABLE (negative quantity transactions)
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_returns (
    return_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no     TEXT NOT NULL,
    original_invoice_no TEXT,
    date_id        INTEGER REFERENCES dim_date(date_id),
    customer_id    INTEGER REFERENCES dim_customer(customer_id),
    product_id     INTEGER REFERENCES dim_product(product_id),
    location_id    INTEGER REFERENCES dim_location(location_id),
    return_quantity INTEGER NOT NULL,
    unit_price      REAL NOT NULL,
    return_amount   REAL NOT NULL
);

-- ============================================================
-- INDEXES for query performance
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_sales_date     ON fact_sales(date_id);
CREATE INDEX IF NOT EXISTS idx_sales_customer ON fact_sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_product  ON fact_sales(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_location ON fact_sales(location_id);
CREATE INDEX IF NOT EXISTS idx_date_year_month ON dim_date(year, month);
