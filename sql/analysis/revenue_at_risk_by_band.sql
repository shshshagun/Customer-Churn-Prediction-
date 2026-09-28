-- sql/analysis/revenue_at_risk_by_band.sql
-- Business question: How much monthly revenue is at risk from attrition, by risk band?
-- Revenue at risk = SUM(monthly_charge * risk_score) per band.
-- Only includes High and Medium risk bands (actionable watchlist).

SELECT
    p.risk_band,
    COUNT(DISTINCT p.subscriber_id)                     AS subscriber_count,
    ROUND(AVG(p.risk_score), 4)                         AS avg_risk_score,
    ROUND(SUM(b.monthly_charge), 2)                     AS total_mrr_in_band,
    ROUND(SUM(b.monthly_charge * p.risk_score), 2)      AS revenue_at_risk,
    ROUND(AVG(b.monthly_charge), 2)                     AS avg_monthly_charge
FROM fact_prediction p
JOIN fact_billing b ON b.subscriber_id = p.subscriber_id
WHERE p.risk_band IN ('High', 'Medium')
  AND p.run_id = (
      SELECT run_id FROM model_run
      WHERE model_name IN ('xgb_calibrated', 'rf_calibrated')
      ORDER BY trained_at DESC LIMIT 1
  )
GROUP BY p.risk_band
ORDER BY
    CASE p.risk_band
        WHEN 'High'   THEN 1
        WHEN 'Medium' THEN 2
        ELSE 3
    END;
