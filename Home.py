from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from utils.csv_manager import (EmployeeManager, JobRequirementManager, SkillAssessmentManager,
                               TrainingCourseManager, CSVStorageError)
from utils.charting import require_plotly

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Workforce Skill Gap", page_icon="📊", layout="wide")
px = require_plotly()


@st.cache_data(show_spinner=False)
def load_data(refresh_token: int):
    """Cache cleaned CSV data by a token that CRUD pages invalidate after writes."""
    employees = EmployeeManager(ROOT / "data" / "employees.csv").load()
    requirements = JobRequirementManager(ROOT / "data" / "job_requirements.csv").load()
    assessments = SkillAssessmentManager(ROOT / "data" / "skill_assessments.csv").load()
    courses = TrainingCourseManager(ROOT / "data" / "training_courses.csv").load()
    return employees, requirements, assessments, courses


st.markdown("## Workforce capability, made actionable")
st.title("Workforce Skill Gap & Training Recommendation")
st.write("A CSV-backed workforce analytics workspace that connects employee roles, current skill assessments, occupational requirements, and targeted learning options.")

try:
    employees, requirements, assessments, courses = load_data(st.session_state.get("data_refresh_token", 0))
except CSVStorageError as exc:
    st.error(str(exc))
    st.info("Check that all four CSV files are present under the project's data folder and have their expected headers.")
    st.stop()

metric_cols = st.columns(4)
metric_cols[0].metric("Employees", f"{len(employees):,}")
metric_cols[1].metric("Skills assessed", f"{len(assessments):,}")
metric_cols[2].metric("Job requirements", f"{len(requirements):,}")
metric_cols[3].metric("Training options", f"{len(courses):,}")

sdg_left, sdg_right = st.columns(2)
with sdg_left:
    st.info("**SDG 8 · Decent Work and Economic Growth**\n\nSupports workforce development by making capability gaps visible and linking them to learning options.")
with sdg_right:
    st.info("**SDG 4 · Quality Education**\n\nEncourages accessible, relevant upskilling and clear learning pathways for employees.")

# Join employee assessments to job-role standards and the curated course catalogue.
enriched = assessments.merge(employees[["emp_id", "department", "job_role"]], on="emp_id", how="left", validate="many_to_one")
enriched = enriched.merge(requirements[["job_role", "skill_name", "industry", "demand", "avg_salary"]],
                          on=["job_role", "skill_name"], how="left", validate="many_to_one")

st.subheader("Explore the workforce skill picture")
filter_cols = st.columns(4)
departments = ["All"] + sorted(enriched["department"].dropna().astype(str).unique().tolist())
roles = ["All"] + sorted(enriched["job_role"].dropna().astype(str).unique().tolist())
skill_values = ["All"] + sorted(enriched["skill_name"].dropna().astype(str).unique().tolist())
industries = ["All"] + sorted(enriched["industry"].dropna().astype(str).unique().tolist())
selected_department = filter_cols[0].selectbox("Department", departments, key="home_department")
selected_role = filter_cols[1].selectbox("Job role", roles, key="home_role")
selected_skill = filter_cols[2].selectbox("Skill", skill_values, key="home_skill")
selected_industry = filter_cols[3].selectbox("Industry", industries, key="home_industry")

view = enriched.copy()
for column, selected in [("department", selected_department), ("job_role", selected_role),
                         ("skill_name", selected_skill), ("industry", selected_industry)]:
    if selected != "All":
        view = view.loc[view[column].astype(str).eq(selected)]
filter_summary = {"Department": selected_department, "Job role": selected_role,
                  "Skill": selected_skill, "Industry": selected_industry}

gap_by_skill = view.groupby("skill_name", as_index=False).agg(
    average_gap=("gap", "mean"), average_current_level=("current_level", "mean"),
    average_required_level=("required_level", "mean"), average_demand=("demand", "mean"),
    assessment_count=("assess_id", "count"),
).sort_values("average_gap", ascending=False)
average_gap = float(view["gap"].mean()) if len(view) else 0.0
gap_col, chart_col = st.columns([1, 2])
gap_col.metric("Average skill gap in this view", f"{average_gap:.2f}" if len(view) else "—")
gap_col.caption("Gap = required level − current level. Negative values mean the assessed level is above the mapped requirement.")
with chart_col:
    if gap_by_skill.empty:
        st.info("No assessment rows match the selected filters.")
    else:
        fig = px.bar(gap_by_skill, x="skill_name", y="average_gap", color="average_demand",
                     hover_data=["assessment_count", "average_current_level", "average_required_level"],
                     title="Average skill gap by skill · color shows O*NET demand", text_auto=".2f",
                     color_continuous_scale="Tealgrn")
        st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("High-demand skills")
    high_demand = requirements.copy()
    if selected_role != "All":
        high_demand = high_demand.loc[high_demand["job_role"].eq(selected_role)]
    if selected_skill != "All":
        high_demand = high_demand.loc[high_demand["skill_name"].eq(selected_skill)]
    if selected_industry != "All":
        high_demand = high_demand.loc[high_demand["industry"].eq(selected_industry)]
    high_demand = high_demand.groupby("skill_name", as_index=False)["demand"].mean().sort_values("demand", ascending=False).head(5)
    st.dataframe(high_demand.rename(columns={"demand": "mean O*NET importance (0–100)"}), hide_index=True, use_container_width=True)
with right:
    st.subheader("Linked data at a glance")
    st.write("**Employee → assessment:** each assessment joins through `emp_id`.\n\n**Role → standard:** each requirement joins through `job_role` and `skill_name`.\n\n**Skill → learning:** course suggestions join through `skill_name`.")

st.subheader("Rule-based training recommendations")
st.caption("Read-only recommendations. Each skill's average gap is matched to a course with the same skill label. The transparent score gives 50% weight to gap relevance, 25% to rating, 15% to lower cost, and 10% to shorter duration. This is a rule, not a machine-learning model.")
if gap_by_skill.empty or courses.empty:
    st.info("Recommendations appear when both assessments and matching courses are available.")
else:
    needs = gap_by_skill.loc[gap_by_skill["average_gap"] > 0].copy()
    if needs.empty:
        st.success("No positive average skill gap remains in this filtered view.")
    else:
        gap_span = float(needs["average_gap"].max() - needs["average_gap"].min())
        needs["relevance"] = 1.0 if gap_span == 0 else (needs["average_gap"] - needs["average_gap"].min()) / gap_span
        ranked = needs.merge(courses, on="skill_name", how="inner", validate="one_to_many")
        cost_max = max(float(ranked["cost"].max()), 1.0)
        duration_max = max(float(ranked["duration_hrs"].max()), 1.0)
        ranked["recommendation_score"] = (0.50 * ranked["relevance"] + 0.25 * ranked["rating"] / 5
                                          + 0.15 * (1 - ranked["cost"] / cost_max)
                                          + 0.10 * (1 - ranked["duration_hrs"] / duration_max))
        ranked = ranked.sort_values(["recommendation_score", "average_gap", "rating"], ascending=False).head(10)
        ranked = ranked.rename(columns={"average_gap": "skill_gap", "course_name": "recommended_course",
                                        "duration_hrs": "duration_hours", "cost": "estimated_cost"})
        st.dataframe(ranked[["skill_gap", "skill_name", "recommended_course", "provider", "rating",
                             "estimated_cost", "duration_hours", "recommendation_score"]],
                     hide_index=True, use_container_width=True,
                     column_config={"skill_gap": st.column_config.NumberColumn("Average skill gap", format="%.2f"),
                                    "estimated_cost": st.column_config.NumberColumn("Estimated cost", format="%.0f"),
                                    "recommendation_score": st.column_config.ProgressColumn("Rule score", min_value=0, max_value=1, format="%.2f")})

with st.expander("Data quality and missing-value strategy"):
    st.write("The shared `DataCleaner` trims whitespace, normalizes mapped role spelling, removes duplicate rows and duplicate IDs, coerces numeric types, and drops records outside declared ranges. Missing numeric values are median-imputed (zero when an entire numeric column is missing); missing categories become `Unknown`; invalid dates are coerced to missing and remain flagged as `NaT` rather than being guessed. UI forms reject missing required fields, invalid IDs, and invalid ranges.")
    st.write("Employee names are anonymous IDs. Skill self-assessment levels are generated teaching examples, not observed employee performance.")

st.caption("The bundled data is a teaching sample, not a current workforce report. Salary units are annualized source income units and are not labeled with a currency in the source sample.")
