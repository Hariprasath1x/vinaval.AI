from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class SpaceDocument(Base):
    __tablename__ = "space_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    space_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "pdf", "txt"
    # "user_upload" = question bank / notes uploaded by student
    # "book" = static syllabus seeded by admin (not user-deletable from UI)
    source: Mapped[str] = mapped_column(String, nullable=False, default="user_upload")
    # e.g., "Important Topics", "Question Banks", "Important Questions", "Notes"
    material_type: Mapped[str] = mapped_column(String, nullable=True, default=None)
    # JSON-serialised list of extracted headings/topics e.g. '["Surface Chemistry","Adsorption"]'
    topics: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    # Number of semantic chunks indexed into ChromaDB
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
