-- sql/analysis/services_count_vs_attrition.sql
-- Business question: Does the number of subscribed services correlate with attrition?

SELECT
    sp.services_count,
    COUNT(*)                                             AS subscriber_count,
    SUM(al.churned_flag)                                 AS churned_count,
    ROUND(1.0 * SUM(al.churned_flag) / COUNT(*), 4)     AS attrition_rate,
    ROUND(AVG(b.monthly_charge), 2)                      AS avg_monthly_charge
FROM dim_service_profile sp
JOIN fact_attrition_label al ON al.subscriber_id = sp.subscriber_id
JOIN fact_billing         b  ON b.subscriber_id  = sp.subscriber_id
GROUP BY sp.services_count
ORDER BY sp.services_count;
