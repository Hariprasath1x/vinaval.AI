"""
3_Space.py — The main Learning Space dashboard.
Five tabs: Learn (RAG Chat), Materials (Upload), Flashcards, Exam Lab (Quiz), Reports.

Additions:
  - NEET topic dropdowns for Flashcards & Quiz
  - Leitner spaced-repetition flashcard session mode
  - Mock Exam countdown timer
  - Explanations shown for ALL quiz questions (not just wrong ones)
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

# ── NEET Topic Catalogue ──────────────────────────────────────────────────────
# Predefined chapter-level topics for each NEET subject so students can
# pick from a dropdown instead of typing freeform text.

NEET_TOPICS = {
    "Physics": [
        "Physical World and Units", "Motion in a Straight Line", "Motion in a Plane",
        "Laws of Motion", "Work, Energy and Power", "System of Particles & Rotational Motion",
        "Gravitation", "Mechanical Properties of Solids", "Mechanical Properties of Fluids",
        "Thermal Properties of Matter", "Thermodynamics", "Kinetic Theory of Gases",
        "Oscillations", "Waves", "Electric Charges and Fields", "Electrostatic Potential and Capacitance",
        "Current Electricity", "Moving Charges and Magnetism", "Magnetism and Matter",
        "Electromagnetic Induction", "Alternating Current", "Electromagnetic Waves",
        "Ray Optics and Optical Instruments", "Wave Optics",
        "Dual Nature of Radiation and Matter", "Atoms", "Nuclei",
        "Semiconductor Electronics", "Communication Systems",
    ],
    "Chemistry": [
        "Some Basic Concepts of Chemistry", "Structure of Atom", "Classification of Elements",
        "Chemical Bonding and Molecular Structure", "States of Matter", "Thermodynamics",
        "Equilibrium", "Redox Reactions", "Hydrogen",
        "The s-Block Elements", "The p-Block Elements", "Organic Chemistry Basics",
        "Hydrocarbons", "Environmental Chemistry",
        "Solid State", "Solutions", "Electrochemistry", "Chemical Kinetics",
        "Surface Chemistry", "General Principles of Extraction of Metals",
        "The p-Block Elements (Period 3)", "The d and f Block Elements",
        "Coordination Compounds", "Haloalkanes and Haloarenes",
        "Alcohols, Phenols and Ethers", "Aldehydes, Ketones and Carboxylic Acids",
        "Amines", "Biomolecules", "Polymers", "Chemistry in Everyday Life",
    ],
    "Botany": [
        "The Living World", "Biological Classification", "Plant Kingdom",
        "Morphology of Flowering Plants", "Anatomy of Flowering Plants",
        "Cell: The Unit of Life", "Cell Cycle and Cell Division",
        "Photosynthesis in Higher Plants", "Respiration in Plants",
        "Plant Growth and Development", "Transport in Plants",
        "Mineral Nutrition", "Sexual Reproduction in Flowering Plants",
        "Principles of Inheritance and Variation", "Molecular Basis of Inheritance",
        "Evolution", "Strategies for Enhancement in Food Production",
        "Microbes in Human Welfare", "Biotechnology: Principles and Processes",
        "Biotechnology and its Applications", "Organisms and Populations",
        "Ecosystem", "Biodiversity and Conservation", "Environmental Issues",
    ],
    "Zoology": [
        "Animal Kingdom", "Structural Organisation in Animals",
        "Human Physiology: Digestion and Absorption",
        "Human Physiology: Breathing and Exchange of Gases",
        "Human Physiology: Body Fluids and Circulation",
        "Human Physiology: Excretory Products and their Elimination",
        "Human Physiology: Locomotion and Movement",
        "Human Physiology: Neural Control and Coordination",
        "Human Physiology: Chemical Coordination and Integration",
        "Human Reproduction", "Reproductive Health",
        "Genetics and Evolution", "Human Health and Disease",
        "Animal Husbandry", "Biodiversity and Conservation",
        "Environmental Issues",
    ],
    "Bio Chemistry": [
        "Biomolecules — Carbohydrates", "Biomolecules — Proteins",
        "Biomolecules — Lipids", "Biomolecules — Nucleic Acids",
        "Enzymes", "Vitamins and Minerals",
        "Metabolism Overview", "Glycolysis", "Krebs Cycle / TCA Cycle",
        "Oxidative Phosphorylation", "Gluconeogenesis",
        "Fatty Acid Synthesis and Oxidation", "Amino Acid Metabolism",
        "Nitrogen Metabolism", "Hormones and Signal Transduction",
        "DNA Replication and Repair", "Transcription", "Translation",
        "Regulation of Gene Expression", "Metabolic Disorders",
    ],
}

def _get_topics(subj: str):
    return NEET_TOPICS.get(subj, [])

# ── Header ────────────────────────────────────────────────────────────────────

col_title, col_nav = st.columns([3, 1])
with col_title:
    st.title(f"📖 {subject}")
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
#  TAB 2 — MATERIALS  (User Uploads)
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
                    st.caption("📚 Book")
                else:
                    if st.button("🗑️", key=f"del_{doc['id']}", help="Delete this document"):
                        if delete_document(space_id, doc["id"]):
                            st.success("Deleted.")
                            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 3 — FLASHCARDS  (with Leitner spaced repetition + topic dropdown)
# ─────────────────────────────────────────────────────────────────────────────

with tab_flashcards:
    st.subheader("🃏 Flashcards")
    st.caption(
        "Generate AI-powered flashcards for any topic. "
        "Rate each card — Hard cards repeat until you master them!"
    )

    avail_topics = _get_topics(subject)

    # ── Generate new set
    with st.form("flashcard_form"):
        col_topic, col_count, col_lang = st.columns([2, 1, 1])
        with col_topic:
            if avail_topics:
                topic_options = avail_topics + ["✏️ Custom (type below)"]
                fc_topic_choice = st.selectbox("Chapter / Topic", topic_options)
                fc_custom = st.text_input(
                    "Custom topic",
                    placeholder="Type your custom topic here...",
                    help="Only used if you selected 'Custom' above.",
                )
                fc_topic = fc_custom.strip() if fc_topic_choice.startswith("✏️") else fc_topic_choice
            else:
                fc_topic = st.text_input(
                    "Topic",
                    placeholder="e.g. Photosynthesis, Newton's Laws...",
                )
        with col_count:
            fc_count = st.number_input("# Cards", min_value=2, max_value=20, value=8)
        with col_lang:
            fc_lang_display = st.selectbox("Language", ["English", "Tamil (தமிழ்)"])
            fc_lang = "ta" if "Tamil" in fc_lang_display else "en"

        gen_submit = st.form_submit_button("✨ Generate Flashcards", type="primary")

    if gen_submit:
        if not fc_topic:
            st.warning("Please select or enter a topic first.")
        else:
            with st.spinner(f"Generating {fc_count} flashcards for '{fc_topic}' in {fc_lang_display}..."):
                cards = generate_flashcards(space_id, fc_topic.strip(), fc_count, lang=fc_lang)
            if cards:
                st.success(f"✅ Generated {len(cards)} flashcards!")
                # Initialise the Leitner session queue — a list of card dicts
                st.session_state["fc_queue"] = list(cards)
                st.session_state["fc_mastered"] = 0
                st.session_state["fc_total"] = len(cards)
                st.session_state["fc_active_topic"] = fc_topic.strip()
                st.session_state["fc_show_back"] = False
                # Remove legacy state
                st.session_state.pop("fc_active_cards", None)

    # ── Leitner Flashcard Session
    if st.session_state.get("fc_queue"):
        queue = st.session_state["fc_queue"]
        mastered = st.session_state.get("fc_mastered", 0)
        total = st.session_state.get("fc_total", len(queue))
        show_back = st.session_state.get("fc_show_back", False)

        st.divider()
        remaining = len(queue)
        st.markdown(
            f"**Topic:** {st.session_state.get('fc_active_topic', '')}  |  "
            f"✅ Mastered: **{mastered}/{total}**  |  🔁 Remaining: **{remaining}**"
        )
        st.progress(mastered / total if total > 0 else 0)

        card = queue[0]
        with st.container(border=True):
            if not show_back:
                st.markdown(f"### 📋 Front\n\n{card['front']}")
                st.caption("Think of the answer, then flip!")
            else:
                st.markdown(f"### 💡 Back\n\n{card['back']}")

        col_flip, col_hard, col_easy = st.columns([2, 1, 1])
        with col_flip:
            if st.button("🔄 Flip Card", use_container_width=True, type="primary"):
                st.session_state["fc_show_back"] = not show_back
                st.rerun()
        with col_hard:
            if st.button("❌ Hard — Again", use_container_width=True, disabled=not show_back,
                         help="I don't know this — move it to the back of the deck"):
                # Move current card to back of queue so it repeats
                card_to_repeat = st.session_state["fc_queue"].pop(0)
                st.session_state["fc_queue"].append(card_to_repeat)
                st.session_state["fc_show_back"] = False
                st.rerun()
        with col_easy:
            if st.button("✅ Got it!", use_container_width=True, disabled=not show_back,
                         help="I know this — remove from deck"):
                st.session_state["fc_queue"].pop(0)
                st.session_state["fc_mastered"] += 1
                st.session_state["fc_show_back"] = False
                st.rerun()

    elif "fc_total" in st.session_state and st.session_state.get("fc_mastered", 0) > 0:
        # Session completed!
        total = st.session_state.get("fc_total", 0)
        st.divider()
        st.balloons()
        st.success(f"🎉 Congratulations! You mastered all **{total}** cards in this session!")
        if st.button("🔁 Start a New Session"):
            for key in ["fc_queue", "fc_mastered", "fc_total", "fc_active_topic", "fc_show_back"]:
                st.session_state.pop(key, None)
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
                    loaded = [{"front": c["front"], "back": c["back"]} for c in saved_cards]
                    st.session_state["fc_queue"] = list(loaded)
                    st.session_state["fc_mastered"] = 0
                    st.session_state["fc_total"] = len(loaded)
                    st.session_state["fc_active_topic"] = t
                    st.session_state["fc_show_back"] = False
                    st.session_state.pop("fc_active_cards", None)
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 4 — EXAM LAB  (MCQ Quiz with timer + topic dropdown + all explanations)
# ─────────────────────────────────────────────────────────────────────────────

# Mock exam duration in seconds (configurable)
MOCK_EXAM_DURATION_SECONDS = 15 * 60  # 15 minutes

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
        st.markdown("**Generate a Practice Quiz or a Full Mock Exam**")
        quiz_type = st.radio("Mode", ["Practice (by Topic)", "Full Mock Exam (Whole Syllabus)"], horizontal=True)
        is_mock_exam = "Mock" in quiz_type

        avail_topics_quiz = _get_topics(subject)
        col_qtopic, col_qcount, col_qlang = st.columns([2, 1, 1])
        with col_qtopic:
            if not is_mock_exam and avail_topics_quiz:
                topic_options_q = avail_topics_quiz + ["✏️ Custom (type below)"]
                q_topic_choice = st.selectbox(
                    "Chapter / Topic",
                    topic_options_q,
                    disabled=is_mock_exam,
                )
                q_custom = st.text_input(
                    "Custom topic",
                    placeholder="Type your custom topic...",
                    disabled=is_mock_exam,
                )
                q_topic = q_custom.strip() if q_topic_choice.startswith("✏️") else q_topic_choice
            else:
                q_topic = st.text_input(
                    "Topic",
                    placeholder="e.g. Cell Division, Thermodynamics...",
                    disabled=is_mock_exam,
                )
        with col_qcount:
            q_count = st.number_input("# Questions", min_value=1, max_value=30, value=15 if is_mock_exam else 5)
        with col_qlang:
            q_lang_display = st.selectbox("Language", ["English", "Tamil (தமிழ்)"], key="quiz_lang")
            q_lang = "ta" if "Tamil" in q_lang_display else "en"

        q_submit = st.form_submit_button("🎯 Generate Quiz/Exam", type="primary")

    if q_submit:
        target_topic = None if is_mock_exam else q_topic.strip()
        if not is_mock_exam and not target_topic:
            st.warning("Please select or enter a topic for practice mode.")
        else:
            with st.spinner(f"Generating {q_count} questions..."):
                questions = generate_quiz(space_id, target_topic, q_count, lang=q_lang)
            if questions:
                st.session_state.quiz_questions = questions
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state.quiz_is_exam = is_mock_exam
                st.session_state.quiz_topic = "Full Mock Exam" if is_mock_exam else target_topic
                # Start timer for mock exam
                if is_mock_exam:
                    st.session_state.quiz_start_time = time.time()
                else:
                    st.session_state.pop("quiz_start_time", None)

    # ── Timer display (mock exam only)
    if (
        st.session_state.get("quiz_questions")
        and st.session_state.get("quiz_is_exam")
        and not st.session_state.get("quiz_submitted")
        and "quiz_start_time" in st.session_state
    ):
        elapsed = time.time() - st.session_state["quiz_start_time"]
        remaining_secs = int(MOCK_EXAM_DURATION_SECONDS - elapsed)

        if remaining_secs > 0:
            mins, secs = divmod(remaining_secs, 60)
            progress_val = 1.0 - (remaining_secs / MOCK_EXAM_DURATION_SECONDS)
            if remaining_secs <= 120:
                st.error(f"⏰ Time remaining: **{mins:02d}:{secs:02d}** — Hurry up!")
            elif remaining_secs <= 300:
                st.warning(f"⏳ Time remaining: **{mins:02d}:{secs:02d}**")
            else:
                st.info(f"🕐 Time remaining: **{mins:02d}:{secs:02d}**")
            st.progress(progress_val)
        else:
            st.error("⏰ **Time's up!** The exam time limit has been reached.")
            st.session_state.quiz_submitted = True
            # Auto-record any unanswered questions as blank
            for q in st.session_state.quiz_questions:
                if q["id"] not in st.session_state.quiz_answers:
                    st.session_state.quiz_answers[q["id"]] = None

    # ── Display Quiz Questions
    if st.session_state.quiz_questions:
        st.divider()
        st.markdown(f"**Quiz — {st.session_state.get('quiz_topic', '')}**   ({len(st.session_state.quiz_questions)} questions)")

        is_exam_mode = st.session_state.get("quiz_is_exam", False)
        if not st.session_state.quiz_submitted:
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

                            review_text = generate_quiz_review(space_id, review_results)
                            st.session_state.quiz_review = review_text

                        st.session_state.quiz_submitted = True
                        st.rerun()

        # ── Show Results if submitted
        if st.session_state.quiz_submitted:
            correct_count = sum(
                1 for q in st.session_state.quiz_questions
                if st.session_state.get(f"exam_result_{q['id']}", {}).get("is_correct")
            )
            total = len(st.session_state.quiz_questions)
            pct = (correct_count / total) * 100 if total else 0

            st.success("🎉 Quiz Completed!")
            c1, c2, c3 = st.columns(3)
            c1.metric("Score", f"{correct_count} / {total}")
            c2.metric("Accuracy", f"{pct:.0f}%")
            c3.metric("Mode", "🎓 Mock Exam" if is_exam_mode else "🏋️ Practice")

            # AI Review
            if st.session_state.get("quiz_review"):
                with st.container(border=True):
                    st.markdown("### 🤖 AI Tutor Review")
                    st.markdown(st.session_state.quiz_review)

            st.divider()
            st.markdown("### Detailed Results")
            for i, q in enumerate(st.session_state.quiz_questions):
                ans = st.session_state.quiz_answers.get(q["id"])
                result_key = f"exam_result_{q['id']}"
                r = st.session_state.get(result_key, {})
                is_correct = r.get("is_correct", False)

                options = {
                    "a": q["option_a"],
                    "b": q["option_b"],
                    "c": q["option_c"],
                    "d": q["option_d"],
                }

                # Border colour based on correctness
                with st.container(border=True):
                    status_icon = "✅" if is_correct else "❌"
                    st.markdown(f"**{status_icon} Q{i+1}.** {q['question']}")

                    for k, v in options.items():
                        correct_opt = r.get("correct_option", "")
                        if k == correct_opt:
                            prefix = "✅ "
                        elif k == ans and not is_correct:
                            prefix = "❌ "
                        else:
                            prefix = "　"
                        weight = "**" if k in (ans, correct_opt) else ""
                        st.markdown(f"{prefix}{weight}{k.upper()}. {v}{weight}")

                    if r:
                        if is_correct:
                            st.success("Correct!")
                        else:
                            st.error(f"Incorrect. Correct answer: **{r.get('correct_option','').upper()}**")

                    # Explanation shown for ALL questions (not only wrong ones)
                    if r.get("explanation"):
                        with st.expander("💡 View Explanation"):
                            st.info(r["explanation"])

            # Option to retry
            st.divider()
            if st.button("🔁 Generate a New Quiz"):
                st.session_state.quiz_questions = []
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state.pop("quiz_review", None)
                st.session_state.pop("quiz_start_time", None)
                st.rerun()


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
