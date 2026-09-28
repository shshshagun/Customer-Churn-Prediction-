-- sql/analysis/data_quality_checks.sql
-- Business question: Are there any data quality issues in the warehouse?
-- Feeds the Data Health & Lineage page.

SELECT 'dim_subscriber'      AS table_name, COUNT(*) AS row_count,
       SUM(CASE WHEN subscriber_id IS NULL THEN 1 ELSE 0 END)    AS null_id_count
FROM dim_subscriber
UNION ALL
SELECT 'dim_service_profile', COUNT(*),
       SUM(CASE WHEN subscriber_id IS NULL THEN 1 ELSE 0 END)
FROM dim_service_profile
UNION ALL
SELECT 'dim_contract', COUNT(*),
       SUM(CASE WHEN subscriber_id IS NULL THEN 1 ELSE 0 END)
FROM dim_contract
UNION ALL
SELECT 'fact_billing', COUNT(*),
       SUM(CASE WHEN subscriber_id IS NULL THEN 1 ELSE 0 END)
FROM fact_billing
UNION ALL
SELECT 'fact_attrition_label', COUNT(*),
       SUM(CASE WHEN subscriber_id IS NULL THEN 1 ELSE 0 END)
FROM fact_attrition_label;
