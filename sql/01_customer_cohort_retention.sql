-- ============================================================
-- File: 01_customer_cohort_retention.sql
-- Purpose: Analyze monthly customer retention by first-purchase cohort
-- Scope: Delivered orders only
-- Customer key: customer_unique_id
-- ============================================================

WITH RECURSIVE

customer_orders AS (
    SELECT DISTINCT
        c.customer_unique_id,
        DATE(o.order_purchase_timestamp, 'start of month') AS order_month
    FROM orders AS o
    JOIN customers AS c
        ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
),

first_purchase AS (
    SELECT
        customer_unique_id,
        MIN(order_month) AS cohort_month
    FROM customer_orders
    GROUP BY customer_unique_id
),

cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_unique_id) AS cohort_size
    FROM first_purchase
    GROUP BY cohort_month
),

data_end AS (
    SELECT
        MAX(order_month) AS max_order_month
    FROM customer_orders
),

cohort_calendar AS (
    -- Month 0 for every cohort
    SELECT
        cs.cohort_month,
        cs.cohort_size,
        0 AS months_since_first_purchase,
        cs.cohort_month AS activity_month
    FROM cohort_sizes AS cs

    UNION ALL

    -- Generate Month 1, Month 2, ...
    -- only while that month is observable in the dataset
    SELECT
        cc.cohort_month,
        cc.cohort_size,
        cc.months_since_first_purchase + 1,
        DATE(cc.activity_month, '+1 month')
    FROM cohort_calendar AS cc
    CROSS JOIN data_end AS de
    WHERE DATE(cc.activity_month, '+1 month') <= de.max_order_month
),

activity_counts AS (
    SELECT
        fp.cohort_month,
        co.order_month AS activity_month,
        COUNT(DISTINCT co.customer_unique_id) AS active_customers
    FROM customer_orders AS co
    JOIN first_purchase AS fp
        ON co.customer_unique_id = fp.customer_unique_id
    GROUP BY
        fp.cohort_month,
        co.order_month
)

SELECT
    cc.cohort_month,
    cc.months_since_first_purchase,
    cc.cohort_size,

    COALESCE(ac.active_customers, 0) AS active_customers,

    ROUND(
        100.0 * COALESCE(ac.active_customers, 0)
        / cc.cohort_size,
        2
    ) AS retention_rate_pct

FROM cohort_calendar AS cc

LEFT JOIN activity_counts AS ac
    ON cc.cohort_month = ac.cohort_month
    AND cc.activity_month = ac.activity_month

ORDER BY
    cc.cohort_month,
    cc.months_since_first_purchase;

