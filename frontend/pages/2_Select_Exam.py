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

    "NEET": {
        "label": "Medical Entrance",
        "description": "National Eligibility cum Entrance Test for undergraduate medical admissions.",
        "icon": "🩺",
        "subjects": [
            {"name": "Physics",   "icon": "⚛️"},
            {"name": "Chemistry", "icon": "🧪"},
            {"name": "Botany",    "icon": "🌿"},
            {"name": "Zoology",   "icon": "🦎"},
            {"name": "Bio Chemistry", "icon": "🧬"},
        ],
    }
}

# ── UI ────────────────────────────────────────────────────────────────────────

st.title("📚 Choose a Subject")
st.markdown("Select a subject to open (or create) your personalized Learning Space.")
st.divider()

selected_exam = "NEET"
st.session_state["selected_exam"] = selected_exam

exam_info = EXAMS[selected_exam]
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
        st.markdown(f"**Ready:** {selected_subject}")
        if st.button("🚀 Open Learning Space", type="primary", use_container_width=True):
            with st.spinner(f"Setting up your {selected_subject} space..."):
                space = create_space(selected_exam, selected_subject)
            if space:
                st.session_state["current_space_id"] = space["id"]
                st.session_state["current_space"] = space
                st.success(f"✅ Space ready! Opening {selected_subject}...")
                st.switch_page("pages/3_Space.py")
