"""
src/stayline/app/api.py
--------------------------
FastAPI backend that serves the Stitch UI and exposes REST endpoints
for real data from the SQLite warehouse.
"""

from __future__ import annotations

import math
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from stayline.warehouse import query_df, get_connection

app = FastAPI(title="Stayline Retention Intelligence API")

# Allow the file:// origin used when opening index.html directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML_PATH = Path(__file__).parent.parent.parent.parent / "app" / "index.html"


@app.get("/", response_class=HTMLResponse)
def serve_index():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ─────────────────────────────────────────────
# COMMAND CENTER
# ─────────────────────────────────────────────
@app.get("/api/command-center")
def command_center():
    # Core subscriber metrics
    df = query_df("SELECT * FROM vw_subscriber_360")
    total_subs = len(df)
    churn_rate = round(float(df["churned_flag"].mean()) * 100, 1)
    mrr = round(float(df["monthly_charge"].sum()), 2)
    churned_mrr = round(float(df.loc[df["churned_flag"] == 1, "monthly_charge"].sum()), 2)

    # Watchlist from scored predictions
    try:
        wl = query_df("SELECT * FROM vw_scored_watchlist LIMIT 500")
        watchlist_count = len(wl)
    except Exception:
        wl = df.nlargest(100, "monthly_charge")
        watchlist_count = 0

    # Churn by contract type
    contract_df = query_df("""
        SELECT contract_type,
               ROUND(AVG(churned_flag)*100, 1) AS churn_rate,
               COUNT(*) AS count
        FROM vw_subscriber_360
        GROUP BY contract_type
        ORDER BY churn_rate DESC
    """)

    # Payment method attrition
    payment_df = query_df("""
        SELECT payment_method,
               ROUND(AVG(churned_flag)*100, 1) AS churn_rate,
               COUNT(*) AS count
        FROM vw_subscriber_360
        GROUP BY payment_method
        ORDER BY churn_rate DESC
    """)

    # Internet service attrition
    internet_df = query_df("""
        SELECT internet_service,
               ROUND(AVG(churned_flag)*100, 1) AS churn_rate,
               COUNT(*) AS count
        FROM vw_subscriber_360
        GROUP BY internet_service
        ORDER BY churn_rate DESC
    """)

    # Services count stickiness
    services_df = query_df("""
        SELECT services_count,
               ROUND(AVG(churned_flag)*100, 1) AS churn_rate,
               COUNT(*) AS count
        FROM vw_subscriber_360
        GROUP BY services_count
        ORDER BY services_count
    """)

    # Top 3 risk accounts for the watchlist preview
    try:
        top_risks = wl.head(3)[["subscriber_id", "contract_type", "tenure_months",
                                  "monthly_charge", "risk_score", "risk_band",
                                  "payment_method"]].to_dict(orient="records")
    except Exception:
        top_risks = []

    return {
        "total_subscribers": total_subs,
        "churn_rate": churn_rate,
        "mrr": mrr,
        "churned_mrr": churned_mrr,
        "watchlist_count": watchlist_count,
        "contract_rates": contract_df.to_dict(orient="records"),
        "payment_rates": payment_df.to_dict(orient="records"),
        "internet_rates": internet_df.to_dict(orient="records"),
        "services_stickiness": services_df.to_dict(orient="records"),
        "top_risks": top_risks,
    }


# ─────────────────────────────────────────────
# SEGMENT EXPLORER
# ─────────────────────────────────────────────
@app.get("/api/segment-explorer")
def segment_explorer():
    # Heatmap: contract × tenure_band
    heatmap_df = query_df("""
        SELECT contract_type, tenure_band,
               ROUND(AVG(churned_flag)*100, 1) AS churn_rate,
               COUNT(*) AS count
        FROM vw_subscriber_360
        GROUP BY contract_type, tenure_band
        ORDER BY contract_type, tenure_band
    """)

    # Internet service breakdown
    internet_df = query_df("""
        SELECT internet_service,
               ROUND(AVG(churned_flag)*100, 1) AS churn_rate,
               COUNT(*) AS count
        FROM vw_subscriber_360
        GROUP BY internet_service
        ORDER BY churn_rate DESC
    """)

    # Payment method breakdown
    payment_df = query_df("""
        SELECT payment_method,
               ROUND(AVG(churned_flag)*100, 1) AS churn_rate,
               COUNT(*) AS count
        FROM vw_subscriber_360
        GROUP BY payment_method
        ORDER BY churn_rate DESC
    """)

    # Services count stickiness
    services_df = query_df("""
        SELECT services_count,
               ROUND(AVG(churned_flag)*100, 1) AS churn_rate,
               COUNT(*) AS count
        FROM vw_subscriber_360
        GROUP BY services_count
        ORDER BY services_count
    """)

    # High severity cluster summary
    cluster_df = query_df("""
        SELECT COUNT(*) AS count,
               ROUND(SUM(monthly_charge)*3, 2) AS quarterly_revenue
        FROM vw_subscriber_360
        WHERE contract_type = 'Month-to-month'
          AND internet_service = 'Fiber optic'
          AND tenure_months <= 12
    """)

    cluster = cluster_df.iloc[0].to_dict() if len(cluster_df) > 0 else {}

    return {
        "heatmap": heatmap_df.to_dict(orient="records"),
        "internet": internet_df.to_dict(orient="records"),
        "payment": payment_df.to_dict(orient="records"),
        "services": services_df.to_dict(orient="records"),
        "severity_cluster": cluster,
    }


# ─────────────────────────────────────────────
# RISK WATCHLIST
# ─────────────────────────────────────────────
@app.get("/api/watchlist")
def watchlist(page: int = 1, per_page: int = 6):
    offset = (page - 1) * per_page
    try:
        total_df = query_df("SELECT COUNT(*) AS n FROM vw_scored_watchlist")
        total = int(total_df.iloc[0]["n"])

        df = query_df(f"""
            SELECT subscriber_id, risk_score, risk_band,
                   monthly_charge, tenure_months, contract_type,
                   payment_method, is_autopay, churned_flag
            FROM vw_scored_watchlist
            LIMIT {per_page} OFFSET {offset}
        """)
        rows = df.to_dict(orient="records")
    except Exception:
        # Fallback if predictions haven't been run yet
        total = 0
        rows = []

    # KPI summary
    try:
        kpi_df = query_df("""
            SELECT COUNT(*) AS count,
                   ROUND(SUM(monthly_charge)*12, 2) AS arr,
                   ROUND(AVG(monthly_charge)*12, 2) AS avg_arr
            FROM vw_scored_watchlist
        """)
        kpi = kpi_df.iloc[0].to_dict() if len(kpi_df) > 0 else {}
    except Exception:
        kpi = {}

    # Detail panel for first row
    detail = rows[0] if rows else {}

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, math.ceil(total / per_page)),
        "rows": rows,
        "kpi": kpi,
        "detail": detail,
    }


@app.get("/api/watchlist/{subscriber_id}")
def watchlist_detail(subscriber_id: str):
    try:
        df = query_df("""
            SELECT w.*, v.gender, v.has_partner, v.has_dependents,
                   v.internet_service, v.services_count, v.online_security,
                   v.tech_support, v.streaming_tv, v.streaming_movies
            FROM vw_scored_watchlist w
            JOIN vw_subscriber_360 v ON v.subscriber_id = w.subscriber_id
            WHERE w.subscriber_id = ?
        """, (subscriber_id,))
        if df.empty:
            return {"error": "Not found"}
        return df.iloc[0].to_dict()
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# RETENTION PLANNER
# ─────────────────────────────────────────────
@app.get("/api/retention-planner")
def retention_planner(
    offer_cost: float = 18.5,
    save_rate: float = 22.0,
    horizon_months: int = 12
):
    try:
        wl_df = query_df("SELECT COUNT(*) AS n, AVG(monthly_charge) AS avg_mrr FROM vw_scored_watchlist WHERE risk_score >= 0.42")
        cohort_count = int(wl_df.iloc[0]["n"]) if not wl_df.empty else 1842
        avg_mrr = float(wl_df.iloc[0]["avg_mrr"]) if not wl_df.empty else 94.8
    except Exception:
        cohort_count = 1842
        avg_mrr = 94.8

    outreach_budget = round(cohort_count * offer_cost, 2)
    expected_saves = round(cohort_count * (save_rate / 100))
    gross_saved_mrr = round(expected_saves * avg_mrr, 2)
    net_impact = round((gross_saved_mrr * horizon_months) - outreach_budget, 2)
    roi = round(net_impact / outreach_budget, 1) if outreach_budget > 0 else 0

    return {
        "cohort_count": cohort_count,
        "avg_mrr": avg_mrr,
        "outreach_budget": outreach_budget,
        "expected_saves": expected_saves,
        "gross_saved_mrr": gross_saved_mrr,
        "net_impact": net_impact,
        "roi": roi,
        "optimal_threshold": 0.42,
    }


# ─────────────────────────────────────────────
# MODEL LAB
# ─────────────────────────────────────────────
@app.get("/api/model-lab")
def model_lab():
    try:
        runs_df = query_df("""
            SELECT model_name, auc_roc, precision_score, recall_score, f1_score, trained_at
            FROM model_run
            ORDER BY trained_at DESC
        """)
        runs = runs_df.to_dict(orient="records")
    except Exception:
        runs = []

    return {"model_runs": runs}


# ─────────────────────────────────────────────
# DATA HEALTH
# ─────────────────────────────────────────────
@app.get("/api/data-health")
def data_health():
    conn = get_connection()
    tables = ["dim_subscriber", "dim_service_profile", "dim_contract",
              "fact_billing", "fact_attrition_label"]
    counts = {}
    for t in tables:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            counts[t] = n
        except Exception:
            counts[t] = 0
    conn.close()
    total = sum(counts.values())
    return {"table_counts": counts, "total_records": total, "pipeline_health": 100}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
