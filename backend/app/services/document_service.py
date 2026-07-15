import os
import uuid
import fitz  # PyMuPDF
from fastapi import UploadFile
from typing import List

from app.core.chroma import get_collection

# Simple recursive character text splitter logic (adapted to be dependency-free)
def chunk_text(text: str, chunk_size: int = 2500, chunk_overlap: int = 500) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
        # Try to find a good breaking point (newline or period)
        break_point = text.rfind("\n", start, end)
        if break_point == -1 or break_point <= start + chunk_size // 2:
            break_point = text.rfind(". ", start, end)
        
        if break_point == -1 or break_point <= start + chunk_size // 2:
            break_point = end # Fallback to strict cut
        else:
            break_point += 1 # Include the newline/period
            
        chunks.append(text[start:break_point].strip())
        start = break_point - chunk_overlap
        if start < 0:
            start = 0
        # Prevent infinite loops if overlap isn't advancing
        if len(chunks) > 1 and start <= (end - chunk_size):
            start = break_point # Force advance
            
    return [c for c in chunks if c] # Remove empty chunks

class DocumentService:
    def __init__(self):
        # We can pass DB session here if needed later
        pass

    async def process_and_index_document(self, file_path: str, exam: str, subject: str, doc_id: int):
        """
        Extract text from the file, chunk it, and index it into ChromaDB.
        """
        text = ""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".pdf":
            try:
                # Open PDF with PyMuPDF
                doc = fitz.open(file_path)
                for page in doc:
                    text += page.get_text() + "\n"
                doc.close()
            except Exception as e:
                raise ValueError(f"Failed to read PDF: {e}")
        elif ext == ".txt":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                # Fallback to utf-8 with replace
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except Exception as e:
                raise ValueError(f"Failed to read TXT: {e}")
        else:
            raise ValueError("Unsupported file type")
            
        if not text.strip():
            raise ValueError("Extracted text is empty")
            
        # Chunk text
        chunks = chunk_text(text)
        
        if not chunks:
            raise ValueError("No chunks created from text")
            
        # Prepare for ChromaDB
        collection = get_collection(exam, subject)
        
        ids = [f"{doc_id}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
        metadatas = [{"doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]
        
        # Add to ChromaDB
        # We do this in batches if there are too many chunks (Chroma has a limit per batch)
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            
            collection.add(
                documents=batch_chunks,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
