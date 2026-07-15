from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    space_id = Column(Integer, ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)   # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    space = relationship("LearningSpace", back_populates="messages")
