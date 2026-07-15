from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.core.database import Base


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    space_id = Column(Integer, ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    front = Column(Text, nullable=False)       # question / term
    back = Column(Text, nullable=False)        # answer / definition
    created_at = Column(DateTime(timezone=True), server_default=func.now())
