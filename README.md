# Vinaval AI

> AI-Powered Learning Arena for Tamil Nadu Aspirants (NEET & TNPSC)

## Project Structure

```
vinavalai/
├── frontend/          # Streamlit Multi-Page App (Python)
├── frontend_react/    # Legacy React + Vite + TypeScript (Backup)
├── backend/           # FastAPI + SQLAlchemy + ChromaDB
├── docker-compose.yml
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.11+
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
- Frontend (Streamlit): http://localhost:8501
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

**Frontend (Streamlit)**
```bash
cd frontend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env    # fill in values (API_URL=http://localhost:8000/api/v1)
streamlit run app.py
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
| `API_URL` | URL to FastAPI backend (e.g., http://localhost:8000/api/v1) |

---

## Authentication (Mock Login)

Currently, the Streamlit frontend uses a **Mock Login** system that bypasses Firebase for rapid development. 

To log in:
1. Navigate to the Streamlit Home Page (`http://localhost:8501`).
2. Enter any valid email (e.g., `test@example.com`).
3. The system will automatically generate a mock user in PostgreSQL and issue a JWT token for all API access.

*(Note: The legacy React app used Firebase Google Auth. To restore Firebase, you'll need to adapt the `auth_service.py` back to using `login_with_firebase` and build a custom Firebase OAuth component for Streamlit).*

---


| Layer | Technology |
|---|---|
| Frontend | Streamlit, Python, requests |
| State | Streamlit Session State |
| Backend | FastAPI, SQLAlchemy (async), Alembic |
| Database | PostgreSQL |
| Vector DB | ChromaDB |
| Embeddings | BAAI/bge-small-en-v1.5 |
| LLM | Groq (Llama 3 70B) |
| Auth | Google OAuth 2.0 + JWT |
| Deployment | Docker + Docker Compose |
