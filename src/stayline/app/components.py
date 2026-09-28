"""
src/stayline/app/components.py
--------------------------------
UI components for the Streamlit app.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from stayline.config import get_settings
from stayline.warehouse import query_df

def apply_styling():
    """Apply custom CSS styling to match design tokens."""
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Sora:wght@600&display=swap');
        
        .metric-card {{
            background-color: #FFFFFF;
            border: 1px solid #E5E7EB;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-label {{
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            color: #6B7280;
        }}
        .metric-value {{
            font-family: 'Sora', sans-serif;
            font-size: 32px;
            font-weight: 600;
            color: #111827;
        }}
        </style>
    """, unsafe_allow_html=True)

def render_metric(label: str, value: str):
    """Renders a styled metric card."""
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def render_kpi_summary():
    """Renders the top-level KPI metrics."""
    df = query_df("SELECT * FROM vw_subscriber_360")
    total_subs = len(df)
    churn_rate = df["churned_flag"].mean()
    mrr = df["monthly_charge"].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric("Total Subscribers", f"{total_subs:,}")
    with col2:
        render_metric("Global Attrition Rate", f"{churn_rate:.1%}")
    with col3:
        render_metric("Monthly Recurring Revenue (MRR)", f"${mrr:,.0f}")
        
def render_churn_by_contract():
    """Renders a bar chart of churn by contract type."""
    df = query_df("""
        SELECT contract_type, ROUND(AVG(churned_flag)*100, 1) as churn_rate 
        FROM vw_subscriber_360 
        GROUP BY contract_type
    """)
    fig = px.bar(df, x="contract_type", y="churn_rate", title="Attrition Rate by Contract Type (%)")
    st.plotly_chart(fig, use_container_width=True)

def render_watchlist():
    """Renders the retention watchlist."""
    df = query_df("SELECT * FROM vw_scored_watchlist LIMIT 100")
    st.dataframe(df, use_container_width=True)
