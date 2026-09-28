"""
src/stayline/validate.py
-------------------------
Validation step: runs schema and quality checks on the raw CSV and writes
data/interim/validation_report.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from stayline.config import get_settings
from stayline.exceptions import ArtifactMissingError, DataValidationError
from stayline.logging_setup import get_logger

logger = get_logger(__name__)

# Expected schema based on the dataset
REQUIRED_COLUMNS: list[str] = [
    "CustomerID", "Gender", "Senior Citizen", "Partner", "Dependents",
    "Tenure Months", "Phone Service", "Multiple Lines", "Internet Service",
    "Online Security", "Online Backup", "Device Protection", "Tech Support",
    "Streaming TV", "Streaming Movies", "Contract", "Paperless Billing",
    "Payment Method", "Monthly Charges", "Total Charges", "Churn Label",
]

ALLOWED_VALUES: dict[str, set[str]] = {
    "Gender": {"Male", "Female"},
    "Senior Citizen": {"Yes", "No"},
    "Partner": {"Yes", "No"},
    "Dependents": {"Yes", "No"},
    "Phone Service": {"Yes", "No"},
    "Multiple Lines": {"Yes", "No", "No phone service"},
    "Internet Service": {"DSL", "Fiber optic", "No"},
    "Online Security": {"Yes", "No", "No internet service"},
    "Online Backup": {"Yes", "No", "No internet service"},
    "Device Protection": {"Yes", "No", "No internet service"},
    "Tech Support": {"Yes", "No", "No internet service"},
    "Streaming TV": {"Yes", "No", "No internet service"},
    "Streaming Movies": {"Yes", "No", "No internet service"},
    "Contract": {"Month-to-month", "One year", "Two year"},
    "Paperless Billing": {"Yes", "No"},
    "Payment Method": {
        "Electronic check", "Mailed check",
        "Bank transfer (automatic)", "Credit card (automatic)",
    },
    "Churn Label": {"Yes", "No"},
}


def _check(
    condition: bool,
    message: str,
    findings: list[dict[str, Any]],
    critical: bool = False,
) -> None:
    status = "PASS" if condition else ("FAIL_CRITICAL" if critical else "FAIL_WARNING")
    findings.append({"check": message, "status": status})
    if not condition:
        if critical:
            logger.error(f"CRITICAL: {message}")
        else:
            logger.warning(f"WARNING: {message}")
    else:
        logger.info(f"PASS: {message}")


def run() -> dict[str, Any]:
    cfg = get_settings()
    raw_path = cfg.data.raw_csv
    if not raw_path.exists():
        raise ArtifactMissingError(f"Raw CSV not found at {raw_path}")

    df = pd.read_csv(raw_path)
    logger.info(f"Loaded {len(df):,} rows for validation")

    findings: list[dict[str, Any]] = []

    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    _check(
        len(missing_cols) == 0,
        f"Required columns present (missing: {missing_cols or 'none'})",
        findings, critical=True,
    )

    if missing_cols:
        _write_report(cfg, findings, df)
        raise DataValidationError(f"Missing required columns: {missing_cols}")

    n_dupes = df["CustomerID"].duplicated().sum()
    _check(
        n_dupes == 0,
        f"CustomerID uniqueness (duplicates: {n_dupes})",
        findings, critical=True,
    )

    for col, allowed in ALLOWED_VALUES.items():
        actual = set(df[col].astype(str).unique()) if col == "Senior Citizen" else set(df[col].dropna().unique())
        unexpected = actual - allowed
        _check(
            len(unexpected) == 0,
            f"Allowed values for '{col}' (unexpected: {unexpected or 'none'})",
            findings,
        )

    _check(
        (df["Tenure Months"] >= 0).all(),
        f"Tenure Months >= 0 (violations: {(df['Tenure Months'] < 0).sum()})",
        findings, critical=True,
    )
    _check(
        (df["Monthly Charges"] > 0).all(),
        f"Monthly Charges > 0 (violations: {(df['Monthly Charges'] <= 0).sum()})",
        findings, critical=True,
    )
    _check(
        df["Tenure Months"].max() <= 200,
        f"Tenure Months max reasonable (<= 200 months)",
        findings,
    )

    tc = pd.to_numeric(df["Total Charges"], errors="coerce")
    n_blank = tc.isna().sum()
    tenure0_count = (df["Tenure Months"] == 0).sum()
    _check(
        n_blank == tenure0_count,
        f"Total Charges blanks ({n_blank}) match Tenure=0 rows ({tenure0_count})",
        findings,
    )

    missing = df.isnull().sum()
    missing_report = missing[missing > 0].to_dict()
    findings.append({
        "check": "Missingness report",
        "status": "INFO",
        "details": missing_report if missing_report else "No missing values",
    })

    churn_counts = df["Churn Label"].value_counts().to_dict()
    churn_rate = churn_counts.get("Yes", 0) / len(df)
    findings.append({
        "check": "Target distribution",
        "status": "INFO",
        "details": {
            "counts": churn_counts,
            "churn_rate": round(churn_rate, 4),
        },
    })
    
    report = _write_report(cfg, findings, df)

    critical_fails = [f for f in findings if f["status"] == "FAIL_CRITICAL"]
    if critical_fails:
        raise DataValidationError(f"{len(critical_fails)} critical validation check(s) failed.")

    logger.info(f"Validation passed. Report at {cfg.data.validation_report}")
    return report


def _write_report(cfg: Any, findings: list[dict], df: pd.DataFrame) -> dict[str, Any]:
    import datetime
    report = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "row_count": len(df),
        "column_count": df.shape[1],
        "findings": findings,
    }
    cfg.data.validation_report.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg.data.validation_report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    return report
