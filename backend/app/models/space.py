from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class LearningSpace(Base):
    __tablename__ = "learning_spaces"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_id = Column(String, nullable=False)          # "NEET" or "TNPSC"
    subject = Column(String, nullable=False)           # e.g. "Physics"
    title = Column(String, nullable=False)             # auto-generated: "{subject} Space"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    messages = relationship("ChatMessage", back_populates="space", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    chat_sessions = relationship("ChatSession", back_populates="space", cascade="all, delete-orphan", order_by="ChatSession.created_at")
    note = relationship("SpaceNote", back_populates="space", uselist=False, cascade="all, delete-orphan")
