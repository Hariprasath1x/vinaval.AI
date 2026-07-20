"""
3_Space.py — The main Learning Space dashboard.
Five tabs: Learn (RAG Chat), Materials (Upload), Flashcards, Exam Lab (Quiz), Reports.
"""
import streamlit as st
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api import (
    get_space,
    get_messages,
    stream_chat,
    upload_document,
    list_documents,
    delete_document,
    generate_flashcards,
    list_flashcards,
    list_flashcard_topics,
    generate_quiz,
    submit_answer,
    get_quiz_stats,
    generate_quiz_review,
)

st.set_page_config(page_title="Learning Space", page_icon="📖", layout="wide")

# ── Auth Guard ────────────────────────────────────────────────────────────────

if "token" not in st.session_state:
    st.warning("⚠️ Please log in first.")
    st.page_link("app.py", label="Go to Login →")
    st.stop()

space_id = st.session_state.get("current_space_id")
if not space_id:
    st.warning("No space selected. Go to Dashboard or Select Exam.")
    col1, col2 = st.columns(2)
    with col1:
        st.page_link("pages/1_Dashboard.py", label="← Dashboard")
    with col2:
        st.page_link("pages/2_Select_Exam.py", label="Select Exam →")
    st.stop()

# ── Load Space ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _fetch_space(sid):
    return get_space(sid)

space = _fetch_space(space_id)
if not space:
    st.error("Space not found.")
    st.stop()

exam_id  = space.get("exam_id", "")
subject  = space.get("subject", "")
title    = space.get("title", f"{exam_id} · {subject}")

# ── Header ────────────────────────────────────────────────────────────────────

col_title, col_nav = st.columns([3, 1])
with col_title:
    st.title(f"📖 {exam_id} — {subject}")
    st.caption(f"Space ID: {space_id} | Use the tabs below to learn, upload material, and practise.")
with col_nav:
    st.page_link("pages/1_Dashboard.py", label="← Back to Dashboard")

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
#  TABS
# ═════════════════════════════════════════════════════════════════════════════

tab_learn, tab_materials, tab_flashcards, tab_quiz, tab_reports = st.tabs([
    "🧠 Learn (AI Chat)",
    "📚 Materials",
    "🃏 Flashcards",
    "📝 Exam Lab",
    "📈 Reports",
])


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1 — LEARN  (RAG Chat)
# ─────────────────────────────────────────────────────────────────────────────

with tab_learn:
    st.subheader("🧠 AI Tutor — Ask Anything")
    st.caption(
        "Your AI tutor uses the **pre-loaded syllabus books** and any **documents you upload** "
        "to answer your questions. Ask topic explanations, doubts, or ask it to quiz you!"
    )

    # Load history from backend on first render
    if "chat_messages" not in st.session_state:
        with st.spinner("Loading chat history..."):
            history = get_messages(space_id)
        st.session_state.chat_messages = [
            {"role": m["role"], "content": m["content"]} for m in history
        ]

    # Display conversation
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Clear chat
    with st.expander("⚙️ Options"):
        if st.button("🗑️ Clear chat display (history saved on server)"):
            st.session_state.chat_messages = []
            st.rerun()

    # Input
    if prompt := st.chat_input("Ask your AI tutor..."):
        # Show user message immediately
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Stream assistant response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            with st.spinner(""):
                for chunk in stream_chat(space_id, prompt):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)

        st.session_state.chat_messages.append({"role": "assistant", "content": full_response})


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 2 — MATERIALS  (User Uploads — question banks, notes, practice papers)
# ─────────────────────────────────────────────────────────────────────────────

with tab_materials:
    st.subheader("📚 Your Study Materials")
    st.info(
        "📌 **How it works:** Upload your **question banks**, **topic notes**, or **practice papers** "
        "(PDF or TXT). They are indexed into the knowledge base and the AI will use them alongside "
        "the **pre-loaded syllabus books** when answering your questions in the Learn tab."
    )

    # ── Upload form
    with st.form("upload_form", clear_on_submit=True):
        st.markdown("**Upload a Document**")
        uploaded_file = st.file_uploader(
            "Choose a PDF or TXT file",
            type=["pdf", "txt"],
            help="Question banks, topic summaries, previous year papers, personal notes, etc.",
        )
        submitted = st.form_submit_button("📤 Upload & Index", type="primary")
        if submitted and uploaded_file:
            with st.spinner(f"Uploading and indexing '{uploaded_file.name}'..."):
                result = upload_document(space_id, uploaded_file.read(), uploaded_file.name)
            if result:
                st.success(
                    f"✅ '{result['filename']}' uploaded and indexed! "
                    "The AI can now use this content to answer your questions."
                )
                st.cache_data.clear()
        elif submitted:
            st.warning("Please select a file first.")

    st.divider()

    # ── Existing documents
    st.markdown("**Indexed Documents**")
    docs = list_documents(space_id)

    if not docs:
        st.info("No documents uploaded yet. Upload your first document above!")
    else:
        for doc in docs:
            col_name, col_type, col_action = st.columns([4, 1, 1])
            with col_name:
                icon = "📄" if doc["file_type"] == "pdf" else "📝"
                st.write(f"{icon} {doc['filename']}")
            with col_type:
                st.caption(doc["file_type"].upper())
            with col_action:
                if doc.get("source") == "book":
                    st.caption("📚 Book")  # Admin-seeded books can't be deleted
                else:
                    if st.button("🗑️", key=f"del_{doc['id']}", help="Delete this document"):
                        if delete_document(space_id, doc["id"]):
                            st.success("Deleted.")
                            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 3 — FLASHCARDS
# ─────────────────────────────────────────────────────────────────────────────

with tab_flashcards:
    st.subheader("🃏 Flashcards")
    st.caption(
        "Generate AI-powered flashcards for any topic. "
        "The AI reads your indexed materials (books + uploads) to create accurate cards."
    )

    # ── Generate new set
    with st.form("flashcard_form"):
        col_topic, col_count, col_lang = st.columns([2, 1, 1])
        with col_topic:
            fc_topic = st.text_input(
                "Topic",
                placeholder=f"e.g. Photosynthesis, Newton's Laws...",
                help="Enter a topic from the syllabus.",
            )
        with col_count:
            fc_count = st.number_input("# Cards", min_value=2, max_value=20, value=8)
        with col_lang:
            fc_lang_display = st.selectbox("Language", ["English", "Tamil (தமிழ்)"])
            fc_lang = "ta" if "Tamil" in fc_lang_display else "en"
            
        gen_submit = st.form_submit_button("✨ Generate Flashcards", type="primary")

    if gen_submit and fc_topic:
        with st.spinner(f"Generating {fc_count} flashcards for '{fc_topic}' in {fc_lang_display}..."):
            cards = generate_flashcards(space_id, fc_topic.strip(), fc_count, lang=fc_lang)
        if cards:
            st.success(f"✅ Generated {len(cards)} flashcards!")
            st.session_state["fc_active_cards"] = cards
            st.session_state["fc_active_topic"] = fc_topic.strip()
            st.session_state["fc_index"] = 0
            st.session_state["fc_show_back"] = False
    elif gen_submit:
        st.warning("Please enter a topic first.")

    # ── Flashcard Viewer (flip-card style)
    if "fc_active_cards" in st.session_state:
        cards = st.session_state.fc_active_cards
        idx = st.session_state.get("fc_index", 0)
        show_back = st.session_state.get("fc_show_back", False)

        st.divider()
        st.markdown(f"**Topic:** {st.session_state.get('fc_active_topic', '')}   |   Card **{idx+1}** of **{len(cards)}**")

        card = cards[idx]
        with st.container(border=True):
            if not show_back:
                st.markdown(f"### 📋 Front\n\n{card['front']}")
                st.caption("Think of the answer, then flip!")
            else:
                st.markdown(f"### 💡 Back\n\n{card['back']}")

        col_flip, col_prev, col_next = st.columns([2, 1, 1])
        with col_flip:
            if st.button(
                "🔄 Flip Card",
                use_container_width=True,
                type="primary",
            ):
                st.session_state.fc_show_back = not show_back
                st.rerun()
        with col_prev:
            if st.button("⬅️ Prev", disabled=(idx == 0), use_container_width=True):
                st.session_state.fc_index = idx - 1
                st.session_state.fc_show_back = False
                st.rerun()
        with col_next:
            if st.button("Next ➡️", disabled=(idx == len(cards)-1), use_container_width=True):
                st.session_state.fc_index = idx + 1
                st.session_state.fc_show_back = False
                st.rerun()

    # ── Previously saved flashcard sets
    st.divider()
    st.markdown("**Saved Flashcard Topics**")
    topics = list_flashcard_topics(space_id)
    if not topics:
        st.info("No saved flashcard sets yet. Generate one above!")
    else:
        for t in topics:
            if st.button(f"📂 Load: {t}", key=f"load_fc_{t}"):
                with st.spinner(f"Loading flashcards for '{t}'..."):
                    saved_cards = list_flashcards(space_id, t)
                if saved_cards:
                    st.session_state["fc_active_cards"] = [
                        {"front": c["front"], "back": c["back"]} for c in saved_cards
                    ]
                    st.session_state["fc_active_topic"] = t
                    st.session_state["fc_index"] = 0
                    st.session_state["fc_show_back"] = False
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 4 — EXAM LAB  (MCQ Quiz)
# ─────────────────────────────────────────────────────────────────────────────

with tab_quiz:
    st.subheader("📝 Exam Lab — Practice MCQs")
    st.caption(
        "Generate multiple-choice questions on any topic. "
        "Your answers are tracked and reported in the Reports tab."
    )

    # ── Generate Quiz
    if "quiz_questions" not in st.session_state:
        st.session_state.quiz_questions = []
        st.session_state.quiz_answers = {}
        st.session_state.quiz_submitted = False

    with st.form("quiz_form"):
        col_qtopic, col_qcount, col_qlang = st.columns([2, 1, 1])
        with col_qtopic:
            q_topic = st.text_input(
                "Topic",
                placeholder="e.g. Cell Division, Thermodynamics...",
            )
        with col_qcount:
            q_count = st.number_input("# Questions", min_value=1, max_value=10, value=5)
        with col_qlang:
            q_lang_display = st.selectbox("Language", ["English", "Tamil (தமிழ்)"], key="quiz_lang")
            q_lang = "ta" if "Tamil" in q_lang_display else "en"
            
        quiz_type = st.radio("Mode", ["Practice (see answers instantly)", "Exam (submit all at end)"], horizontal=True)
        is_exam = "Exam" in quiz_type
        q_submit = st.form_submit_button("🎯 Generate Quiz", type="primary")

    if q_submit and q_topic:
        with st.spinner(f"Generating {q_count} questions on '{q_topic}' in {q_lang_display}..."):
            questions = generate_quiz(space_id, q_topic.strip(), q_count, lang=q_lang)
        if questions:
            st.session_state.quiz_questions = questions
            st.session_state.quiz_answers = {}
            st.session_state.quiz_submitted = False
            st.session_state.quiz_is_exam = is_exam
            st.session_state.quiz_topic = q_topic.strip()
    elif q_submit:
        st.warning("Please enter a topic.")

    # ── Display Quiz Questions
    if st.session_state.quiz_questions:
        st.divider()
        st.markdown(f"**Quiz — {st.session_state.get('quiz_topic', '')}**   ({len(st.session_state.quiz_questions)} questions)")

        is_exam_mode = st.session_state.get("quiz_is_exam", False)
        if not submitted_all:
            with st.form("quiz_taking_form"):
                for i, q in enumerate(st.session_state.quiz_questions):
                    with st.container(border=True):
                        st.markdown(f"**Q{i+1}.** {q['question']}")
                        options = {
                            "a": q["option_a"],
                            "b": q["option_b"],
                            "c": q["option_c"],
                            "d": q["option_d"],
                        }
                        # We use session state to store answers dynamically inside the form
                        choice = st.radio(
                            f"Select answer for Q{i+1}",
                            options=list(options.keys()),
                            format_func=lambda k: f"{k.upper()}. {options[k]}",
                            key=f"quiz_q_{q['id']}",
                            label_visibility="collapsed",
                            index=None,
                        )

                st.divider()
                submit_quiz = st.form_submit_button("📩 Submit Quiz", type="primary", use_container_width=True)

                if submit_quiz:
                    # Validate all questions have an answer
                    unanswered = [q for q in st.session_state.quiz_questions if st.session_state.get(f"quiz_q_{q['id']}") is None]
                    if unanswered:
                        st.warning("⚠️ Please answer all questions before submitting.")
                    else:
                        with st.spinner("Submitting answers and generating AI review..."):
                            review_results = []
                            for q in st.session_state.quiz_questions:
                                ans = st.session_state.get(f"quiz_q_{q['id']}")
                                st.session_state.quiz_answers[q["id"]] = ans
                                result = submit_answer(space_id, q["id"], ans, is_exam=is_exam_mode)
                                if result:
                                    st.session_state[f"exam_result_{q['id']}"] = result
                                    review_results.append({"topic": q["topic"], "is_correct": result["is_correct"]})
                            
                            # Generate AI review
                            review_text = generate_quiz_review(space_id, review_results)
                            st.session_state.quiz_review = review_text
                        
                        st.session_state.quiz_submitted = True
                        st.rerun()

        # Show Results if submitted
        if submitted_all:
            st.success("🎉 Quiz Completed!")
            
            # Display Score
            correct_count = sum(1 for q in st.session_state.quiz_questions if st.session_state.get(f"exam_result_{q['id']}", {}).get("is_correct"))
            total = len(st.session_state.quiz_questions)
            st.metric("Final Score", f"{correct_count} / {total} ({(correct_count/total)*100:.0f}%)")

            # Display AI Review
            if st.session_state.get("quiz_review"):
                with st.container(border=True):
                    st.markdown("### 🤖 AI Tutor Review")
                    st.markdown(st.session_state.quiz_review)
            
            st.divider()
            st.markdown("### Detailed Results")
            for i, q in enumerate(st.session_state.quiz_questions):
                with st.container(border=True):
                    st.markdown(f"**Q{i+1}.** {q['question']}")
                    
                    # Show user's answer and result
                    ans = st.session_state.quiz_answers.get(q["id"])
                    result_key = f"exam_result_{q['id']}"
                    
                    options = {
                        "a": q["option_a"],
                        "b": q["option_b"],
                        "c": q["option_c"],
                        "d": q["option_d"],
                    }
                    for k, v in options.items():
                        if k == ans:
                            st.write(f"👉 **{k.upper()}. {v}** *(Your Answer)*")
                        else:
                            st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;{k.upper()}. {v}")

                    if result_key in st.session_state:
                        r = st.session_state[result_key]
                        if r["is_correct"]:
                            st.success("✅ Correct!")
                        else:
                            st.error(f"❌ Incorrect. Correct answer: **{r['correct_option'].upper()}**")
                        if r.get("explanation"):
                            st.info(f"💡 {r['explanation']}")


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 5 — REPORTS
# ─────────────────────────────────────────────────────────────────────────────

with tab_reports:
    st.subheader("📈 Performance Reports")
    st.caption("Track your accuracy and progress across practice sessions and exam simulations.")

    with st.spinner("Loading statistics..."):
        stats = get_quiz_stats(space_id)

    if not stats:
        st.info("No quiz attempts yet. Take a practice quiz in the Exam Lab to see your stats here!")
    else:
        # Overall metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Questions", stats["total_all"])
        with col2:
            st.metric("Correct Answers", stats["correct_all"])
        with col3:
            st.metric("Overall Accuracy", f"{stats['accuracy_all']:.1f}%")

        st.divider()

        col4, col5, col6 = st.columns(3)
        with col4:
            st.markdown("**🏋️ Practice Mode**")
            st.metric("Questions", stats["total_practice"])
            st.metric("Accuracy", f"{stats['accuracy_practice']:.1f}%")
        with col5:
            st.markdown("**🎓 Exam Mode**")
            st.metric("Questions", stats["total_exam"])
            st.metric("Accuracy", f"{stats['accuracy_exam']:.1f}%")
        with col6:
            st.markdown("**📚 Topics Practised**")
            topics = stats.get("topics_practiced", [])
            if topics:
                for t in topics[:10]:
                    st.write(f"• {t}")
                if len(topics) > 10:
                    st.caption(f"... and {len(topics)-10} more")
            else:
                st.caption("No topics yet.")

        # Progress bar visual
        st.divider()
        st.markdown("**Overall Accuracy**")
        acc = stats["accuracy_all"] / 100
        st.progress(min(acc, 1.0), text=f"{stats['accuracy_all']:.1f}%")
        if stats["accuracy_all"] >= 80:
            st.success("🌟 Excellent! Keep it up!")
        elif stats["accuracy_all"] >= 60:
            st.info("📈 Good progress! Review your weak topics.")
        else:
            st.warning("📖 Keep practicing — focus on your weak areas.")
