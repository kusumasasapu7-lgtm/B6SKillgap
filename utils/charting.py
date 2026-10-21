"""Friendly optional-dependency handling for Plotly chart pages."""
from __future__ import annotations

import streamlit as st

try:
    import plotly.express as _plotly_express
except ModuleNotFoundError:
    _plotly_express = None


def require_plotly():
    """Return Plotly Express or stop with setup guidance instead of a traceback."""
    if _plotly_express is None:
        st.error("Plotly is required to display this dashboard's charts.")
        st.info("From the project folder, run `python -m pip install -r requirements.txt`, then restart Streamlit.")
        st.stop()
    return _plotly_express
