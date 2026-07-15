import os
import tempfile
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import SpaceDocument
from app.services.space_service import SpaceService
from app.services.document_service import DocumentService
from app.core.chroma import delete_document_chunks

router = APIRouter(prefix="/spaces", tags=["Documents"])

@router.post("/{space_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    space_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document, extract text, and index it into ChromaDB for RAG."""
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
    
    # Check size (e.g. max 10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 10MB limit.",
        )
        
    # Save to DB
    new_doc = SpaceDocument(
        space_id=space_id,
        filename=file.filename,
        file_type=ext[1:]
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    
    # Save temporarily to process
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
        
    try:
        # Process and index
        doc_svc = DocumentService()
        await doc_svc.process_and_index_document(tmp_path, space.exam_id, space.subject, new_doc.id)
    except Exception as e:
        # Rollback DB if indexing fails
        await db.delete(new_doc)
        await db.commit()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {e}"
        )
        
    # Cleanup
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
        
    return {
        "id": new_doc.id,
        "filename": new_doc.filename,
        "file_type": new_doc.file_type,
        "created_at": new_doc.created_at
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
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "created_at": d.created_at
        } for d in docs
    ]

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
            SpaceDocument.space_id == space_id
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
        
    # Delete from ChromaDB
    try:
        delete_document_chunks(space.exam_id, space.subject, doc_id)
    except Exception as e:
        print(f"Warning: Failed to delete chunks from ChromaDB: {e}")
        # Proceed with DB deletion anyway
        
    # Delete from SQL DB
    await db.delete(doc)
    await db.commit()
