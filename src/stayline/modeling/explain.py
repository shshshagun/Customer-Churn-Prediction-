"""
src/stayline/modeling/explain.py
----------------------------------
Calculates feature importance using permutation importance.
(Fallback from SHAP if not available).
"""

from __future__ import annotations

import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline

from stayline.config import get_settings
from stayline.logging_setup import get_logger

logger = get_logger(__name__)

def calculate_permutation_importance(model: Pipeline, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """
    Computes permutation importance for the given pipeline model.
    """
    logger.info("Computing permutation importance...")
    cfg = get_settings()
    
    result = permutation_importance(
        model, X, y, n_repeats=5, random_state=cfg.modeling.random_seed, n_jobs=-1, scoring="roc_auc"
    )
    
    importance_df = pd.DataFrame({
        "feature": X.columns,
        "importance_mean": result.importances_mean,
        "importance_std": result.importances_std
    }).sort_values(by="importance_mean", ascending=False)
    
    cfg.data.processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = cfg.data.feature_importance_csv
    importance_df.to_csv(out_path, index=False)
    logger.info(f"Feature importance saved to {out_path}")
    
    return importance_df
