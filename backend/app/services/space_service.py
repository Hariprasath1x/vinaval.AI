import logging
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.space_repository import SpaceRepository
from app.core.constants import is_valid_subject, EXAM_MAP
from app.models.space import LearningSpace
from app.models.chat_session import ChatSession
from app.models.message import ChatMessage
from app.models.note import SpaceNote
from app.schemas.space import SpaceCreate, NoteUpdate
from app.rag.chain import stream_chat

logger = logging.getLogger(__name__)


class SpaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SpaceRepository(db)

    # ── Spaces ─────────────────────────────────────────────────────────────────

    async def get_or_create_space(self, user_id: int, data: SpaceCreate) -> LearningSpace:
        """
        Return an existing space for (user, exam, subject) or create a new one.
        This ensures clicking the same subject card multiple times opens the same space.
        """
        if data.exam_id not in EXAM_MAP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown exam '{data.exam_id}'.",
            )
        if not is_valid_subject(data.exam_id, data.subject):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{data.subject}' is not a valid subject for {data.exam_id}.",
            )

        existing = await self.repo.find_existing_space(user_id, data.exam_id, data.subject)
        if existing:
            return existing
        return await self.repo.create_space(user_id, data.exam_id, data.subject)

    async def get_space(self, space_id: int, user_id: int) -> LearningSpace:
        space = await self.repo.get_space_by_id(space_id, user_id)
        if not space:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning Space not found.",
            )
        return space

    async def list_spaces(self, user_id: int) -> List[LearningSpace]:
        return await self.repo.list_spaces(user_id)

    async def delete_space(self, space_id: int, user_id: int) -> bool:
        """Delete a Learning Space. Raises 404 if not found or not owned by user."""
        deleted = await self.repo.delete_space(space_id, user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning Space not found.",
            )
        return True

    # ── Chat Sessions ──────────────────────────────────────────────────────────

    async def create_chat_session(self, space_id: int, name: str = "New Chat") -> ChatSession:
        return await self.repo.create_chat_session(space_id, name)

    async def list_chat_sessions(self, space_id: int) -> List[ChatSession]:
        return await self.repo.list_chat_sessions(space_id)

    async def rename_chat_session(self, session_id: int, space_id: int, name: str) -> ChatSession:
        session = await self.repo.rename_chat_session(session_id, space_id, name)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
        return session

    async def delete_chat_session(self, session_id: int, space_id: int) -> bool:
        deleted = await self.repo.delete_chat_session(session_id, space_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
        return True

    async def suggest_session_name(
        self, session_id: int, space: LearningSpace, first_user_msg: str, first_ai_response: str
    ) -> str:
        """Ask Groq to suggest a short 3-5 word title for this chat. Fire-and-forget friendly."""
        from app.core.config import get_settings
        from groq import AsyncGroq
        settings = get_settings()
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)

        prompt = (
            f"Given this first exchange in a {space.exam_id} {space.subject} tutoring chat, "
            f"suggest a short, descriptive title (3-5 words, no punctuation) that captures the main topic.\n\n"
            f"User: {first_user_msg[:200]}\n"
            f"AI: {first_ai_response[:300]}\n\n"
            f"Title (3-5 words only):"
        )

        try:
            resp = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.3,
            )
            suggestion = resp.choices[0].message.content.strip()
            # Clean up quotes or newlines
            suggestion = suggestion.strip('"\'').split('\n')[0][:60]
            await self.repo.set_ai_suggested_name(session_id, suggestion)
            return suggestion
        except Exception:
            return ""

    # ── Chat ───────────────────────────────────────────────────────────────────

    async def get_messages(self, space_id: int, session_id: Optional[int] = None) -> List[ChatMessage]:
        return await self.repo.get_messages(space_id, session_id=session_id)

    async def save_user_message(self, space_id: int, content: str,
                                session_id: Optional[int] = None) -> ChatMessage:
        return await self.repo.add_message(space_id, "user", content, session_id=session_id)

    async def save_assistant_message(self, space_id: int, content: str,
                                     session_id: Optional[int] = None) -> ChatMessage:
        return await self.repo.add_message(space_id, "assistant", content, session_id=session_id)

    async def stream_ai_response(
        self,
        space: LearningSpace,
        user_message: str,
        forced_lang: Optional[str] = None,
        active_doc_id: Optional[int] = None,
        active_doc_filename: Optional[str] = None,
        chat_session_id: Optional[int] = None,
    ):
        """
        Generator: yields SSE-formatted chunks, then saves both messages to DB.
        Optionally scoped to a chat session. After first exchange, triggers AI name suggestion.
        """
        logger.info("[CHAT] Stream generator started")

        # Build history for this session (last 20 messages for context window)
        logger.info("[CHAT] Loading chat history")
        messages = await self.repo.get_messages(space.id, session_id=chat_session_id)
        logger.info(f"[CHAT] Chat history loaded count={len(messages)}")
        history = [{"role": m.role, "content": m.content} for m in messages[-20:]]
        is_first_exchange = len(history) == 0

        # Save user message
        logger.info("[CHAT] Persisting user message")
        msg = await self.repo.add_message(space.id, "user", user_message, session_id=chat_session_id)
        msg_id = getattr(msg, 'id', 'unknown')
        logger.info(f"[CHAT] User message persisted message_id={msg_id}")

        logger.info("[CHAT] Starting RAG/LLM stream")
        # Stream AI response
        full_response: list[str] = []
        async for chunk in stream_chat(
            space.exam_id,
            space.subject,
            history,
            user_message,
            forced_lang,
            active_doc_id=active_doc_id,
            active_doc_filename=active_doc_filename,
            space_id=space.id,
        ):
            full_response.append(chunk)
            yield chunk

        full_text = "".join(full_response)

        # Persist the complete assistant message
        await self.repo.add_message(space.id, "assistant", full_text, session_id=chat_session_id)

        # After first exchange: generate AI name suggestion (non-blocking)
        if is_first_exchange and chat_session_id:
            try:
                await self.suggest_session_name(chat_session_id, space, user_message, full_text)
            except Exception:
                pass  # Never let name suggestion crash the main flow

    # ── Notes ──────────────────────────────────────────────────────────────────

    async def get_note(self, space_id: int) -> Optional[SpaceNote]:
        return await self.repo.get_note(space_id)

    async def upsert_note(self, space_id: int, data: NoteUpdate) -> SpaceNote:
        return await self.repo.upsert_note(space_id, data.content)
