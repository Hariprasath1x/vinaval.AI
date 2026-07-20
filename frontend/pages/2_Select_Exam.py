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
        "label": "NEET — Medical Entrance",
        "description": "National Eligibility cum Entrance Test for undergraduate medical admissions.",
        "icon": "🩺",
        "subjects": [
            {"name": "Physics",   "icon": "⚛️"},
            {"name": "Chemistry", "icon": "🧪"},
            {"name": "Botany",    "icon": "🌿"},
            {"name": "Zoology",   "icon": "🦎"},
        ],
    },
    "TNPSC": {
        "label": "TNPSC — Civil Services",
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

st.title("🎯 Choose Your Learning Path")
st.markdown("Select an exam and subject to open (or create) your personalized Learning Space.")
st.divider()

# Exam selection
exam_col1, exam_col2 = st.columns(2)
selected_exam = st.session_state.get("selected_exam")

for idx, (exam_id, exam_info) in enumerate(EXAMS.items()):
    col = exam_col1 if idx == 0 else exam_col2
    with col:
        active = selected_exam == exam_id
        border_style = "border: 2px solid #4f8ef7;" if active else "border: 2px solid transparent;"
        with st.container(border=True):
            st.subheader(f"{exam_info['icon']} {exam_info['label']}")
            st.caption(exam_info["description"])
            if st.button(
                f"✅ Selected" if active else f"Select {exam_id}",
                key=f"exam_{exam_id}",
                type="primary" if active else "secondary",
                use_container_width=True,
            ):
                st.session_state["selected_exam"] = exam_id
                st.session_state.pop("selected_subject", None)
                st.rerun()

st.divider()

# Subject selection (shown after exam chosen)
if selected_exam:
    exam_info = EXAMS[selected_exam]
    st.subheader(f"📚 Choose a Subject — {selected_exam}")
    selected_subject = st.session_state.get("selected_subject")

    subject_cols = st.columns(3)
    subjects = exam_info["subjects"]
    for idx, subj in enumerate(subjects):
        with subject_cols[idx % 3]:
            active = selected_subject == subj["name"]
            if st.button(
                f"{subj['icon']} {subj['name']}",
                key=f"subj_{subj['name']}",
                type="primary" if active else "secondary",
                use_container_width=True,
            ):
                st.session_state["selected_subject"] = subj["name"]
                st.rerun()

    if selected_subject:
        st.divider()
        st.markdown(f"**Ready:** {selected_exam} → {selected_subject}")
        if st.button("🚀 Open Learning Space", type="primary", use_container_width=True):
            with st.spinner(f"Setting up your {selected_exam} {selected_subject} space..."):
                space = create_space(selected_exam, selected_subject)
            if space:
                st.session_state["current_space_id"] = space["id"]
                st.session_state["current_space"] = space
                st.success(f"✅ Space ready! Opening {selected_exam} {selected_subject}...")
                st.switch_page("pages/3_Space.py")
else:
    st.info("👆 Select an exam above to continue.")
