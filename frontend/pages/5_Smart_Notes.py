import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api import get_spaces
from utils.ui import render_sidebar
from utils.notes_component import render_smart_notes_view

st.set_page_config(page_title="Smart Notes", page_icon="📓", layout="wide")

if "token" not in st.session_state and "token" in st.query_params:
    st.session_state["token"] = st.query_params["token"]
    st.session_state["user"] = {"name": "Vinaval Student", "email": "student@vinaval.ai"}

if "token" not in st.session_state:
    st.warning("⚠️ Please log in from the Home page first.")
    st.page_link("app.py", label="Go to Login →")
    st.stop()


render_sidebar()

st.title("📓 Smart Notes")
st.markdown(
    "Generate comprehensive, structured exam notes grounded in the syllabus or your uploaded materials. "
    "Select your Learning Space below to view and generate notes."
)

with st.spinner("Loading spaces..."):
    spaces = get_spaces()

if not spaces:
    st.info("You don't have any Learning Spaces yet. Create a space first to generate and organize notes.")
    st.page_link("pages/2_Select_Exam.py", label="➕ Create Your First Space →")
    st.stop()

# Space selection
current_space = st.session_state.get("current_space")
space_options = {f"{s.get('subject')} ({s.get('exam_id')}) - ID #{s.get('id')}": s for s in spaces}

# Determine default index
default_idx = 0
if current_space:
    for idx, (label, s) in enumerate(space_options.items()):
        if s.get("id") == current_space.get("id"):
            default_idx = idx
            break

col_pick, col_space_link = st.columns([3, 1])
with col_pick:
    selected_label = st.selectbox(
        "Current Learning Space",
        list(space_options.keys()),
        index=default_idx,
        key="sn_page_space_select",
    )
    selected_space = space_options[selected_label]
    st.session_state["current_space"] = selected_space
    st.session_state["current_space_id"] = selected_space["id"]

with col_space_link:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    st.page_link("pages/3_Space.py", label="Open Full Space →", icon="🚀")

st.divider()

render_smart_notes_view(selected_space)
