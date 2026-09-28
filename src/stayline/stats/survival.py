"""
src/stayline/stats/survival.py
--------------------------------
Kaplan-Meier retention curves by contract type with multivariate log-rank test.

Uses the lifelines library:
 - KaplanMeierFitter per contract type (tenure = time, churned_flag = event).
 - Multivariate log-rank test (logrank_test pairwise + Mantel-Haenszel).

Outputs:
 - data/processed/stats/km_curves.csv — survival probabilities at each timeline point.
 - data/processed/stats/km_summary.csv — median survival and log-rank p-values.

All wording is correlational, not causal.
"""

from __future__ import annotations

import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test

from stayline.config import get_settings
from stayline.logging_setup import get_logger
from stayline.warehouse import query_df

logger = get_logger(__name__)


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run Kaplan-Meier survival analysis and save results."""
    cfg = get_settings()
    cfg.data.stats_dir.mkdir(parents=True, exist_ok=True)

    df = query_df(
        "SELECT tenure_months, churned_flag, contract_type FROM vw_subscriber_360"
    )
    logger.info(f"Loaded {len(df):,} rows for survival analysis")

    # -----------------------------------------------------------------
    # Kaplan-Meier per contract type
    # -----------------------------------------------------------------
    curve_rows = []
    summary_rows = []

    for contract in sorted(df["contract_type"].unique()):
        subset = df[df["contract_type"] == contract]
        kmf = KaplanMeierFitter()
        kmf.fit(
            durations=subset["tenure_months"],
            event_observed=subset["churned_flag"],
            label=contract,
        )

        # Store curve (survival function at each timeline step)
        sf = kmf.survival_function_.reset_index()
        sf.columns = ["timeline", "survival_prob"]
        sf["contract_type"] = contract
        curve_rows.append(sf)

        # Median survival (None if not reached)
        median = kmf.median_survival_time_
        summary_rows.append({
            "contract_type": contract,
            "n_subscribers": len(subset),
            "n_events": int(subset["churned_flag"].sum()),
            "median_survival_months": float(median) if median < 1e9 else None,
            "plain_english": (
                f"{contract} subscribers: {subset['churned_flag'].mean():.1%} attrition rate. "
                f"Median retention: "
                f"{'not reached (>50% still active)' if median >= 1e9 else f'{median:.0f} months'}."
            ),
        })
        logger.info(f"  {contract}: n={len(subset)}, events={subset['churned_flag'].sum()}, median={median:.1f}")

    km_curves = pd.concat(curve_rows, ignore_index=True)
    km_summary = pd.DataFrame(summary_rows)

    # -----------------------------------------------------------------
    # Multivariate log-rank test
    # -----------------------------------------------------------------
    mlr = multivariate_logrank_test(
        df["tenure_months"],
        df["contract_type"],
        df["churned_flag"],
    )
    p_logrank = float(mlr.p_value)
    logger.info(f"Multivariate log-rank p-value: {p_logrank:.6f}")

    km_summary["logrank_p_global"] = round(p_logrank, 6)
    km_summary["logrank_significant"] = p_logrank < 0.05
    km_summary["plain_english"] = km_summary["plain_english"] + (
        f" Global log-rank test: p = {p_logrank:.4f} "
        f"({'significant' if p_logrank < 0.05 else 'not significant'} difference across groups)."
    )

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    km_curves.to_csv(cfg.data.stats_dir / "km_curves.csv", index=False)
    km_summary.to_csv(cfg.data.stats_dir / "km_summary.csv", index=False)
    logger.info(f"KM curves saved to {cfg.data.stats_dir / 'km_curves.csv'}")
    logger.info(f"KM summary saved to {cfg.data.stats_dir / 'km_summary.csv'}")

    return km_curves, km_summary
