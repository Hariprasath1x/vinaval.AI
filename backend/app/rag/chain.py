"""
RAG chain for Vinaval AI — exam-specific AI tutor using Groq (Llama 3 70B).

Multilingual Pipeline
---------------------
1. Retrieval  : ChromaDB is queried across BOTH language collections (en + ta)
               for a given exam/subject. The multilingual embedding model
               (paraphrase-multilingual-MiniLM-L12-v2) maps Tamil and English
               queries into the same semantic space, so cross-language retrieval
               works out of the box.

2. LLM        : Groq Llama 3 70B is instructed to:
               • Detect the student's language from their message.
               • Reply in the same language (Tamil or English) automatically.
               • When replying in Tamil, use clear modern Tamil and transliterate
                 technical terms in parentheses where helpful.

3. MCQ/Cards  : Generation prompts pass the detected language so questions and
                explanations are produced in the student's preferred language.

Hybrid RAG (v2)
---------------
Intent classification (keyword-heuristic, zero-latency) routes each query to
the optimal retrieval strategy:

  QUESTION / DEFINE_TERM / FIND_TOPIC
      → Semantic vector search (Chroma) with optional doc_id filter
  LIST_TOPICS
      → Return stored topics metadata (no vector search)
  EXPLAIN_DOCUMENT / SUMMARIZE_DOCUMENT / GENERATE_NOTES /
  GENERATE_QUIZ / GENERATE_FLASHCARDS
      → Load ALL chunks for the active document

When active_doc_id is set, retrieval is restricted to that file only.
When no file is selected, only the pre-seeded syllabus books are searched.
"""
from __future__ import annotations
import json
import logging
import re as _re
import time
from typing import AsyncGenerator, List, Dict, Tuple, Optional
import google.generativeai as genai  # type: ignore
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Shared LLM Completion Helper (Gemini → Groq fallback) ────────────────────

async def _llm_complete(
    prompt: str,
    max_tokens: int = 3000,
    temperature: float = 0.5,
    system_instruction: Optional[str] = None,
    model_override: Optional[str] = None,
    response_mime_type: Optional[str] = None,
) -> str:
    """
    Non-streaming LLM completion using Gemini.
    Returns the raw response text.
    """
    if settings.GEMINI_API_KEY:
        try:
            logger.info(f"[LLM] Attempting Gemini completion (model: {model_override or settings.GEMINI_MODEL})")
            genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore
            model = genai.GenerativeModel(  # type: ignore
                model_override or settings.GEMINI_MODEL,
                system_instruction=system_instruction,
            )
            
            gen_config_kwargs = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
            if response_mime_type:
                gen_config_kwargs["response_mime_type"] = response_mime_type  # type: ignore

            from google.api_core import retry_async, retry
            response = await model.generate_content_async(
                contents=[{"role": "user", "parts": [prompt]}],
                generation_config=genai.types.GenerationConfig(**gen_config_kwargs),  # type: ignore
                request_options={"retry": retry_async.AsyncRetry(predicate=retry.if_transient_error), "timeout": 15.0}
            )
            text = response.text.strip() if response.text else ""
            if text:
                logger.info("[LLM] Gemini completion succeeded")
                return text
            return ""
        except Exception as e:
            logger.error(f"[LLM] Gemini completion failed: {e}. Falling back to Groq.")
            if settings.GROQ_API_KEY:
                try:
                    from groq import AsyncGroq
                    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
                    messages = []
                    if system_instruction:
                        messages.append({"role": "system", "content": system_instruction})
                    messages.append({"role": "user", "content": prompt})
                    chat_completion = await client.chat.completions.create(
                        messages=messages,
                        model=settings.GROQ_MODEL,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    text = chat_completion.choices[0].message.content
                    if text:
                        logger.info("[LLM] Groq completion succeeded")
                        return text
                    return ""
                except Exception as groq_e:
                    logger.error(f"[LLM] Groq fallback failed: {groq_e}")
                    raise ValueError("LLM completion failed for both Gemini and Groq")
            else:
                raise ValueError(f"LLM completion failed: {e}")
    else:
        raise ValueError("No GEMINI_API_KEY configured on the server.")


async def _llm_complete_stream(
    prompt: str,
    max_tokens: int = 3000,
    temperature: float = 0.5,
    system_instruction: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    if settings.GEMINI_API_KEY:
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                settings.GEMINI_MODEL,
                system_instruction=system_instruction,
            )
            gen_config_kwargs = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
            from google.api_core import retry_async, retry
            response_stream = await model.generate_content_async(
                contents=[{"role": "user", "parts": [prompt]}],
                generation_config=genai.types.GenerationConfig(**gen_config_kwargs),
                stream=True,
                request_options={"retry": retry_async.AsyncRetry(predicate=retry.if_transient_error), "timeout": 15.0}
            )
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
            return
        except Exception as e:
            logger.error(f"[LLM] Gemini stream failed: {e}. Falling back to Groq.")
            if settings.GROQ_API_KEY:
                try:
                    from groq import AsyncGroq
                    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
                    messages = []
                    if system_instruction:
                        messages.append({"role": "system", "content": system_instruction})
                    messages.append({"role": "user", "content": prompt})
                    stream = await client.chat.completions.create(
                        messages=messages,
                        model=settings.GROQ_MODEL,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                    async for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                    return
                except Exception as groq_e:
                    logger.error(f"[LLM] Groq fallback stream failed: {groq_e}")
                    raise ValueError("LLM stream failed for both Gemini and Groq")
            else:
                raise ValueError(f"LLM stream failed: {e}")
    else:
        raise ValueError("No GEMINI_API_KEY configured on the server.")

class RAGSystemError(Exception):
    """Raised when ChromaDB or vector store fails."""
    pass

# ── Language Detection (heuristic) ───────────────────────────────────────────
_TAMIL_RE = _re.compile(r"[\u0B80-\u0BFF]")


def _detect_lang(text: str) -> str:
    """Return 'ta' if the text contains significant Tamil Unicode, else 'en'."""
    if not text:
        return "en"
    ratio = len(_TAMIL_RE.findall(text)) / max(len(text), 1)
    return "ta" if ratio > 0.03 else "en"


# ── Intent Classification (keyword heuristic — zero latency) ─────────────────
#
# Intent → Retrieval strategy:
#   LIST_TOPICS          → topics metadata only
#   EXPLAIN_DOCUMENT     → all chunks for active doc
#   SUMMARIZE_DOCUMENT   → all chunks for active doc
#   GENERATE_NOTES       → all chunks for active doc
#   GENERATE_QUIZ        → all chunks for active doc
#   GENERATE_FLASHCARDS  → all chunks for active doc
#   QUESTION / GENERAL   → semantic vector search

_DOC_FULL_PATTERNS = [
    # EXPLAIN_DOCUMENT
    (_re.compile(r"\b(explain all|explain every|go through|teach me all|cover all|walk me through all)\b", _re.I), "EXPLAIN_DOCUMENT"),
    # SUMMARIZE_DOCUMENT
    (_re.compile(r"\b(summarize|summarise|summary|overview|briefly explain|give me an overview)\b", _re.I), "SUMMARIZE_DOCUMENT"),
    # GENERATE_NOTES
    (_re.compile(r"\b(make notes|create notes|generate notes|write notes|prepare notes|revision notes|study notes)\b", _re.I), "GENERATE_NOTES"),
    # GENERATE_QUIZ
    (_re.compile(r"\b(generate quiz|create quiz|make quiz|quiz me|mcq|multiple choice|one-mark|two-mark|question paper)\b", _re.I), "GENERATE_QUIZ"),
    # GENERATE_FLASHCARDS
    (_re.compile(r"\b(flashcard|flash card|make cards|create cards)\b", _re.I), "GENERATE_FLASHCARDS"),
]

_LIST_PATTERNS = _re.compile(
    r"\b(list (all )?(topics|chapters|sections|contents)|what (topics|chapters|sections) are|show (me )?(the )?(topics|chapters|list)|table of contents|contents of|all topics|all chapters)\b",
    _re.I,
)


def classify_intent(message: str) -> str:
    """
    Classify user intent using keyword patterns.
    Returns one of: LIST_TOPICS | EXPLAIN_DOCUMENT | SUMMARIZE_DOCUMENT |
                    GENERATE_NOTES | GENERATE_QUIZ | GENERATE_FLASHCARDS | QUESTION
    """
    if _LIST_PATTERNS.search(message):
        return "LIST_TOPICS"
    for pattern, intent in _DOC_FULL_PATTERNS:
        if pattern.search(message):
            return intent
    return "QUESTION"


# ── System Prompts ────────────────────────────────────────────────────────────


FALLBACK_SYSTEM_PROMPT = """\
{lang_enforcement}\
You are VinavalAI, an educational AI assistant designed to help students learn clearly and effectively.
Your task is to answer the user's question accurately, clearly, and directly.

The question could not be sufficiently answered using the available TN textbook knowledge base, so you are operating in FALLBACK MODE.
Answer the user's question using your general knowledge and reasoning for {exam} ({exam_tag}) - {subject}.

Rules:
1. Answer the actual question directly.
2. Do not claim that information comes from the TN textbook unless textbook context was explicitly provided.
3. Do not fabricate textbook references, chapter names, page numbers, citations, or sources.
4. If you are uncertain about a factual claim, acknowledge the uncertainty rather than inventing information.
5. Keep explanations appropriate for the student's likely academic level.
6. For NEET/TNPSC-related questions, prioritize exam usefulness and conceptual clarity.
7. Use examples when they improve understanding.
8. Use tables for useful comparisons.
9. Use bullet points for lists.
10. Break complicated concepts into smaller sections.
11. Do not unnecessarily repeat the user's question.
12. Do not provide excessively verbose explanations when a concise answer is sufficient.


### Language (IMPORTANT):
{lang_block}
"""

SYSTEM_PROMPT = """\
{lang_enforcement}\
You are Vinaval AI — an expert, encouraging AI tutor for Tamil Nadu students preparing for \
{exam} ({exam_tag}).

You are specialising in **{subject}** for this Learning Space.

### Your Teaching Philosophy:
You are NOT a chatbot that gives one-liner answers. You are a passionate teacher who:
- **Explains deeply** — Give thorough, well-structured explanations (minimum 3-4 paragraphs for concept questions). A student should finish reading your response and genuinely understand the topic.
- **Uses real analogies** — Connect abstract concepts to real-world examples the student can relate to (e.g. explaining diffusion using the smell of perfume spreading across a room).
- **Shows the working** — For numerical problems, show each step clearly with formula → substitution → calculation → result.
- **Uses formatting powerfully** — Use headings (##), bullet points, numbered steps, bold key terms, and markdown tables to organize information.
- **Includes equations** — For Physics and Chemistry, write mathematical formulas using LaTeX inline notation, e.g. $F = ma$, $E = mc^2$, $PV = nRT$.
- **Summarises** — End complex explanations with a short "Key Takeaways" or "Remember" bullet list.
- **Connects topics** — After answering, suggest 1-2 related topics or chapters the student should revise next.
- **Encourages** — Be warm, patient, and motivating. Celebrate progress.

### Response Length Constraints (CRITICAL):
- **Never cut off your response abruptly.** Always wrap up your explanation logically within a reasonable length.
- If you cannot fit the full answer into a single, comprehensive response, provide a high-level summary and focus only on the most critical concepts rather than trailing off.
- For a simple factual question ("What is osmosis?"): 2-3 paragraphs + 1 real example.
- For a concept question ("Explain Newton's Laws"): Full structured explanation, 4-6 paragraphs, with examples, equations, and a summary table.
- For a "how to solve" question: Step-by-step worked solution with all intermediate steps shown.
- For greetings or off-topic: Short and friendly.

### Scope:
- Focus strictly on {exam} {subject} syllabus topics.
- Politely redirect off-topic questions back to studies.

### Language (IMPORTANT):
{lang_block}

{context_block}
You are a deeply knowledgeable, warm, and motivating teacher. \
Your mission is to help every student — Tamil medium or English medium — \
fully master {subject} and crack {exam} with confidence!

"""

# System prompt used when active file context is set or mode is my_study_gpt — stricter grounding
DOCUMENT_SYSTEM_PROMPT = """\
{lang_enforcement}\
You are Vinaval AI — an AI tutor helping a student understand their study materials.

{filename_str}
Subject: {exam} → {subject}

### CRITICAL RULES:
1. Answer STRICTLY based on the content provided in the "### Document Content" or "### Context from Your Study Materials" section below.
2. If a topic is covered in the content, explain it clearly and thoroughly.
3. If a topic is NOT present in the content, say explicitly:
   "I couldn't find enough relevant information in your selected materials to answer this confidently. Try selecting a relevant material or asking about a topic covered in it."
   — DO NOT provide a general answer. Never hallucinate silently. Do NOT substitute information from NCERT, NTA, AIPMT, coaching material, external books, or general model knowledge.
4. Always attribute your answer to the supplied materials when using it.
5. NEVER cut off your response abruptly. Always wrap up your explanation logically within a reasonable length. If you cannot fit the full answer, summarize it instead of trailing off.

### Language:
{lang_block}

{context_block}
Be warm, structured, and thorough.

"""

EXAM_TAGS = {
    "NEET":  "Medical Entrance Exam",
    "TNPSC": "Tamil Nadu Civil Services Exam",
}


# ── RAG Retrieval — Syllabus Books (no doc filter) ───────────────────────────

def _retrieve_syllabus_context(exam: str, subject: str, query: str, n_results: int = 4) -> Tuple[str, int]:
    """
    Semantic search across pre-seeded syllabus book collections only.
    Used when no active file is selected.
    """
    try:
        from app.core.vector_store import get_vector_store

        logger.info(f"[RAG] Looking up collections exam={exam} subject={subject}")
        start_lookup = time.perf_counter()
        collections = get_vector_store().get_collections_for_subject(exam, subject)
        lookup_elapsed = (time.perf_counter() - start_lookup) * 1000

        if not collections:
            logger.info(f"[RAG] Collections found count=0 names=[] elapsed_ms={lookup_elapsed:.2f}")
            return "", 0

        names = [c.name for c in collections]
        logger.info(f"[RAG] Collections found count={len(collections)} names={names} elapsed_ms={lookup_elapsed:.2f}")

        all_docs: List[str] = []
        all_metas: List[dict] = []
        seen: set = set()

        for col in collections:
            try:
                logger.info(f"[RAG] Querying collection={col.name}")
                k = min(max(2, n_results), col.count())
                if k == 0:
                    continue

                logger.info("[RAG] Executing similarity search")
                query_start = time.perf_counter()
                results = col.query(query_texts=[query], n_results=k)
                query_elapsed = (time.perf_counter() - query_start) * 1000
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                logger.info(f"[RAG] Collection query completed collection={col.name} chunks={len(docs)} elapsed_ms={query_elapsed:.2f}")

                for doc, meta in zip(docs, metas):
                    # Skip user-uploaded chunks when in syllabus-only mode
                    if meta.get("source") == "user_upload":
                        continue
                    key = doc[:120]
                    if key not in seen:
                        seen.add(key)
                        all_docs.append(doc)
                        all_metas.append(meta)
            except Exception as exc:
                logger.warning("Retrieval error on collection %s: %s", col.name, exc)

        if not all_docs:
            return "", 0

        all_docs = all_docs[:n_results]
        all_metas = all_metas[:n_results]

        lines = ["### Context from Syllabus:\n"]
        for doc, meta in zip(all_docs, all_metas):
            lang_tag = {"en": "[EN]", "ta": "[TA]"}.get(meta.get("lang", ""), "")
            topic = meta.get("book_title", meta.get("topic", "Syllabus"))
            lines.append(f"**{lang_tag} [{topic}]** {doc.strip()}\n")

        lines.append(
            "\nUse the above context to answer accurately. "
            "If the question is not covered by context, draw on your general "
            "knowledge of the syllabus.\n"
        )
        return "\n".join(lines) + "\n", len(all_docs)

    except Exception as exc:
        logger.error("ChromaDB retrieval failed: %s", exc)
        raise RAGSystemError("Retrieval system error") from exc


# ── RAG Retrieval — User RAG (My Study GPT) ──────────────────────────────────

def _retrieve_user_context(
    exam: str, subject: str, query: str, space_id: int, n_results: int = 5
) -> Tuple[str, int]:
    """
    Semantic search restricted to a student's personal learning space (User RAG).
    Only returns chunks from documents uploaded by the user to this specific space.
    """
    try:
        from app.core.vector_store import get_vector_store

        logger.info(f"[RAG] Looking up user collections exam={exam} subject={subject} space_id={space_id}")
        start_lookup = time.perf_counter()
        collections = get_vector_store().get_collections_for_subject(exam, subject)
        _ = (time.perf_counter() - start_lookup) * 1000

        if not collections:
            return "", 0

        all_docs: List[str] = []
        all_metas: List[dict] = []
        seen: set = set()

        for col in collections:
            try:
                k = min(max(2, n_results), col.count())
                if k == 0:
                    continue

                # We query for space_id and source = user_upload
                # Note: If the vector provider doesn't support $and perfectly, we filter in memory too
                results = col.query(
                    query_texts=[query],
                    n_results=k * 2, # fetch extra to account for manual filtering
                    where={"space_id": space_id}
                )
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                
                for doc, meta in zip(docs, metas):
                    if meta.get("space_id") != space_id or meta.get("source") != "user_upload":
                        continue
                        
                    key = doc[:120]
                    if key not in seen:
                        seen.add(key)
                        all_docs.append(doc)
                        all_metas.append(meta)
            except Exception as exc:
                logger.warning("User-filtered retrieval error on %s: %s", col.name, exc)

        if not all_docs:
            return "", 0

        # Sort by relevance roughly (since we interleaved multiple collections, we just take the top N we gathered)
        all_docs = all_docs[:n_results]
        all_metas = all_metas[:n_results]

        lines = ["### Context from Your Study Materials:\n"]
        for doc, meta in zip(all_docs, all_metas):
            topic = meta.get("topic", "")
            mat_type = meta.get("material_type", "")
            label = f"[{mat_type} - {topic}]" if topic else f"[{mat_type}]"
            lines.append(f"**{label}** {doc.strip()}\n")

        lines.append(
            "\nUse ONLY the above context to answer. "
            "If the question is not covered by the context, state clearly that "
            "the user's materials do not contain the answer.\n"
        )
        return "\n".join(lines) + "\n", len(all_docs)

    except Exception as exc:
        logger.error("User context retrieval failed: %s", exc)
        raise RAGSystemError("Retrieval system error") from exc


# ── RAG Retrieval — Active File (vector search with doc_id filter) ────────────

def _retrieve_doc_context(
    exam: str, subject: str, query: str, doc_id: int, n_results: int = 5
) -> Tuple[str, int]:
    """
    Semantic search restricted to a single uploaded document via doc_id filter.
    """
    try:
        from app.core.vector_store import get_vector_store

        logger.info(f"[RAG] Looking up collections exam={exam} subject={subject}")
        start_lookup = time.perf_counter()
        collections = get_vector_store().get_collections_for_subject(exam, subject)
        lookup_elapsed = (time.perf_counter() - start_lookup) * 1000

        if not collections:
            logger.info(f"[RAG] Collections found count=0 names=[] elapsed_ms={lookup_elapsed:.2f}")
            return "", 0

        names = [col.name for col in collections]
        logger.info(f"[RAG] Collections found count={len(collections)} names={names} elapsed_ms={lookup_elapsed:.2f}")

        all_docs: List[str] = []
        all_metas: List[dict] = []
        seen: set = set()

        for col in collections:
            try:
                logger.info(f"[RAG] Querying collection={col.name}")
                k = min(max(2, n_results), col.count())
                if k == 0:
                    continue

                logger.info("[RAG] Executing similarity search")
                query_start = time.perf_counter()
                results = col.query(
                    query_texts=[query],
                    n_results=k,
                    where={"doc_id": doc_id},
                )
                query_elapsed = (time.perf_counter() - query_start) * 1000
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                logger.info(f"[RAG] Collection query completed collection={col.name} chunks={len(docs)} elapsed_ms={query_elapsed:.2f}")
                for doc, meta in zip(docs, metas):
                    key = doc[:120]
                    if key not in seen:
                        seen.add(key)
                        all_docs.append(doc)
                        all_metas.append(meta)
            except Exception as exc:
                logger.warning("Doc-filtered retrieval error on %s: %s", col.name, exc)

        if not all_docs:
            return "", 0

        all_docs = all_docs[:n_results]
        all_metas = all_metas[:n_results]

        lines = ["### Document Content (from uploaded notes):\n"]
        for doc, meta in zip(all_docs, all_metas):
            topic = meta.get("topic", "")
            label = f"[{topic}]" if topic else ""
            lines.append(f"**{label}** {doc.strip()}\n")

        return "\n".join(lines) + "\n", len(all_docs)

    except Exception as exc:
        logger.error("Doc retrieval failed: %s", exc)
        raise RAGSystemError("Retrieval system error") from exc


# ── RAG Retrieval — Load ALL chunks for a document ────────────────────────────

def _load_all_doc_chunks(exam: str, subject: str, doc_id: int) -> Tuple[str, int, List[str]]:
    """
    Load ALL stored chunks for a specific document (bypasses vector search).
    Used for EXPLAIN_DOCUMENT, SUMMARIZE_DOCUMENT, GENERATE_NOTES, etc.

    Returns (context_block_str, chunk_count, unique_topics_list)
    """
    try:
        from app.core.vector_store import get_vector_store
        collections = get_vector_store().get_collections_for_subject(exam, subject)
        if not collections:
            return "", 0, []

        all_docs: List[str] = []
        all_metas: List[dict] = []
        seen_ids: set = set()

        for col in collections:
            try:
                results = col.get(where={"doc_id": doc_id})
                docs = results.get("documents", [])
                metas = results.get("metadatas", [])
                ids = results.get("ids", [])
                for doc_id_item, doc, meta in zip(ids, docs, metas):
                    if doc_id_item not in seen_ids:
                        seen_ids.add(doc_id_item)
                        all_docs.append(doc)
                        all_metas.append(meta)
            except Exception as exc:
                logger.warning("Full-doc load error on %s: %s", col.name, exc)

        if not all_docs:
            return "", 0, []

        # Sort by chunk_index for logical order
        paired = sorted(zip(all_metas, all_docs), key=lambda x: x[0].get("chunk_index", 0))
        if paired:
            unzipped = list(zip(*paired))
            all_metas, all_docs = list(unzipped[0]), list(unzipped[1])
        else:
            all_metas, all_docs = [], []

        topics_found: List[str] = []
        seen_topics: set = set()
        lines = ["### Complete Document Content (from uploaded notes):\n"]
        for doc, meta in zip(all_docs, all_metas):
            topic = meta.get("topic", "")
            if topic and topic not in seen_topics:
                seen_topics.add(topic)
                topics_found.append(topic)
                lines.append(f"\n#### {topic}\n")
            lines.append(doc.strip() + "\n")

        return "\n".join(lines), len(all_docs), topics_found

    except Exception as exc:
        logger.error("Failed to load all doc chunks: %s", exc)
        raise RAGSystemError("Retrieval system error") from exc


# ── Topics Metadata Retrieval ─────────────────────────────────────────────────

def _get_topics_from_metadata(exam: str, subject: str, doc_id: int) -> List[str]:
    """
    Extract unique topic labels from ChromaDB chunk metadata for a document.
    Much faster than loading full text.
    """
    try:
        from app.core.vector_store import get_vector_store
        collections = get_vector_store().get_collections_for_subject(exam, subject)
        topics: List[str] = []
        seen: set = set()
        for col in collections:
            try:
                results = col.get(where={"doc_id": doc_id}, include=["metadatas"])
                for meta in results.get("metadatas", []):
                    t = meta.get("topic", "")
                    if t and t not in seen:
                        seen.add(t)
                        topics.append(t)
            except Exception:
                pass
        return topics
    except Exception:
        return []


# ── System Prompt Builder ─────────────────────────────────────────────────────

def _build_lang_block(forced_lang: Optional[str] = None) -> str:
    if forced_lang == "ta":
        return (
            "🔴 STRICT LANGUAGE RULE — TAMIL ONLY:\n"
            "- You MUST write your ENTIRE response in **Tamil** only.\n"
            "- Do NOT write any sentences or bullet points in English.\n"
            "- Do NOT switch to English mid-response.\n"
            "- Use clear, modern Tamil script (தமிழ்).\n"
            "- For technical/scientific terms, write the Tamil word first, then the English term in parentheses — e.g. \"ஒளிச்சேர்க்கை (Photosynthesis)\".\n"
            "- Headings, bullet points, and all prose MUST be in Tamil.\n"
            "- Equations and chemical formulas remain in their universal notation (e.g. H₂O, E=mc²)."
        )
    elif forced_lang == "en":
        return (
            "🔴 STRICT LANGUAGE RULE — ENGLISH ONLY:\n"
            "- You MUST write your ENTIRE response in **English** only.\n"
            "- Do NOT write any Tamil script (தமிழ்) anywhere in your response.\n"
            "- Do NOT include Tamil words, Tamil translations, or Tamil text in parentheses.\n"
            "- Do NOT mix Tamil and English (no \"Tanglish\").\n"
            "- All headings, bullet points, explanations, and examples must be in English.\n"
            "- Even if the reference material contains Tamil text, translate the meaning into English — do NOT copy Tamil script into your answer."
        )
    else:
        return (
            "- Detect the language the student is writing in.\n"
            "- If the student writes in **Tamil**, reply entirely in **Tamil**.\n"
            "  • Use clear, modern Tamil.\n"
            "  • For technical terms, write the Tamil word first, then the English term in parentheses — e.g. \"ஒளிச்சேர்க்கை (Photosynthesis)\".\n"
            "  • Use markdown formatting even in Tamil replies.\n"
            "  • Equations and chemical formulas remain in their universal notation.\n"
            "- If the student writes in **English**, reply in **English**.\n"
            "- If the student mixes languages (Tanglish), match their style naturally."
        )


def _build_system_prompt(
    exam: str,
    subject: str,
    context_block: str = "",
    forced_lang: Optional[str] = None,
    filename: Optional[str] = None,
    mode: str = "rag",
) -> str:
    tag = EXAM_TAGS.get(exam, exam)
    lang_block = _build_lang_block(forced_lang)

    # Top-of-prompt language enforcement banner (only when language is explicitly forced)
    if forced_lang in ("en", "ta"):
        lang_name = "ENGLISH" if forced_lang == "en" else "TAMIL"
        lang_enforcement = (
            f"⚠️  CRITICAL INSTRUCTION — OUTPUT LANGUAGE: {lang_name} ONLY\n"
            f"Your response MUST be written entirely in {lang_name}. "
            f"No exceptions. Ignore the language of any retrieved context chunks.\n\n"
        )
    else:
        lang_enforcement = ""

    if mode == "fallback":
        return FALLBACK_SYSTEM_PROMPT.format(
            exam=exam,
            exam_tag=tag,
            subject=subject,
            lang_block=lang_block,
            lang_enforcement=lang_enforcement,
        )

    if mode == "my_study_gpt" or filename:
        filename_str = f"Active document: **{filename}**" if filename else "Source: User Study Materials"
        return DOCUMENT_SYSTEM_PROMPT.format(
            exam=exam,
            subject=subject,
            filename_str=filename_str,
            lang_block=lang_block,
            lang_enforcement=lang_enforcement,
            context_block=context_block,
        )

    return SYSTEM_PROMPT.format(
        exam=exam,
        exam_tag=tag,
        subject=subject,
        lang_block=lang_block,
        lang_enforcement=lang_enforcement,
        context_block=context_block,
    )


# ── Chat ──────────────────────────────────────────────────────────────────────

async def stream_chat(
    exam: str,
    subject: str,
    history: List[Dict[str, str]],
    user_message: str,
    forced_lang: Optional[str] = None,
    active_doc_id: Optional[int] = None,
    active_doc_filename: Optional[str] = None,
    space_id: Optional[int] = None,
    previous_state: Optional[Dict] = None,
    mode: str = "ai_tutor",
) -> AsyncGenerator[str, None]:
    """
    Stream an AI response token-by-token using Groq's async client.
    """
    from app.rag.retrieval_log import log_retrieval

    t_start = time.monotonic()
    
    if previous_state:
        # ── CONTINUATION MODE ──
        # Skip RAG completely, reuse the previous context and mode
        logger.info("[CHAT] Resuming previous generation state.")
        intent = "QUESTION"
        context_block = previous_state.get("context", "")
        mode = previous_state.get("mode", "rag")
        n_chunks = len(context_block) // 500 if context_block else 0
        n_topics = 0
        filename = active_doc_filename
    else:
        # ── NORMAL MODE ──
        intent = classify_intent(user_message)
        context_block = ""
        n_chunks = 0
        n_topics = 0
        filename = active_doc_filename
        try:
            if mode == "my_study_gpt":
                if active_doc_id:
                    if intent == "LIST_TOPICS":
                        topics = _get_topics_from_metadata(exam, subject, active_doc_id)
                        n_topics = len(topics)
                        if topics:
                            topic_lines = "\n".join(f"- {t}" for t in topics)
                            context_block = f"### Topics in the uploaded document:\n{topic_lines}\n"
                        else:
                            context_block = "### Note: No specific topic headings were detected in this document.\n"
                    elif intent in ("EXPLAIN_DOCUMENT", "SUMMARIZE_DOCUMENT", "GENERATE_NOTES",
                                    "GENERATE_QUIZ", "GENERATE_FLASHCARDS"):
                        context_block, n_chunks, found_topics = _load_all_doc_chunks(exam, subject, active_doc_id)
                        n_topics = len(found_topics)
                    else:
                        intent = "QUESTION"
                        context_block, n_chunks = _retrieve_doc_context(
                            exam, subject, user_message, active_doc_id, n_results=3
                        )
                elif space_id:
                    intent = "QUESTION"
                    logger.info(f"[RAG] Mode: My Study GPT, querying user space_id={space_id}")
                    context_block, n_chunks = _retrieve_user_context(exam, subject, user_message, space_id, n_results=4)
                    
                if n_chunks == 0 and intent == "QUESTION":
                    # For My Study GPT, do not fall back to syllabus RAG or general knowledge. Just yield error.
                    yield "I couldn't find enough relevant information in your selected materials to answer this confidently. Try selecting a relevant material or asking about a topic covered in it."
                    return
                    
            else:
                # mode == "ai_tutor"
                if active_doc_id:
                    if intent == "LIST_TOPICS":
                        topics = _get_topics_from_metadata(exam, subject, active_doc_id)
                        n_topics = len(topics)
                        if topics:
                            topic_lines = "\n".join(f"- {t}" for t in topics)
                            context_block = f"### Topics in the uploaded document:\n{topic_lines}\n"
                        else:
                            context_block = "### Note: No specific topic headings were detected in this document.\n"
                    elif intent in ("EXPLAIN_DOCUMENT", "SUMMARIZE_DOCUMENT", "GENERATE_NOTES",
                                    "GENERATE_QUIZ", "GENERATE_FLASHCARDS"):
                        context_block, n_chunks, found_topics = _load_all_doc_chunks(exam, subject, active_doc_id)
                        n_topics = len(found_topics)
                    else:
                        intent = "QUESTION"
                        context_block, n_chunks = _retrieve_doc_context(
                            exam, subject, user_message, active_doc_id, n_results=3
                        )
                else:
                    intent = "QUESTION"
                    context_block, n_chunks = _retrieve_syllabus_context(exam, subject, user_message, n_results=3)
                    
                if n_chunks == 0 and intent == "QUESTION" and not active_doc_id:
                    # AI Tutor can fall back to general knowledge if syllabus RAG yields 0 chunks.
                    mode = "fallback"
                
        except RAGSystemError:
            # If ChromaDB fails entirely, yield a friendly error message and stop.
            yield "I'm having trouble accessing my textbook knowledge base right now. Please try again in a moment."
            return

    retrieval_ms = (time.monotonic() - t_start) * 1000

    try:
        log_retrieval(
            space_id=space_id or 0,
            active_doc_id=active_doc_id,
            intent=intent,
            chunks_retrieved=n_chunks,
            topics_used=n_topics,
            retrieval_ms=retrieval_ms,
        )
    except Exception:
        pass  # never let logging break the response

    logger.debug(
        "RAG intent=%s doc_id=%s chunks=%d topics=%d retrieval_ms=%.0f mode=%s",
        intent, active_doc_id, n_chunks, n_topics, retrieval_ms, mode
    )

    system_prompt = _build_system_prompt(exam, subject, context_block, forced_lang, filename, mode=mode)

    # Output a hidden state token at the very beginning so the backend service can capture the state
    import json
    state_json = json.dumps({"mode": mode, "context": context_block})
    yield f"[STATE_DUMP]{state_json}[/STATE_DUMP]"

    # Truncate history to prevent exceeding token limits
    # Keep only the last 6 messages (3 turns)
    recent_history = history[-6:] if history else []

    # Use higher token budget for full-doc operations, but keep it safe for API limits.
    # We increase this from 3000 to 6000 to prevent abrupt cutoffs, while relying on system prompts for conciseness.
    max_tokens = 6000 if intent in ("EXPLAIN_DOCUMENT", "SUMMARIZE_DOCUMENT",
                                     "GENERATE_NOTES") else 3000

    if settings.GEMINI_API_KEY:
        try:
            logger.info("[LLM] Starting LLM request")
            logger.info(f"[LLM] provider=gemini model={settings.GEMINI_MODEL} context_chunks={n_chunks} history_messages={len(recent_history)}")
            genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore
            model = genai.GenerativeModel(settings.GEMINI_MODEL, system_instruction=system_prompt)  # type: ignore

            gemini_history = []
            for msg in recent_history:
                # Map roles: 'assistant' -> 'model', 'user' -> 'user'
                role = "model" if msg["role"] == "assistant" else "user"
                gemini_history.append({"role": role, "parts": [msg["content"]]})

            gemini_history.append({"role": "user", "parts": [user_message]})

            logger.info("[LLM] LLM request started")
            llm_start = time.perf_counter()
            stream = await model.generate_content_async(
                contents=gemini_history,
                stream=True,
                generation_config=genai.types.GenerationConfig(  # type: ignore
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                )
            )

            first_chunk = True
            async for chunk in stream:
                if first_chunk:
                    first_elapsed = (time.perf_counter() - llm_start) * 1000
                    logger.info(f"[LLM] First response chunk received elapsed_ms={first_elapsed:.2f}")
                    first_chunk = False
                if chunk.text:
                    yield chunk.text

            llm_elapsed = (time.perf_counter() - llm_start) * 1000
            logger.info(f"[LLM] LLM stream completed elapsed_ms={llm_elapsed:.2f}")
            return

        except Exception as e:
            logger.exception(f"[LLM] Gemini API failed exception_type={type(e).__name__}. Falling back to Groq.")
            if settings.GROQ_API_KEY:
                try:
                    from groq import AsyncGroq
                    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    
                    for msg in recent_history:
                        role = "assistant" if msg["role"] == "assistant" else "user"
                        messages.append({"role": role, "content": msg["content"]})
                    messages.append({"role": "user", "content": user_message})

                    logger.info(f"[LLM] provider=groq model={settings.GROQ_MODEL}")
                    llm_start = time.perf_counter()
                    
                    stream = await client.chat.completions.create(
                        messages=messages,
                        model=settings.GROQ_MODEL,
                        temperature=0.7,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                    
                    first_chunk = True
                    async for chunk in stream:
                        if first_chunk:
                            first_elapsed = (time.perf_counter() - llm_start) * 1000
                            logger.info(f"[LLM] First response chunk received (Groq) elapsed_ms={first_elapsed:.2f}")
                            first_chunk = False
                        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content

                    llm_elapsed = (time.perf_counter() - llm_start) * 1000
                    logger.info(f"[LLM] LLM stream completed (Groq) elapsed_ms={llm_elapsed:.2f}")
                    return
                except Exception as groq_e:
                    logger.exception(f"[LLM] Groq API fallback failed exception_type={type(groq_e).__name__}")
                    yield "Error: An unexpected error occurred while communicating with the LLMs."
            else:
                yield "Error: An unexpected error occurred while communicating with the LLM."
    else:
        logger.error("[LLM] No GEMINI_API_KEY configured.")
        yield "Error: No API key configured on the server."


async def get_chat_response(
    exam: str,
    subject: str,
    history: List[Dict[str, str]],
    user_message: str,
    forced_lang: Optional[str] = None,
    active_doc_id: Optional[int] = None,
    active_doc_filename: Optional[str] = None,
) -> str:
    """Non-streaming version — returns full response. Used as fallback or for testing."""
    parts = []
    async for chunk in stream_chat(
        exam, subject, history, user_message, forced_lang,
        active_doc_id, active_doc_filename
    ):
        parts.append(chunk)
    return "".join(parts)


# ── MCQ Generation ────────────────────────────────────────────────────────────

MCQ_SYSTEM = """\
You are an expert MCQ question generator for Tamil Nadu competitive exams.
{topic_instruction}
for {exam} {subject}.

{context_block}
### Output Language:
{lang_instruction}

STRICT OUTPUT FORMAT — respond ONLY with Newline Delimited JSON (NDJSON).
Each question MUST be a single, flat JSON object on its own line, with NO line breaks inside the object.
Example:
{{"topic": "Specific chapter or topic name", "question": "Full question text here?", "option_a": "First option", "option_b": "Second option", "option_c": "Third option", "option_d": "Fourth option", "correct_option": "a", "explanation": "Brief explanation of why the answer is correct."}}

Rules:
- Each object on a new line.
- Each question must have exactly 4 options (a, b, c, d).
- correct_option must be one of: "a", "b", "c", "d".
- Questions should be exam-level difficulty.
- Output ONLY the raw JSON lines — absolutely no markdown, no code fences, no array brackets.
"""

_MCQ_LANG_INSTRUCTIONS = {
    "ta": (
        "Generate ALL question text, options, and explanations in Tamil. "
        "For technical/scientific terms, include the English term in parentheses — "
        "e.g. 'ஒளிச்சேர்க்கை (Photosynthesis)'."
    ),
    "en": "Generate all question text, options, and explanations in English.",
}


async def generate_mcqs(
    exam: str,
    subject: str,
    topic: Optional[str] = None,
    count: int = 5,
    lang: str = "en",
    source_type: str = "curriculum",
    space_id: Optional[int] = None,
) -> List[Dict]:
    """
    Generate MCQ questions using Groq, grounded in ChromaDB context.
    """
    search_query = topic if topic else f"{exam} {subject} syllabus overview"
    
    if source_type == "user" and space_id:
        context_block, chunk_count = _retrieve_user_context(exam, subject, search_query, space_id, n_results=5 if not topic else 3)
        if chunk_count > 0 and len(context_block) < 500:
            # Augment with curriculum if user context is very sparse (e.g. just topic names)
            syl_context, _ = _retrieve_syllabus_context(exam, subject, search_query, n_results=2)
            context_block += "\n\n### Additional Reference Material:\n" + syl_context
    else:
        context_block, _ = _retrieve_syllabus_context(exam, subject, search_query, n_results=5 if not topic else 3)
        
    if context_block:
        if len(context_block) > 15000:
            context_block = context_block[:15000] + "\n...[truncated]"
        context_block = (
            "### Reference Material from Syllabus:\n" + context_block +
            "\nBase your questions on this material where possible.\n"
        )

    lang_instruction = _MCQ_LANG_INSTRUCTIONS.get(lang, _MCQ_LANG_INSTRUCTIONS["en"])

    async def generate_batch(batch_count: int, batch_index: int) -> List[Dict]:
        batch_prompt = MCQ_SYSTEM.format(
            exam=exam,
            subject=subject,
            topic_instruction=f"Generate exactly {batch_count} multiple-choice questions on the topic: \"{topic}\"" if topic else f"Generate exactly {batch_count} multiple-choice questions covering diverse topics",
            count=batch_count,
            context_block=context_block,
            lang_instruction=lang_instruction,
        )
        
        t0 = time.perf_counter()
        raw = await _llm_complete(
            batch_prompt, 
            max_tokens=4096, 
            temperature=0.5,
            response_mime_type="application/json"
        )
        logger.info(f"[TELEMETRY] generate_mcqs batch {batch_index} LLM time: {time.perf_counter() - t0:.3f}s for {batch_count} Qs")
        
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1] if len(parts) >= 3 else raw.replace("```json", "").replace("```", "")
            if raw.strip().startswith("json"):
                raw = raw.strip()[4:]
                
        raw = raw.strip()
        
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            # Basic recovery
            last_brace = raw.rfind("}")
            first_bracket = raw.find("[")
            if last_brace != -1 and first_bracket != -1:
                try:
                    repaired = raw[first_bracket:last_brace + 1] + "]"
                    return json.loads(repaired)
                except Exception:
                    pass
            logger.error(f"Failed to parse MCQ JSON: {e}")
            return []

    # Chunk into batches of max 10 for parallel generation
    import asyncio
    batch_sizes = []
    remaining = count
    while remaining > 0:
        sz = min(10, remaining)
        batch_sizes.append(sz)
        remaining -= sz

    t_start = time.perf_counter()
    tasks = [generate_batch(sz, i) for i, sz in enumerate(batch_sizes)]
    results = await asyncio.gather(*tasks)
    
    questions = []
    for r in results:
        if isinstance(r, list):
            questions.extend(r)
            
    logger.info(f"[TELEMETRY] generate_mcqs total parallel time: {time.perf_counter() - t_start:.3f}s for {len(questions)} Qs (requested {count})")
    return questions[:count]


# ── Flashcard Generation ──────────────────────────────────────────────────────

FLASHCARD_SYSTEM = """\
You are an expert study-card creator for Tamil Nadu competitive exams.
Generate exactly {count} flashcards on the topic: "{topic}"
for {exam} {subject}.

{context_block}
### Output Language:
{lang_instruction}

STRICT OUTPUT FORMAT — respond ONLY with Newline Delimited JSON (NDJSON).
Each flashcard MUST be a single, flat JSON object on its own line, with NO line breaks inside the object.
Example:
{{"front": "Term or question here?", "back": "Definition or answer here."}}

Rules:
- Each object on a new line.
- front: a concise term, concept, formula label, or question.
- back: a clear, complete explanation or answer.
- Flashcards must be exam-relevant and factually accurate.
- Output ONLY the raw JSON lines — absolutely no markdown, no code fences, no array brackets.
"""

_FLASH_LANG_INSTRUCTIONS = {
    "ta": (
        "Write ALL fronts and backs in Tamil. "
        "For technical terms, show the Tamil word first then the English in parentheses."
    ),
    "en": "Write all fronts and backs in English.",
}


async def generate_flashcards(
    exam: str,
    subject: str,
    topic: str,
    count: int = 8,
    lang: str = "en",
) -> List[Dict]:
    """Generate flashcard pairs (front/back) using Groq, grounded in ChromaDB context."""
    context_block, _ = _retrieve_syllabus_context(exam, subject, topic, n_results=5)
    if context_block:
        context_block = (
            "### Reference Material from Syllabus:\n" + context_block +
            "\nBase the flashcards strictly on this material.\n"
        )

    lang_instruction = _FLASH_LANG_INSTRUCTIONS.get(lang, _FLASH_LANG_INSTRUCTIONS["en"])

    async def generate_batch(batch_count: int, batch_index: int) -> List[Dict]:
        batch_prompt = FLASHCARD_SYSTEM.format(
            exam=exam,
            subject=subject,
            topic=topic,
            count=batch_count,
            context_block=context_block,
            lang_instruction=lang_instruction,
        )

        t0 = time.perf_counter()
        raw = await _llm_complete(
            batch_prompt, 
            max_tokens=4096, 
            temperature=0.4,
            response_mime_type="application/json"
        )
        logger.info(f"[TELEMETRY] generate_flashcards batch {batch_index} LLM time: {time.perf_counter() - t0:.3f}s for {batch_count} cards")
        
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1] if len(parts) >= 3 else raw.replace("```json", "").replace("```", "")
            if raw.strip().startswith("json"):
                raw = raw.strip()[4:]
                
        raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            last_brace = raw.rfind("}")
            first_bracket = raw.find("[")
            if last_brace != -1 and first_bracket != -1:
                try:
                    repaired = raw[first_bracket:last_brace + 1] + "]"
                    return json.loads(repaired)
                except Exception:
                    pass
            logger.error(f"Failed to parse Flashcard JSON: {e}")
            return []

    import asyncio
    batch_sizes = []
    remaining = count
    while remaining > 0:
        sz = min(15, remaining)  # Flashcards are smaller, so we can do larger batches
        batch_sizes.append(sz)
        remaining -= sz

    t_start = time.perf_counter()
    tasks = [generate_batch(sz, i) for i, sz in enumerate(batch_sizes)]
    results = await asyncio.gather(*tasks)
    
    cards = []
    for r in results:
        if isinstance(r, list):
            cards.extend(r)
            
    logger.info(f"[TELEMETRY] generate_flashcards total parallel time: {time.perf_counter() - t_start:.3f}s for {len(cards)} cards (requested {count})")
    return cards[:count]


# ── Quiz Review ───────────────────────────────────────────────────────────────

REVIEW_SYSTEM = """\
You are an expert tutor for {exam} {subject}.
A student has just completed a quiz. Here are the results of the questions they answered:

{results_block}

Total score: {score}/{total} ({percentage}%)

Write a short, encouraging review of their performance in a single paragraph (max 4-5 sentences).
Specifically highlight which topics they are strong in and which topics they need to concentrate more on.
Be highly encouraging, personalized, and constructive. If they did poorly, tell them it's part of the learning process.
"""


async def generate_quiz_review(
    exam: str,
    subject: str,
    results: List[Dict[str, bool]],
) -> str:
    """Generate a quick AI review of the student's quiz performance."""
    total = len(results)
    if total == 0:
        return "No questions answered yet. Keep studying!"

    score = sum(1 for r in results if r["is_correct"])
    percentage = round(score / total * 100, 1)

    results_lines = []
    for i, r in enumerate(results, 1):
        status = "Correct" if r["is_correct"] else "Incorrect"
        results_lines.append(f"Q{i} (Topic: {r['topic']}) - {status}")

    results_block = "\n".join(results_lines)

    prompt = REVIEW_SYSTEM.format(
        exam=exam,
        subject=subject,
        results_block=results_block,
        score=score,
        total=total,
        percentage=percentage,
    )

    return await _llm_complete(prompt, max_tokens=300, temperature=0.6)


# ── Performance Analysis ──────────────────────────────────────────────────────

PERFORMANCE_ANALYSIS_SYSTEM = """\
You are an expert academic mentor analyzing a student's performance on a quiz for {exam} {subject}.

Here is the student's structured performance data:
{metrics_json}

Please write a comprehensive, encouraging performance analysis.
Provide the output strictly in the following JSON format without any markdown wrappers or extra text.
{{
  "overall_summary": "A 2-4 sentence paragraph summarizing their overall performance.",
  "ai_narrative": "A full, personalized mentor paragraph giving them guidance on what to do next based on their performance, pointing out specific strong/weak topics mentioned in the metrics."
}}
"""

async def generate_performance_analysis(
    exam: str,
    subject: str,
    structured_metrics: Dict,
) -> Dict[str, str]:
    """Generate a detailed AI performance narrative from structured metrics."""
    # We strip out large JSON blobs to save tokens if necessary, but here we pass it all
    # since it's already structured and relatively small.
    metrics_json = json.dumps(structured_metrics, indent=2)
    prompt = PERFORMANCE_ANALYSIS_SYSTEM.format(
        exam=exam,
        subject=subject,
        metrics_json=metrics_json,
    )

    raw = await _llm_complete(prompt, max_tokens=1000, temperature=0.6)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse performance analysis JSON. Error: {e}")
        return {
            "overall_summary": "Excellent effort on completing the test.",
            "ai_narrative": "Your performance data was processed successfully."
        }

async def generate_mcqs_stream(
    exam: str,
    subject: str,
    topic: Optional[str] = None,
    count: int = 5,
    lang: str = "en",
    source_type: str = "curriculum",
    space_id: Optional[int] = None,
) -> AsyncGenerator[Dict, None]:
    search_query = topic if topic else f"{exam} {subject} syllabus overview"
    
    if source_type == "user" and space_id:
        context_block, chunk_count = _retrieve_user_context(exam, subject, search_query, space_id, n_results=5 if not topic else 3)
        if chunk_count > 0 and len(context_block) < 500:
            syl_context, _ = _retrieve_syllabus_context(exam, subject, search_query, n_results=2)
            context_block += "\n\n### Additional Reference Material:\n" + syl_context
    else:
        context_block, _ = _retrieve_syllabus_context(exam, subject, search_query, n_results=5 if not topic else 3)
        
    if context_block:
        if len(context_block) > 15000:
            context_block = context_block[:15000] + "\n...[truncated]"
        context_block = (
            "### Reference Material from Syllabus:\n" + context_block +
            "\nBase your questions on this material where possible.\n"
        )

    lang_instruction = _MCQ_LANG_INSTRUCTIONS.get(lang, _MCQ_LANG_INSTRUCTIONS["en"])

    batch_prompt = MCQ_SYSTEM.format(
        exam=exam,
        subject=subject,
        topic_instruction=f'Generate exactly {count} multiple-choice questions on the topic: "{topic}"' if topic else f'Generate exactly {count} multiple-choice questions covering diverse topics',
        count=count,
        context_block=context_block,
        lang_instruction=lang_instruction,
    )
    
    buffer = ""
    brace_count = 0
    obj_str = ""
    async for chunk in _llm_complete_stream(batch_prompt, max_tokens=4096, temperature=0.5):
        buffer += chunk
        while buffer:
            if brace_count == 0:
                start = buffer.find("{")
                if start == -1:
                    buffer = ""
                    break
                buffer = buffer[start:]
                brace_count = 1
                obj_str = "{"
                buffer = buffer[1:]
            
            # Find the next { or }
            next_open = buffer.find("{")
            next_close = buffer.find("}")
            
            if next_close == -1:
                obj_str += buffer
                buffer = ""
                break
                
            if next_open != -1 and next_open < next_close:
                brace_count += 1
                obj_str += buffer[:next_open + 1]
                buffer = buffer[next_open + 1:]
            else:
                brace_count -= 1
                obj_str += buffer[:next_close + 1]
                buffer = buffer[next_close + 1:]
                
                if brace_count == 0:
                    try:
                        obj = json.loads(obj_str)
                        yield obj
                    except Exception:
                        pass
                    obj_str = ""


async def generate_flashcards_stream(
    exam: str,
    subject: str,
    topic: str,
    count: int = 10,
    lang: str = "en",
    source_type: str = "curriculum",
    space_id: Optional[int] = None,
) -> AsyncGenerator[Dict, None]:
    if source_type == "user" and space_id:
        context_block, chunk_count = _retrieve_user_context(exam, subject, topic, space_id, n_results=5)
        if chunk_count > 0 and len(context_block) < 500:
            syl_context, _ = _retrieve_syllabus_context(exam, subject, topic, n_results=2)
            context_block += "\n\n### Additional Reference Material:\n" + syl_context
    else:
        context_block, _ = _retrieve_syllabus_context(exam, subject, topic, n_results=5)

    if context_block:
        if len(context_block) > 15000:
            context_block = context_block[:15000] + "\n...[truncated]"
        context_block = (
            "### Reference Material from Syllabus:\n" + context_block +
            "\nBase your flashcards on this material where possible.\n"
        )

    lang_instruction = _FLASH_LANG_INSTRUCTIONS.get(lang, _FLASH_LANG_INSTRUCTIONS["en"])

    batch_prompt = FLASHCARD_SYSTEM.format(
        exam=exam,
        subject=subject,
        topic=topic,
        count=count,
        context_block=context_block,
        lang_instruction=lang_instruction,
    )
    
    buffer = ""
    brace_count = 0
    obj_str = ""
    async for chunk in _llm_complete_stream(batch_prompt, max_tokens=4096, temperature=0.5):
        buffer += chunk
        while buffer:
            if brace_count == 0:
                start = buffer.find("{")
                if start == -1:
                    buffer = ""
                    break
                buffer = buffer[start:]
                brace_count = 1
                obj_str = "{"
                buffer = buffer[1:]
            
            # Find the next { or }
            next_open = buffer.find("{")
            next_close = buffer.find("}")
            
            if next_close == -1:
                obj_str += buffer
                buffer = ""
                break
                
            if next_open != -1 and next_open < next_close:
                brace_count += 1
                obj_str += buffer[:next_open + 1]
                buffer = buffer[next_open + 1:]
            else:
                brace_count -= 1
                obj_str += buffer[:next_close + 1]
                buffer = buffer[next_close + 1:]
                
                if brace_count == 0:
                    try:
                        obj = json.loads(obj_str)
                        yield obj
                    except Exception:
                        pass
                    obj_str = ""
