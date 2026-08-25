from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ChatSession(Base):
    """A named chat conversation within a Learning Space (ChatGPT-style)."""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    space_id = Column(Integer, ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, default="New Chat")
    ai_suggested_name = Column(String, nullable=True)   # AI suggestion, user may override
    state = Column(Text, nullable=True)                 # JSON string storing continuation state
    chat_type = Column(String(50), nullable=False, default="AI_TUTOR") # AI_TUTOR, MYSTUDYGPT, FILE_CHAT
    file_id = Column(Integer, ForeignKey("space_documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan",
                            order_by="ChatMessage.created_at")
    space = relationship("LearningSpace", back_populates="chat_sessions")
