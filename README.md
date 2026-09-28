# Stayline Retention Intelligence

Stayline Retention Intelligence is a full-stack analytical platform designed to monitor subscriber attrition risk, identify actionable retention opportunities, and simulate the ROI of intervention campaigns. 

Built with a fast, modern tech stack (Python, FastAPI, and Tailwind CSS), Stayline provides real-time telemetry, predictive cohort intelligence, and retention planning tools.

---

## 🌟 Features

- **Command Center:** Real-time subscriber churn pulse, monitoring total subscribers, MRR, churn-lost MRR, and attrition across contract tiers.
- **Segment Explorer:** Multi-dimensional heatmap analyzing attrition concentration across contract tiers and tenure tranches. Identify high-severity clusters causing preventable MRR churn.
- **Risk Watchlist:** View prioritized high-risk subscribers. Review their predicted churn probability (calibrated via XGBoost/Random Forest models) and immediately take action, such as offering a Loyalty Shield or assigning to a VIP Escalation Desk.
- **Retention Planner:** A decision engine to simulate intervention unit economics. Adjust the offer cost and expected save rate to find the optimal risk threshold (θ) that maximizes Net Impact ROI.
- **Model Lab & Data Health:** Review ML model metrics (AUC-ROC, Precision, F1) and live warehouse data ingestion health.

---

## 🏗️ Architecture

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python)
  - Provides REST API endpoints querying a locally built SQLite Data Warehouse.
  - Exposes aggregated KPIs, ML predictions, and live segment cuts.
- **Frontend:** Single Page Application (HTML / Vanilla JS / Tailwind CSS)
  - Implements the premium Google Stitch "Slate Mosaic" design system.
  - Zero build step for the frontend, uses Tailwind CDN.
- **Data Pipeline:** Custom Python pipeline extracting raw data, engineering features, and scoring subscribers with an XGBoost Classifier, persisting into a Star Schema SQLite DB.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- `pip`

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone <your-repo-url>
cd stayline
pip install -e .
pip install fastapi uvicorn
```

### 2. Build the Data Warehouse & Run Models

Before starting the UI, you need to ingest the data and run the ML models:

```bash
# 1. Clean the raw data
python -m stayline clean

# 2. Engineer features
python -m stayline engineer

# 3. Build the SQLite warehouse (creates the DB in data/warehouse.db)
python -m stayline build-warehouse

# 4. Train the ML models and generate predictions
python -m stayline train
```

### 3. Start the Dashboard

Run the FastAPI backend server:

```bash
python -m stayline.app.api
# or run via uvicorn directly:
# uvicorn stayline.app.api:app --reload --host 127.0.0.1 --port 8000
```

Open your browser to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 📂 Project Structure

```text
stayline/
├── app/
│   └── index.html                # Main Frontend Dashboard (SPA)
├── data/                         # Raw CSVs, processed data, and warehouse.db
├── sql/                          # SQL schemas and views
├── src/
│   └── stayline/
│       ├── app/
│       │   └── api.py            # FastAPI Backend Server
│       ├── modeling/             # Scikit-learn/XGBoost training pipelines
│       ├── stats/                # Statistical analysis modules
│       ├── warehouse.py          # SQLite DB Builder
│       └── ...
├── pyproject.toml                # Project metadata and dependencies
└── README.md                     # You are here
```

---

## 🛠️ API Endpoints

The FastAPI server exposes several key endpoints used by the dashboard:

- `GET /api/command-center` - Core KPIs and top risks
- `GET /api/segment-explorer` - Heatmap data and drilldown charts
- `GET /api/watchlist` - Paginated predictions with risk scores
- `GET /api/watchlist/{subscriber_id}` - Detailed view for a specific subscriber
- `GET /api/retention-planner` - Dynamic ROI and impact calculations
- `GET /api/model-lab` - Historical model performance metrics
- `GET /api/data-health` - Live table row counts

---

## 📄 License

This project is licensed under the MIT License.
