-- ============================================================
-- File: 07_payment_reconciliation.sql
-- Purpose: Reconcile order-level expected order value
--          against recorded customer payments
-- Scope: Delivered orders
-- ============================================================

WITH item_totals AS (
    SELECT
        oi.order_id,
        ROUND(SUM(oi.price), 2) AS gmv,
        ROUND(SUM(oi.freight_value), 2) AS freight,
        ROUND(
            SUM(oi.price) + SUM(oi.freight_value),
            2
        ) AS expected_order_value
    FROM order_items AS oi
    GROUP BY oi.order_id
),

payment_totals AS (
    SELECT
        p.order_id,
        ROUND(SUM(p.payment_value), 2) AS payment_total,
        COUNT(*) AS payment_records
    FROM payments AS p
    GROUP BY p.order_id
),

reconciliation_base AS (
    SELECT
        o.order_id,
        o.order_status,

        it.gmv,
        it.freight,
        it.expected_order_value,

        pt.payment_total,
        pt.payment_records,

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

classified_orders AS (
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

            WHEN payment_difference < -1.00
                THEN 'Payment Below Order Value'
        END AS reconciliation_status

    FROM reconciliation_base
),

ranked_anomalies AS (
    SELECT
        *,

        ROW_NUMBER() OVER (
            ORDER BY ABS(payment_difference) DESC
        ) AS anomaly_rank

    FROM classified_orders

    WHERE reconciliation_status NOT IN (
        'Matched',
        'Minor Difference'
    )
)

SELECT
    anomaly_rank,
    order_id,
    gmv,
    freight,
    expected_order_value,
    payment_total,
    payment_difference,
    payment_records,
    reconciliation_status

FROM ranked_anomalies

ORDER BY anomaly_rank;