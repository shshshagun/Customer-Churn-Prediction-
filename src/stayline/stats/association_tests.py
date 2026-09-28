"""
src/stayline/stats/association_tests.py
----------------------------------------
Chi-square tests of independence between churned_flag and categorical variables.
Outputs Cramér's V effect sizes and Benjamini-Hochberg adjusted p-values.

Results written to data/processed/stats/association_tests.csv with a
plain_english column summarising each finding in non-technical language.

Statistical approach:
 - Chi-square test of independence (scipy.stats.chi2_contingency).
 - Cramér's V = sqrt(chi2 / (n * (min(r, c) - 1))).
 - BH FDR correction via statsmodels.stats.multitest.multipletests.
 - All wording is correlational, not causal.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from statsmodels.stats.multitest import multipletests

from stayline.config import get_settings
from stayline.logging_setup import get_logger
from stayline.warehouse import query_df

logger = get_logger(__name__)

CATEGORICAL_FEATURES = [
    "contract_type",
    "payment_method",
    "internet_service",
    "paperless_billing",
    "is_senior",
    "has_partner",
    "has_dependents",
    "gender",
    "is_autopay",
]


def cramers_v(chi2: float, n: int, r: int, c: int) -> float:
    """Compute Cramér's V effect size. Returns 0 if undefined."""
    denom = n * (min(r, c) - 1)
    if denom <= 0:
        return 0.0
    return math.sqrt(chi2 / denom)


def _interpret_v(v: float) -> str:
    if v >= 0.35:
        return "large"
    if v >= 0.20:
        return "moderate"
    if v >= 0.10:
        return "small"
    return "negligible"


def _plain_english(row: dict) -> str:
    feature = row["feature"].replace("_", " ")
    sig = "statistically significant" if row["bh_significant"] else "not statistically significant"
    strength = _interpret_v(row["cramers_v"])
    return (
        f"The association between {feature} and subscriber attrition is "
        f"{sig} (adjusted p = {row['p_adjusted']:.3f}) "
        f"with a {strength} effect size (Cramér's V = {row['cramers_v']:.3f}). "
        f"Correlation only — no causal claim is made."
    )


def run() -> pd.DataFrame:
    """Run all chi-square association tests and save results."""
    cfg = get_settings()
    cfg.data.stats_dir.mkdir(parents=True, exist_ok=True)

    df = query_df("SELECT * FROM vw_subscriber_360")
    logger.info(f"Loaded {len(df):,} rows for association tests")

    rows = []
    for feat in CATEGORICAL_FEATURES:
        if feat not in df.columns:
            logger.warning(f"Column '{feat}' not found — skipping")
            continue

        contingency = pd.crosstab(df[feat], df["churned_flag"])
        chi2, p, dof, _ = chi2_contingency(contingency)
        n = len(df)
        r, c = contingency.shape
        v = cramers_v(chi2, n, r, c)

        rows.append({
            "feature": feat,
            "test": "chi-square",
            "chi2": round(chi2, 4),
            "dof": int(dof),
            "p_raw": round(p, 6),
            "cramers_v": round(v, 4),
            "effect_size_label": _interpret_v(v),
        })
        logger.info(f"  {feat}: chi2={chi2:.2f}, p={p:.4f}, V={v:.3f}")

    results = pd.DataFrame(rows)

    # Benjamini-Hochberg FDR correction
    reject, p_adj, _, _ = multipletests(
        results["p_raw"].values, method="fdr_bh", alpha=0.05
    )
    results["p_adjusted"] = p_adj.round(6)
    results["bh_significant"] = reject

    # Plain-English column
    results["plain_english"] = results.apply(
        lambda row: _plain_english(row.to_dict()), axis=1
    )

    out = cfg.data.stats_dir / "association_tests.csv"
    results.to_csv(out, index=False)
    logger.info(f"Association tests saved to {out}")

    return results
