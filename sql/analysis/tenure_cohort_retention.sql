-- sql/analysis/tenure_cohort_retention.sql
-- Business question: What fraction of subscribers survive past each tenure milestone?
-- Uses window functions (SQLite >= 3.25).

WITH cohort AS (
    SELECT
        s.tenure_months,
        COUNT(*) AS subscribers_at_tenure
    FROM dim_subscriber s
    JOIN fact_attrition_label al ON al.subscriber_id = s.subscriber_id
    WHERE al.churned_flag = 0  -- still active (survived)
    GROUP BY s.tenure_months
),
total AS (
    SELECT COUNT(*) AS total_subscribers FROM dim_subscriber
)
SELECT
    c.tenure_months,
    c.subscribers_at_tenure,
    t.total_subscribers,
    ROUND(
        1.0 * SUM(c.subscribers_at_tenure) OVER (ORDER BY c.tenure_months DESC)
        / t.total_subscribers,
        4
    ) AS cumulative_share_retained
FROM cohort c
CROSS JOIN total t
ORDER BY c.tenure_months;
