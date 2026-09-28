-- sql/analysis/attrition_by_contract_and_tenure.sql
-- Business question: How does attrition vary across contract type and tenure band?
-- Minimum-n filter: only report cells with >= 50 subscribers.

WITH base AS (
    SELECT
        c.contract_type,
        s.tenure_band,
        COUNT(*)                    AS subscriber_count,
        SUM(al.churned_flag)        AS churned_count,
        ROUND(
            1.0 * SUM(al.churned_flag) / COUNT(*), 4
        )                           AS attrition_rate
    FROM dim_subscriber s
    JOIN dim_contract         c  ON c.subscriber_id  = s.subscriber_id
    JOIN fact_attrition_label al ON al.subscriber_id = s.subscriber_id
    GROUP BY c.contract_type, s.tenure_band
)
SELECT *
FROM base
WHERE subscriber_count >= 50
ORDER BY contract_type, attrition_rate DESC;
