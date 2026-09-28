-- sql/analysis/payment_method_attrition.sql
-- Business question: How does attrition vary by payment method and autopay status?

SELECT
    c.payment_method,
    c.is_autopay,
    COUNT(*)                                             AS subscriber_count,
    SUM(al.churned_flag)                                 AS churned_count,
    ROUND(1.0 * SUM(al.churned_flag) / COUNT(*), 4)     AS attrition_rate,
    ROUND(AVG(b.monthly_charge), 2)                      AS avg_monthly_charge
FROM dim_contract c
JOIN fact_attrition_label al ON al.subscriber_id = c.subscriber_id
JOIN fact_billing         b  ON b.subscriber_id  = c.subscriber_id
GROUP BY c.payment_method, c.is_autopay
ORDER BY attrition_rate DESC;
