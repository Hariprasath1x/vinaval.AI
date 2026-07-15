"""
RAG chain for Vinaval AI — exam-specific AI tutor using Groq (Llama 3 70B).

The chain performs semantic search against ChromaDB to retrieve relevant
syllabus chunks, then injects them as context into the system prompt before
calling the LLM. This grounds the AI's answers in real curriculum content.
Falls back gracefully if ChromaDB is empty or unavailable.
"""
from __future__ import annotations
import json
import logging
from typing import AsyncGenerator, List, Dict

from groq import AsyncGroq
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Vinaval AI — an expert, encouraging AI tutor helping students in Tamil Nadu \
prepare for {exam} ({exam_tag}).

You are specializing in **{subject}** for this Learning Space.

### Your teaching style:
- Explain concepts clearly, using simple language and analogies.
- When answering, structure your responses with headings, bullet points, or numbered lists where helpful.
- Provide worked examples whenever possible.
- After explaining a concept, ask a follow-up question or suggest what to study next.
- If a student makes a mistake, gently correct them and explain why.
- Keep answers concise but complete — avoid padding.
- Use markdown formatting for your responses.

### Scope:
- Focus strictly on {exam} {subject} syllabus topics.
- If the student asks something outside this scope, kindly redirect them.

### Language:
- Respond in English unless the student writes in Tamil, in which case reply in Tamil.

{context_block}
You are friendly, patient, and motivating. Your goal is to help the student master {subject} and crack {exam}!"""

EXAM_TAGS = {
    "NEET": "Medical Entrance Exam",
    "TNPSC": "Tamil Nadu Civil Services Exam",
}


# ── RAG Retrieval Helper ───────────────────────────────────────────────────────

def _retrieve_context(exam: str, subject: str, query: str, n_results: int = 3) -> str:
    """
    Semantic search against ChromaDB for the most relevant syllabus chunks.
    Returns a formatted context block string, or empty string on any error.
    """
    try:
        from app.core.chroma import get_collection
        collection = get_collection(exam, subject)
        if collection.count() == 0:
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
        )
        docs: List[str] = results.get("documents", [[]])[0]
        metas: List[dict] = results.get("metadatas", [[]])[0]

        if not docs:
            return ""

        lines = ["### Context from Syllabus:\n"]
        for doc, meta in zip(docs, metas):
            topic = meta.get("topic", "General")
            lines.append(f"**[{topic}]** {doc.strip()}\n")
        lines.append(
            "\nUse the above context to answer accurately. "
            "If the question is not covered by context, draw on your general knowledge of the syllabus.\n"
        )
        return "\n".join(lines) + "\n"
    except Exception as exc:
        logger.warning("ChromaDB retrieval failed (answering without context): %s", exc)
        return ""


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
    history: List[Dict[str, str]],   # [{"role": "user"/"assistant", "content": "..."}]
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Stream an AI response token-by-token using Groq's async client.
    Retrieves relevant syllabus chunks from ChromaDB first.

    Yields:
        str — each text chunk as it arrives from the API
    """
    context_block = _retrieve_context(exam, subject, user_message, n_results=3)
    if context_block:
        logger.debug("RAG: injecting %d chars of context", len(context_block))

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    messages = [{"role": "system", "content": _build_system_prompt(exam, subject, context_block)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    stream = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        max_tokens=1024,
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

MCQ_SYSTEM = """You are an expert MCQ question generator for competitive exams.
Generate exactly {count} multiple-choice questions on the topic: "{topic}"
for {exam} {subject}.

{context_block}
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
- Output ONLY the JSON array — absolutely no markdown, no code fences, no explanation outside the JSON.
"""


async def generate_mcqs(exam: str, subject: str, topic: str, count: int = 5) -> List[Dict]:
    """
    Generate MCQ questions using Groq, grounded in ChromaDB context.
    Returns a list of dicts: question, option_a/b/c/d, correct_option, explanation.
    Raises ValueError if JSON parsing fails.
    """
    context_block = _retrieve_context(exam, subject, topic, n_results=5)
    if context_block:
        context_block = "### Reference Material from Syllabus:\n" + context_block + \
                        "\nBase your questions on this material where possible.\n"

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    prompt = MCQ_SYSTEM.format(
        exam=exam, subject=subject, topic=topic, count=count, context_block=context_block
    )
    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.5,
        stream=False,
    )

    raw = response.choices[0].message.content.strip()
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

FLASHCARD_SYSTEM = """You are an expert study-card creator for competitive exams.
Generate exactly {count} flashcards on the topic: "{topic}"
for {exam} {subject}.

{context_block}
STRICT OUTPUT FORMAT — respond ONLY with a valid JSON array, no other text:
[
  {{
    "front": "Term or question here?",
    "back": "Definition or answer here."
  }}
]

Rules:
- front: a concise term, concept, formula label, or question (max 2 lines).
- back: a clear, complete explanation or answer (2-4 sentences max).
- Flashcards must be exam-relevant and factually accurate.
- No duplicate fronts.
- Output ONLY the JSON array — no markdown, no code fences, no extra text.
"""


async def generate_flashcards(exam: str, subject: str, topic: str, count: int = 8) -> List[Dict]:
    """
    Generate flashcard pairs (front/back) using Groq, grounded in ChromaDB context.
    Returns a list of dicts: front, back.
    Raises ValueError if JSON parsing fails.
    """
    context_block = _retrieve_context(exam, subject, topic, n_results=5)
    if context_block:
        context_block = "### Reference Material from Syllabus:\n" + context_block + \
                        "\nBase the flashcards strictly on this material.\n"

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    prompt = FLASHCARD_SYSTEM.format(
        exam=exam, subject=subject, topic=topic, count=count, context_block=context_block
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

