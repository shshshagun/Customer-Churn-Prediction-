"""
src/stayline/config.py
-----------------------
Loads and validates settings.yaml and assumptions.yaml.

All paths in settings.yaml are relative to the project root.  The project
root is resolved as the parent of the `stayline/` repo directory (i.e. the
directory containing pyproject.toml).

Usage:
    from stayline.config import get_settings, get_assumptions
    cfg = get_settings()
    asm = get_assumptions()
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

# ---------------------------------------------------------------------------
# Project-root resolution
# ---------------------------------------------------------------------------

def _find_project_root() -> Path:
    """Walk up from this file's location until we find pyproject.toml."""
    candidate = Path(__file__).resolve()
    for parent in [candidate, *candidate.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback: cwd
    return Path.cwd()


PROJECT_ROOT: Path = _find_project_root()


def resolve(relative_path: str) -> Path:
    """Resolve a settings-relative path against the project root."""
    return PROJECT_ROOT / relative_path


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Raised when a required config value is missing or invalid."""


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------

@dataclass
class ProjectConfig:
    name: str
    product: str
    version: str


@dataclass
class DataConfig:
    raw_csv: Path
    validation_report: Path
    cleaning_log: Path
    processed_dir: Path
    stats_dir: Path
    insights_json: Path
    feature_importance_csv: Path
    warehouse_db: Path


@dataclass
class ModelingConfig:
    random_seed: int
    test_size: float
    cv_folds: int
    imbalance_strategy: str
    risk_band_high_threshold: Optional[float]
    risk_band_medium_threshold: Optional[float]
    fallback_high_threshold: float
    fallback_medium_threshold: float
    keras_max_epochs: int
    keras_patience: int
    keras_batch_size: int
    keras_learning_rate: float
    keras_l2: float
    keras_val_split: float
    search_n_iter: int


@dataclass
class ReportsConfig:
    excel_path: Path
    briefs_dir: Path
    powerbi_data_dir: Path


@dataclass
class LogsConfig:
    pipeline_log: Path


@dataclass
class SqlConfig:
    schema: Path
    views: Path
    analysis_dir: Path


@dataclass
class Settings:
    project: ProjectConfig
    data: DataConfig
    modeling: ModelingConfig
    reports: ReportsConfig
    logs: LogsConfig
    sql: SqlConfig
    models_dir: Path
    watchlist_top_n: int


# ---------------------------------------------------------------------------
# Assumptions dataclass
# ---------------------------------------------------------------------------

@dataclass
class RetentionOfferAssumptions:
    offer_cost_per_subscriber: float
    assumed_save_rate: float
    value_horizon_months: int


@dataclass
class PlannerDefaults:
    offer_cost_min: float
    offer_cost_max: float
    offer_cost_step: float
    save_rate_min: float
    save_rate_max: float
    save_rate_step: float
    value_horizon_min: int
    value_horizon_max: int
    value_horizon_step: int


@dataclass
class Assumptions:
    retention_offer: RetentionOfferAssumptions
    planner_defaults: PlannerDefaults


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and return the validated Settings object (cached)."""
    raw = _load_yaml(PROJECT_ROOT / "config" / "settings.yaml")

    p = raw["project"]
    d = raw["data"]
    m = raw["modeling"]
    r = raw["reports"]
    lg = raw["logs"]
    s = raw["sql"]

    return Settings(
        project=ProjectConfig(
            name=p["name"],
            product=p["product"],
            version=p["version"],
        ),
        data=DataConfig(
            raw_csv=resolve(d["raw_csv"]),
            validation_report=resolve(d["validation_report"]),
            cleaning_log=resolve(d["cleaning_log"]),
            processed_dir=resolve(d["processed_dir"]),
            stats_dir=resolve(d["stats_dir"]),
            insights_json=resolve(d["insights_json"]),
            feature_importance_csv=resolve(d["feature_importance_csv"]),
            warehouse_db=resolve(d["warehouse_db"]),
        ),
        modeling=ModelingConfig(
            random_seed=m["random_seed"],
            test_size=m["test_size"],
            cv_folds=m["cv_folds"],
            imbalance_strategy=m["imbalance_strategy"],
            risk_band_high_threshold=m.get("risk_band_high_threshold"),
            risk_band_medium_threshold=m.get("risk_band_medium_threshold"),
            fallback_high_threshold=m["fallback_high_threshold"],
            fallback_medium_threshold=m["fallback_medium_threshold"],
            keras_max_epochs=m["keras_max_epochs"],
            keras_patience=m["keras_patience"],
            keras_batch_size=m["keras_batch_size"],
            keras_learning_rate=m["keras_learning_rate"],
            keras_l2=m["keras_l2"],
            keras_val_split=m["keras_val_split"],
            search_n_iter=m["search_n_iter"],
        ),
        reports=ReportsConfig(
            excel_path=resolve(r["excel_path"]),
            briefs_dir=resolve(r["briefs_dir"]),
            powerbi_data_dir=resolve(r["powerbi_data_dir"]),
        ),
        logs=LogsConfig(pipeline_log=resolve(lg["pipeline_log"])),
        sql=SqlConfig(
            schema=resolve(s["schema"]),
            views=resolve(s["views"]),
            analysis_dir=resolve(s["analysis_dir"]),
        ),
        models_dir=resolve(raw["models_dir"]),
        watchlist_top_n=raw["watchlist_top_n"],
    )


@lru_cache(maxsize=1)
def get_assumptions() -> Assumptions:
    """Load and return the validated Assumptions object (cached)."""
    raw = _load_yaml(PROJECT_ROOT / "config" / "assumptions.yaml")

    ro = raw["retention_offer"]
    pd_ = raw["planner_defaults"]

    return Assumptions(
        retention_offer=RetentionOfferAssumptions(
            offer_cost_per_subscriber=float(ro["offer_cost_per_subscriber"]),
            assumed_save_rate=float(ro["assumed_save_rate"]),
            value_horizon_months=int(ro["value_horizon_months"]),
        ),
        planner_defaults=PlannerDefaults(
            offer_cost_min=pd_["offer_cost_min"],
            offer_cost_max=pd_["offer_cost_max"],
            offer_cost_step=pd_["offer_cost_step"],
            save_rate_min=pd_["save_rate_min"],
            save_rate_max=pd_["save_rate_max"],
            save_rate_step=pd_["save_rate_step"],
            value_horizon_min=pd_["value_horizon_min"],
            value_horizon_max=pd_["value_horizon_max"],
            value_horizon_step=pd_["value_horizon_step"],
        ),
    )


def update_risk_thresholds(high: float, medium: float) -> None:
    """Persist computed risk thresholds back to settings.yaml at runtime."""
    path = PROJECT_ROOT / "config" / "settings.yaml"
    raw = _load_yaml(path)
    raw["modeling"]["risk_band_high_threshold"] = round(float(high), 4)
    raw["modeling"]["risk_band_medium_threshold"] = round(float(medium), 4)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(raw, fh, default_flow_style=False, allow_unicode=True)
    # Invalidate cache
    get_settings.cache_clear()
