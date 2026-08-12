# VinavalAI — Render Deployment Guide

> **Branch:** `react_version` | **Target:** [https://vinaval.hariprasath.me](https://vinaval.hariprasath.me)

---

## Architecture Overview

```
React + Vite (Render Static Site)
        ↓  VITE_API_URL
FastAPI + Uvicorn (Render Native Python Web Service)
        ↓
Firebase Authentication  ←→  Gemini / Groq
        ↓
SQLite + Alembic
        ↓
ChromaDB RAG (pre-built)
```

---

## Backend — Web Service

| Setting | Value |
|---|---|
| **Service type** | Web Service |
| **Branch** | `react_version` |
| **Root Directory** | `backend` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt && alembic upgrade head` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health` |

---

## Frontend — Static Site

| Setting | Value |
|---|---|
| **Service type** | Static Site |
| **Branch** | `react_version` |
| **Root Directory** | `frontend` |
| **Build Command** | `npm install && npm run build` |
| **Publish Directory** | `dist` |

> The `frontend/public/_redirects` file handles SPA routing (`/* → /index.html 200`).
> Render also reads the `routes` section in `render.yaml` for the same purpose.

---

## Environment Variables

### Backend (set in Render dashboard)

| Variable | Purpose | Secret | Required |
|---|---|---|---|
| `APP_NAME` | Application name displayed in health check | No | No (has default) |
| `APP_ENV` | Set to `production` | No | Yes |
| `DEBUG` | Set to `false` | No | Yes |
| `DATABASE_URL` | SQLite connection string | No | Yes |
| `SECRET_KEY` | JWT signing key | **Yes** | Yes |
| `ALGORITHM` | JWT algorithm (`HS256`) | No | No (has default) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes | No | No (default: 10080) |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to service-account JSON | **Yes (path)** | Yes |
| `FIREBASE_WEB_API_KEY` | Firebase web client key (for password-reset flow) | No* | Yes |
| `GROQ_API_KEY` | Groq LLM API key | **Yes** | Yes |
| `GROQ_MODEL` | Groq model name | No | No (has default) |
| `GEMINI_API_KEY` | Gemini API key (Groq fallback) | **Yes** | Recommended |
| `GEMINI_MODEL` | Gemini model name | No | No (has default) |
| `CHROMA_PERSIST_DIR` | Path to pre-built ChromaDB | No | Yes |
| `FRONTEND_URL` | CORS allowed origin | No | Yes |

> \* Firebase Web API Key is a **public** client-side key (not a service-account private key).
> It is safe to expose in the browser, but configuring it via env var makes rotation easier.

#### Recommended Render values

```env
APP_ENV=production
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///./vinavalai.db
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">
FIREBASE_SERVICE_ACCOUNT_PATH=/etc/secrets/firebase.json
FIREBASE_WEB_API_KEY=AIzaSyClUultgV7XpYjT1teKAbtchNGpRfqr04A
CHROMA_PERSIST_DIR=./chroma_db
FRONTEND_URL=https://vinaval.hariprasath.me
```

### Frontend (set in Render dashboard)

| Variable | Purpose | Secret | Required |
|---|---|---|---|
| `VITE_API_URL` | Backend API base URL | No | Yes |

#### Recommended value

```env
VITE_API_URL=https://<your-backend-service>.onrender.com/api/v1
```

> Replace `<your-backend-service>` with the actual Render service name after deployment.

---

## Firebase Secret File

The Firebase Admin SDK requires a service-account JSON file at runtime.

**Do NOT commit this file.** It is already covered by `.gitignore`.

### Steps

1. Download from Firebase Console → Project Settings → Service Accounts → **Generate new private key**
2. In the Render dashboard for the backend service, go to **Secret Files**
3. Add file:
   - **Filename in service:** `/etc/secrets/firebase.json`
   - **Contents:** paste the JSON
4. Set the environment variable:
   ```
   FIREBASE_SERVICE_ACCOUNT_PATH=/etc/secrets/firebase.json
   ```

---

## ChromaDB — IMPORTANT

The pre-built ChromaDB (`backend/chroma_db/`) is **not committed to git** (it's in `.gitignore`).

This means you **must** make it available on Render by one of these methods:

### Option A — Render Disk (Recommended for persistence)
1. Add a **Disk** to your backend web service in Render dashboard
2. Mount path: `/opt/render/project/src/chroma_db` (or adjust to your working directory)
3. Upload the `chroma_db/` contents to that disk path
4. Set: `CHROMA_PERSIST_DIR=./chroma_db`

### Option B — Re-seed on deploy (Only if books/ is available)
Add to build command:
```bash
pip install -r requirements.txt && alembic upgrade head && python scripts/seed_rag.py
```
> ⚠️ This is slow (~200MB PDFs, many embeddings) and requires `books/` to be accessible.

### Option C — Commit chroma_db to git (simplest but large)
If the database is small enough for Render's free tier:
1. Remove `backend/chroma_db/` from `.gitignore`
2. `git add backend/chroma_db && git commit`
3. No env var change needed

> The pre-built `chroma_db/` is ~208MB. Free Render accounts have a 500MB disk limit.

---

## SPA Routing

React Router requires all routes to serve `index.html`.

This is handled by:
1. `frontend/public/_redirects` — Render-native redirect rule
2. `render.yaml` routes section — Blueprint-level SPA rewrite

No additional nginx config is needed.

---

## Alembic Migrations

Run automatically as part of the build command:
```bash
alembic upgrade head
```

The `alembic/env.py` converts the `sqlite+aiosqlite://` URL to `sqlite://` for synchronous migrations automatically.

---

## Custom Domain

After deploying the frontend Static Site:
1. In Render dashboard → your static site → **Settings → Custom Domains**
2. Add: `vinaval.hariprasath.me`
3. Follow Render's DNS instructions (typically a CNAME record)
4. After domain is live, update `FRONTEND_URL` on the backend to `https://vinaval.hariprasath.me`
5. Update `VITE_API_URL` on the frontend if the backend URL changes

---

## Google Authentication Flow

The frontend redirects to `<backend>/auth/google-popup?return_url=<origin>`.

The backend serves a Firebase JS SDK popup page that:
1. Opens Google Sign-In popup
2. Gets Firebase ID token
3. Redirects back to `<return_url>/?firebase_token=<token>`
4. Frontend POSTs token to `/api/v1/auth/firebase` to get a JWT

**Firebase Authorized Domains:** You must add your Render backend URL and frontend domain to Firebase Console → Authentication → Settings → Authorized Domains.

---

## Health Check

```
GET /health
→ 200 {"status": "ok", "app": "VinavalAI"}
```

No authentication required. Does not call Gemini, Firebase, or ChromaDB.

---

## Local Development

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev
```

Requires `backend/.env` with local values (see `backend/.env.example`).
