"""
src/stayline/cli.py
--------------------
Command-line interface for the Stayline pipeline.

Usage:
    python -m stayline <step>

Available steps:
    ingest          Copy raw data; compute checksum.
    validate        Schema and quality checks on raw data.
    clean           Clean and normalise; engineer features.
    features        (alias for clean — feature engineering is part of clean step)
    warehouse       Build SQLite schema; load all data; run views.
    stats           Run all statistical analyses.
    train           Train and calibrate all ML models (sklearn + Keras).
    score           Score all subscribers; write predictions to DB.
    insights        Compute ranked business insights from DB + model outputs.
    excel           Generate the Excel workbook.
    powerbi-export  Export star-schema CSVs and DAX/M artefacts.
    run-all         Run all steps in sequence.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Callable

from stayline.logging_setup import get_logger

logger = get_logger(__name__)

STEPS: dict[str, str] = {
    "ingest": "Copy raw data and verify checksum",
    "validate": "Validate schema and data quality",
    "clean": "Clean, normalise, and engineer features",
    "features": "Alias for clean",
    "warehouse": "Build SQLite schema; load all data",
    "stats": "Run statistical analyses",
    "train": "Train and calibrate all ML models",
    "score": "Score all subscribers and persist predictions",
    "insights": "Compute ranked business insights",
    "excel": "Generate Excel workbook",
    "powerbi-export": "Export Power BI artefacts",
    "run-all": "Run all steps in sequence",
}


def _run_step(name: str) -> None:
    """Dispatch a single named step."""
    start = time.time()
    logger.info("=" * 60)
    logger.info(f"STEP: {name}")
    logger.info("=" * 60)

    if name in ("ingest",):
        from stayline.ingest import run as ingest_run
        ingest_run()

    elif name in ("validate",):
        from stayline.validate import run as validate_run
        validate_run()

    elif name in ("clean", "features"):
        from stayline.clean import run as clean_run
        from stayline.features import run as features_run
        clean_run()
        features_run()

    elif name == "warehouse":
        from stayline.warehouse import run as warehouse_run
        warehouse_run()

    elif name == "stats":
        from stayline.stats.association_tests import run as assoc_run
        from stayline.stats.numeric_tests import run as numeric_run
        from stayline.stats.odds_ratios import run as or_run
        from stayline.stats.survival import run as survival_run
        assoc_run()
        numeric_run()
        or_run()
        survival_run()

    elif name == "train":
        from stayline.modeling.sklearn_models import run as sklearn_run
        from stayline.modeling.keras_model import run as keras_run
        sklearn_run()
        keras_run()

    elif name == "score":
        from stayline.modeling.sklearn_models import run_scoring
        run_scoring()

    elif name == "insights":
        from stayline.insights import run as insights_run
        insights_run()

    elif name == "excel":
        from stayline.reporting.excel_workbook import run as excel_run
        excel_run()

    elif name == "powerbi-export":
        from stayline.reporting.powerbi_export import run as pbi_run
        pbi_run()

    else:
        logger.error(f"Unknown step: {name}")
        sys.exit(1)

    elapsed = time.time() - start
    logger.info(f"STEP '{name}' completed in {elapsed:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="stayline",
        description="Stayline Retention Intelligence — data pipeline CLI",
    )
    parser.add_argument(
        "step",
        nargs="?",
        choices=list(STEPS.keys()),
        default=None,
        help="Pipeline step to run",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available steps",
    )

    args = parser.parse_args()

    if args.list or args.step is None:
        print("\nStayline pipeline steps:\n")
        for step, desc in STEPS.items():
            print(f"  {step:<18} {desc}")
        print(f"\nUsage: python -m stayline <step>\n")
        sys.exit(0)

    if args.step == "run-all":
        ordered = ["ingest", "validate", "clean", "warehouse", "stats",
                   "train", "score", "insights", "excel", "powerbi-export"]
        for step in ordered:
            _run_step(step)
        logger.info("All steps completed successfully.")
    else:
        _run_step(args.step)
