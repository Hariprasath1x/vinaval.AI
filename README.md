# Vinaval AI

> AI-Powered Learning Arena for Tamil Nadu Aspirants (NEET & TNPSC)

## Project Structure

```
vinavalai/
├── frontend/          # React + Vite + TypeScript + Tailwind CSS
├── backend/           # FastAPI + SQLAlchemy + ChromaDB
├── docker-compose.yml
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Docker & Docker Compose (recommended)

---

### Option A — Docker (Recommended)

```bash
# 1. Copy env files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 2. Fill in your secrets in both .env files
# 3. Start all services
docker-compose up --build
```

App will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

### Option B — Local Development

**Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env    # fill in values

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env    # fill in VITE_GOOGLE_CLIENT_ID
npm run dev
```

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async connection string |
| `SECRET_KEY` | JWT signing secret (generate a strong random key) |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |
| `GROQ_API_KEY` | Groq API key |

### Frontend (`frontend/.env`)
| Variable | Description |
|---|---|
| `VITE_GOOGLE_CLIENT_ID` | Same Google OAuth Client ID |
| `VITE_GOOGLE_REDIRECT_URI` | Redirect URI (must match Google Console) |

---

## Firebase Auth Setup

### Firebase Console (once per project)
1. Go to [Firebase Console](https://console.firebase.google.com/) → Create project
2. **Authentication** → Sign-in method → Enable **Google**
3. **Project Settings** → Your apps → Add a **Web app** → Copy the config into `frontend/.env`
4. **Project Settings** → Service Accounts → **Generate new private key** → save as `backend/firebase-service-account.json`

> ⚠️ Never commit `firebase-service-account.json` to git. Add it to `.gitignore`.

### Environment Variables

**Backend (`backend/.env`)**
| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async connection string |
| `SECRET_KEY` | JWT signing secret (generate a strong random key) |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to downloaded Firebase service account JSON |
| `GROQ_API_KEY` | Groq API key from [console.groq.com](https://console.groq.com) |

**Frontend (`frontend/.env`)**
| Variable | Description |
|---|---|
| `VITE_FIREBASE_API_KEY` | From Firebase Web App config |
| `VITE_FIREBASE_AUTH_DOMAIN` | From Firebase Web App config |
| `VITE_FIREBASE_PROJECT_ID` | From Firebase Web App config |
| `VITE_FIREBASE_APP_ID` | From Firebase Web App config |


| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| State | TanStack Query, React Context |
| Backend | FastAPI, SQLAlchemy (async), Alembic |
| Database | PostgreSQL |
| Vector DB | ChromaDB |
| Embeddings | BAAI/bge-small-en-v1.5 |
| LLM | Groq (Llama 3 70B) |
| Auth | Google OAuth 2.0 + JWT |
| Deployment | Docker + Docker Compose |
