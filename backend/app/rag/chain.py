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
"""
from __future__ import annotations
import json
import logging
from typing import AsyncGenerator, List, Dict, Tuple

from groq import AsyncGroq
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Language Detection (heuristic) ────────────────────────────────────────────
import re as _re
_TAMIL_RE = _re.compile(r"[\u0B80-\u0BFF]")

def _detect_lang(text: str) -> str:
    """Return 'ta' if the text contains significant Tamil Unicode, else 'en'."""
    if not text:
        return "en"
    ratio = len(_TAMIL_RE.findall(text)) / max(len(text), 1)
    return "ta" if ratio > 0.03 else "en"


# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are Vinaval AI — an expert, encouraging AI tutor for Tamil Nadu students preparing for \
{exam} ({exam_tag}).

You are specialising in **{subject}** for this Learning Space.

### Teaching style:
- Explain concepts clearly with simple language and relatable analogies.
- Structure responses with headings, bullet points, or numbered lists.
- Provide worked examples whenever possible.
- After each concept, suggest what the student should study next.
- Gently correct mistakes and explain why.
- Keep answers concise but complete — avoid padding.
- Use markdown formatting.

### Scope:
- Focus strictly on {exam} {subject} syllabus topics.
- Politely redirect off-topic questions.

### Language (IMPORTANT):
- Detect the language the student is writing in.
- If the student writes in **Tamil**, reply entirely in **Tamil**.
  • Use clear, modern Tamil.
  • For technical terms (e.g. DNA, photosynthesis), write the Tamil word first, \
then the English term in parentheses — e.g. "ஒளிச்சேர்க்கை (Photosynthesis)".
  • Use markdown formatting even in Tamil replies.
- If the student writes in **English**, reply in **English**.
- If the student mixes languages (Tanglish), match their style.

{context_block}
You are friendly, patient, and deeply motivating. \
Your goal is to help every student — whether studying in Tamil medium or English medium — \
master {subject} and crack {exam}!"""

EXAM_TAGS = {
    "NEET":  "Medical Entrance Exam",
    "TNPSC": "Tamil Nadu Civil Services Exam",
}


# ── RAG Retrieval ──────────────────────────────────────────────────────────────

def _retrieve_context(exam: str, subject: str, query: str, n_results: int = 4) -> Tuple[str, int]:
    """
    Semantic search across ALL language collections for this exam+subject.

    Strategy:
      • Query both 'neet_physics_en' and 'neet_physics_ta' (and legacy 'neet_physics').
      • Merge results, deduplicate, keep the top-n by relevance (Chroma returns
        results ordered by distance — we simply interleave and take the first n).

    Returns:
        (context_block_str, total_chunks_found)
    """
    try:
        from app.core.chroma import get_collections_for_subject
        collections = get_collections_for_subject(exam, subject)

        if not collections:
            return "", 0

        all_docs:  List[str]  = []
        all_metas: List[dict] = []

        per_col = max(2, n_results)  # query each collection independently
        seen: set = set()

        for col in collections:
            try:
                k = min(per_col, col.count())
                if k == 0:
                    continue
                results = col.query(query_texts=[query], n_results=k)
                docs:  List[str]  = results.get("documents", [[]])[0]
                metas: List[dict] = results.get("metadatas",  [[]])[0]
                for doc, meta in zip(docs, metas):
                    # Deduplicate identical text
                    key = doc[:120]
                    if key not in seen:
                        seen.add(key)
                        all_docs.append(doc)
                        all_metas.append(meta)
            except Exception as exc:
                logger.warning("Retrieval error on collection %s: %s", col.name, exc)

        if not all_docs:
            return "", 0

        # Trim to requested n_results
        all_docs  = all_docs[:n_results]
        all_metas = all_metas[:n_results]

        lines = ["### Context from Syllabus:\n"]
        for doc, meta in zip(all_docs, all_metas):
            lang_tag  = {"en": "[EN]", "ta": "[TA]"}.get(meta.get("lang", ""), "")
            topic     = meta.get("book_title", meta.get("topic", "Syllabus"))
            lines.append(f"**{lang_tag} [{topic}]** {doc.strip()}\n")

        lines.append(
            "\nUse the above context to answer accurately. "
            "If the question is not covered by context, draw on your general "
            "knowledge of the syllabus.\n"
        )
        return "\n".join(lines) + "\n", len(all_docs)

    except Exception as exc:
        logger.warning("ChromaDB retrieval failed (answering without context): %s", exc)
        return "", 0


def _build_system_prompt(exam: str, subject: str, context_block: str = "") -> str:
    tag = EXAM_TAGS.get(exam, exam)
    return SYSTEM_PROMPT.format(
        exam=exam,
        exam_tag=tag,
        subject=subject,
        context_block=context_block,
    )


# ── Chat ───────────────────────────────────────────────────────────────────────

async def stream_chat(
    exam: str,
    subject: str,
    history: List[Dict[str, str]],   # [{"role": "user"/"assistant", "content": "…"}]
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Stream an AI response token-by-token using Groq's async client.

    1. Detects the student's language.
    2. Retrieves relevant syllabus chunks from ALL language collections.
    3. Builds the system prompt with injected context.
    4. Streams the LLM response.
    """
    context_block, n_chunks = _retrieve_context(exam, subject, user_message, n_results=4)
    if context_block:
        logger.debug("RAG: injecting %d context chunks (%d chars)", n_chunks, len(context_block))
    else:
        logger.debug("RAG: no context chunks found — answering from model knowledge")

    lang = _detect_lang(user_message)
    logger.debug("Detected student language: %s", lang)

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    messages = [{"role": "system", "content": _build_system_prompt(exam, subject, context_block)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    stream = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def get_chat_response(
    exam: str,
    subject: str,
    history: List[Dict[str, str]],
    user_message: str,
) -> str:
    """Non-streaming version — returns full response. Used as fallback or for testing."""
    parts = []
    async for chunk in stream_chat(exam, subject, history, user_message):
        parts.append(chunk)
    return "".join(parts)


# ── MCQ Generation ─────────────────────────────────────────────────────────────

MCQ_SYSTEM = """\
You are an expert MCQ question generator for Tamil Nadu competitive exams.
Generate exactly {count} multiple-choice questions on the topic: "{topic}"
for {exam} {subject}.

{context_block}
### Output Language:
{lang_instruction}

STRICT OUTPUT FORMAT — respond ONLY with a valid JSON array, no other text:
[
  {{
    "question": "Full question text here?",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_option": "a",
    "explanation": "Brief explanation of why the answer is correct."
  }}
]

Rules:
- Each question must have exactly 4 options (a, b, c, d).
- correct_option must be one of: "a", "b", "c", "d".
- Questions should be exam-level difficulty.
- No duplicate questions.
- Output ONLY the JSON array — absolutely no markdown, no code fences, no text outside the JSON.
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
    topic: str,
    count: int = 5,
    lang: str = "en",
) -> List[Dict]:
    """
    Generate MCQ questions using Groq, grounded in ChromaDB context.

    Args:
        lang: "en" or "ta" — controls output language of questions + explanations.

    Returns a list of dicts: question, option_a/b/c/d, correct_option, explanation.
    """
    context_block, _ = _retrieve_context(exam, subject, topic, n_results=5)
    if context_block:
        context_block = (
            "### Reference Material from Syllabus:\n" + context_block +
            "\nBase your questions on this material where possible.\n"
        )

    lang_instruction = _MCQ_LANG_INSTRUCTIONS.get(lang, _MCQ_LANG_INSTRUCTIONS["en"])

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    prompt = MCQ_SYSTEM.format(
        exam=exam,
        subject=subject,
        topic=topic,
        count=count,
        context_block=context_block,
        lang_instruction=lang_instruction,
    )
    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.5,
        stream=False,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        questions = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"MCQ generation returned invalid JSON: {e}\nRaw: {raw[:300]}")

    if not isinstance(questions, list):
        raise ValueError("MCQ generation did not return a JSON array.")

    return questions


# ── Flashcard Generation ───────────────────────────────────────────────────────

FLASHCARD_SYSTEM = """\
You are an expert study-card creator for Tamil Nadu competitive exams.
Generate exactly {count} flashcards on the topic: "{topic}"
for {exam} {subject}.

{context_block}
### Output Language:
{lang_instruction}

STRICT OUTPUT FORMAT — respond ONLY with a valid JSON array, no other text:
[
  {{
    "front": "Term or question here?",
    "back": "Definition or answer here."
  }}
]

Rules:
- front: a concise term, concept, formula label, or question (max 2 lines).
- back: a clear, complete explanation or answer (2–4 sentences max).
- Flashcards must be exam-relevant and factually accurate.
- No duplicate fronts.
- Output ONLY the JSON array — no markdown, no code fences, no extra text.
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
    """
    Generate flashcard pairs (front/back) using Groq, grounded in ChromaDB context.

    Args:
        lang: "en" or "ta" — controls output language of cards.

    Returns a list of dicts: front, back.
    """
    context_block, _ = _retrieve_context(exam, subject, topic, n_results=5)
    if context_block:
        context_block = (
            "### Reference Material from Syllabus:\n" + context_block +
            "\nBase the flashcards strictly on this material.\n"
        )

    lang_instruction = _FLASH_LANG_INSTRUCTIONS.get(lang, _FLASH_LANG_INSTRUCTIONS["en"])

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    prompt = FLASHCARD_SYSTEM.format(
        exam=exam,
        subject=subject,
        topic=topic,
        count=count,
        context_block=context_block,
        lang_instruction=lang_instruction,
    )
    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.4,
        stream=False,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        cards = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Flashcard generation returned invalid JSON: {e}\nRaw: {raw[:300]}")

    if not isinstance(cards, list):
        raise ValueError("Flashcard generation did not return a JSON array.")

    return cards


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
    results: List[Dict[str, bool]],  # list of {"topic": str, "is_correct": bool}
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

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    prompt = REVIEW_SYSTEM.format(
        exam=exam,
        subject=subject,
        results_block=results_block,
        score=score,
        total=total,
        percentage=percentage,
    )
    
    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.6,
        stream=False,
    )

    return response.choices[0].message.content.strip()
