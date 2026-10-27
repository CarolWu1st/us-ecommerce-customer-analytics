-- ============================================================
-- File: 08_payment_reconciliation_summary.sql
-- Purpose: Summarize order-level payment reconciliation results
-- Scope: Delivered orders
-- ============================================================

WITH item_totals AS (
    SELECT
        order_id,
        ROUND(
            SUM(price) + SUM(freight_value),
            2
        ) AS expected_order_value
    FROM order_items
    GROUP BY order_id
),

payment_totals AS (
    SELECT
        order_id,
        ROUND(SUM(payment_value), 2) AS payment_total
    FROM payments
    GROUP BY order_id
),

reconciliation AS (
    SELECT
        o.order_id,
        it.expected_order_value,
        pt.payment_total,

        CASE
            WHEN pt.payment_total IS NULL THEN NULL
            ELSE ROUND(
                pt.payment_total - it.expected_order_value,
                2
            )
        END AS payment_difference

    FROM orders AS o

    JOIN item_totals AS it
        ON o.order_id = it.order_id

    LEFT JOIN payment_totals AS pt
        ON o.order_id = pt.order_id

    WHERE o.order_status = 'delivered'
),

classified AS (
    SELECT
        *,

        CASE
            WHEN payment_total IS NULL
                THEN 'Missing Payment'

            WHEN ABS(payment_difference) <= 0.01
                THEN 'Matched'

            WHEN ABS(payment_difference) <= 1.00
                THEN 'Minor Difference'

            WHEN payment_difference > 1.00
                THEN 'Payment Above Order Value'

            ELSE 'Payment Below Order Value'
        END AS reconciliation_status

    FROM reconciliation
)

SELECT
    reconciliation_status,

    COUNT(*) AS orders,

    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
        3
    ) AS order_share_pct,

    ROUND(
        AVG(ABS(payment_difference)),
        2
    ) AS avg_absolute_difference,

    ROUND(
        MAX(ABS(payment_difference)),
        2
    ) AS max_absolute_difference

FROM classified

GROUP BY reconciliation_status

ORDER BY orders DESC;