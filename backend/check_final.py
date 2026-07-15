from app.main import app
from app.core.chroma import get_collection, delete_document_chunks
from app.rag.chain import stream_chat, generate_mcqs, generate_flashcards, _retrieve_context
print("Full backend import check OK")
