"""
src/stayline/modeling/sklearn_models.py
-----------------------------------------
Train and calibrate scikit-learn models.
"""

from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from stayline.config import get_settings
from stayline.logging_setup import get_logger
from stayline.modeling.evaluation import evaluate_model
from stayline.modeling.preprocessing import get_features_and_target, get_preprocessor
from stayline.warehouse import query_df, get_connection

logger = get_logger(__name__)


def _save_model(model: Pipeline, model_name: str, metrics: dict, run_id: str) -> None:
    cfg = get_settings()
    cfg.models_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = cfg.models_dir / f"{model_name}_{run_id}.joblib"
    joblib.dump(model, model_path)
    
    # Save model run to db
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO model_run (
            run_id, model_name, trained_at, seed, cv_auc_mean, cv_auc_std,
            cv_pr_auc_mean, cv_pr_auc_std, test_auc, test_pr_auc, test_recall,
            test_precision, test_f1, test_brier, threshold, artifact_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id, model_name, datetime.datetime.utcnow().isoformat() + "Z", cfg.modeling.random_seed,
            metrics.get("cv_auc_mean"), metrics.get("cv_auc_std"),
            metrics.get("cv_pr_auc_mean"), metrics.get("cv_pr_auc_std"),
            metrics.get("test_roc_auc"), metrics.get("test_pr_auc"), metrics.get("test_recall"),
            metrics.get("test_precision"), metrics.get("test_f1"), metrics.get("test_brier"),
            0.5, str(model_path)
        )
    )
    conn.commit()
    conn.close()


def train_sklearn_models(df: pd.DataFrame) -> None:
    cfg = get_settings()
    X, y = get_features_and_target(df)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=cfg.modeling.test_size, random_state=cfg.modeling.random_seed, stratify=y
    )

    models = {
        "logreg": LogisticRegression(class_weight="balanced", random_state=cfg.modeling.random_seed, max_iter=1000),
        "random_forest": RandomForestClassifier(class_weight="balanced", random_state=cfg.modeling.random_seed),
        "xgboost": XGBClassifier(scale_pos_weight=2.7, random_state=cfg.modeling.random_seed, use_label_encoder=False, eval_metric="logloss"),
    }
    
    cv = StratifiedKFold(n_splits=cfg.modeling.cv_folds, shuffle=True, random_state=cfg.modeling.random_seed)
    
    for name, clf in models.items():
        logger.info(f"Training {name}...")
        pipeline = Pipeline(steps=[("preprocessor", get_preprocessor()), ("classifier", clf)])
        
        cv_results = cross_validate(
            pipeline, X_train, y_train, cv=cv, scoring=["roc_auc", "average_precision"], n_jobs=-1
        )
        
        pipeline.fit(X_train, y_train)
        y_prob = pipeline.predict_proba(X_test)[:, 1]
        y_pred = pipeline.predict(X_test)
        
        test_metrics = evaluate_model(y_test, y_pred, y_prob)
        metrics = {
            "cv_auc_mean": float(cv_results["test_roc_auc"].mean()),
            "cv_auc_std": float(cv_results["test_roc_auc"].std()),
            "cv_pr_auc_mean": float(cv_results["test_average_precision"].mean()),
            "cv_pr_auc_std": float(cv_results["test_average_precision"].std()),
            "test_roc_auc": test_metrics["roc_auc"],
            "test_pr_auc": test_metrics["pr_auc"],
            "test_recall": test_metrics["recall"],
            "test_precision": test_metrics["precision"],
            "test_f1": test_metrics["f1"],
            "test_brier": test_metrics["brier"],
        }
        
        run_id = str(uuid.uuid4())
        _save_model(pipeline, name, metrics, run_id)
        
        # Calibrate tree models
        if name in ["random_forest", "xgboost"]:
            logger.info(f"Calibrating {name}...")
            calibrated_clf = CalibratedClassifierCV(clf, method="isotonic", cv=cv)
            calibrated_pipeline = Pipeline(steps=[("preprocessor", get_preprocessor()), ("classifier", calibrated_clf)])
            calibrated_pipeline.fit(X_train, y_train)
            y_prob_cal = calibrated_pipeline.predict_proba(X_test)[:, 1]
            y_pred_cal = calibrated_pipeline.predict(X_test)
            test_metrics_cal = evaluate_model(y_test, y_pred_cal, y_prob_cal)
            
            metrics_cal = {
                "cv_auc_mean": None,
                "cv_auc_std": None,
                "cv_pr_auc_mean": None,
                "cv_pr_auc_std": None,
                "test_roc_auc": test_metrics_cal["roc_auc"],
                "test_pr_auc": test_metrics_cal["pr_auc"],
                "test_recall": test_metrics_cal["recall"],
                "test_precision": test_metrics_cal["precision"],
                "test_f1": test_metrics_cal["f1"],
                "test_brier": test_metrics_cal["brier"],
            }
            run_id_cal = str(uuid.uuid4())
            _save_model(calibrated_pipeline, f"{name}_calibrated", metrics_cal, run_id_cal)


def run() -> None:
    df = query_df("SELECT * FROM vw_subscriber_360")
    logger.info(f"Loaded {len(df):,} rows for training sklearn models.")
    train_sklearn_models(df)


def run_scoring() -> None:
    cfg = get_settings()
    df = query_df("SELECT * FROM vw_subscriber_360")
    X, _ = get_features_and_target(df)
    
    conn = get_connection()
    model_runs = pd.read_sql_query("SELECT run_id, model_name, artifact_path, threshold FROM model_run", conn)
    
    predictions = []
    
    for _, row in model_runs.iterrows():
        run_id = row["run_id"]
        model_name = row["model_name"]
        artifact_path = row["artifact_path"]
        threshold = row["threshold"] or 0.5
        
        logger.info(f"Scoring with {model_name} (run_id: {run_id})")
        if artifact_path.endswith(".joblib"):
            model = joblib.load(artifact_path)
            y_prob = model.predict_proba(X)[:, 1]
        else:
            # Handle keras
            pass # TODO
            continue
            
        risk_band = []
        for p in y_prob:
            if p >= cfg.modeling.fallback_high_threshold:
                risk_band.append("High")
            elif p >= cfg.modeling.fallback_medium_threshold:
                risk_band.append("Medium")
            else:
                risk_band.append("Low")
                
        pred_flag = (y_prob >= threshold).astype(int)
        
        for i, sub_id in enumerate(df["subscriber_id"]):
            predictions.append((
                run_id, sub_id, model_name, float(y_prob[i]), risk_band[i], int(pred_flag[i])
            ))
            
    conn.executemany(
        """
        INSERT OR REPLACE INTO fact_prediction (
            run_id, subscriber_id, model_name, risk_score, risk_band, predicted_flag
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        predictions
    )
    conn.commit()
    conn.close()
    logger.info(f"Inserted {len(predictions):,} predictions into fact_prediction.")
