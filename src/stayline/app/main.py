"""
src/stayline/app/main.py
--------------------------
Main Streamlit entry point.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="Stayline Retention Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit defaults to make it full screen
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        iframe {
            border: none;
            height: 100vh !important;
        }
    </style>
""", unsafe_allow_html=True)

# Load the combined Stitch UI HTML
html_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "app", "index.html")
with open(html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Render it full screen
components.html(html_content, height=1200, scrolling=True)
