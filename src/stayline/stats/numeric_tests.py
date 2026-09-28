"""
src/stayline/stats/numeric_tests.py
-------------------------------------
Numeric tests comparing churned vs. retained distributions for
tenure_months and monthly_charge.

Approach:
 - Check distribution shape (skewness, QQ-style summary).
 - Welch's t-test (unequal variances assumed).
 - Mann-Whitney U test (non-parametric).
 - Effect sizes: Cohen's d (standardised mean difference),
   rank-biserial correlation r = 1 - 2U/(n1*n2).
 - Bootstrap 95% CIs for the mean difference (2000 resamples, fixed seed).

Results written to data/processed/stats/numeric_tests.csv.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from stayline.config import get_settings
from stayline.logging_setup import get_logger
from stayline.warehouse import query_df

logger = get_logger(__name__)

RNG_SEED = 42
N_BOOTSTRAP = 2000


def cohens_d(g1: np.ndarray, g2: np.ndarray) -> float:
    """Pooled-SD Cohen's d (positive if g1 > g2)."""
    n1, n2 = len(g1), len(g2)
    pooled_std = np.sqrt(
        ((n1 - 1) * g1.std(ddof=1) ** 2 + (n2 - 1) * g2.std(ddof=1) ** 2)
        / (n1 + n2 - 2)
    )
    if pooled_std == 0:
        return 0.0
    return float((g1.mean() - g2.mean()) / pooled_std)


def rank_biserial(U: float, n1: int, n2: int) -> float:
    """Rank-biserial correlation from Mann-Whitney U."""
    return float(1.0 - 2.0 * U / (n1 * n2))


def bootstrap_mean_diff_ci(
    g1: np.ndarray, g2: np.ndarray, n: int = N_BOOTSTRAP, seed: int = RNG_SEED
) -> tuple[float, float]:
    """Bootstrap 95% CI for (mean(g1) - mean(g2))."""
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n):
        s1 = rng.choice(g1, size=len(g1), replace=True)
        s2 = rng.choice(g2, size=len(g2), replace=True)
        diffs.append(s1.mean() - s2.mean())
    diffs = np.array(diffs)
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def _interpret_d(d: float) -> str:
    a = abs(d)
    if a >= 0.8:
        return "large"
    if a >= 0.5:
        return "moderate"
    if a >= 0.2:
        return "small"
    return "negligible"


def _plain_english(row: dict) -> str:
    feat = row["feature"].replace("_", " ")
    direction = "higher" if row["mean_churned"] > row["mean_retained"] else "lower"
    sig = "statistically significant" if row["p_ttest"] < 0.05 else "not statistically significant"
    strength = _interpret_d(row["cohens_d"])
    return (
        f"Churned subscribers have {direction} {feat} on average "
        f"(churned: {row['mean_churned']:.1f}, retained: {row['mean_retained']:.1f}). "
        f"The difference is {sig} (t-test p = {row['p_ttest']:.4f}), "
        f"with a {strength} effect (Cohen's d = {row['cohens_d']:.3f}). "
        f"Correlation only — no causal claim is made."
    )


def run() -> pd.DataFrame:
    """Run numeric tests and save results."""
    cfg = get_settings()
    cfg.data.stats_dir.mkdir(parents=True, exist_ok=True)

    df = query_df("SELECT tenure_months, monthly_charge, churned_flag FROM vw_subscriber_360")
    logger.info(f"Loaded {len(df):,} rows for numeric tests")

    churned = df[df["churned_flag"] == 1]
    retained = df[df["churned_flag"] == 0]

    rows = []
    for feat in ["tenure_months", "monthly_charge"]:
        g1 = churned[feat].dropna().values
        g2 = retained[feat].dropna().values

        skew_churned = float(stats.skew(g1))
        skew_retained = float(stats.skew(g2))

        t_stat, p_ttest = stats.ttest_ind(g1, g2, equal_var=False)
        u_stat, p_mwu = stats.mannwhitneyu(g1, g2, alternative="two-sided")

        d = cohens_d(g1, g2)
        rb = rank_biserial(float(u_stat), len(g1), len(g2))
        ci_lo, ci_hi = bootstrap_mean_diff_ci(g1, g2)

        row = {
            "feature": feat,
            "n_churned": len(g1),
            "n_retained": len(g2),
            "mean_churned": round(g1.mean(), 3),
            "mean_retained": round(g2.mean(), 3),
            "std_churned": round(g1.std(ddof=1), 3),
            "std_retained": round(g2.std(ddof=1), 3),
            "skew_churned": round(skew_churned, 3),
            "skew_retained": round(skew_retained, 3),
            "t_stat": round(float(t_stat), 4),
            "p_ttest": round(float(p_ttest), 6),
            "u_stat": round(float(u_stat), 1),
            "p_mwu": round(float(p_mwu), 6),
            "cohens_d": round(d, 4),
            "effect_label": _interpret_d(d),
            "rank_biserial_r": round(rb, 4),
            "bootstrap_ci_lo": round(ci_lo, 3),
            "bootstrap_ci_hi": round(ci_hi, 3),
        }
        row["plain_english"] = _plain_english(row)
        rows.append(row)

        logger.info(
            f"  {feat}: mean_churned={g1.mean():.2f}, mean_retained={g2.mean():.2f}, "
            f"p_ttest={p_ttest:.4f}, d={d:.3f}"
        )

    results = pd.DataFrame(rows)
    out = cfg.data.stats_dir / "numeric_tests.csv"
    results.to_csv(out, index=False)
    logger.info(f"Numeric tests saved to {out}")
    return results
