import json
import os
import tempfile

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import SpaceDocument
from app.services.space_service import SpaceService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/spaces", tags=["Documents"])


@router.post("/{space_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    space_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a user document (question bank, topic notes, practice paper).
    The file is parsed, topic headings are extracted, semantic chunks are created,
    and everything is indexed into ChromaDB.

    Returns enriched metadata including detected topics and chunk count.
    """
    # Verify space access
    space_svc = SpaceService(db)
    space = await space_svc.get_space(space_id, current_user.id)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and TXT files are supported.",
        )

    # Read file content
    content = await file.read()

    # Check size (max 10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 10MB limit.",
        )

    # Save to DB (initial row — topics/chunk_count filled in after processing)
    new_doc = SpaceDocument(
        space_id=space_id,
        filename=file.filename,
        file_type=ext[1:],
        source="user_upload",
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    # Save temporarily to process
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Process, extract topics, create semantic chunks, index into Chroma
        doc_svc = DocumentService()
        stats = await doc_svc.process_and_index_document(
            tmp_path, space.exam_id, space.subject, new_doc.id
        )
    except Exception as e:
        # Rollback DB if indexing fails
        await db.delete(new_doc)
        await db.commit()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {e}",
        )

    # Cleanup temp file
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    # Persist topics and chunk_count back into the DB row
    new_doc.topics = json.dumps(stats["topics"], ensure_ascii=False)
    new_doc.chunk_count = stats["chunk_count"]
    await db.commit()
    await db.refresh(new_doc)

    return {
        "id":          new_doc.id,
        "filename":    new_doc.filename,
        "file_type":   new_doc.file_type,
        "source":      new_doc.source,
        "pages":       stats["pages"],
        "chunk_count": stats["chunk_count"],
        "topics":      stats["topics"],
        "created_at":  new_doc.created_at,
    }


@router.get("/{space_id}/documents")
async def list_documents(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents uploaded to this space."""
    space_svc = SpaceService(db)
    await space_svc.get_space(space_id, current_user.id)

    result = await db.execute(select(SpaceDocument).where(SpaceDocument.space_id == space_id))
    docs = result.scalars().all()

    return [
        {
            "id":          d.id,
            "filename":    d.filename,
            "file_type":   d.file_type,
            "source":      d.source,
            "chunk_count": d.chunk_count,
            "topics":      json.loads(d.topics) if d.topics else [],
            "created_at":  d.created_at,
        }
        for d in docs
    ]


@router.get("/{space_id}/documents/{doc_id}/topics")
async def get_document_topics(
    space_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the extracted topics list for a specific document."""
    space_svc = SpaceService(db)
    await space_svc.get_space(space_id, current_user.id)

    result = await db.execute(
        select(SpaceDocument).where(
            SpaceDocument.id == doc_id,
            SpaceDocument.space_id == space_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "doc_id":   doc.id,
        "filename": doc.filename,
        "topics":   json.loads(doc.topics) if doc.topics else [],
    }


@router.delete("/{space_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    space_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its associated vector chunks."""
    space_svc = SpaceService(db)
    space = await space_svc.get_space(space_id, current_user.id)

    result = await db.execute(
        select(SpaceDocument).where(
            SpaceDocument.id == doc_id,
            SpaceDocument.space_id == space_id,
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Delete from VectorStore via DocumentService
    try:
        doc_svc = DocumentService()
        await doc_svc.delete_document_chunks(space.exam_id, space.subject, doc_id)
    except Exception as e:
        print(f"Warning: Failed to delete chunks from ChromaDB: {e}")

    # Delete from SQL DB
    await db.delete(doc)
    await db.commit()
