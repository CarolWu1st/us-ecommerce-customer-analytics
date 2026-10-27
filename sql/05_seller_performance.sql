-- ============================================================
-- File: 05_seller_performance.sql
-- Purpose: Build a seller-level performance scorecard
-- Scope: Delivered orders only
-- ============================================================

WITH seller_order_value AS (
    SELECT
        oi.seller_id,
        oi.order_id,
        SUM(oi.price) AS seller_gmv,
        COUNT(*) AS items_sold
    FROM order_items AS oi
    GROUP BY
        oi.seller_id,
        oi.order_id
),

order_reviews AS (
    SELECT
        order_id,
        AVG(review_score) AS avg_review_score
    FROM reviews
    GROUP BY order_id
),

seller_order_base AS (
    SELECT
        sov.seller_id,
        sov.order_id,
        sov.seller_gmv,
        sov.items_sold,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        r.avg_review_score,

        CASE
            WHEN o.order_delivered_customer_date >
                 o.order_estimated_delivery_date
            THEN 1
            ELSE 0
        END AS is_late

    FROM seller_order_value AS sov

    JOIN orders AS o
        ON sov.order_id = o.order_id

    LEFT JOIN order_reviews AS r
        ON sov.order_id = r.order_id

    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
),

seller_metrics AS (
    SELECT
        seller_id,

        COUNT(DISTINCT order_id) AS delivered_orders,

        ROUND(
            SUM(seller_gmv),
            2
        ) AS gmv,

        SUM(items_sold) AS items_sold,

        ROUND(
            SUM(seller_gmv) / COUNT(DISTINCT order_id),
            2
        ) AS gmv_per_order,

        ROUND(
            AVG(avg_review_score),
            2
        ) AS avg_review_score,

        ROUND(
            100.0 * SUM(is_late) / COUNT(*),
            2
        ) AS late_delivery_rate_pct

    FROM seller_order_base

    GROUP BY seller_id
)

SELECT
    seller_id,
    delivered_orders,
    gmv,
    items_sold,
    gmv_per_order,
    avg_review_score,
    late_delivery_rate_pct,

    DENSE_RANK() OVER (
        ORDER BY gmv DESC
    ) AS gmv_rank

FROM seller_metrics

-- Avoid evaluating sellers with only a handful of orders
WHERE delivered_orders >= 50

ORDER BY gmv DESC;