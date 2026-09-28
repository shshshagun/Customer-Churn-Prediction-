"""
src/stayline/stats/odds_ratios.py
-----------------------------------
Logistic regression odds ratios with 95% CIs and VIF multicollinearity check.

Uses statsmodels Logit with the cleaned numeric/encoded feature matrix.
Outputs data/processed/stats/odds_ratios.csv with forest-plot data.

All wording is correlational, not causal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

from stayline.config import get_settings
from stayline.logging_setup import get_logger
from stayline.warehouse import query_df

logger = get_logger(__name__)


def _encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """Simple binary encoding for logistic regression."""
    enc = pd.DataFrame()
    enc["tenure_months"] = df["tenure_months"]
    enc["monthly_charge"] = df["monthly_charge"]
    enc["services_count"] = df["services_count"]
    enc["is_senior"] = (df["is_senior"] == "Yes").astype(int)
    enc["has_partner"] = (df["has_partner"] == "Yes").astype(int)
    enc["has_dependents"] = (df["has_dependents"] == "Yes").astype(int)
    enc["is_autopay"] = df["is_autopay"].astype(int)
    enc["is_new_subscriber"] = df["is_new_subscriber"].astype(int)
    enc["fibre_without_support"] = df["fibre_without_support"].astype(int)
    enc["has_protection_bundle"] = df["has_protection_bundle"].astype(int)
    enc["contract_one_year"] = (df["contract_type"] == "One year").astype(int)
    enc["contract_two_year"] = (df["contract_type"] == "Two year").astype(int)
    enc["internet_fibre"] = (df["internet_service"] == "Fiber optic").astype(int)
    enc["internet_dsl"] = (df["internet_service"] == "DSL").astype(int)
    enc["paperless_billing"] = (df["paperless_billing"] == "Yes").astype(int)
    return enc


def _vif(X: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, col in enumerate(X.columns):
        rows.append({"feature": col, "vif": round(variance_inflation_factor(X.values, i), 2)})
    return pd.DataFrame(rows)


def run() -> pd.DataFrame:
    cfg = get_settings()
    cfg.data.stats_dir.mkdir(parents=True, exist_ok=True)

    df = query_df("SELECT * FROM vw_subscriber_360")
    logger.info(f"Loaded {len(df):,} rows for odds-ratio analysis")

    X_raw = _encode_features(df)
    y = df["churned_flag"].values

    # Drop rows with NaN
    mask = X_raw.notna().all(axis=1)
    X_raw = X_raw[mask]
    y = y[mask]

    # Add intercept
    X = sm.add_constant(X_raw)

    # Fit logistic regression
    model = sm.Logit(y, X).fit(disp=0)
    logger.info("Logistic regression converged.")

    params = model.params
    conf = model.conf_int()
    conf.columns = ["ci_lo_log", "ci_hi_log"]

    results = pd.DataFrame({
        "feature": params.index,
        "log_odds": params.values.round(4),
        "odds_ratio": np.exp(params.values).round(4),
        "or_ci_lo": np.exp(conf["ci_lo_log"].values).round(4),
        "or_ci_hi": np.exp(conf["ci_hi_log"].values).round(4),
        "p_value": model.pvalues.values.round(6),
    })
    results = results[results["feature"] != "const"].reset_index(drop=True)
    results["significant"] = results["p_value"] < 0.05
    results["plain_english"] = results.apply(
        lambda r: (
            f"A one-unit increase in {r['feature'].replace('_',' ')} is associated with "
            f"an odds ratio of {r['odds_ratio']:.2f} (95% CI: {r['or_ci_lo']:.2f}–{r['or_ci_hi']:.2f}), "
            f"{'significant' if r['significant'] else 'not significant'} at p = {r['p_value']:.3f}. "
            f"Correlation only — no causal claim is made."
        ),
        axis=1,
    )

    out = cfg.data.stats_dir / "odds_ratios.csv"
    results.to_csv(out, index=False)
    logger.info(f"Odds ratios saved to {out}")

    # VIF
    vif_df = _vif(X_raw)
    vif_out = cfg.data.stats_dir / "vif.csv"
    vif_df.to_csv(vif_out, index=False)
    high_vif = vif_df[vif_df["vif"] > 10]
    if not high_vif.empty:
        logger.warning(f"High VIF features (>10): {high_vif['feature'].tolist()}")
    else:
        logger.info("No multicollinearity issues (all VIF <= 10)")

    return results
