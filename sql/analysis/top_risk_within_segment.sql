-- sql/analysis/top_risk_within_segment.sql
-- Business question: Who are the top-N highest-risk subscribers in each contract segment?
-- Uses ROW_NUMBER() window function (SQLite >= 3.25).

WITH ranked AS (
    SELECT
        p.subscriber_id,
        c.contract_type,
        p.risk_score,
        p.risk_band,
        b.monthly_charge,
        s.tenure_months,
        ROW_NUMBER() OVER (
            PARTITION BY c.contract_type
            ORDER BY p.risk_score DESC
        ) AS rank_in_segment
    FROM fact_prediction p
    JOIN dim_subscriber      s  ON s.subscriber_id  = p.subscriber_id
    JOIN dim_contract        c  ON c.subscriber_id  = p.subscriber_id
    JOIN fact_billing        b  ON b.subscriber_id  = p.subscriber_id
    WHERE p.run_id = (
        SELECT run_id FROM model_run
        WHERE model_name IN ('xgb_calibrated', 'rf_calibrated')
        ORDER BY trained_at DESC LIMIT 1
    )
)
SELECT
    contract_type,
    rank_in_segment,
    subscriber_id,
    risk_score,
    risk_band,
    monthly_charge,
    tenure_months
FROM ranked
WHERE rank_in_segment <= 20
ORDER BY contract_type, rank_in_segment;
