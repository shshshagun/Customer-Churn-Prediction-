"""
src/stayline/modeling/preprocessing.py
----------------------------------------
Scikit-learn ColumnTransformer pipelines to ensure no data leakage.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, OrdinalEncoder

def get_preprocessor() -> ColumnTransformer:
    """
    Returns a ColumnTransformer for preprocessing features.
    Numerical: StandardScaler
    Categorical (unordered): OneHotEncoder
    Ordinal: OrdinalEncoder (if any)
    """
    numeric_features = [
        "tenure_months",
        "monthly_charge",
        "lifetime_billed",
        "services_count",
        "avg_monthly_spend_to_date",
        "price_vs_history_gap",
    ]
    
    categorical_features = [
        "gender",
        "is_senior",
        "has_partner",
        "has_dependents",
        "phone_service",
        "multiple_lines",
        "internet_service",
        "online_security",
        "online_backup",
        "device_protection",
        "tech_support",
        "streaming_tv",
        "streaming_movies",
        "contract_type",
        "paperless_billing",
        "payment_method",
    ]
    
    # Binary features are already 0/1, we can pass them through or scale them.
    # We will pass them through.
    binary_features = [
        "is_autopay",
        "is_new_subscriber",
        "fibre_without_support",
        "has_protection_bundle",
        "contract_commitment_months", # Ordinal, already numeric 0, 12, 24
    ]

    numeric_transformer = Pipeline(steps=[
        ("scaler", StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ("onehot", OneHotEncoder(handle_unknown="ignore", drop="first"))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
            ("passthrough", "passthrough", binary_features)
        ]
    )

    return preprocessor

def get_features_and_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Extracts features X and target y from the dataframe."""
    # Ensure no label leakage
    drop_cols = ["subscriber_id", "churned_flag", "tenure_band"]
    X = df.drop(columns=[col for col in drop_cols if col in df.columns])
    y = df["churned_flag"]
    return X, y
