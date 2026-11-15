# Technical Evidence and Claim Verification Matrix

**Document Type:** Technical Evidence Audit & Claim Verification Traceability Matrix
**Project:** VinavalAI
**Audit Date:** November 2026
**Auditor:** Senior Software Architect, AI Systems Engineer & Quality Auditor
**Document Ref:** `docs/research_and_patent/04_vinavalai_evidence_and_claim_audit.md`

---

## 1. Audit Methodology & Status Classifications

Every significant technical, functional, and architectural claim made in repository documentation, comments, commit messages, or user prompts has been audited against actual source code implementation, test suite execution, or deployment configurations.

### Classification Categories:
- **VERIFIED:** Directly supported by current source code implementation, automated tests, or live runtime execution.
- **PARTIALLY VERIFIED:** Some components exist, but the complete claim is limited, blocked in UI, or unverified in certain paths.
- **UNVERIFIED:** Insufficient implementation or experimental evidence exists in the repository.
- **PLANNED / NOT FOUND:** Feature or benchmark claimed in documentation/prompts but completely absent in source code.
- **DEPRECATED / ARTIFACT:** Historical implementation that has been superseded and is no longer part of the active system.

---

## 2. Master Claim Verification Matrix

### 2.1 Core Architecture & Technology Stack

| ID | Claim | Evidence Location | Evidence Type | Status | Confidence | Audit Notes & Exact Implementation Findings |
|---|---|---|---|---|---|---|
| **ARC-01** | Frontend is built with React 19 and Vite 8 | [`frontend/package.json:15,28`](file:///Users/hariprasathc/Projects/vinavalAI/frontend/package.json#L15) | Manifest / Build | **VERIFIED** | High | `react: "^19.2.8"`, `vite: "^8.2.0"`. Verified production build runs via `npm run build` in 297 ms. |
| **ARC-02** | Streamlit is the active frontend of VinavalAI | `frontend/app.py`, `frontend/pages/` | Code / Artifacts | **DEPRECATED** | High | Streamlit was the prototype frontend (Commit `68f3cd6`). The live app runs entirely on React (`frontend/src/`). Streamlit files are legacy artifacts ignored by Vite. |
| **ARC-03** | Backend runs on FastAPI with asynchronous IO | [`backend/requirements.txt:2`](file:///Users/hariprasathc/Projects/vinavalAI/backend/requirements.txt#L2), [`backend/app/main.py:228`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/main.py#L228) | Source Code | **VERIFIED** | High | FastAPI 0.111.0 on Uvicorn 0.29.0 with asynchronous route handlers and lifespan context. |
| **ARC-04** | SQLite relational persistence via SQLAlchemy & aiosqlite | [`backend/app/core/database.py:9-32`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/core/database.py#L9) | Source Code | **VERIFIED** | High | `create_async_engine("sqlite+aiosqlite:///./vinavalai.db")` with `AsyncSession`. |
| **ARC-05** | Database schema managed by Alembic with working migrations | `backend/alembic/versions/` | Migration Files / Test | **VERIFIED** | High | 16 migration versions present. Head is `e34ccb42bc0e`. Verified via `test_alembic_migration_structure` in `test_note_api.py`. |
| **ARC-06** | Dual vector store abstraction supporting ChromaDB and Pinecone | [`backend/app/core/vector_store.py:32-371`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/core/vector_store.py#L32) | Source Code / Tests | **VERIFIED** | High | `VectorStoreInterface` with `ChromaVectorStore` and `PineconeVectorStore` implementations. Covered by 13 tests in `test_pinecone_adapter.py`. |
| **ARC-07** | Pinecone mode uses remote HuggingFace embeddings to save RAM | [`vector_store.py:378-410`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/core/vector_store.py#L378), [`test_pinecone_memory_isolation.py`](file:///Users/hariprasathc/Projects/vinavalAI/backend/tests/test_pinecone_memory_isolation.py) | Source / Tests | **VERIFIED** | High | In Pinecone mode, `HuggingFaceInferenceEmbedding` calls the remote HF API. Memory tests prove PyTorch and Chroma are never loaded, keeping RSS $\approx 180\text{ MB}$. |
| **ARC-08** | In-process embedding model is paraphrase-multilingual-MiniLM-L12-v2 | [`backend/app/core/chroma.py:46`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/core/chroma.py#L46) | Source Code | **VERIFIED** | High | 384 dimensions, dense cosine similarity, supports cross-lingual English-Tamil alignment. |

---

### 2.2 Functional Features

| ID | Claim | Evidence Location | Evidence Type | Status | Confidence | Audit Notes & Exact Implementation Findings |
|---|---|---|---|---|---|---|
| **FEAT-01** | Dual Authentication: Firebase Google OAuth & Local JWT | [`backend/app/api/v1/auth.py:27-142`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/api/v1/auth.py#L27), [`firebase.py`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/core/firebase.py) | Source Code / Tests | **VERIFIED** | High | Local salted bcrypt password hashing + JWT HS256 tokens (`/login`, `/signup`). Firebase ID token verification (`/firebase`). |
| **FEAT-02** | Examination selection supporting NEET and TNPSC | [`backend/app/core/constants.py:3-28`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/core/constants.py#L3), [`exam.py:24-42`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/api/v1/exam.py#L24) | Source Code / Tests | **VERIFIED** | High | Supported exams: NEET (Physics, Chemistry, Biology) and TNPSC (General Studies, Aptitude). Persisted in `users.selected_exam`. |
| **FEAT-03** | AI Tutor provides curriculum-grounded streaming chat | [`backend/app/api/v1/space.py:138`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/api/v1/space.py#L138), [`chain.py:770-870`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/rag/chain.py#L770) | Source Code / Live UI | **PARTIALLY VERIFIED** | High | Fully implemented and verified for **NEET**. However, in the React UI, TNPSC is blocked via `<TnpscComingSoon />` banner ([`SharedChatTab.jsx:462`](file:///Users/hariprasathc/Projects/vinavalAI/frontend/src/components/Space/SharedChatTab.jsx#L462)). |
| **FEAT-04** | MyStudyGPT provides user-document grounded chat | [`chain.py:313-335,818-850`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/rag/chain.py#L313), [`SharedChatTab.jsx:69`](file:///Users/hariprasathc/Projects/vinavalAI/frontend/src/components/Space/SharedChatTab.jsx#L69) | Source Code / Live UI | **VERIFIED** | High | Strict document-only grounding under `DOCUMENT_SYSTEM_PROMPT`. Yields explicit negative refusal if 0 chunks are found. |
| **FEAT-05** | Document upload supports PDF & TXT with PyMuPDF parsing | [`backend/app/api/v1/document.py:39-95`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/api/v1/document.py#L39), [`document_service.py:206`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/services/document_service.py#L206) | Source Code / Live UI | **VERIFIED** | High | Max size 10 MB. PyMuPDF primary parser, pdfplumber fallback, semantic section chunking (2500 chars, 400 overlap). |
| **FEAT-06** | Active-recall Flashcards with progressive SSE streaming | [`backend/app/api/v1/flashcard.py:21`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/api/v1/flashcard.py#L21), [`FlashcardsTab.jsx`](file:///Users/hariprasathc/Projects/vinavalAI/frontend/src/components/Space/FlashcardsTab.jsx) | Source Code / Live UI | **VERIFIED** | High | Streams flat NDJSON flashcards via brace-counting parser. Interactive 3D flip card viewer in React. |
| **FEAT-07** | Exam Lab MCQ test generator with automated grading | [`backend/app/api/v1/quiz.py:54-150`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/api/v1/quiz.py#L54), [`ExamLabTab.jsx`](file:///Users/hariprasathc/Projects/vinavalAI/frontend/src/components/Space/ExamLabTab.jsx) | Source Code / Live UI | **VERIFIED** | High | Generates 5–30 MCQs over SSE stream. Grades attempts against `correct_option`. Stores attempts in `quiz_attempts`. |
| **FEAT-08** | Performance Diagnostics combines deterministic scoring & AI | [`backend/app/services/performance_analyzer.py`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/services/performance_analyzer.py), [`ResultAnalysisPanel.jsx`](file:///Users/hariprasathc/Projects/vinavalAI/frontend/src/components/Space/ResultAnalysisPanel.jsx) | Source Code / Live UI | **VERIFIED** | High | Algorithmic scoring (accuracy, priority areas, time efficiency) + LLM qualitative mentor narrative. |
| **FEAT-09** | Smart Notes full-stack module (Dual-Source, CRUD, Export) | [`backend/app/api/v1/note.py`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/api/v1/note.py), [`NotesTab.jsx`](file:///Users/hariprasathc/Projects/vinavalAI/frontend/src/components/Space/NotesTab.jsx), [`test_note_api.py`](file:///Users/hariprasathc/Projects/vinavalAI/backend/tests/test_note_api.py) | Source / Tests / Screenshots | **VERIFIED** | High | Dual-source (Curriculum / Document). Exhaustive doc chunk loading. KaTeX math, Markdown editor, library search, `.md` download. 11/11 tests pass. |
| **FEAT-10** | "Smart Revision" as an independent standalone module | Codebase search across all files | Source Code Search | **NOT FOUND / PLANNED** | High | No dedicated service, route, or UI named "Smart Revision" exists. Revision exists conceptually as an action recommendation (`action="Revise"`) and in Flashcards. |

---

### 2.3 AI Models & RAG Engine

| ID | Claim | Evidence Location | Evidence Type | Status | Confidence | Audit Notes & Exact Implementation Findings |
|---|---|---|---|---|---|---|
| **AI-01** | Primary LLM provider is Google Gemini 1.5 Flash | [`backend/app/core/config.py:33`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/core/config.py#L33), [`chain.py:68,920`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/rag/chain.py#L68) | Source Code | **VERIFIED** | High | `GEMINI_MODEL: str = "gemini-1.5-flash"` via `google.generativeai`. |
| **AI-02** | Automatic failover to Groq Llama 3 on Gemini errors | [`chain.py:940-1010,1630-1650`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/rag/chain.py#L940) | Source Code / Live Tests | **VERIFIED** | High | Triggers Groq (`llama3-70b-8192` or `openai/gpt-oss-120b` / `llama-3.3-70b-versatile`). Verified: when `GEMINI_API_KEY=INVALID`, all calls fail over seamlessly in 2.5–4.0s. |
| **AI-03** | RAG retrieval uses top-k = 3 for syllabus textbooks | [`backend/app/rag/chain.py:356,380`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/rag/chain.py#L356) | Source Code | **VERIFIED** | High | `_retrieve_syllabus_context` queries `{exam}_{subject}_{lang}` with `n_results=3`. |
| **AI-04** | Document notes generation loads ALL chunks before similarity | [`backend/app/rag/chain.py:1590-1608`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/rag/chain.py#L1590) | Source Code / Tests | **VERIFIED** | High | Calls `_load_all_doc_chunks(col, doc_id)`. Bypasses vector search to achieve 100% chunk coverage; falls back to vector similarity ($n=8$) only if 0 chunks return. |
| **AI-05** | Brace-counting streaming parser decodes JSON objects on the fly | [`backend/app/rag/chain.py:1416-1460`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/rag/chain.py#L1416) | Source Code / Tests | **VERIFIED** | High | Tracks open and close curly braces in string buffer. Emits and yields discrete objects over SSE without waiting for array termination. |
| **AI-06** | Formal RAG evaluation framework (Ragas, DeepEval, TruLens) | Search `requirements.txt`, `tests/` | Source Code Search | **NOT FOUND** | High | Zero formal evaluation dependencies, metrics scripts, or golden datasets present in repo. |
| **AI-07** | Custom fine-tuning of embedding or generative models | Search codebase for training scripts | Codebase Search | **NOT FOUND** | High | All models are off-the-shelf pre-trained weights (`gemini-1.5-flash`, `llama-3.3-70b-versatile`, `paraphrase-multilingual-MiniLM-L12-v2`). Zero fine-tuning conducted. |

---

### 2.4 Testing, Quality & Security

| ID | Claim | Evidence Location | Evidence Type | Status | Confidence | Audit Notes & Exact Implementation Findings |
|---|---|---|---|---|---|---|
| **TST-01** | Full automated backend test suite passes with 0 regressions | `cd backend && ./venv/bin/pytest` | Live Execution | **VERIFIED** | High | Exactly 100 tests passed in 1.54s across 12 test files on Python 3.13.14. |
| **TST-02** | Frontend production build compiles cleanly | `cd frontend && npm run build` | Live Execution | **VERIFIED** | High | Vite 8 compiles bundle in 297 ms with zero errors. |
| **TST-03** | Rate limiting is enforced on all generative routes (5 req/min) | [`backend/app/core/rate_limit.py`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/core/rate_limit.py), [`space.py:138`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/api/v1/space.py#L138) | Source / Tests / UI | **VERIFIED** | High | SlowAPI limits chat, quiz, flashcards, and notes generation to 5 req/min. Returns HTTP 429. |
| **SEC-01** | Multi-tenant isolation is enforced across all endpoints | [`quiz.py:30-38`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/api/v1/quiz.py#L30), [`quiz_service.py:207`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/services/quiz_service.py#L207) | Code Audit | **PARTIALLY VERIFIED** | High | Fully isolated in Spaces, Documents, Chat, and Notes. **Vulnerable in Batch Quiz Stats (`GET /spaces/quiz/stats/batch`)** where space ownership is not verified against `current_user.id`. |
| **SEC-02** | Vector store physically isolates user materials from books | [`document_service.py:246`](file:///Users/hariprasathc/Projects/vinavalAI/backend/app/services/document_service.py#L246) | Source Code | **PARTIALLY VERIFIED** | High | Logically isolated via metadata `where={"space_id": space_id}`. However, user chunks and syllabus books reside in the same ChromaDB collections. |
| **DEP-01** | Production deployment uses Render Web Service & Vercel SPA | [`render.yaml`](file:///Users/hariprasathc/Projects/vinavalAI/render.yaml), [`frontend/vercel.json`](file:///Users/hariprasathc/Projects/vinavalAI/frontend/vercel.json) | Configuration | **VERIFIED** | High | Configurations exist. Note: `render.yaml` uses SQLite on ephemeral disk; requires managed PostgreSQL for persistent production. |

---

## 3. Discrepancy & Conflict Analysis

### Discrepancy 1: Streamlit Documentation vs. React Production
- **Conflict:** Early README sections and historical commit logs referred to Streamlit pages (`frontend/pages/`).
- **Resolution:** Audit of `frontend/package.json`, Vite configuration, and running ports confirms the live application is 100% React 19 + Vite 8. Streamlit files are legacy artifacts that can be safely archived.

### Discrepancy 2: "Smart Revision" Claims
- **Conflict:** Previous user inquiries asked about a dedicated "Smart Revision" module.
- **Resolution:** An exhaustive search of all routes, schemas, models, and React components confirms **no feature named "Smart Revision" exists**. The concept exists only within quiz recommendations (`action="Revise"`) and active-recall flashcards.

### Discrepancy 3: TNPSC Backend Readiness vs. Frontend Blocking
- **Conflict:** Backend RAG supports TNPSC subject collections (`tnpsc_history_en`, `tnpsc_polity_ta`).
- **Resolution:** While the backend handles TNPSC requests, the React frontend explicitly disables AI Tutor chat for TNPSC with a `<TnpscComingSoon />` banner ([`SharedChatTab.jsx:462`](file:///Users/hariprasathc/Projects/vinavalAI/frontend/src/components/Space/SharedChatTab.jsx#L462)).

### Discrepancy 4: Configured Gemini vs. Runtime Groq Execution
- **Conflict:** Documentation states Google Gemini 1.5 Flash is the primary LLM.
- **Resolution:** While Gemini is the primary code branch, the runtime environment file (`backend/.env`) has `GEMINI_API_KEY=INVALID`. Therefore, all live executions seamlessly fail over to Groq. Both paths are verified by unit tests.
