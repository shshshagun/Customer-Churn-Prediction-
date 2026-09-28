"""
src/stayline/clean.py
----------------------
Cleaning step: reads raw CSV, applies documented transformations, and writes
data/interim/cleaned_subscribers.csv plus data/interim/cleaning_log.csv.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd

from stayline.config import get_settings
from stayline.exceptions import ArtifactMissingError
from stayline.logging_setup import get_logger

logger = get_logger(__name__)

CLEANED_CSV = "data/interim/cleaned_subscribers.csv"

_INTERNET_ADD_ONS: list[str] = [
    "Online Security", "Online Backup", "Device Protection",
    "Tech Support", "Streaming TV", "Streaming Movies",
]

_RENAME: dict[str, str] = {
    "CustomerID": "subscriber_id",
    "Gender": "gender",
    "Senior Citizen": "is_senior",
    "Partner": "has_partner",
    "Dependents": "has_dependents",
    "Tenure Months": "tenure_months",
    "Phone Service": "phone_service",
    "Multiple Lines": "multiple_lines",
    "Internet Service": "internet_service",
    "Online Security": "online_security",
    "Online Backup": "online_backup",
    "Device Protection": "device_protection",
    "Tech Support": "tech_support",
    "Streaming TV": "streaming_tv",
    "Streaming Movies": "streaming_movies",
    "Contract": "contract_type",
    "Paperless Billing": "paperless_billing",
    "Payment Method": "payment_method",
    "Monthly Charges": "monthly_charge",
    "Total Charges": "lifetime_billed",
    "Churn Label": "churned_flag",
}

def run() -> pd.DataFrame:
    cfg = get_settings()
    raw_path = cfg.data.raw_csv
    if not raw_path.exists():
        raise ArtifactMissingError(f"Raw CSV not found.")

    df = pd.read_csv(raw_path)
    logger.info(f"Loaded raw data: {len(df):,} rows")

    log_entries: list[dict[str, Any]] = []

    # Rule 1
    df["Total Charges"] = pd.to_numeric(df["Total Charges"], errors="coerce")
    n_blank = df["Total Charges"].isna().sum()
    df.loc[df["Tenure Months"] == 0, "Total Charges"] = df.loc[df["Tenure Months"] == 0, "Total Charges"].fillna(0.0)
    log_entries.append({
        "rule": "Total Charges blank → 0.0 for Tenure=0",
        "rows_affected": int(n_blank),
        "rationale": "Subscribers with tenure=0 have not yet been billed.",
    })

    # Rule 2
    for col in _INTERNET_ADD_ONS:
        n = (df[col] == "No internet service").sum()
        df[col] = df[col].replace("No internet service", "No")
        log_entries.append({
            "rule": f"{col}: 'No internet service' → 'No'",
            "rows_affected": int(n),
            "rationale": "Simplifies encoding.",
        })

    # Rule 3
    n = (df["Multiple Lines"] == "No phone service").sum()
    df["Multiple Lines"] = df["Multiple Lines"].replace("No phone service", "No")
    log_entries.append({
        "rule": "Multiple Lines: 'No phone service' → 'No'",
        "rows_affected": int(n),
        "rationale": "Redundant.",
    })

    # Rule 4: Senior Citizen is already Yes/No in this dataset, but check anyway
    if df["Senior Citizen"].dtype == int or df["Senior Citizen"].dtype == float:
        df["Senior Citizen"] = df["Senior Citizen"].map({0: "No", 1: "Yes"})
        log_entries.append({
            "rule": "Senior Citizen: 0/1 int → 'No'/'Yes'",
            "rows_affected": int(len(df)),
            "rationale": "Consistent Yes/No.",
        })

    # Keep only the columns we actually want to rename/keep, dropping the rest
    # (e.g. Churn Value, Churn Score, CLTV, Churn Reason which might be leakage)
    cols_to_keep = list(_RENAME.keys())
    df = df[cols_to_keep]

    # Rule 5
    df = df.rename(columns=_RENAME)
    log_entries.append({
        "rule": "Rename all columns to snake_case and drop leakage columns",
        "rows_affected": 0,
        "rationale": "Consistent naming.",
    })

    # Rule 6
    df["churned_flag"] = df["churned_flag"].map({"Yes": 1, "No": 0}).astype(int)
    log_entries.append({
        "rule": "churned_flag: 'Yes'/'No' → 1/0",
        "rows_affected": int(len(df)),
        "rationale": "Binary target.",
    })

    cleaned_path = cfg.data.raw_csv.parent.parent / "interim" / "cleaned_subscribers.csv"
    cleaned_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cleaned_path, index=False)
    
    log_path = cfg.data.cleaning_log
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["rule", "rows_affected", "rationale"])
        writer.writeheader()
        writer.writerows(log_entries)

    return df

def load_cleaned() -> pd.DataFrame:
    cfg = get_settings()
    path = cfg.data.raw_csv.parent.parent / "interim" / "cleaned_subscribers.csv"
    return pd.read_csv(path)
