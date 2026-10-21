from pathlib import Path

import pandas as pd
import streamlit as st

from utils.csv_manager import EmployeeManager, JobRequirementManager, SkillAssessmentManager
from utils.charting import require_plotly
from utils.page_components import make_report, render_crud_page

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Skill Assessments | Workforce Skill Gap", page_icon="🧭", layout="wide")
px = require_plotly()
manager = SkillAssessmentManager(ROOT / "data" / "skill_assessments.csv", ROOT / "data" / "employees.csv", ROOT / "data" / "job_requirements.csv")
employee_source = EmployeeManager(ROOT / "data" / "employees.csv")
requirement_source = JobRequirementManager(ROOT / "data" / "job_requirements.csv")


def choices(source, column, fallback):
    try:
        return sorted(source.load()[column].dropna().astype(str).unique().tolist())
    except Exception:
        return fallback


FIELDS = [
    {"name": "assess_id", "label": "Assessment ID", "default": "ASM-071"},
    {"name": "emp_id", "type": "select", "options": lambda: choices(employee_source, "emp_id", [])},
    {"name": "skill_name", "type": "select", "options": lambda: choices(requirement_source, "skill_name", [])},
    {"name": "current_level", "type": "number", "min": 0, "max": 7, "default": 3, "step": 0.1},
    {"name": "assessed_date", "type": "date"},
]


def filtered(frame, prefix):
    result = frame.copy()
    cols = st.columns(4)
    search = cols[0].text_input("Search assessment or employee ID", key=f"{prefix}_search").strip()
    employee = cols[1].selectbox("Employee", ["All"] + sorted(result["emp_id"].astype(str).unique().tolist()), key=f"{prefix}_emp")
    skill = cols[2].selectbox("Skill", ["All"] + sorted(result["skill_name"].astype(str).unique().tolist()), key=f"{prefix}_skill")
    dates = pd.to_datetime(result["assessed_date"], errors="coerce")
    first_date = dates.dropna().min()
    default_start = first_date.date() if pd.notna(first_date) else pd.Timestamp.today().date()
    start = cols[3].date_input("Assessed on or after", value=default_start, key=f"{prefix}_date")
    filters = {"Search": search or "All", "Employee": employee, "Skill": skill,
               "Date from": str(start)}
    if search:
        result = result.loc[result["assess_id"].astype(str).str.contains(search, case=False) | result["emp_id"].astype(str).str.contains(search, case=False)]
    if employee != "All":
        result = result.loc[result["emp_id"].astype(str).eq(employee)]
    if skill != "All":
        result = result.loc[result["skill_name"].astype(str).eq(skill)]
    result = result.loc[pd.to_datetime(result["assessed_date"], errors="coerce").dt.date >= start]
    return result, filters


def stats(frame):
    a, b, c, d = st.columns(4)
    a.metric("Assessments", f"{len(frame):,}")
    b.metric("Average current", f"{frame['current_level'].mean():.2f}" if len(frame) else "—")
    c.metric("Average required", f"{frame['required_level'].mean():.2f}" if len(frame) else "—")
    d.metric("Average gap", f"{frame['gap'].mean():.2f}" if len(frame) else "—")
    st.caption("Required level is looked up from the employee's job role and selected skill. Gap is always calculated as required level − current level.")


def charts(frame):
    if frame.empty:
        st.info("No assessments match these filters.")
        return
    left, right = st.columns(2)
    gaps = frame.groupby("skill_name", as_index=False)["gap"].mean().sort_values("gap", ascending=False)
    left.plotly_chart(px.bar(gaps, x="skill_name", y="gap", color="gap", title="Average gap per skill", text_auto=".2f"), use_container_width=True)
    by_date = frame.assign(assessed_date=pd.to_datetime(frame["assessed_date"], errors="coerce")).groupby("assessed_date", as_index=False)["gap"].mean().sort_values("assessed_date")
    right.plotly_chart(px.line(by_date, x="assessed_date", y="gap", markers=True, title="Average gap over time"), use_container_width=True)


def report(frame, filters):
    metrics = {"assessment_count": len(frame), "average_current_level": round(float(frame["current_level"].mean()), 2) if len(frame) else 0,
               "average_required_level": round(float(frame["required_level"].mean()), 2) if len(frame) else 0,
               "average_gap": round(float(frame["gap"].mean()), 2) if len(frame) else 0}
    return make_report("Skill assessment", frame, filters, metrics)


render_crud_page(title="Skill Assessments", subtitle="Record current capability, compare it with mapped O*NET requirements, and track the calculated gap.",
                 manager=manager, fields=FIELDS, filter_func=filtered, chart_func=charts, stats_func=stats, export_summary=report)
