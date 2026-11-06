from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class SpaceNote(Base):
    __tablename__ = "space_notes"

    id = Column(Integer, primary_key=True, index=True)
    space_id = Column(Integer, ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False, default="Untitled Note")
    topic = Column(String(255), nullable=True)
    content = Column(Text, nullable=False, default="")
    source_type = Column(String(50), nullable=False, default="manual")  # "manual" | "topic" | "document"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    space = relationship("LearningSpace", back_populates="notes")
