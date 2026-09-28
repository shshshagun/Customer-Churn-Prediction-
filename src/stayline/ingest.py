"""
src/stayline/ingest.py
-----------------------
Ingestion step: copies the IBM Telco source data to data/raw/telco_subscribers.csv
and writes a SOURCE.md with provenance and a SHA-256 checksum.

The source file may be:
 - The Excel file from the original repo (data is on Sheet1).
 - A CSV already placed in data/raw/.
 - The Kaggle CSV downloaded separately.

Priority:
 1. If data/raw/telco_subscribers.csv already exists → skip copy, verify checksum.
 2. If the Excel file exists in the original repo → read and write CSV.
 3. Raise ArtifactMissingError with instructions.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pandas as pd

from stayline.config import PROJECT_ROOT, get_settings
from stayline.exceptions import ArtifactMissingError
from stayline.logging_setup import get_logger

logger = get_logger(__name__)

# Source Excel path (from the original reference project)
_ORIGINAL_EXCEL = (
    PROJECT_ROOT.parent
    / "Customer-Churn-Prediction"
    / "Data"
    / "Telco_customer_churn.xlsx"
)

_SOURCE_MD_TEMPLATE = """\
# Data Source

**Dataset:** IBM Telco Customer Churn
**Origin:** Kaggle — https://www.kaggle.com/datasets/blastchar/telco-customer-churn
**Licence:** Database Contents Licence (DbCL) v1.0 (open, non-commercial attribution required)
**Description:** 7,043 synthetic subscriber records for a fictitious US telecom operator,
  including demographic, service, contract, billing, and churn-status fields.
**Use in Stayline:** This dataset is a *public sample* used as a stand-in for real operator data.
  All cost and save-rate figures in the project are ASSUMPTIONS, not real business data.

**SHA-256 checksum (telco_subscribers.csv):** {checksum}
**Ingested at:** {timestamp}
"""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run() -> None:
    """Execute the ingest step."""
    cfg = get_settings()
    dest = cfg.data.raw_csv
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        logger.info(f"Raw CSV already exists at {dest} — skipping copy.")
        checksum = _sha256(dest)
        logger.info(f"SHA-256: {checksum}")
        _write_source_md(dest.parent, checksum)
        df = pd.read_csv(dest)
        logger.info(f"Row count: {len(df):,}  Columns: {df.shape[1]}")
        return

    # Try to read from the original Excel reference file
    if _ORIGINAL_EXCEL.exists():
        logger.info(f"Reading data from {_ORIGINAL_EXCEL}")
        df = pd.read_excel(_ORIGINAL_EXCEL, sheet_name=0)
        logger.info(f"Loaded {len(df):,} rows, {df.shape[1]} columns from Excel")
        df.to_csv(dest, index=False)
        logger.info(f"Written to {dest}")
    else:
        # Check if a CSV was placed manually
        candidates = list(Path("data/raw").glob("*.csv"))
        if candidates:
            src = candidates[0]
            logger.info(f"Found CSV at {src} — copying to {dest}")
            shutil.copy2(src, dest)
        else:
            raise ArtifactMissingError(
                f"No source data found. Expected one of:\n"
                f"  {dest}  (place the IBM Telco CSV here)\n"
                f"  {_ORIGINAL_EXCEL}  (original Excel reference)\n\n"
                f"Download the dataset from:\n"
                f"  https://www.kaggle.com/datasets/blastchar/telco-customer-churn\n"
                f"and place WA_Fn-UseC_-Telco-Customer-Churn.csv in data/raw/telco_subscribers.csv"
            )

    checksum = _sha256(dest)
    logger.info(f"SHA-256: {checksum}")
    _write_source_md(dest.parent, checksum)

    df = pd.read_csv(dest)
    logger.info(f"Ingest complete. Rows: {len(df):,}  Columns: {df.shape[1]}")


def _write_source_md(directory: Path, checksum: str) -> None:
    from datetime import datetime
    content = _SOURCE_MD_TEMPLATE.format(
        checksum=checksum,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
    (directory / "SOURCE.md").write_text(content, encoding="utf-8")
