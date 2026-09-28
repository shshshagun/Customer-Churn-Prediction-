"""
src/stayline/modeling/keras_model.py
--------------------------------------
Train and evaluate a TensorFlow/Keras multi-layer perceptron.
"""

from __future__ import annotations

import datetime
import uuid
from pathlib import Path

import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras import Input, Model
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.layers import BatchNormalization, Dense, Dropout
from tensorflow.keras.regularizers import l2

from stayline.config import get_settings
from stayline.logging_setup import get_logger
from stayline.modeling.evaluation import evaluate_model
from stayline.modeling.preprocessing import get_features_and_target, get_preprocessor
from stayline.warehouse import query_df, get_connection

logger = get_logger(__name__)


def build_model(input_shape: int, learning_rate: float, l2_reg: float) -> Model:
    inputs = Input(shape=(input_shape,))
    x = Dense(64, activation="relu", kernel_regularizer=l2(l2_reg))(inputs)
    x = BatchNormalization()(x)
    x = Dropout(0.3)(x)
    x = Dense(32, activation="relu", kernel_regularizer=l2(l2_reg))(x)
    x = Dropout(0.2)(x)
    outputs = Dense(1, activation="sigmoid")(x)
    
    model = Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=[tf.keras.metrics.AUC(name="auc"), tf.keras.metrics.AUC(curve="PR", name="pr_auc")],
    )
    return model


def train_keras_model(df: pd.DataFrame) -> None:
    cfg = get_settings()
    tf.keras.utils.set_random_seed(cfg.modeling.random_seed)
    
    X, y = get_features_and_target(df)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=cfg.modeling.test_size, random_state=cfg.modeling.random_seed, stratify=y
    )
    
    X_train_t, X_val, y_train_t, y_val = train_test_split(
        X_train, y_train, test_size=cfg.modeling.keras_val_split, 
        random_state=cfg.modeling.random_seed, stratify=y_train
    )
    
    preprocessor = get_preprocessor()
    X_train_t_proc = preprocessor.fit_transform(X_train_t)
    X_val_proc = preprocessor.transform(X_val)
    X_test_proc = preprocessor.transform(X_test)
    
    # Calculate class weights
    neg = (y_train_t == 0).sum()
    pos = (y_train_t == 1).sum()
    total = neg + pos
    weight_for_0 = (1 / neg) * (total / 2.0)
    weight_for_1 = (1 / pos) * (total / 2.0)
    class_weight = {0: weight_for_0, 1: weight_for_1}
    
    model = build_model(X_train_t_proc.shape[1], cfg.modeling.keras_learning_rate, cfg.modeling.keras_l2)
    
    callbacks = [
        EarlyStopping(monitor="val_pr_auc", mode="max", patience=cfg.modeling.keras_patience, restore_best_weights=True),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=5, min_lr=1e-5),
    ]
    
    logger.info("Training Keras model...")
    model.fit(
        X_train_t_proc, y_train_t,
        epochs=cfg.modeling.keras_max_epochs,
        batch_size=cfg.modeling.keras_batch_size,
        validation_data=(X_val_proc, y_val),
        class_weight=class_weight,
        callbacks=callbacks,
        verbose=0
    )
    
    y_prob = model.predict(X_test_proc).flatten()
    y_pred = (y_prob > 0.5).astype(int)
    
    test_metrics = evaluate_model(y_test, y_pred, y_prob)
    
    run_id = str(uuid.uuid4())
    cfg.models_dir.mkdir(parents=True, exist_ok=True)
    model_path = cfg.models_dir / f"tf_mlp_{run_id}.keras"
    model.save(model_path)
    
    # Also save the preprocessor so we can score later
    import joblib
    preprocessor_path = cfg.models_dir / f"tf_mlp_preprocessor_{run_id}.joblib"
    joblib.dump(preprocessor, preprocessor_path)
    
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO model_run (
            run_id, model_name, trained_at, seed, test_auc, test_pr_auc, 
            test_recall, test_precision, test_f1, test_brier, threshold, artifact_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id, "tf_mlp", datetime.datetime.utcnow().isoformat() + "Z", cfg.modeling.random_seed,
            test_metrics["roc_auc"], test_metrics["pr_auc"], test_metrics["recall"],
            test_metrics["precision"], test_metrics["f1"], test_metrics["brier"],
            0.5, str(model_path)
        )
    )
    conn.commit()
    conn.close()
    
def run() -> None:
    df = query_df("SELECT * FROM vw_subscriber_360")
    logger.info(f"Loaded {len(df):,} rows for training keras model.")
    train_keras_model(df)
