-- sql/analysis/kpi_summary.sql
-- Business question: What are the top-line subscriber and revenue KPIs?
-- Outputs: subscribers, attrition rate, MRR, MRR lost to churn,
--          average tenure, ARPU by attrition status.

SELECT
    COUNT(*)                                                AS total_subscribers,
    SUM(al.churned_flag)                                   AS churned_count,
    COUNT(*) - SUM(al.churned_flag)                        AS retained_count,
    ROUND(
        1.0 * SUM(al.churned_flag) / COUNT(*), 4
    )                                                      AS attrition_rate,
    ROUND(SUM(b.monthly_charge), 2)                        AS total_mrr,
    ROUND(
        SUM(CASE WHEN al.churned_flag = 1 THEN b.monthly_charge ELSE 0 END), 2
    )                                                      AS mrr_lost_to_churn,
    ROUND(AVG(s.tenure_months), 2)                         AS avg_tenure_months,
    ROUND(AVG(b.monthly_charge), 2)                        AS avg_monthly_charge,
    ROUND(
        AVG(CASE WHEN al.churned_flag = 1 THEN b.monthly_charge END), 2
    )                                                      AS arpu_churned,
    ROUND(
        AVG(CASE WHEN al.churned_flag = 0 THEN b.monthly_charge END), 2
    )                                                      AS arpu_retained
FROM dim_subscriber s
JOIN fact_billing         b  ON b.subscriber_id  = s.subscriber_id
JOIN fact_attrition_label al ON al.subscriber_id = s.subscriber_id;
