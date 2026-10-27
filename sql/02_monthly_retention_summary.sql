-- ============================================================
-- File: 02_monthly_retention_summary.sql
-- Purpose: Calculate weighted monthly customer retention
--          after first purchase
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

month_offsets AS (
    SELECT 1 AS months_since_first_purchase

    UNION ALL

    SELECT months_since_first_purchase + 1
    FROM month_offsets
    WHERE months_since_first_purchase < 12
),

eligible_cohorts AS (
    SELECT
        cs.cohort_month,
        cs.cohort_size,
        mo.months_since_first_purchase,
        DATE(
            cs.cohort_month,
            '+' || mo.months_since_first_purchase || ' months'
        ) AS activity_month
    FROM cohort_sizes AS cs
    CROSS JOIN month_offsets AS mo
    CROSS JOIN data_end AS de
    WHERE DATE(
        cs.cohort_month,
        '+' || mo.months_since_first_purchase || ' months'
    ) <= de.max_order_month
),

activity_counts AS (
    SELECT
        fp.cohort_month,
        co.order_month AS activity_month,
        COUNT(DISTINCT co.customer_unique_id) AS active_customers
    FROM customer_orders AS co
    JOIN first_purchase AS fp
        ON co.customer_unique_id = fp.customer_unique_id
    WHERE co.order_month > fp.cohort_month
    GROUP BY
        fp.cohort_month,
        co.order_month
)

SELECT
    ec.months_since_first_purchase,

    COUNT(DISTINCT ec.cohort_month) AS eligible_cohorts,

    SUM(ec.cohort_size) AS eligible_customers,

    SUM(
        COALESCE(ac.active_customers, 0)
    ) AS active_customers,

    ROUND(
        100.0 * SUM(COALESCE(ac.active_customers, 0))
        / SUM(ec.cohort_size),
        2
    ) AS weighted_retention_rate_pct

FROM eligible_cohorts AS ec

LEFT JOIN activity_counts AS ac
    ON ec.cohort_month = ac.cohort_month
    AND ec.activity_month = ac.activity_month

GROUP BY
    ec.months_since_first_purchase

ORDER BY
    ec.months_since_first_purchase;


