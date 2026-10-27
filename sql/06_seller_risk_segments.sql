-- ============================================================
-- File: 06_seller_risk_segments.sql
-- Purpose: Segment sellers by commercial value and
--          customer-experience risk
-- Scope: Delivered orders only
-- Minimum volume: 50 delivered orders
-- ============================================================

WITH seller_order_value AS (
    SELECT
        oi.seller_id,
        oi.order_id,
        SUM(oi.price) AS seller_gmv
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

    HAVING COUNT(DISTINCT order_id) >= 50
),

seller_quartiles AS (
    SELECT
        seller_id,
        delivered_orders,
        gmv,
        avg_review_score,
        late_delivery_rate_pct,

        NTILE(4) OVER (
            ORDER BY gmv DESC
        ) AS gmv_quartile,

        NTILE(4) OVER (
            ORDER BY avg_review_score ASC
        ) AS review_risk_quartile,

        NTILE(4) OVER (
            ORDER BY late_delivery_rate_pct DESC
        ) AS late_risk_quartile

    FROM seller_metrics
)

SELECT
    seller_id,
    delivered_orders,
    gmv,
    avg_review_score,
    late_delivery_rate_pct,

    gmv_quartile,
    review_risk_quartile,
    late_risk_quartile,

    CASE
        WHEN gmv_quartile = 1
             AND (
                 review_risk_quartile = 1
                 OR late_risk_quartile = 1
             )
        THEN 'Priority Monitoring'

        WHEN gmv_quartile = 1
             AND review_risk_quartile = 4
             AND late_risk_quartile = 4
        THEN 'High-Value Strong Performer'

        WHEN gmv_quartile = 1
        THEN 'High-Value Mixed Performance'

        ELSE 'Standard Seller'
    END AS seller_segment

FROM seller_quartiles

ORDER BY
    CASE seller_segment
        WHEN 'Priority Monitoring' THEN 1
        WHEN 'High-Value Strong Performer' THEN 2
        WHEN 'High-Value Mixed Performance' THEN 3
        ELSE 4
    END,
    gmv DESC;