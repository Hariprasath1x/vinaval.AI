"""
Book Seeding Script for Vinaval AI
====================================
Pre-loads static TN textbook / syllabus content into ChromaDB.
Books are the admin-seeded core knowledge base. Students CANNOT delete these.

Usage:
    cd backend

    # Seed an English NEET Physics textbook
    venv\\Scripts\\python.exe scripts/seed_books.py --exam NEET --subject Physics --lang en --file /path/to/physics_en.pdf

    # Seed a Tamil TNPSC History textbook (use --use-pymupdf for Tamil PDFs to avoid pdfplumber font crashes)
    venv\Scripts\python.exe scripts/seed_books.py --exam TNPSC --subject History --lang ta --file /path/to/history_ta.pdf --use-pymupdf

    # List all indexed collections
    venv\Scripts\python.exe scripts/seed_books.py --list

    # Clear all chunks from a specific book (by title) in a collection
    venv\Scripts\python.exe scripts/seed_books.py --delete --exam NEET --subject Physics --lang en --title "NCERT Physics Part 1"

Language Support
----------------
  --lang en   → stores in collection  neet_physics_en
  --lang ta   → stores in collection  neet_physics_ta
  (no --lang) → stores in collection  neet_physics   (legacy)

The multilingual embedding model (paraphrase-multilingual-MiniLM-L12-v2)
ensures Tamil and English embeddings are in the same semantic space, so a
Tamil student's query will surface relevant English chunks and vice-versa.

Metadata stored per chunk:
  {
    "source":      "book",
    "exam":        "NEET",
    "subject":     "Physics",
    "lang":        "en",          # or "ta" — absent in legacy chunks
    "book_title":  "NCERT Physics Part 1",
    "chunk_index": 42
  }
"""
import argparse
import os
import sys
import uuid
import re

# Ensure stdout/stderr support UTF-8 on Windows command line
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.vector_store import get_vector_store

BOOK_SOURCE_TAG = "book"

# Tamil Unicode range: U+0B80–U+0BFF
_TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")


# ── Text Extraction ────────────────────────────────────────────────────────────

def extract_text_from_file(
    file_path: str,
    start_page: int = 1,
    end_page: int | None = None,
    force_pymupdf: bool = False,
) -> str:
    """
    Extract raw text from a PDF or TXT file, optionally restricting to a page range (1-indexed).

    For Tamil PDFs, pdfplumber can crash due to complex font encoding.
    Pass force_pymupdf=True (or use --use-pymupdf flag) to skip pdfplumber entirely.
    PyMuPDF (fitz) handles Tamil Unicode reliably.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        # --- PyMuPDF path (reliable for Tamil fonts) ---
        def extract_with_pymupdf() -> str:
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text = ""
                total_pages = len(doc)
                start_idx = max(0, start_page - 1)
                end_idx = min(total_pages, end_page) if end_page else total_pages
                print(f"   [PyMuPDF] Reading pages {start_page} to {end_idx}...")
                for i in range(start_idx, end_idx):
                    page_text = doc[i].get_text("text")  # "text" mode preserves Unicode
                    if page_text:
                        text += page_text + "\n"
                doc.close()
                return text
            except ImportError:
                return ""

        # --- pdfplumber path (better for English layout PDFs) ---
        def extract_with_pdfplumber() -> str:
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(file_path) as pdf:
                    total_pages = len(pdf.pages)
                    start_idx = max(0, start_page - 1)
                    end_idx = min(total_pages, end_page) if end_page else total_pages
                    print(f"   [pdfplumber] Reading pages {start_page} to {end_idx}...")
                    for i in range(start_idx, end_idx):
                        try:
                            t = pdf.pages[i].extract_text()
                            if t:
                                text += t + "\n"
                        except Exception as page_err:
                            print(f"   [WARN] pdfplumber failed on page {i+1}, skipping: {page_err}")
                            continue
                return text
            except ImportError:
                return ""

        # --- RapidOCR path (multi-threaded for high speed on scanned PDFs) ---
        def extract_with_ocr() -> str:
            try:
                import fitz
                import numpy as np
                import cv2
                from rapidocr_onnxruntime import RapidOCR
                from concurrent.futures import ThreadPoolExecutor, as_completed

                doc = fitz.open(file_path)
                total_pages = len(doc)
                start_idx = max(0, start_page - 1)
                end_idx = min(total_pages, end_page) if end_page else total_pages
                page_indices = list(range(start_idx, end_idx))
                total_to_process = len(page_indices)

                # Pre-render page pixmaps (fast in PyMuPDF)
                print(f"   [RapidOCR] Pre-rendering {total_to_process} pages...")
                images = []
                for idx in page_indices:
                    pix = doc[idx].get_pixmap(dpi=110)
                    img = cv2.cvtColor(np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, 3)), cv2.COLOR_RGB2BGR)
                    images.append((idx, img))
                doc.close()

                print(f"   [RapidOCR] Multi-threaded OCR on {total_to_process} pages (4 parallel workers)...")

                def ocr_single_page(item):
                    page_num, img = item
                    engine = RapidOCR()
                    result, _ = engine(img)
                    if result:
                        page_text = "\n".join([line[1] for line in result if line and len(line) > 1])
                        return page_num, page_text
                    return page_num, ""

                results_map = {}
                completed = 0
                max_workers = min(6, os.cpu_count() or 4)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(ocr_single_page, item) for item in images]
                    for future in as_completed(futures):
                        p_num, p_text = future.result()
                        results_map[p_num] = p_text
                        completed += 1
                        print(f"\r   [RapidOCR] Progress: {completed}/{total_to_process} pages processed...", end="", flush=True)

                print("\n   [RapidOCR] OCR extraction complete!")
                # Reconstruct text in page order
                ordered_text = [results_map[idx] for idx in page_indices if idx in results_map]
                return "\n".join(ordered_text)
            except Exception as ocr_err:
                print(f"\n   [WARN] OCR extraction failed: {ocr_err}")
                return ""

        if force_pymupdf:
            text = extract_with_pymupdf()
        else:
            # Try pdfplumber first; fall back to PyMuPDF on empty/failed extraction
            text = extract_with_pdfplumber()
            if not text.strip():
                print("   [WARN] pdfplumber returned no text. Falling back to PyMuPDF...")
                text = extract_with_pymupdf()

        if not text.strip():
            print("   [INFO] Scanned image PDF detected. Triggering RapidOCR engine...")
            text = extract_with_ocr()

        if text.strip():
            return text

        print("ERROR: Could not extract text from PDF via pdfplumber, PyMuPDF, or RapidOCR.")
        sys.exit(1)

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    else:
        print(f"ERROR: Unsupported file type: {ext}. Only PDF and TXT are supported.")
        sys.exit(1)

    # Unreachable, but keeps linters happy
    return ""


def detect_language(text: str) -> str:
    """
    Heuristic: if >5% of characters are Tamil Unicode, label it 'ta', else 'en'.
    Only used when --lang is not passed explicitly.
    """
    if not text:
        return "en"
    tamil_chars = len(_TAMIL_RE.findall(text))
    ratio = tamil_chars / max(len(text), 1)
    return "ta" if ratio > 0.05 else "en"


# ── Chunking ───────────────────────────────────────────────────────────────────

def chunk_text(text: str, lang: str = "en", chunk_size: int = 1500, chunk_overlap: int = 300) -> list[str]:
    """
    Split text into overlapping chunks.

    For Tamil text we also split on '।' (Devanagari danda) and multiple newlines
    because Tamil books often don't use '. ' as a sentence delimiter.
    """
    # Normalise whitespace
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r" {2,}", " ", text)

    # Sentence-boundary characters: Tamil-aware
    if lang == "ta":
        # Split on newlines (paragraph), Tamil fullstop, or '. '
        splitter_re = re.compile(r"(?<=[\u0964\u0965.\n])\s+")
    else:
        splitter_re = re.compile(r"(?<=\.\s)\s*|\n{2,}")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break

        # Try to break on a natural boundary within the window
        window = text[start:end]
        # Find the last natural boundary in the window
        match = None
        for m in splitter_re.finditer(window):
            match = m
        if match and match.start() > chunk_size // 2:
            break_point = start + match.start()
        else:
            # Fall back to last newline, then last space
            bp = text.rfind("\n", start, end)
            if bp <= start + chunk_size // 2:
                bp = text.rfind(" ", start, end)
            break_point = bp if bp > start else end

        chunk = text[start:break_point].strip()
        if chunk:
            chunks.append(chunk)
        start = max(start + 1, break_point - chunk_overlap)

    return [c for c in chunks if len(c) > 50]  # filter tiny fragments


# ── Seeding ────────────────────────────────────────────────────────────────────

def seed_book(
    exam: str,
    subject: str,
    file_path: str,
    lang: str | None = None,
    book_title: str | None = None,
    start_page: int = 1,
    end_page: int | None = None,
    force_pymupdf: bool = False,
) -> None:
    """Index a TN textbook / syllabus file into ChromaDB."""
    exam = exam.upper()
    subject = subject.title()
    book_title = book_title or os.path.basename(file_path)

    print(f"\n[Seeding] [{exam}] {subject} -- '{book_title}'")
    print(f"   File   : {file_path}")
    if start_page > 1 or end_page:
        print(f"   Pages  : {start_page} to {end_page or 'end'}")
    if force_pymupdf:
        print("   Engine : PyMuPDF (forced)")

    # -- Extract text --
    print("   Extracting text...")
    text = extract_text_from_file(file_path, start_page, end_page, force_pymupdf=force_pymupdf)
    if not text.strip():
        print("ERROR: Extracted text is empty. Check the file (may be image-only PDF).")
        sys.exit(1)
    print(f"   OK Extracted {len(text):,} characters.")

    # -- Detect / confirm language --
    if lang:
        lang = lang.lower().strip()
    else:
        lang = detect_language(text)
        print(f"   🌐 Auto-detected language: '{lang}' (pass --lang to override)")

    lang_label = {"en": "English", "ta": "Tamil"}.get(lang, lang.upper())
    print(f"   Language: {lang_label}")

    # -- Chunk --
    print("   Chunking text...")
    chunks = chunk_text(text, lang=lang)
    print(f"   OK Created {len(chunks)} chunks.")

    # -- Get language-specific collection --
    collection = get_vector_store().get_collection(exam, subject, lang)
    existing = collection.count()
    col_name = collection.name
    print(f"   Collection '{col_name}' already has {existing} chunks.")

    # ── Build IDs and metadata ──
    book_slug = re.sub(r"[^a-z0-9_]", "_", book_title.lower())[:40]
    ids = [f"book_{book_slug}_{i}_{uuid.uuid4().hex[:6]}" for i in range(len(chunks))]
    metadatas = [
        {
            "source":      BOOK_SOURCE_TAG,
            "exam":        exam,
            "subject":     subject,
            "lang":        lang,
            "book_title":  book_title,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    # -- Index in batches of 100 --
    print("   Indexing into ChromaDB...")
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        b_chunks = chunks[i: i + batch_size]
        b_ids    = ids[i: i + batch_size]
        b_meta   = metadatas[i: i + batch_size]
        collection.add(documents=b_chunks, metadatas=b_meta, ids=b_ids)
        print(f"   Batch {i // batch_size + 1}: indexed {len(b_chunks)} chunks.")

    new_count = collection.count()
    print(f"\nDone! Collection '{col_name}' now has {new_count} total chunks.")
    print(f"   Added : {new_count - existing} new chunks for [{exam}] {subject} ({lang_label}).\n")


# ── Delete ─────────────────────────────────────────────────────────────────────

def delete_book(exam: str, subject: str, lang: str | None, book_title: str) -> None:
    """Remove all chunks belonging to a specific book title from a collection."""
    exam    = exam.upper()
    subject = subject.title()
    if lang:
        lang = lang.lower().strip()

    collection = get_vector_store().get_collection(exam, subject, lang)
    results = collection.get(where={"book_title": book_title})
    ids = results.get("ids", [])
    if not ids:
        print(f"⚠️  No chunks found for book '{book_title}' in {collection.name}.")
        return
    collection.delete(ids=ids)
    print(f"🗑️  Deleted {len(ids)} chunks for '{book_title}' from '{collection.name}'.")


# ── List ───────────────────────────────────────────────────────────────────────

def list_collections() -> None:
    """List all ChromaDB collections and their chunk counts."""
    store = get_vector_store()
    collection_names = store.list_collections()
    if not collection_names:
        print("No collections found. Seed some books first!")
        return
    print("\n📚 ChromaDB Collections:")
    print(f"  {'Collection':<35} {'Lang':<6} {'Chunks':>8}")
    print("  " + "─" * 52)
    for name in collection_names:
        c = store.get_collection_by_name(name)
        # Infer language from collection name suffix
        parts = name.rsplit("_", 1)
        lang = parts[-1] if len(parts) == 2 and parts[-1] in ("en", "ta") else "—"
        print(f"  {name:<35} {lang:<6} {c.count():>8,}")
    print()


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed TN textbook content into ChromaDB for Vinaval AI RAG.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/seed_books.py --exam NEET --subject Physics --lang en --file ncert_physics.pdf
  python scripts/seed_books.py --exam NEET --subject Physics --lang ta --file tn_physics_ta.pdf
  python scripts/seed_books.py --exam TNPSC --subject History --lang ta --file tnpsc_history_ta.pdf
  python scripts/seed_books.py --list
  python scripts/seed_books.py --delete --exam NEET --subject Physics --lang en --title "NCERT Physics Part 1"
        """,
    )
    parser.add_argument("--exam",    help="Exam ID: NEET or TNPSC")
    parser.add_argument("--subject", help="Subject (e.g. Physics, History, Biology)")
    parser.add_argument("--lang",    help="Language code: en (English) or ta (Tamil). Auto-detected if omitted.")
    parser.add_argument("--file",    help="Path to PDF or TXT file to index")
    parser.add_argument("--title",   help="Display title for the book (defaults to filename)")
    parser.add_argument("--start-page", type=int, default=1, help="Page number to start extraction from (1-indexed)")
    parser.add_argument("--end-page", type=int, help="Page number to end extraction at (1-indexed)")
    parser.add_argument("--use-pymupdf", action="store_true", help="Force PyMuPDF for extraction (recommended for Tamil PDFs)")
    parser.add_argument("--list",    action="store_true", help="List all collections and chunk counts")
    parser.add_argument("--delete",  action="store_true", help="Delete all chunks for --title from the collection")

    args = parser.parse_args()

    if args.list:
        list_collections()
        sys.exit(0)

    if args.delete:
        if not args.exam or not args.subject or not args.title:
            parser.print_help()
            print("\nERROR: --exam, --subject, and --title are required for --delete.")
            sys.exit(1)
        delete_book(args.exam, args.subject, args.lang, args.title)
        sys.exit(0)

    # Seed
    if not args.exam or not args.subject or not args.file:
        parser.print_help()
        print("\nERROR: --exam, --subject, and --file are required for seeding.")
        sys.exit(1)

    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    seed_book(
        args.exam,
        args.subject,
        args.file,
        lang=args.lang,
        book_title=args.title,
        start_page=args.start_page,
        end_page=args.end_page,
        force_pymupdf=args.use_pymupdf,
    )
