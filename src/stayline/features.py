"""
src/stayline/features.py
-------------------------
Feature engineering step: adds label-free, row-wise derived features to the
cleaned DataFrame and writes data/interim/features_subscribers.csv.

All features are deterministic and computed without any target leakage.
Rationale for each feature is documented here and in docs/feature_dictionary.md.

Features added:
 1. tenure_band        — categorical bin of tenure_months.
 2. services_count     — total billable services subscribed.
 3. has_protection_bundle — binary flag for security/backup/device/tech bundle.
 4. avg_monthly_spend_to_date — TotalCharges / max(tenure, 1).
 5. price_vs_history_gap — monthly_charge minus avg_monthly_spend_to_date.
 6. is_autopay         — binary flag for automatic payment methods.
 7. is_new_subscriber  — binary flag for tenure <= 6 months.
 8. fibre_without_support — binary: fibre internet with no online security AND no tech support.
 9. contract_commitment_months — ordinal: 0 / 12 / 24.
"""

from __future__ import annotations

import pandas as pd

from stayline.config import get_settings
from stayline.exceptions import ArtifactMissingError
from stayline.logging_setup import get_logger

logger = get_logger(__name__)

FEATURES_CSV = "data/interim/features_subscribers.csv"

_TENURE_BINS = [0, 6, 12, 24, 48, 72, float("inf")]
_TENURE_LABELS = ["0–6 mo", "7–12 mo", "13–24 mo", "25–48 mo", "49–72 mo", "73+ mo"]

_AUTOPAY_METHODS = {"Bank transfer (automatic)", "Credit card (automatic)"}

_CONTRACT_MONTHS = {"Month-to-month": 0, "One year": 12, "Two year": 24}


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all engineered features to a cleaned DataFrame.
    Pure function — does not read or write any files.
    All operations are row-wise and label-free.
    """
    df = df.copy()

    # 1. tenure_band
    df["tenure_band"] = pd.cut(
        df["tenure_months"],
        bins=_TENURE_BINS,
        labels=_TENURE_LABELS,
        right=True,
        include_lowest=True,
    ).astype(str)

    # 2. services_count — count all add-on services that are "Yes"
    service_cols = [
        "phone_service", "multiple_lines",
        "online_security", "online_backup", "device_protection",
        "tech_support", "streaming_tv", "streaming_movies",
    ]
    df["services_count"] = (df[service_cols] == "Yes").sum(axis=1).astype(int)

    # 3. has_protection_bundle
    protection_cols = ["online_security", "online_backup", "device_protection", "tech_support"]
    df["has_protection_bundle"] = (
        (df[protection_cols] == "Yes").sum(axis=1) >= 2
    ).astype(int)

    # 4. avg_monthly_spend_to_date
    df["avg_monthly_spend_to_date"] = (
        df["lifetime_billed"] / df["tenure_months"].clip(lower=1)
    ).round(2)

    # 5. price_vs_history_gap
    df["price_vs_history_gap"] = (
        df["monthly_charge"] - df["avg_monthly_spend_to_date"]
    ).round(2)

    # 6. is_autopay
    df["is_autopay"] = df["payment_method"].isin(_AUTOPAY_METHODS).astype(int)

    # 7. is_new_subscriber
    df["is_new_subscriber"] = (df["tenure_months"] <= 6).astype(int)

    # 8. fibre_without_support
    df["fibre_without_support"] = (
        (df["internet_service"] == "Fiber optic")
        & (df["online_security"] == "No")
        & (df["tech_support"] == "No")
    ).astype(int)

    # 9. contract_commitment_months
    df["contract_commitment_months"] = df["contract_type"].map(_CONTRACT_MONTHS).astype(int)

    return df


def run() -> pd.DataFrame:
    """Execute the feature engineering step and write the output CSV."""
    cfg = get_settings()
    cleaned_path = cfg.data.raw_csv.parent.parent / "interim" / "cleaned_subscribers.csv"
    if not cleaned_path.exists():
        raise ArtifactMissingError(
            f"Cleaned CSV not found at {cleaned_path}. Run: python -m stayline clean"
        )

    df = pd.read_csv(cleaned_path)
    logger.info(f"Loaded cleaned data: {len(df):,} rows")

    df = engineer_features(df)
    logger.info(f"Features added. Shape: {df.shape}")

    out_path = cleaned_path.parent / "features_subscribers.csv"
    df.to_csv(out_path, index=False)
    logger.info(f"Features CSV written to {out_path}")

    return df


def load_features() -> pd.DataFrame:
    """Load the features CSV. Raises ArtifactMissingError if not found."""
    cfg = get_settings()
    path = cfg.data.raw_csv.parent.parent / "interim" / "features_subscribers.csv"
    if not path.exists():
        raise ArtifactMissingError(
            f"Features CSV not found at {path}. Run: python -m stayline clean"
        )
    return pd.read_csv(path)
