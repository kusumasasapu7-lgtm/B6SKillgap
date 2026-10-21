from pathlib import Path

import pandas as pd
import streamlit as st

from utils.csv_manager import TrainingCourseManager
from utils.charting import require_plotly
from utils.page_components import make_report, render_crud_page

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Training Courses | Workforce Skill Gap", page_icon="🎓", layout="wide")
px = require_plotly()
manager = TrainingCourseManager(ROOT / "data" / "training_courses.csv")

FIELDS = [
    {"name": "course_id", "label": "Course ID", "default": "CRS-031"},
    {"name": "course_name", "label": "Course name"},
    {"name": "skill_name", "type": "select", "options": ["Active Listening", "Critical Thinking", "Reading Comprehension", "Speaking", "Active Learning"]},
    {"name": "provider", "default": "Coursera"},
    {"name": "duration_hrs", "type": "number", "min": 0.1, "max": 1000, "default": 4, "step": 0.5},
    {"name": "cost", "type": "number", "min": 0, "max": 1000000, "default": 0, "step": 1},
    {"name": "rating", "type": "number", "min": 0, "max": 5, "default": 4, "step": 0.1},
    {"name": "mode", "type": "select", "options": ["Online", "Hybrid", "In-person"]},
]


def filtered(frame, prefix):
    result = frame.copy()
    cols = st.columns(4)
    search = cols[0].text_input("Search course", key=f"{prefix}_search").strip()
    filters = {"Course search": search or "All"}
    for index, (column, label) in enumerate([("skill_name", "Skill"), ("provider", "Provider"), ("mode", "Mode")], start=1):
        value = cols[index].selectbox(label, ["All"] + sorted(result[column].astype(str).unique().tolist()), key=f"{prefix}_{column}")
        filters[label] = value
        if value != "All":
            result = result.loc[result[column].astype(str).eq(value)]
    if search:
        result = result.loc[result["course_name"].astype(str).str.contains(search, case=False, na=False)]
    return result, filters


def stats(frame):
    a, b, c, d = st.columns(4)
    a.metric("Courses", f"{len(frame):,}")
    b.metric("Average rating", f"{frame['rating'].mean():.2f}/5" if len(frame) else "—")
    c.metric("Average estimated cost", f"{frame['cost'].mean():,.0f}" if len(frame) else "—")
    d.metric("Average duration", f"{frame['duration_hrs'].mean():.1f} hrs" if len(frame) else "—")
    if len(frame):
        with st.expander("Course count by mode"):
            st.dataframe(frame.groupby("mode").size().reset_index(name="course_count"), hide_index=True, use_container_width=True)
    st.caption("Course ratings, estimated costs, durations, and recommended delivery mode are clearly identified as demo values in the README.")


def charts(frame):
    if frame.empty:
        st.info("No courses match these filters.")
        return
    left, right = st.columns(2)
    left.plotly_chart(px.pie(frame.groupby("mode", as_index=False).size(), names="mode", values="size", title="Mode distribution", hole=0.35), use_container_width=True)
    right.plotly_chart(px.scatter(frame, x="cost", y="rating", size="duration_hrs", color="skill_name", hover_name="course_name", title="Estimated cost vs rating"), use_container_width=True)


def report(frame, filters):
    metrics = {"course_count": len(frame), "average_rating": round(float(frame["rating"].mean()), 2) if len(frame) else 0,
               "average_estimated_cost": round(float(frame["cost"].mean()), 2) if len(frame) else 0,
               "average_duration_hrs": round(float(frame["duration_hrs"].mean()), 2) if len(frame) else 0}
    return make_report("Training course", frame, filters, metrics)


render_crud_page(title="Training Courses", subtitle="Curate skill-aligned learning options and compare the estimated time, cost, and learner signal.",
                 manager=manager, fields=FIELDS, filter_func=filtered, chart_func=charts, stats_func=stats, export_summary=report)
