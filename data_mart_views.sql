-- ============================================================
-- Online Retail Data Warehouse - Data Mart Views
-- Sales & Marketing Department Data Mart
-- ============================================================

-- View 1: Monthly Sales by Category
CREATE VIEW IF NOT EXISTS vw_monthly_sales_by_category AS
SELECT
    d.year,
    d.month,
    d.month_name,
    p.category,
    COUNT(DISTINCT f.invoice_no)   AS order_count,
    SUM(f.quantity)                AS units_sold,
    ROUND(SUM(f.total_amount), 2)  AS revenue,
    ROUND(AVG(f.unit_price), 2)    AS avg_unit_price
FROM fact_sales f
JOIN dim_date     d ON f.date_id     = d.date_id
JOIN dim_product  p ON f.product_id  = p.product_id
GROUP BY d.year, d.month, d.month_name, p.category
ORDER BY d.year, d.month, p.category;

-- View 2: Customer Segment Performance
CREATE VIEW IF NOT EXISTS vw_customer_segments AS
SELECT
    c.segment,
    c.region,
    COUNT(DISTINCT c.customer_id)         AS customer_count,
    COUNT(DISTINCT f.invoice_no)          AS total_orders,
    ROUND(SUM(f.total_amount), 2)         AS total_revenue,
    ROUND(AVG(f.total_amount), 2)         AS avg_order_line_value,
    ROUND(SUM(f.total_amount) /
          NULLIF(COUNT(DISTINCT f.invoice_no), 0), 2) AS avg_order_value
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.segment, c.region
ORDER BY total_revenue DESC;

-- View 3: Top Products by Revenue
CREATE VIEW IF NOT EXISTS vw_top_products AS
SELECT
    p.stock_code,
    p.description,
    p.category,
    p.subcategory,
    p.is_gift,
    COUNT(DISTINCT f.invoice_no)   AS order_count,
    SUM(f.quantity)                AS total_units_sold,
    ROUND(SUM(f.total_amount), 2)  AS total_revenue,
    ROUND(AVG(f.unit_price), 2)    AS avg_price
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.stock_code, p.description, p.category, p.subcategory, p.is_gift
ORDER BY total_revenue DESC;

-- View 4: Regional Sales Performance
CREATE VIEW IF NOT EXISTS vw_regional_performance AS
SELECT
    l.continent,
    l.region,
    l.country,
    d.year,
    COUNT(DISTINCT f.invoice_no)   AS orders,
    COUNT(DISTINCT f.customer_id)  AS customers,
    ROUND(SUM(f.total_amount), 2)  AS revenue,
    ROUND(SUM(f.total_amount) /
          NULLIF(COUNT(DISTINCT f.customer_id), 0), 2) AS revenue_per_customer
FROM fact_sales f
JOIN dim_location l ON f.location_id = l.location_id
JOIN dim_date     d ON f.date_id     = d.date_id
GROUP BY l.continent, l.region, l.country, d.year
ORDER BY revenue DESC;

-- View 5: Year-over-Year Revenue Comparison
CREATE VIEW IF NOT EXISTS vw_yoy_revenue AS
SELECT
    d.year,
    d.month,
    d.month_name,
    ROUND(SUM(f.total_amount), 2) AS monthly_revenue,
    SUM(SUM(f.total_amount)) OVER (PARTITION BY d.year
        ORDER BY d.month ROWS UNBOUNDED PRECEDING) AS cumulative_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- View 6: Customer Retention / Order Frequency
CREATE VIEW IF NOT EXISTS vw_customer_retention AS
SELECT
    customer_id,
    COUNT(DISTINCT invoice_no)         AS order_count,
    MIN(date_id)                       AS first_order_date,
    MAX(date_id)                       AS last_order_date,
    ROUND(SUM(total_amount), 2)        AS lifetime_value,
    CASE
        WHEN COUNT(DISTINCT invoice_no) = 1 THEN 'One-time'
        WHEN COUNT(DISTINCT invoice_no) BETWEEN 2 AND 5 THEN 'Occasional'
        WHEN COUNT(DISTINCT invoice_no) > 5 THEN 'Loyal'
    END AS customer_type
FROM fact_sales
GROUP BY customer_id
ORDER BY lifetime_value DESC;
