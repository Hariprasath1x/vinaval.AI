# Vinaval AI — Learning Arena

Welcome to **Vinaval AI**! This is a smart, AI-powered learning platform designed for students preparing for competitive exams like NEET and TNPSC in Tamil Nadu. It offers a bilingual (English and Tamil) AI tutor, custom flashcards, and practice quizzes based on official syllabus books and your own uploaded notes.

---

## 📖 Features & Flow

Think of this app as having two main pieces working together: a **Frontend** (what you see and click) and a **Backend** (the brain that does the heavy lifting). 

1. **Secure Authentication:** You can sign in using your Email or a Google account. The frontend talks to Firebase and the backend to securely log you in. You can also view and manage your profile details securely.
2. **Personalized Learning Spaces:** You select an exam (like NEET) and a subject (like Physics). This creates an isolated study dashboard.
3. **Intelligent Hybrid RAG Chat:** When you ask a question, the backend searches through its vector database (ChromaDB) to find relevant chunks from the official syllabus books. It sends these to a super-smart AI model (Llama 3 via Groq) which answers your question. You can use the **Language Toggle** to force the AI to respond purely in English or purely in Tamil.
4. **Document Analysis:** Upload your own PDF notes or text files! The backend semantic-chunks the text, extracts metadata, and saves it. The AI can dynamically focus on explaining or summarizing your specific notes.
5. **Exam Lab & Flashcards:** Generate flashcards and quizzes instantly based on the books and your uploads. Take a quiz, get graded, and receive a personalized AI review of your performance. Quiz history and accuracy stats are neatly tracked in the **Reports** tab.

---

## 📂 File Architecture

The project is structured to strictly separate the FastAPI backend from the Streamlit frontend.

```text
vinavalai/
├── backend/                  # FastAPI Backend API Server
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/              # API Route handlers (v1)
│   │   ├── core/             # Config, security, and database connections
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── rag/              # AI LangChain pipelines and Document routing
│   │   ├── repositories/     # Database CRUD operations
│   │   ├── schemas/          # Pydantic validation schemas
│   │   └── services/         # Core business logic
│   ├── main.py               # FastAPI application entry point
│   └── requirements.txt      # Backend Python dependencies
├── frontend/                 # Streamlit Web Application
│   ├── pages/                # Multi-page routing (Dashboard, Space, etc.)
│   ├── utils/                # API helpers and reusable UI components
│   ├── app.py                # Streamlit entry point (Login)
│   └── requirements.txt      # Frontend Python dependencies
├── tests/                    # End-to-End and Integration Tests
├── docker-compose.yml        # Docker configuration for isolated deployments
├── start.bat                 # Windows quick-start launcher
└── start.sh                  # MacOS/Linux quick-start launcher
```

---

## 🛠️ The Technology Stack

We keep things modern, fast, and lightweight:

*   **Frontend:** Built with **Streamlit** (Python) for rapid, data-centric AI application UI.
*   **Backend:** Built with **FastAPI** (Python) for asynchronous, high-performance API handling.
*   **Relational Database:** **SQLite** (`vinavalai.db`) stores user accounts, chat history, quiz attempts, and flashcards. 
*   **Vector Database:** **ChromaDB**. Stores document embeddings using `paraphrase-multilingual-MiniLM-L12-v2` so it understands both English and Tamil natively.
*   **LLM Engine:** Powered by **Groq** using the **Llama 3 70B** model for incredibly fast inference.

---

## 🚀 How to Run the App

The absolute easiest way to run the app is using the provided start scripts. You don't need Docker for everyday local development!

### Option 1: One-Click Start (Windows/Mac/Linux)

**If you are on Windows:**
Just double-click the `start.bat` file in the main folder! It will automatically start both the backend and the frontend in separate windows.

**If you are on Mac/Linux:**
Run the shell script in your terminal:
```bash
./start.sh
```

### Option 2: Run Using Docker
If you want to run the app in a completely isolated environment (like if you are deploying to a server), you can use Docker.

```bash
docker-compose up --build
```

---

## 🌐 Where to view the app

Once started, open your web browser and go to:
*   **The App (Streamlit Frontend):** `http://localhost:8501`
*   *(The Backend runs silently in the background at `http://localhost:8000`)*

---

## 🔑 Environment Variables
Make sure you have your API keys set up before running!

**In `backend/.env`:**
*   `GROQ_API_KEY` - Your key from Groq to power the AI.
*   `GROQ_MODEL` - We recommend `llama-3.3-70b-versatile`.
*   *(Make sure `firebase-service-account.json` is also in the backend folder!)*

**In `frontend/.env`:**
*   `API_URL` - Set to `http://localhost:8000/api/v1`

---

## 📚 Adding Official Syllabus Books

As an admin, you can load official textbooks into the database so all students can learn from them. The AI will use these books to answer questions.

```bash
cd backend

# Seed a NEET Physics textbook (English)
python scripts/seed_books.py --exam NEET --subject Physics --lang en --file /path/to/physics.pdf --title "NCERT Physics"

# Seed a TNPSC History guide (Tamil)
python scripts/seed_books.py --exam TNPSC --subject History --lang ta --file /path/to/history_tamil.pdf
```
