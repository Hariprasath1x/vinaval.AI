# VinavalAI — Pre-Deployment Audit & Readiness Report

**Generated:** 2026-10-22  
**Target Architecture:**  
- **Frontend:** Vercel Free (React / Vite)  
- **Backend:** Render Free (FastAPI / Native Python)  
- **Vector Database:** Pinecone Serverless (Free Tier)  
- **Target Git Branch:** `main`  
- **Application Goal:** Preserve Dual-RAG Architecture (Syllabus RAG & User Document RAG) and all existing application functionality.

---

## 1. Executive Summary

A comprehensive, evidence-based pre-deployment audit and code remediation was conducted on the VinavalAI repository on branch `main`. All safe code fixes and verifications have been implemented directly in the codebase and validated with automated tests and builds.

### Audit & Deployment Verdict: **GO AFTER MANUAL SETUP**

All code-level defects, test failures, routing gaps, and LLM provider fallbacks have been resolved:
- **Backend Automated Tests:** **71 / 71 tests passed (100% pass rate)**.
- **Frontend Production Build:** **Built successfully in 176ms** (`vite build` production bundle generated without errors).
- **Pinecone Migration Dry-Run:** **29 / 29 syllabus seed chunks validated across 10 namespaces** (0 skipped).
- **Code Hygiene Check:** `git diff --check` passed cleanly with **0 whitespace or syntax defects**.

No live external database migrations or deployments have been executed. The codebase is now ready for deployment. The remaining steps are strictly operational actions in external cloud dashboards (Pinecone, Render, Vercel, Firebase) using your credentials.

---

## 2. Changes Implemented and Files Modified

The following targeted, evidence-backed fixes were applied across the repository:

### 2.1 Frontend Routing (`frontend/vercel.json`)
- **Problem:** React Router v7 deep links and browser refreshes (e.g. `/welcome`, `/dashboard`, `/space/:id`) returned 404 errors on Vercel because Vercel does not automatically parse Netlify `_redirects` files in zero-config Vite projects.
- **Fix:** Created `frontend/vercel.json` with a rewrite rule mapping all routes (`/(.*)`) to `/index.html`:
  ```json
  {
    "rewrites": [
      {
        "source": "/(.*)",
        "destination": "/index.html"
      }
    ]
  }
  ```

### 2.2 Streaming 401 Recovery & Health Check Path (`frontend/src/services/api.js`)
- **Problem:** In `streamObjects` and `streamPost`, when a 401 token expiration occurred, the client attempted to trigger token refresh by calling `api.get('/health')`. Because `api` uses `BASE_URL = /api/v1`, this requested `/api/v1/health`, which returned HTTP 404 (the FastAPI health check is attached at root `/health`). Additionally, the retry logic needed safe concurrent-refresh coordination.
- **Fix:**
  - Added `BACKEND_ROOT_URL = BASE_URL.replace(/\/api\/v1\/?$/, "")`.
  - Routed `api.get('/health')` to `${BACKEND_ROOT_URL}/health`.
  - Extracted a dedicated `refreshAuthToken()` helper that preserves:
    - Thread-safe `isRefreshing` lock and `failedQueue` promise queue for concurrent requests.
    - Updated access and refresh tokens in `localStorage`.
    - Session cleanup and page reload on refresh failure.
  - Updated both `streamObjects` and `streamPost` to call root `${BACKEND_ROOT_URL}/health`, await `refreshAuthToken()`, and set `options.headers["Authorization"] = 'Bearer ' + token` directly on the retried fetch.

### 2.3 Render Blueprint Cleanup (`render.yaml`)
- **Problem:** `render.yaml` hardcoded `branch: react_version` and defined a redundant static site frontend service on Render, conflicting with the required Vercel deployment and the `main` branch.
- **Fix:**
  - Updated backend service `branch: main`.
  - Removed the redundant `vinavalai-frontend` static site service.
  - Kept the FastAPI backend service and all necessary environment variables (`DATABASE_URL`, `VECTOR_STORE_PROVIDER=pinecone`, `PINECONE_INDEX_NAME`, `PINECONE_API_KEY` sync:false, `SECRET_KEY`, `FIREBASE_CREDENTIALS_PATH`).

### 2.4 LLM Model Selection & Standalone Groq Fallback (`backend/app/core/config.py`, `backend/.env.example`, `backend/app/rag/chain.py`)
- **Problem:**
  - `config.py` default model was set to `gemini-3.6-flash`, which is not a valid Google AI Studio model name (expected `gemini-1.5-flash`).
  - `chain.py` raised a hard `ValueError` if `GEMINI_API_KEY` was missing, preventing Groq from operating independently even when `GROQ_API_KEY` was configured.
- **Fix:**
  - Updated default model in `config.py` and `.env.example` to `gemini-1.5-flash`.
  - Updated `_llm_complete`, `_llm_complete_stream`, and `stream_ai_response` in `chain.py` so that Gemini is attempted first when configured, but cleanly falls back to Groq if Gemini fails or if `GEMINI_API_KEY` is unset. Groq now functions completely independently.

### 2.5 Quiz Generation SSE Streaming Contract (`backend/app/services/quiz_service.py`, `backend/tests/test_quiz_api.py`)
- **Problem:** The endpoint `POST /spaces/{space_id}/quiz/generate` is an SSE streaming endpoint returning `StreamingResponse` (HTTP 200, `text/event-stream`), consumed incrementally by `ExamLabTab.jsx` via `api.streamObjects`. Four unit tests in `TestGenerateQuestions` were outdated, asserting synchronous HTTP 201 with a JSON body. Additionally, if the LLM returned unparseable text, the stream silently finished without emitting an error event.
- **Fix:**
  - In `quiz_service.py`, added question counting to `generate_questions_stream`. If zero valid questions are produced, it yields `event: error\ndata: {"error": "AI returned no valid questions. Try a different topic."}\n\n`, aligning the streaming error behavior with the non-streaming endpoint and frontend handler.
  - In `test_quiz_api.py`, updated `_make_gemini_model_mock` with `_MockGeminiResponse` supporting both `.text` attribute and async streaming iteration (`__aiter__` / `__anext__`).
  - Added `_parse_sse_events` helper and updated all four tests in `TestGenerateQuestions` to validate the true SSE streaming protocol (`session`, `question`, `error`, `complete` events with HTTP 200 status).

### 2.6 Migration Script Numpy Compatibility (`backend/scripts/migrate_to_pinecone.py`)
- **Problem:** Line 128 checked `emb = embeddings[i] if embeddings and i < len(embeddings) else None`. When Chroma returns embeddings as a NumPy array, `if embeddings:` raises `ValueError: The truth value of an array with more than one element is ambiguous`.
- **Fix:** Changed check to `embeddings is not None` and converted embedding vectors to Python lists (`emb.tolist() if hasattr(emb, "tolist") else list(emb)`) for Pinecone upsert payloads.

---

## 3. Final Test and Verification Results

All tests and verification commands were executed locally.

| Verification Item | Command | Result | Notes |
| :--- | :--- | :--- | :--- |
| **Backend Test Suite** | `pytest backend/tests -v` | **71 Passed / 0 Failed** (0.30s) | 100% passing across auth, pinecone adapter, quiz API, RAG chain, and space service |
| **Frontend Production Build** | `npm run build` (in `frontend/`) | **Exit Code 0** (176ms) | Vite v8.2.1 produced clean `dist/` bundle (HTML, CSS, JS) |
| **Pinecone Migration Dry-Run** | `python backend/scripts/migrate_to_pinecone.py --dry-run` | **Exit Code 0** | Validated 29/29 Chroma seed records across 10 namespaces, 0 skipped |
| **Code Formatting / Whitespace** | `git diff --check` | **Exit Code 0** | Clean diff with zero whitespace defects |

---

## 4. Exact Pinecone Index Settings & Seed Migration Procedure

### 4.1 Pinecone Index Settings
In the Pinecone Console (or via API), configure your serverless index with these exact parameters:

| Setting | Required Value | Rationale |
| :--- | :--- | :--- |
| **Index Name** | `vinavalai-rag` | Matches `PINECONE_INDEX_NAME` in `render.yaml` and `.env.example` |
| **Dimensions** | `384` | Strictly matches the dense embeddings produced by `sentence-transformers/all-MiniLM-L6-v2` |
| **Metric** | `cosine` | Required by the cosine similarity ranking in VinavalAI's vector adapter |
| **Cloud Provider** | `aws` | Serverless free tier supported cloud |
| **Region** | `us-east-1` | Serverless free tier default region |

### 4.2 Seed Migration Procedure
The local seed syllabus chunks (29 vectors in `backend/chroma_db/`) must be migrated to Pinecone once before production traffic begins:

1. Open your local terminal in the project root:
   ```bash
   cd backend
   ```
2. Set your Pinecone environment variables:
   ```bash
   export PINECONE_API_KEY="your-actual-pinecone-api-key"
   export PINECONE_INDEX_NAME="vinavalai-rag"
   ```
3. Run the migration script:
   ```bash
   python scripts/migrate_to_pinecone.py
   ```
4. **Idempotency Guarantee:** The migration script uses deterministic vector IDs matching the source Chroma IDs (`doc_0`, `doc_1`, etc.) within each namespace (`neet_physics`, `tnpsc_history`, etc.). Pinecone upserts will overwrite records with matching IDs rather than creating duplicates. Repeated executions are completely safe and idempotent.

---

## 5. Render Backend Configuration & Firebase Secret File

### 5.1 Render Web Service Settings
- **Service Type:** Web Service
- **Runtime:** Native Python (`Python 3`)
- **Branch:** `main`
- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt && alembic upgrade head`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`

### 5.2 Required Environment Variables on Render

| Variable Name | Recommended Value | Secret? | Purpose |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | No | Enables production mode (strictly requires Pinecone) |
| `DATABASE_URL` | `postgresql+asyncpg://<user>:<password>@<host>/<dbname>` | Yes | Persistent PostgreSQL connection (see Section 6) |
| `SECRET_KEY` | *(Generate via `openssl rand -hex 32`)* | Yes | JWT signing secret |
| `ALGORITHM` | `HS256` | No | JWT encryption algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| `30` | No | Access token lifespan |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | No | Refresh token lifespan |
| `VECTOR_STORE_PROVIDER` | `pinecone` | No | Dual-RAG vector store provider |
| `PINECONE_INDEX_NAME` | `vinavalai-rag` | No | Pinecone index name |
| `PINECONE_API_KEY` | *(Your Pinecone API Key)* | Yes | Pinecone authentication |
| `GEMINI_API_KEY` | *(Your Google AI Studio Key)* | Yes | Primary LLM provider |
| `GEMINI_MODEL` | `gemini-1.5-flash` | No | Supported Gemini model |
| `GROQ_API_KEY` | *(Your Groq Cloud Key)* | Yes | Fallback / Standalone LLM provider |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | No | Fast Groq model |
| `FIREBASE_CREDENTIALS_PATH` | `/etc/secrets/firebase_service_account.json` | No | Path to mounted secret file |
| `FRONTEND_URL` | `https://<your-app>.vercel.app` | No | CORS allowed origins (comma-separated) |

### 5.3 Firebase Secret File Configuration on Render
Render allows mounting sensitive JSON service accounts as files without committing them to Git:
1. In the Render Dashboard, go to your Web Service → **Environment** tab.
2. Scroll to **Secret Files** and click **Add Secret File**.
3. Set **Filename:** `firebase_service_account.json`
4. The mount path will automatically be `/etc/secrets/firebase_service_account.json`.
5. Paste the entire contents of your local `backend/firebase-service-account.json`.
6. Click **Save**.

---

## 6. Persistent Database Setup & Free-Tier Limitations

### 6.1 Database Persistence Analysis
- **SQLite on Render Free:** Render Free Web Service instances are ephemeral. When the service sleeps after 15 minutes of inactivity or is redeployed, the local filesystem resets. An SQLite file (`vinavalai.db`) will lose all registered users, spaces, uploaded document metadata, and quiz histories.
- **Recommended Setup:** Connect to an external managed PostgreSQL database:
  - **Neon Serverless Postgres (Free Tier):** Provides a free 0.5 GB Postgres instance with connection pooling.
  - **Supabase (Free Tier):** Provides a free 500 MB Postgres instance.
  - **Render Managed PostgreSQL:** Simple integration within the Render dashboard.
- **Connection String Format:** Ensure the connection string uses the async driver:
  ```
  DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>/<database>
  ```
  `backend/alembic/env.py` and `backend/requirements.txt` already include `asyncpg` and `psycopg2-binary`, fully supporting automatic migrations on build via `alembic upgrade head`.

### 6.2 Unavoidable Free-Tier Limitations
- **Render Cold Starts:** The free instance spins down after 15 minutes of inactivity. Waking up on the first incoming request takes ~30 to 50 seconds. The frontend displays loading states, and the health-check path will respond once booted.
- **Memory Allocation (512 MB):** The SentenceTransformer embedding model (`all-MiniLM-L6-v2`) requires ~120 MB RAM during warm-up. Background warm-up is enabled in `main.py` so the server can bind to `$PORT` immediately and stay within the 512 MB memory boundary.
- **Pinecone Serverless Free Tier:** Includes 1 free serverless index with 2GB storage and generous read/write quotas, which easily accommodates the initial 29 syllabus chunks and thousands of user document chunks.

---

## 7. Vercel Project Settings & Environment Variables

### 7.1 Vercel Project Settings
In the Vercel Dashboard, import the Git repository with these settings:
- **Framework Preset:** `Vite`
- **Root Directory:** `frontend`
- **Build Command:** `npm run build` (or leave default `vite build`)
- **Output Directory:** `dist`
- **Install Command:** `npm install`

### 7.2 Vercel Environment Variables
Add the following variable under **Settings → Environment Variables**:

| Variable Name | Value | Purpose |
| :--- | :--- | :--- |
| `VITE_API_URL` | `https://<your-render-service>.onrender.com/api/v1` | Points the React client to your deployed FastAPI backend |

---

## 8. Firebase Authorized Domains & CORS Settings

To allow both Email/Password authentication and Google OAuth popup sign-in:

### 8.1 Firebase Console
1. Open the [Firebase Console](https://console.firebase.google.com/) → Your Project → **Authentication** → **Settings** tab.
2. Under **Authorized domains**, click **Add domain**.
3. Add:
   - `<your-app>.vercel.app` (Vercel production domain)
   - `<your-app>-git-*.vercel.app` (optional: for Vercel preview deployments)
   - `<your-backend>.onrender.com` (Render backend domain)
   - Any custom domain you plan to bind (e.g. `vinaval.example.com`).

### 8.2 Backend CORS Origin
In your Render Dashboard, ensure `FRONTEND_URL` contains your Vercel URL:
```
FRONTEND_URL=https://<your-app>.vercel.app
```
`backend/app/main.py` parses comma-separated URLs in `FRONTEND_URL` and adds them to `CORSMiddleware`. In addition, `main.py` automatically sets `Cross-Origin-Opener-Policy: same-origin-allow-popups` so that Google OAuth popups can communicate back to the React application.

---

## 9. Ordered List of Actions Requiring External Dashboards

Follow these ordered steps to complete deployment:

1. **Pinecone Dashboard:**
   - Log in to [Pinecone Console](https://app.pinecone.io/).
   - Create a Serverless index named `vinavalai-rag` with **Dimensions: 384**, **Metric: cosine**, **Cloud: AWS**, **Region: us-east-1**.
   - Copy your Pinecone API Key.
2. **Local Seed Migration (Run Once):**
   - Run in your local terminal:
     ```bash
     cd backend
     export PINECONE_API_KEY="<your-pinecone-key>"
     export PINECONE_INDEX_NAME="vinavalai-rag"
     python scripts/migrate_to_pinecone.py
     ```
   - Confirm output shows 29 vectors migrated across all 10 namespaces.
3. **External PostgreSQL Database:**
   - Create a free PostgreSQL database (on Neon, Supabase, or Render).
   - Copy the async connection string (`postgresql+asyncpg://...`).
4. **Render Backend Deployment:**
   - Log in to [Render Dashboard](https://dashboard.render.com/) → **New + → Web Service**.
   - Connect your GitHub repository, choose branch `main`, and set root directory to `backend`.
   - Add Secret File: `firebase_service_account.json` mounted at `/etc/secrets/firebase_service_account.json` with your service account JSON.
   - Add all environment variables from Section 5.2.
   - Click **Deploy Web Service** and note your assigned URL (`https://<backend>.onrender.com`).
5. **Vercel Frontend Deployment:**
   - Log in to [Vercel Dashboard](https://vercel.com/) → **Add New... → Project**.
   - Select your repository, set Root Directory to `frontend`.
   - Add Environment Variable: `VITE_API_URL=https://<backend>.onrender.com/api/v1`.
   - Click **Deploy** and note your assigned URL (`https://<frontend>.vercel.app`).
6. **Link Origins:**
   - In Render Dashboard, update `FRONTEND_URL` to `https://<frontend>.vercel.app`.
   - In Firebase Console, add `<frontend>.vercel.app` to **Authorized domains**.

---

## 10. Post-Deployment Smoke Test Checklist

Once both services are deployed, perform these verification steps on the live application:

- [ ] **1. Health Check:**
  - Execute `curl -i https://<backend>.onrender.com/health`
  - Verify status code is `200 OK` and response body is `{"status":"ok","app":"VinavalAI"}`.
- [ ] **2. SPA Route Reload:**
  - In a browser, open `https://<frontend>.vercel.app/welcome` and hard-refresh (Cmd+Shift+R / Ctrl+F5).
  - Verify page reloads without a 404 error.
- [ ] **3. User Signup & Login:**
  - Create a new account with email and password.
  - Verify registration succeeds, access token is saved in `localStorage`, and client navigates to `/dashboard`.
- [ ] **4. Google OAuth Sign-In:**
  - Click "Sign in with Google" on the login page.
  - Verify Google popup opens, completes authentication, and redirects to the dashboard.
- [ ] **5. Syllabus RAG (Pipeline A):**
  - Open NEET Physics space → Chat Tab.
  - Ask: `"What is Newton's First Law?"`.
  - Verify response streams tokens and cites syllabus reference material.
- [ ] **6. User Document RAG (Pipeline B):**
  - Open Materials Tab in a space.
  - Upload a test PDF document (e.g. lecture notes).
  - Verify upload completes, topics are extracted, and chunks are indexed in Pinecone under the space namespace.
  - Switch chat to Document Chat mode and query the uploaded document. Verify the answer is synthesized from the document.
- [ ] **7. Quiz Generation & SSE Streaming:**
  - Open Exam Lab Tab. Request 5 practice MCQs on any topic.
  - Verify questions stream into the interface one by one.
  - Submit an answer and verify correctness and explanation are returned.
- [ ] **8. Document Deletion:**
  - Delete the uploaded test document in the Materials Tab.
  - Verify document record is removed from the UI and vector chunks are purged from Pinecone.

---

## 11. Final Decision

### **GO AFTER MANUAL SETUP**

The codebase is completely verified, robust, and free of blocking defects. Deployment may proceed immediately following the manual cloud dashboard configurations outlined in Section 9.
