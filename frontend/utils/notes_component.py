import re
from typing import Optional, Dict, Any, List
import streamlit as st

from utils.api import (
    generate_smart_notes,
    create_smart_note,
    list_smart_notes,
    get_smart_note,
    update_smart_note,
    delete_smart_note,
    list_documents,
)


def render_smart_notes_view(space: Dict[str, Any]):
    space_id = space["id"]
    exam = space.get("exam_id", "NEET")
    subject = space.get("subject", "General")

    st.subheader(f"📓 Smart Notes — {subject}")
    st.caption(
        f"Generate high-yield, structured study notes grounded in {exam} {subject} curriculum or your uploaded documents. "
        "Review, customize, save to your library, and export as Markdown."
    )

    # Session state keys scoped to this space
    draft_key = f"sn_draft_{space_id}"
    editing_key = f"sn_editing_{space_id}"

    # Fetch user's uploaded documents for this space
    docs = list_documents(space_id)

    # Two main sub-views: Generator / Editor & Notes Library
    subtab_gen, subtab_lib = st.tabs(["✨ Generate & Edit", "📚 Saved Notes Library"])

    with subtab_gen:
        # Form for generating notes
        st.markdown("#### 1. Configure Notes Source")
        col_src, col_lang = st.columns([2, 1])

        with col_src:
            src_choice = st.radio(
                "Knowledge Source",
                ["📖 Syllabus Topic", "📄 Uploaded Document"],
                horizontal=True,
                key=f"sn_src_type_{space_id}",
            )

        with col_lang:
            lang_choice = st.selectbox(
                "Language",
                ["English", "Tamil (தமிழ்)"],
                key=f"sn_lang_{space_id}",
            )
            lang_code = "ta" if "Tamil" in lang_choice else "en"

        topic_val: Optional[str] = None
        doc_id_val: Optional[int] = None
        source_type_val = "curriculum"
        doc_choice_label = ""

        if src_choice == "📖 Syllabus Topic":
            source_type_val = "curriculum"
            topic_input = st.text_input(
                "Topic Name",
                placeholder=f"e.g. Wave Optics, Thermodynamics, Photosynthesis in {subject}...",
                key=f"sn_custom_topic_{space_id}",
            )
            topic_val = topic_input.strip()

        else:  # Uploaded Document
            source_type_val = "document"
            if not docs:
                st.info(
                    "ℹ️ No documents uploaded yet in this space. "
                    "Upload study materials in the **📚 Materials** tab, or switch to **📖 Syllabus Topic**."
                )
            else:
                doc_map = {f"{d.get('filename', f'Document #{d.get('id')}')} (ID: {d.get('id')})": d.get('id') for d in docs}
                doc_choice_label = st.selectbox("Select Document", list(doc_map.keys()), key=f"sn_doc_choice_{space_id}")
                doc_id_val = doc_map.get(doc_choice_label)
                doc_topic_input = st.text_input(
                    "Focus Subtopic (Optional)",
                    placeholder="Leave blank to synthesize notes from the whole document...",
                    key=f"sn_doc_subtopic_{space_id}",
                )
                topic_val = doc_topic_input.strip() if doc_topic_input.strip() else None

        # Generate Button
        col_btn, _ = st.columns([2, 3])
        with col_btn:
            gen_clicked = st.button("🚀 Generate Smart Notes", type="primary", use_container_width=True, key=f"sn_gen_btn_{space_id}")

        if gen_clicked:
            if source_type_val == "curriculum" and not topic_val:
                st.warning("⚠️ Please provide a topic name before generating.")
            elif source_type_val == "document" and not doc_id_val:
                st.warning("⚠️ Please select an uploaded document.")
            else:
                src_label = f"document '{doc_choice_label}'" if source_type_val == "document" else f"topic '{topic_val}'"
                with st.spinner(f"Generating structured Smart Notes from {src_label} in {lang_choice}..."):
                    result = generate_smart_notes(
                        space_id=space_id,
                        topic=topic_val,
                        doc_id=doc_id_val,
                        lang=lang_code,
                        source_type=source_type_val,
                    )
                if result:
                    st.success("✅ Notes generated successfully!")
                    st.session_state[draft_key] = {
                        "id": None,
                        "title": result.get("title", f"{topic_val or subject} - Smart Notes"),
                        "topic": result.get("topic") or topic_val,
                        "content": result.get("content", ""),
                        "source_type": source_type_val,
                        "lang": lang_code,
                        "chunks_used": result.get("chunks_used", 0),
                    }
                    st.session_state[editing_key] = False
                    st.rerun()

        st.divider()

        # ── Active Note / Draft Display & Editor ─────────────────────────────
        draft = st.session_state.get(draft_key)
        if draft:
            st.markdown("#### 2. Note Preview & Actions")

            is_editing = st.session_state.get(editing_key, False)
            chunks_cnt = draft.get("chunks_used", 0)
            lang_label = "Tamil (தமிழ்)" if draft.get("lang") == "ta" else "English"
            badge_text = f"🌐 Language: **{lang_label}**  |  🏷️ Source: **{draft.get('source_type', 'curriculum').title()}**"
            if chunks_cnt > 0:
                badge_text += f"  |  🔍 Grounding: **{chunks_cnt} chunks retrieved**"
            st.caption(badge_text)

            # Metadata controls
            col_t1, col_t2 = st.columns([3, 2])
            with col_t1:
                title_val = st.text_input("Title", value=draft.get("title", ""), key=f"sn_title_input_{space_id}")
            with col_t2:
                topic_tag = st.text_input("Topic Tag", value=draft.get("topic") or "", key=f"sn_topic_input_{space_id}")

            draft["title"] = title_val
            draft["topic"] = topic_tag

            # Mode toggle: Preview vs Edit
            mode_col1, mode_col2, mode_col3 = st.columns([1, 1, 3])
            with mode_col1:
                if st.button("👁️ Reader View", use_container_width=True, type="secondary" if is_editing else "primary", key=f"sn_view_btn_{space_id}"):
                    st.session_state[editing_key] = False
                    st.rerun()
            with mode_col2:
                if st.button("✏️ Edit Markdown", use_container_width=True, type="primary" if is_editing else "secondary", key=f"sn_edit_btn_{space_id}"):
                    st.session_state[editing_key] = True
                    st.rerun()

            if is_editing:
                updated_content = st.text_area(
                    "Markdown Content",
                    value=draft.get("content", ""),
                    height=500,
                    key=f"sn_content_textarea_{space_id}",
                    help="Supports GitHub Flavored Markdown and LaTeX math ($...$)",
                )
                draft["content"] = updated_content
            else:
                with st.container(border=True):
                    st.markdown(draft.get("content", ""))

            # Action buttons
            col_save, col_dl, col_discard = st.columns([2, 2, 1])
            with col_save:
                save_label = "💾 Update Saved Note" if draft.get("id") else "💾 Save to Library"
                if st.button(save_label, type="primary", use_container_width=True, key=f"sn_save_btn_{space_id}"):
                    if not draft.get("content", "").strip():
                        st.error("Cannot save empty notes.")
                    else:
                        with st.spinner("Saving note..."):
                            if draft.get("id"):
                                updated = update_smart_note(
                                    space_id=space_id,
                                    note_id=draft["id"],
                                    title=draft["title"],
                                    content=draft["content"],
                                    topic=draft["topic"],
                                )
                                if updated:
                                    st.success("✅ Note updated!")
                                    st.session_state[draft_key] = updated
                                    st.rerun()
                            else:
                                created = create_smart_note(
                                    space_id=space_id,
                                    title=draft["title"],
                                    content=draft["content"],
                                    topic=draft["topic"],
                                    source_type=draft.get("source_type", "manual"),
                                )
                                if created:
                                    st.success("✅ Note saved to library!")
                                    st.session_state[draft_key] = created
                                    st.rerun()

            with col_dl:
                safe_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', draft.get("title", "smart_notes")).lower()
                st.download_button(
                    label="📥 Download Markdown (.md)",
                    data=draft.get("content", ""),
                    file_name=f"{safe_slug}.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key=f"sn_dl_btn_{space_id}",
                )

            with col_discard:
                if st.button("🗑️ Discard", use_container_width=True, key=f"sn_discard_btn_{space_id}"):
                    st.session_state.pop(draft_key, None)
                    st.session_state.pop(editing_key, None)
                    st.rerun()
        else:
            st.info("💡 Choose a source above and click **🚀 Generate Smart Notes** to generate a new study guide, or open a saved note from the **📚 Saved Notes Library** tab.")

    # ── Subtab: Saved Notes Library ──────────────────────────────────────────
    with subtab_lib:
        st.markdown("#### 📚 Saved Notes Library")
        search_query = st.text_input(
            "🔍 Search notes by keyword, topic, or content...",
            key=f"sn_lib_search_{space_id}",
            placeholder="Type to filter notes...",
        )

        with st.spinner("Loading saved notes..."):
            saved_notes = list_smart_notes(space_id, search=search_query)

        if not saved_notes:
            if search_query:
                st.warning(f"No notes found matching '{search_query}'.")
            else:
                st.info("No notes saved in this space yet. Generate and save notes using the **✨ Generate & Edit** tab!")
        else:
            st.markdown(f"**{len(saved_notes)} Saved Note(s)**")
            for note in saved_notes:
                with st.container(border=True):
                    c_title, c_meta, c_actions = st.columns([3, 2, 2])
                    with c_title:
                        st.subheader(note.get("title", "Untitled Note"))
                    with c_meta:
                        t_tag = note.get("topic") or "General"
                        src = note.get("source_type", "manual").title()
                        created_dt = (note.get("created_at") or "")[:10]
                        st.caption(f"🏷️ Topic: **{t_tag}** | Source: **{src}**\n📅 {created_dt}")
                    with c_actions:
                        btn_c1, btn_c2 = st.columns(2)
                        with btn_c1:
                            if st.button("📖 Open", key=f"sn_open_{note['id']}", type="primary", use_container_width=True):
                                st.session_state[draft_key] = dict(note)
                                st.session_state[editing_key] = False
                                st.rerun()
                        with btn_c2:
                            del_confirm_key = f"sn_del_confirm_{note['id']}"
                            if not st.session_state.get(del_confirm_key):
                                if st.button("🗑️", key=f"sn_del_{note['id']}", use_container_width=True, help="Delete note"):
                                    st.session_state[del_confirm_key] = True
                                    st.rerun()
                            else:
                                if st.button("Confirm", key=f"sn_del_yes_{note['id']}", type="secondary", use_container_width=True):
                                    if delete_smart_note(space_id, note["id"]):
                                        st.success("Note deleted.")
                                        if draft and draft.get("id") == note["id"]:
                                            st.session_state.pop(draft_key, None)
                                        st.session_state.pop(del_confirm_key, None)
                                        st.rerun()

