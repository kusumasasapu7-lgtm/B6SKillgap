from pathlib import Path
import pandas as pd
import streamlit as st
from utils.csv_manager import JobRequirementManager
from utils.charting import require_plotly
from utils.page_components import make_report, render_crud_page

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Job Requirements | Workforce Skill Gap", page_icon="🧩", layout="wide")
px = require_plotly()
manager = JobRequirementManager(ROOT / "data" / "job_requirements.csv")

FIELDS = [
    {"name": "req_id", "label": "Requirement ID", "default": "REQ-036"},
    {"name": "job_role", "type": "select", "options": ["Biological Technicians", "General and Operations Managers", "Medical Scientists, Except Epidemiologists", "Industrial Production Managers", "Sales Representatives, Wholesale and Manufacturing, Technical and Scientific Products", "Sales Managers", "Human Resources Specialists"]},
    {"name": "industry", "type": "select", "options": ["Life Sciences & Research", "Commercial Operations", "Manufacturing & Operations", "Healthcare & Life Sciences", "Business Services", "Unknown"]},
    {"name": "skill_name", "type": "select", "options": ["Active Listening", "Critical Thinking", "Reading Comprehension", "Speaking", "Active Learning"]},
    {"name": "min_level", "type": "number", "min": 0, "max": 7, "default": 4, "step": 0.01},
    {"name": "demand", "type": "number", "min": 0, "max": 100, "default": 70, "step": 1},
    {"name": "avg_salary", "type": "number", "min": 0, "max": 100000000, "default": 0, "step": 100},
]


def filtered(frame, prefix):
    result = frame.copy()
    cols = st.columns(4)
    search = cols[0].text_input("Search requirements", key=f"{prefix}_search").strip()
    filters = {"Search": search or "All"}
    for index, (column, label) in enumerate([("industry", "Industry"), ("job_role", "Job role"), ("skill_name", "Skill")], start=1):
        value = cols[index].selectbox(label, ["All"] + sorted(result[column].astype(str).unique().tolist()), key=f"{prefix}_{column}")
        filters[label] = value
        if value != "All":
            result = result.loc[result[column].astype(str).eq(value)]
    if search:
        mask = result["job_role"].astype(str).str.contains(search, case=False) | result["skill_name"].astype(str).str.contains(search, case=False) | result["industry"].astype(str).str.contains(search, case=False)
        result = result.loc[mask]
    return result, filters


def stats(frame):
    a, b, c, d = st.columns(4)
    a.metric("Requirements", f"{len(frame):,}")
    b.metric("Average salary", f"{frame['avg_salary'].mean():,.0f}" if len(frame) else "—")
    c.metric("Average demand", f"{frame['demand'].mean():.1f}" if len(frame) else "—")
    d.metric("Highest-demand skill", frame.loc[frame["demand"].idxmax(), "skill_name"] if len(frame) else "—")
    st.caption("Demand is O*NET's standardized Importance rating (0–100). Minimum level converts O*NET's standardized Level rating to the original 0–7 range.")


def charts(frame):
    if frame.empty:
        st.info("No requirements match these filters.")
        return
    left, right = st.columns(2)
    demand = frame.groupby("skill_name", as_index=False)["demand"].mean()
    left.plotly_chart(px.pie(demand, names="skill_name", values="demand", title="Demand share by skill", hole=0.35), use_container_width=True)
    industry = frame.groupby("industry", as_index=False)["skill_name"].nunique().rename(columns={"skill_name": "skills"})
    right.plotly_chart(px.bar(industry, x="industry", y="skills", color="industry", title="Skills per industry", text_auto=True), use_container_width=True)


def report(frame, filters):
    metrics = {"requirement_count": len(frame), "average_salary": round(float(frame["avg_salary"].mean()), 2) if len(frame) else 0,
               "average_demand": round(float(frame["demand"].mean()), 2) if len(frame) else 0,
               "highest_demand_skill": str(frame.loc[frame["demand"].idxmax(), "skill_name"]) if len(frame) else "—"}
    return make_report("Job requirements", frame, filters, metrics)


render_crud_page(title="Job Requirements", subtitle="Maintain role-level skill standards, demand signals, and illustrative salary benchmarks.",
                 manager=manager, fields=FIELDS, filter_func=filtered, chart_func=charts, stats_func=stats, export_summary=report)
