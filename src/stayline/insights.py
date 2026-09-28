"""
src/stayline/insights.py
-------------------------
Compute business insights based on the trained models and warehouse data.
Writes results to data/processed/insights.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from stayline.config import get_settings
from stayline.logging_setup import get_logger
from stayline.warehouse import query_df

logger = get_logger(__name__)

def run() -> None:
    """Generate business insights and persist to json."""
    cfg = get_settings()
    logger.info("Computing business insights...")
    
    # 1. Total revenue at risk
    rar_df = query_df("""
        SELECT SUM(b.monthly_charge * p.risk_score) as rev_at_risk
        FROM fact_prediction p
        JOIN fact_billing b ON b.subscriber_id = p.subscriber_id
        WHERE p.run_id = (
            SELECT run_id FROM model_run
            WHERE model_name IN ('xgb_calibrated', 'rf_calibrated')
            ORDER BY trained_at DESC LIMIT 1
        )
        AND p.risk_band IN ('High', 'Medium')
    """)
    
    rev_at_risk = float(rar_df["rev_at_risk"].iloc[0]) if not rar_df.empty and not rar_df["rev_at_risk"].isna().iloc[0] else 0.0
    
    # 2. Attrition by contract type
    contract_df = query_df("""
        SELECT c.contract_type, 
               COUNT(*) as total, 
               SUM(al.churned_flag) as churned,
               ROUND(1.0 * SUM(al.churned_flag) / COUNT(*), 4) as churn_rate
        FROM dim_contract c
        JOIN fact_attrition_label al ON c.subscriber_id = al.subscriber_id
        GROUP BY c.contract_type
        ORDER BY churn_rate DESC
    """)
    
    insights = {
        "revenue_at_risk": round(rev_at_risk, 2),
        "contract_insights": contract_df.to_dict(orient="records"),
        "top_recommendation": "Target month-to-month subscribers in their first 6 months with discounted 1-year contract upgrades."
    }
    
    cfg.data.processed_dir.mkdir(parents=True, exist_ok=True)
    with open(cfg.data.insights_json, "w", encoding="utf-8") as f:
        json.dump(insights, f, indent=2)
        
    logger.info(f"Insights saved to {cfg.data.insights_json}")
