import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api import get_spaces, delete_space, get_quiz_stats

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

# ── Dashboard Stats Row ───────────────────────────────────────────────────────

if spaces:
    # Aggregate quick stats across all spaces
    total_questions = 0
    total_correct = 0
    most_practiced = None
    best_accuracy = 0.0

    for sp in spaces:
        stats = get_quiz_stats(sp["id"])
        if stats and stats.get("total_all", 0) > 0:
            total_questions += stats["total_all"]
            total_correct += stats["correct_all"]
            if stats["accuracy_all"] > best_accuracy:
                best_accuracy = stats["accuracy_all"]
                most_practiced = sp.get("subject", "—")

    overall_acc = round(total_correct / total_questions * 100, 1) if total_questions > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📚 Learning Spaces", len(spaces))
    m2.metric("❓ Total Questions", f"{total_questions:,}")
    m3.metric("🎯 Overall Accuracy", f"{overall_acc:.1f}%")
    m4.metric("🏆 Best Subject", most_practiced or "—")

    if total_questions > 0:
        st.progress(min(overall_acc / 100, 1.0), text=f"Overall accuracy: {overall_acc:.1f}%")

    st.divider()

# ── Space Cards ───────────────────────────────────────────────────────────────

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
                st.caption(f"{exam_icon} {exam} · Created: {space.get('created_at', '')[:10]}")

                col_open, col_del = st.columns([3, 1])
                with col_open:
                    if st.button("Open Space →", key=f"open_{space['id']}", type="primary", use_container_width=True):
                        st.session_state["current_space_id"] = space["id"]
                        st.session_state["current_space"] = space
                        st.switch_page("pages/3_Space.py")
                with col_del:
                    # Toggle confirm state per space
                    confirm_key = f"confirm_del_{space['id']}"
                    if not st.session_state.get(confirm_key):
                        if st.button("🗑️", key=f"del_{space['id']}", help="Delete this space", use_container_width=True):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    else:
                        st.warning(f"Delete **{subj}**?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("✅ Yes", key=f"del_yes_{space['id']}", use_container_width=True):
                                if delete_space(space["id"]):
                                    st.session_state.pop(confirm_key, None)
                                    st.success("Space deleted.")
                                    st.rerun()
                        with col_no:
                            if st.button("❌ No", key=f"del_no_{space['id']}", use_container_width=True):
                                st.session_state.pop(confirm_key, None)
                                st.rerun()

st.divider()
st.page_link("pages/2_Select_Exam.py", label="➕ Add a New Learning Space")
