"""Optional redirect entry point. Home.py is the recommended Streamlit entry point."""
import streamlit as st

st.set_page_config(page_title="Workforce Skill Gap", page_icon="📊", layout="wide")
st.title("Workforce Skill Gap & Training Recommendation")
st.write("Open the full dashboard and data-management pages.")
if st.button("Open the Workforce Dashboard", type="primary"):
    st.switch_page("Home.py")
st.caption("The recommended launch command is `streamlit run Home.py`.")
