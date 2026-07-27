import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api import get_spaces

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

if "token" not in st.session_state:
    st.warning("⚠️ Please log in from the Home page first.")
    st.page_link("app.py", label="Go to Login →")
    st.stop()

user = st.session_state.get("user", {})
st.title(f"👋 Welcome back, {user.get('name', 'Student')}!")
st.markdown("Your active Learning Spaces are below. Each space contains your AI tutor, uploaded materials, flashcards, and quiz progress.")

# Refresh button
col_title, col_refresh = st.columns([4, 1])
with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()

st.divider()

# ── Load Spaces ───────────────────────────────────────────────────────────────

with st.spinner("Loading your spaces..."):
    spaces = get_spaces()

EXAM_ICONS = {"NEET": "🩺", "TNPSC": "🏛️"}
SUBJECT_ICONS = {
    "Physics": "⚛️", "Chemistry": "🧪", "Botany": "🌿", "Zoology": "🦎", "Bio Chemistry": "🧬",
    "History": "📜", "Geography": "🌍", "Polity": "⚖️",
    "Economics": "📈", "Science": "🔬", "Current Affairs": "📰",
}

if not spaces:
    st.info("You don't have any Learning Spaces yet.")
    st.page_link("pages/2_Select_Exam.py", label="➕ Create Your First Space →")
else:
    st.markdown(f"**{len(spaces)} Space(s)**")
    cols = st.columns(3)
    for i, space in enumerate(spaces):
        with cols[i % 3]:
            exam = space.get("exam_id", "")
            subj = space.get("subject", "")
            exam_icon = EXAM_ICONS.get(exam, "📖")
            subj_icon = SUBJECT_ICONS.get(subj, "📚")
            with st.container(border=True):
                st.subheader(f"{subj_icon} {subj}")
                st.caption(f"Created: {space.get('created_at', '')[:10]}")
                if st.button("Open Space →", key=f"open_{space['id']}", type="primary", use_container_width=True):
                    st.session_state["current_space_id"] = space["id"]
                    st.session_state["current_space"] = space
                    st.switch_page("pages/3_Space.py")

st.divider()
st.page_link("pages/2_Select_Exam.py", label="➕ Add a New Learning Space")
