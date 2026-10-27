-- ============================================================
-- File: 04_basket_structure.sql
-- Purpose: Analyze the category composition of delivered orders
-- ============================================================

WITH order_categories AS (
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

basket_size AS (
    SELECT
        order_id,
        COUNT(DISTINCT category) AS category_count
    FROM order_categories
    GROUP BY order_id
)

SELECT
    category_count,
    COUNT(*) AS orders,
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
        2
    ) AS order_share_pct
FROM basket_size
GROUP BY category_count
ORDER BY category_count;