from pathlib import Path

import pandas as pd
import streamlit as st

from utils.csv_manager import EmployeeManager
from utils.charting import require_plotly
from utils.page_components import make_report, render_crud_page

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Employees | Workforce Skill Gap", page_icon="👥", layout="wide")
px = require_plotly()
manager = EmployeeManager(ROOT / "data" / "employees.csv")

FIELDS = [
    {"name": "emp_id", "label": "Employee ID", "default": "EMP-031"},
    {"name": "name", "label": "Anonymous name", "default": "Employee_031"},
    {"name": "department", "type": "select", "options": ["Research & Development", "Sales", "Human Resources", "Unknown"]},
    {"name": "job_role", "type": "select", "options": [
        "Biological Technicians", "General and Operations Managers", "Medical Scientists, Except Epidemiologists",
        "Industrial Production Managers", "Sales Representatives, Wholesale and Manufacturing, Technical and Scientific Products",
        "Sales Managers", "Human Resources Specialists"]},
    {"name": "experience_yrs", "type": "number", "min": 0, "max": 60, "default": 0, "step": 0.5},
    {"name": "education_level", "type": "select", "options": ["Below College", "College", "Bachelor's", "Master's", "Doctoral", "Unknown"]},
    {"name": "salary", "type": "number", "min": 0, "max": 100000000, "default": 0, "step": 100},
]


def filtered(frame: pd.DataFrame, prefix: str):
    cols = st.columns(4)
    search = cols[0].text_input("Search name", key=f"{prefix}_search").strip()
    result = frame.copy()
    filters = {"Name search": search or "All"}
    for col, label in [("department", "Department"), ("job_role", "Job role"), ("education_level", "Education")]:
        choices = ["All"] + sorted(result[col].dropna().astype(str).unique().tolist())
        value = cols[("department", "job_role", "education_level").index(col) + 1].selectbox(label, choices, key=f"{prefix}_{col}")
        filters[label] = value
        if value != "All":
            result = result.loc[result[col].astype(str).eq(value)]
    if search:
        result = result.loc[result["name"].astype(str).str.contains(search, case=False, na=False)]
    return result, filters


def stats(frame: pd.DataFrame):
    a, b, c = st.columns(3)
    a.metric("Employee count", f"{len(frame):,}")
    b.metric("Average salary", f"{frame['salary'].mean():,.0f}" if len(frame) else "—")
    c.metric("Average experience", f"{frame['experience_yrs'].mean():.1f} yrs" if len(frame) else "—")
    if len(frame):
        with st.expander("Group-by summaries"):
            st.dataframe(frame.groupby("department", as_index=False)["salary"].mean().rename(columns={"salary": "average_salary"}), hide_index=True, use_container_width=True)
            st.dataframe(frame.groupby("job_role").size().reset_index(name="employee_count"), hide_index=True, use_container_width=True)


def charts(frame: pd.DataFrame):
    if frame.empty:
        st.info("No employees match these filters.")
        return
    left, right = st.columns(2)
    with left:
        by_department = frame.groupby("department", as_index=False).size().rename(columns={"size": "employees"})
        st.plotly_chart(px.bar(by_department, x="department", y="employees", color="department", title="Employees per department", text_auto=True), use_container_width=True)
    with right:
        st.plotly_chart(px.histogram(frame, x="experience_yrs", nbins=10, title="Experience distribution", labels={"experience_yrs": "Years of experience"}), use_container_width=True)


def report(frame, filters):
    metrics = {"employee_count": len(frame), "average_salary": round(float(frame["salary"].mean()), 2) if len(frame) else 0,
               "average_experience_yrs": round(float(frame["experience_yrs"].mean()), 2) if len(frame) else 0}
    return make_report("Employee", frame, filters, metrics)


render_crud_page(title="Employee Data", subtitle="Manage the anonymous workforce sample and explore department, role, and experience patterns.",
                 manager=manager, fields=FIELDS, filter_func=filtered, chart_func=charts, stats_func=stats, export_summary=report)
