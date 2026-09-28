-- sql/views.sql
-- Stayline Retention Intelligence — Analytical Views
-- ===================================================
-- These views are created after the schema and data loads.
-- They are read-only convenience joins used by the Streamlit app and SQL queries.

-- -------------------------------------------------------------------
-- vw_subscriber_360: full subscriber profile in a single flat row
-- -------------------------------------------------------------------
DROP VIEW IF EXISTS vw_subscriber_360;
CREATE VIEW vw_subscriber_360 AS
SELECT
    s.subscriber_id,
    s.gender,
    s.is_senior,
    s.has_partner,
    s.has_dependents,
    s.tenure_months,
    s.tenure_band,
    s.is_new_subscriber,
    sp.phone_service,
    sp.multiple_lines,
    sp.internet_service,
    sp.online_security,
    sp.online_backup,
    sp.device_protection,
    sp.tech_support,
    sp.streaming_tv,
    sp.streaming_movies,
    sp.services_count,
    sp.has_protection_bundle,
    sp.fibre_without_support,
    c.contract_type,
    c.paperless_billing,
    c.payment_method,
    c.is_autopay,
    c.contract_commitment_months,
    b.monthly_charge,
    b.lifetime_billed,
    b.avg_monthly_spend_to_date,
    b.price_vs_history_gap,
    al.churned_flag
FROM dim_subscriber s
JOIN dim_service_profile  sp ON sp.subscriber_id = s.subscriber_id
JOIN dim_contract         c  ON c.subscriber_id  = s.subscriber_id
JOIN fact_billing         b  ON b.subscriber_id  = s.subscriber_id
JOIN fact_attrition_label al ON al.subscriber_id = s.subscriber_id;

-- -------------------------------------------------------------------
-- vw_scored_watchlist: latest scored subscribers with calibrated risk
-- Picks the best calibrated model run (model_name = 'xgb_calibrated' or
-- fallback to the latest run_id).
-- -------------------------------------------------------------------
DROP VIEW IF EXISTS vw_scored_watchlist;
CREATE VIEW vw_scored_watchlist AS
WITH latest_run AS (
    -- Pick the most recent run for the calibrated model; fall back to any model
    SELECT run_id
    FROM model_run
    WHERE model_name IN ('xgb_calibrated', 'rf_calibrated', 'logreg', 'xgboost', 'random_forest')
    ORDER BY
        CASE model_name
            WHEN 'xgb_calibrated' THEN 1
            WHEN 'rf_calibrated'  THEN 2
            WHEN 'xgboost'        THEN 3
            WHEN 'random_forest'  THEN 4
            ELSE 5
        END,
        trained_at DESC
    LIMIT 1
)
SELECT
    p.subscriber_id,
    p.model_name,
    p.risk_score,
    p.risk_band,
    p.predicted_flag,
    s.tenure_months,
    s.tenure_band,
    s.is_senior,
    c.contract_type,
    c.payment_method,
    c.is_autopay,
    b.monthly_charge,
    al.churned_flag
FROM fact_prediction p
JOIN latest_run         lr ON lr.run_id       = p.run_id
JOIN dim_subscriber      s  ON s.subscriber_id  = p.subscriber_id
JOIN dim_contract        c  ON c.subscriber_id  = p.subscriber_id
JOIN fact_billing        b  ON b.subscriber_id  = p.subscriber_id
JOIN fact_attrition_label al ON al.subscriber_id = p.subscriber_id
ORDER BY p.risk_score DESC;
