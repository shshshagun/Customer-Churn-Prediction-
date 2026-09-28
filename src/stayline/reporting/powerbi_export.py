"""
src/stayline/reporting/powerbi_export.py
-----------------------------------------
Exports star-schema CSVs for Power BI.
"""

from __future__ import annotations

import pandas as pd

from stayline.config import get_settings
from stayline.logging_setup import get_logger
from stayline.warehouse import get_connection

logger = get_logger(__name__)

def run() -> None:
    cfg = get_settings()
    cfg.reports.powerbi_data_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Exporting CSVs for Power BI...")
    
    conn = get_connection()
    tables = [
        "dim_subscriber", 
        "dim_service_profile", 
        "dim_contract",
        "fact_billing", 
        "fact_attrition_label", 
        "fact_prediction", 
        "model_run"
    ]
    
    for table in tables:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        out_path = cfg.reports.powerbi_data_dir / f"{table}.csv"
        df.to_csv(out_path, index=False)
        logger.info(f"Exported {table} to {out_path}")
        
    conn.close()
    
    # Also write a dummy BUILD_GUIDE.md and measures.dax for now
    powerbi_dir = cfg.reports.powerbi_data_dir.parent
    
    guide_path = powerbi_dir / "BUILD_GUIDE.md"
    guide_path.write_text("# Power BI Build Guide\n\nInstructions to build the Power BI dashboard from the exported CSVs.", encoding="utf-8")
    
    measures_path = powerbi_dir / "measures.dax"
    measures_path.write_text("Total Subscribers = COUNTROWS(dim_subscriber)\n", encoding="utf-8")
    
    logger.info("Power BI export complete.")
