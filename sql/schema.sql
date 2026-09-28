-- sql/schema.sql
-- Stayline Retention Intelligence — SQLite Data Warehouse Schema
-- =============================================================
-- Requires SQLite >= 3.25 for window functions (verified: 3.45.1).
-- All tables use snake_case column names matching the cleaned DataFrame.
-- Foreign key enforcement: enable with PRAGMA foreign_keys = ON;

PRAGMA foreign_keys = ON;

-- -------------------------------------------------------------------
-- Dimension: subscriber demographics
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_subscriber (
    subscriber_id           TEXT PRIMARY KEY NOT NULL,
    gender                  TEXT NOT NULL CHECK (gender IN ('Male', 'Female')),
    is_senior               TEXT NOT NULL CHECK (is_senior IN ('Yes', 'No')),
    has_partner             TEXT NOT NULL CHECK (has_partner IN ('Yes', 'No')),
    has_dependents          TEXT NOT NULL CHECK (has_dependents IN ('Yes', 'No')),
    tenure_months           INTEGER NOT NULL CHECK (tenure_months >= 0),
    tenure_band             TEXT NOT NULL,
    is_new_subscriber       INTEGER NOT NULL CHECK (is_new_subscriber IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_dim_subscriber_tenure ON dim_subscriber (tenure_months);
CREATE INDEX IF NOT EXISTS idx_dim_subscriber_senior ON dim_subscriber (is_senior);

-- -------------------------------------------------------------------
-- Dimension: service profile
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_service_profile (
    subscriber_id           TEXT NOT NULL REFERENCES dim_subscriber (subscriber_id),
    phone_service           TEXT NOT NULL CHECK (phone_service IN ('Yes', 'No')),
    multiple_lines          TEXT NOT NULL CHECK (multiple_lines IN ('Yes', 'No')),
    internet_service        TEXT NOT NULL CHECK (internet_service IN ('DSL', 'Fiber optic', 'No')),
    online_security         TEXT NOT NULL CHECK (online_security IN ('Yes', 'No')),
    online_backup           TEXT NOT NULL CHECK (online_backup IN ('Yes', 'No')),
    device_protection       TEXT NOT NULL CHECK (device_protection IN ('Yes', 'No')),
    tech_support            TEXT NOT NULL CHECK (tech_support IN ('Yes', 'No')),
    streaming_tv            TEXT NOT NULL CHECK (streaming_tv IN ('Yes', 'No')),
    streaming_movies        TEXT NOT NULL CHECK (streaming_movies IN ('Yes', 'No')),
    services_count          INTEGER NOT NULL CHECK (services_count >= 0),
    has_protection_bundle   INTEGER NOT NULL CHECK (has_protection_bundle IN (0, 1)),
    fibre_without_support   INTEGER NOT NULL CHECK (fibre_without_support IN (0, 1)),
    PRIMARY KEY (subscriber_id)
);

-- -------------------------------------------------------------------
-- Dimension: contract and payment
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_contract (
    subscriber_id               TEXT NOT NULL REFERENCES dim_subscriber (subscriber_id),
    contract_type               TEXT NOT NULL CHECK (contract_type IN ('Month-to-month', 'One year', 'Two year')),
    paperless_billing           TEXT NOT NULL CHECK (paperless_billing IN ('Yes', 'No')),
    payment_method              TEXT NOT NULL,
    is_autopay                  INTEGER NOT NULL CHECK (is_autopay IN (0, 1)),
    contract_commitment_months  INTEGER NOT NULL CHECK (contract_commitment_months IN (0, 12, 24)),
    PRIMARY KEY (subscriber_id)
);

CREATE INDEX IF NOT EXISTS idx_dim_contract_type ON dim_contract (contract_type);
CREATE INDEX IF NOT EXISTS idx_dim_contract_autopay ON dim_contract (is_autopay);

-- -------------------------------------------------------------------
-- Fact: billing
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_billing (
    subscriber_id               TEXT NOT NULL REFERENCES dim_subscriber (subscriber_id),
    monthly_charge              REAL NOT NULL CHECK (monthly_charge > 0),
    lifetime_billed             REAL NOT NULL CHECK (lifetime_billed >= 0),
    avg_monthly_spend_to_date   REAL NOT NULL,
    price_vs_history_gap        REAL NOT NULL,
    PRIMARY KEY (subscriber_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_billing_monthly ON fact_billing (monthly_charge);

-- -------------------------------------------------------------------
-- Fact: attrition label (ground truth)
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_attrition_label (
    subscriber_id   TEXT NOT NULL REFERENCES dim_subscriber (subscriber_id),
    churned_flag    INTEGER NOT NULL CHECK (churned_flag IN (0, 1)),
    PRIMARY KEY (subscriber_id)
);

-- -------------------------------------------------------------------
-- Fact: model predictions (long format — one row per subscriber per model run)
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_prediction (
    run_id          TEXT NOT NULL,
    subscriber_id   TEXT NOT NULL REFERENCES dim_subscriber (subscriber_id),
    model_name      TEXT NOT NULL,
    risk_score      REAL NOT NULL CHECK (risk_score BETWEEN 0.0 AND 1.0),
    risk_band       TEXT NOT NULL CHECK (risk_band IN ('High', 'Medium', 'Low')),
    predicted_flag  INTEGER NOT NULL CHECK (predicted_flag IN (0, 1)),
    PRIMARY KEY (run_id, subscriber_id, model_name)
);

CREATE INDEX IF NOT EXISTS idx_fact_pred_run   ON fact_prediction (run_id);
CREATE INDEX IF NOT EXISTS idx_fact_pred_model  ON fact_prediction (model_name);
CREATE INDEX IF NOT EXISTS idx_fact_pred_band   ON fact_prediction (risk_band);
CREATE INDEX IF NOT EXISTS idx_fact_pred_score  ON fact_prediction (risk_score DESC);

-- -------------------------------------------------------------------
-- Metadata: model run registry
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS model_run (
    run_id          TEXT PRIMARY KEY NOT NULL,
    model_name      TEXT NOT NULL,
    trained_at      TEXT NOT NULL,
    seed            INTEGER NOT NULL,
    cv_auc_mean     REAL,
    cv_auc_std      REAL,
    cv_pr_auc_mean  REAL,
    cv_pr_auc_std   REAL,
    test_auc        REAL,
    test_pr_auc     REAL,
    test_recall     REAL,
    test_precision  REAL,
    test_f1         REAL,
    test_brier      REAL,
    threshold       REAL,
    artifact_path   TEXT
);
