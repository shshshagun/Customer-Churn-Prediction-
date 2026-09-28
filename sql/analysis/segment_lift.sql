-- sql/analysis/segment_lift.sql
-- Business question: Which segments have materially higher attrition than the base rate?
-- Shows lift = segment_rate / base_rate. Minimum-n filter: >= 50 subscribers.

WITH overall AS (
    SELECT ROUND(1.0 * SUM(churned_flag) / COUNT(*), 6) AS base_rate
    FROM fact_attrition_label
),
segments AS (
    SELECT
        'Contract'             AS segment_dimension,
        c.contract_type        AS segment_value,
        COUNT(*)               AS subscriber_count,
        SUM(al.churned_flag)   AS churned_count,
        ROUND(1.0 * SUM(al.churned_flag) / COUNT(*), 4) AS attrition_rate
    FROM dim_contract c
    JOIN fact_attrition_label al ON al.subscriber_id = c.subscriber_id
    GROUP BY c.contract_type

    UNION ALL

    SELECT
        'Internet Service'      AS segment_dimension,
        sp.internet_service     AS segment_value,
        COUNT(*)                AS subscriber_count,
        SUM(al.churned_flag)    AS churned_count,
        ROUND(1.0 * SUM(al.churned_flag) / COUNT(*), 4) AS attrition_rate
    FROM dim_service_profile sp
    JOIN fact_attrition_label al ON al.subscriber_id = sp.subscriber_id
    GROUP BY sp.internet_service

    UNION ALL

    SELECT
        'Payment Method'        AS segment_dimension,
        c.payment_method        AS segment_value,
        COUNT(*)                AS subscriber_count,
        SUM(al.churned_flag)    AS churned_count,
        ROUND(1.0 * SUM(al.churned_flag) / COUNT(*), 4) AS attrition_rate
    FROM dim_contract c
    JOIN fact_attrition_label al ON al.subscriber_id = c.subscriber_id
    GROUP BY c.payment_method

    UNION ALL

    SELECT
        'Senior Citizen'        AS segment_dimension,
        s.is_senior             AS segment_value,
        COUNT(*)                AS subscriber_count,
        SUM(al.churned_flag)    AS churned_count,
        ROUND(1.0 * SUM(al.churned_flag) / COUNT(*), 4) AS attrition_rate
    FROM dim_subscriber s
    JOIN fact_attrition_label al ON al.subscriber_id = s.subscriber_id
    GROUP BY s.is_senior
)
SELECT
    seg.segment_dimension,
    seg.segment_value,
    seg.subscriber_count,
    seg.churned_count,
    seg.attrition_rate,
    ov.base_rate,
    ROUND(seg.attrition_rate / ov.base_rate, 3) AS lift_vs_base
FROM segments seg
CROSS JOIN overall ov
WHERE seg.subscriber_count >= 50
ORDER BY lift_vs_base DESC;
