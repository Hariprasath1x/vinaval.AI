import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api import create_space

st.set_page_config(page_title="Select Exam", page_icon="🎯", layout="wide")

if "token" not in st.session_state:
    st.warning("⚠️ Please log in from the Home page first.")
    st.page_link("app.py", label="Go to Login →")
    st.stop()

# ── Exam & Subject Data ───────────────────────────────────────────────────────

EXAMS = {
    "NEET": {
        "label": "Medical Entrance",
        "description": "National Eligibility cum Entrance Test for undergraduate medical admissions.",
        "icon": "🩺",
        "subjects": [
            {"name": "Physics",       "icon": "⚛️"},
            {"name": "Chemistry",     "icon": "🧪"},
            {"name": "Botany",        "icon": "🌿"},
            {"name": "Zoology",       "icon": "🦎"},
            {"name": "Bio Chemistry", "icon": "🧬"},
        ],
    },
    "TNPSC": {
        "label": "Tamil Nadu Civil Services",
        "description": "Tamil Nadu Public Service Commission exam for government service recruitment.",
        "icon": "🏛️",
        "subjects": [
            {"name": "History",        "icon": "📜"},
            {"name": "Geography",      "icon": "🌍"},
            {"name": "Polity",         "icon": "⚖️"},
            {"name": "Economics",      "icon": "📈"},
            {"name": "Science",        "icon": "🔬"},
            {"name": "Current Affairs","icon": "📰"},
        ],
    },
}

# ── UI ────────────────────────────────────────────────────────────────────────

st.title("📚 Choose Your Exam & Subject")
st.markdown("Select an exam and then a subject to open (or create) your personalized Learning Space.")
st.divider()

# ── Exam Selection ────────────────────────────────────────────────────────────

selected_exam = st.session_state.get("selected_exam", "NEET")

exam_cols = st.columns(len(EXAMS))
for idx, (exam_id, exam_info) in enumerate(EXAMS.items()):
    with exam_cols[idx]:
        is_active = selected_exam == exam_id
        if st.button(
            f"{exam_info['icon']} {exam_id}\n\n*{exam_info['label']}*",
            key=f"exam_{exam_id}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            st.session_state["selected_exam"] = exam_id
            st.session_state.pop("selected_subject", None)
            st.rerun()

st.session_state["selected_exam"] = selected_exam
exam_info = EXAMS[selected_exam]

st.divider()
st.markdown(f"**{exam_info['icon']} {selected_exam}** — {exam_info['description']}")
st.markdown("**Select a Subject:**")

# ── Subject Selection ─────────────────────────────────────────────────────────

selected_subject = st.session_state.get("selected_subject")

subject_cols = st.columns(3)
subjects = exam_info["subjects"]
for idx, subj in enumerate(subjects):
    with subject_cols[idx % 3]:
        active = selected_subject == subj["name"]
        if st.button(
            f"{subj['icon']} {subj['name']}",
            key=f"subj_{selected_exam}_{subj['name']}",
            type="primary" if active else "secondary",
            use_container_width=True,
        ):
            st.session_state["selected_subject"] = subj["name"]
            st.rerun()

if selected_subject and selected_subject in [s["name"] for s in subjects]:
    st.divider()
    st.markdown(f"**Ready:** {exam_info['icon']} {selected_exam} → {selected_subject}")
    if st.button("🚀 Open Learning Space", type="primary", use_container_width=True):
        with st.spinner(f"Setting up your {selected_subject} space..."):
            space = create_space(selected_exam, selected_subject)
        if space:
            st.session_state["current_space_id"] = space["id"]
            st.session_state["current_space"] = space
            st.success(f"✅ Space ready! Opening {selected_subject}...")
            st.switch_page("pages/3_Space.py")
