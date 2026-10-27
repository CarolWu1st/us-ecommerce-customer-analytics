-- ============================================================
-- File: 03_category_affinity.sql
-- Purpose: Identify product categories frequently purchased
--          together in delivered orders
-- Scope: Delivered orders only
-- ============================================================

WITH category_orders AS (
    SELECT DISTINCT
        oi.order_id,
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name_clean
        ) AS category
    FROM order_items AS oi
    JOIN orders AS o
        ON oi.order_id = o.order_id
    JOIN products AS p
        ON oi.product_id = p.product_id
    LEFT JOIN category_translation AS ct
        ON p.product_category_name = ct.product_category_name
    WHERE o.order_status = 'delivered'
),

total_orders AS (
    SELECT
        COUNT(DISTINCT order_id) AS total_order_count
    FROM category_orders
),

category_counts AS (
    SELECT
        category,
        COUNT(DISTINCT order_id) AS category_orders
    FROM category_orders
    GROUP BY category
),

category_pairs AS (
    SELECT
        a.category AS category_a,
        b.category AS category_b,
        COUNT(DISTINCT a.order_id) AS pair_orders
    FROM category_orders AS a
    JOIN category_orders AS b
        ON a.order_id = b.order_id
        AND a.category < b.category
    GROUP BY
        a.category,
        b.category
)

SELECT
    cp.category_a,
    cp.category_b,
    cp.pair_orders,

    ca.category_orders AS category_a_orders,
    cb.category_orders AS category_b_orders,

    ROUND(
        100.0 * cp.pair_orders / t.total_order_count,
        3
    ) AS support_pct,

    ROUND(
        100.0 * cp.pair_orders / ca.category_orders,
        2
    ) AS confidence_a_to_b_pct,

    ROUND(
        100.0 * cp.pair_orders / cb.category_orders,
        2
    ) AS confidence_b_to_a_pct,

    ROUND(
        (
            1.0 * cp.pair_orders / ca.category_orders
        )
        /
        (
            1.0 * cb.category_orders / t.total_order_count
        ),
        2
    ) AS lift

FROM category_pairs AS cp

JOIN category_counts AS ca
    ON cp.category_a = ca.category

JOIN category_counts AS cb
    ON cp.category_b = cb.category

CROSS JOIN total_orders AS t

WHERE cp.pair_orders >= 10

ORDER BY
    lift DESC,
    cp.pair_orders DESC;