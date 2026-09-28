"""
src/stayline/warehouse.py
--------------------------
Warehouse step: creates the SQLite schema, loads cleaned feature data into
the star-schema tables, and creates the analytical views.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from stayline.config import PROJECT_ROOT, get_settings
from stayline.exceptions import ArtifactMissingError
from stayline.logging_setup import get_logger

logger = get_logger(__name__)


def get_connection() -> sqlite3.Connection:
    """Return a connection to the Stayline SQLite warehouse."""
    cfg = get_settings()
    cfg.data.warehouse_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cfg.data.warehouse_db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def run_sql_file(conn: sqlite3.Connection, path: Path) -> None:
    """Execute all statements in a SQL file."""
    sql = path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
    logger.info(f"Executed SQL file: {path.name}")


def _load_features_df() -> pd.DataFrame:
    cfg = get_settings()
    path = cfg.data.raw_csv.parent.parent / "interim" / "features_subscribers.csv"
    if not path.exists():
        raise ArtifactMissingError(
            f"Features CSV not found at {path}. Run: python -m stayline clean"
        )
    return pd.read_csv(path)


def _insert_tables(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    """Insert all rows from the features DataFrame into the warehouse tables."""

    # dim_subscriber
    dim_sub = df[[
        "subscriber_id", "gender", "is_senior", "has_partner", "has_dependents",
        "tenure_months", "tenure_band", "is_new_subscriber",
    ]].drop_duplicates("subscriber_id")
    dim_sub.to_sql("dim_subscriber", conn, if_exists="append", index=False)
    logger.info(f"dim_subscriber: {len(dim_sub):,} rows")

    # dim_service_profile
    dim_svc = df[[
        "subscriber_id", "phone_service", "multiple_lines", "internet_service",
        "online_security", "online_backup", "device_protection", "tech_support",
        "streaming_tv", "streaming_movies", "services_count",
        "has_protection_bundle", "fibre_without_support",
    ]].drop_duplicates("subscriber_id")
    dim_svc.to_sql("dim_service_profile", conn, if_exists="append", index=False)
    logger.info(f"dim_service_profile: {len(dim_svc):,} rows")

    # dim_contract
    dim_con = df[[
        "subscriber_id", "contract_type", "paperless_billing", "payment_method",
        "is_autopay", "contract_commitment_months",
    ]].drop_duplicates("subscriber_id")
    dim_con.to_sql("dim_contract", conn, if_exists="append", index=False)
    logger.info(f"dim_contract: {len(dim_con):,} rows")

    # fact_billing
    fact_bil = df[[
        "subscriber_id", "monthly_charge", "lifetime_billed",
        "avg_monthly_spend_to_date", "price_vs_history_gap",
    ]].drop_duplicates("subscriber_id")
    fact_bil.to_sql("fact_billing", conn, if_exists="append", index=False)
    logger.info(f"fact_billing: {len(fact_bil):,} rows")

    # fact_attrition_label
    fact_atl = df[["subscriber_id", "churned_flag"]].drop_duplicates("subscriber_id")
    fact_atl.to_sql("fact_attrition_label", conn, if_exists="append", index=False)
    logger.info(f"fact_attrition_label: {len(fact_atl):,} rows")


def run() -> None:
    """Execute the warehouse build step."""
    cfg = get_settings()
    
    if cfg.data.warehouse_db.exists():
        # Force SQLite to close connections by ensuring wal/shm files are not locked
        import time
        time.sleep(0.1)
        try:
            cfg.data.warehouse_db.unlink()
        except OSError:
            pass # might be locked, but let's try
            
    df = _load_features_df()
    logger.info(f"Loaded {len(df):,} rows from features CSV")

    conn = get_connection()

    # Build schema
    run_sql_file(conn, cfg.sql.schema)

    # Insert data
    _insert_tables(conn, df)

    # Create views
    run_sql_file(conn, cfg.sql.views)

    # Verify
    for table in ["dim_subscriber", "dim_service_profile", "dim_contract",
                  "fact_billing", "fact_attrition_label"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        logger.info(f"  {table}: {n:,} rows")

    conn.close()
    logger.info(f"Warehouse built at {cfg.data.warehouse_db}")


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run a SQL query against the warehouse and return a DataFrame."""
    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def run_analysis_query(query_name: str) -> pd.DataFrame:
    """
    Execute a named analysis query from sql/analysis/ and return a DataFrame.
    query_name: e.g. 'kpi_summary' (no .sql extension).
    """
    cfg = get_settings()
    sql_path = cfg.sql.analysis_dir / f"{query_name}.sql"
    if not sql_path.exists():
        raise ArtifactMissingError(f"Analysis SQL not found: {sql_path}")
    sql = sql_path.read_text(encoding="utf-8")
    return query_df(sql)
