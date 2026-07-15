from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class SpaceNote(Base):
    __tablename__ = "space_notes"

    id = Column(Integer, primary_key=True, index=True)
    space_id = Column(Integer, ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    space = relationship("LearningSpace", back_populates="note")
