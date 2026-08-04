# Vinaval AI — Learning Arena

Welcome to **Vinaval AI**! This is a smart, AI-powered learning platform designed for students preparing for competitive exams like NEET and TNPSC in Tamil Nadu. It offers a bilingual (English and Tamil) AI tutor, custom flashcards, and practice quizzes based on official syllabus books and your own uploaded notes.

---

## 📖 How It Works (The Flow)

Think of this app as having two main pieces working together: a **Frontend** (what you see and click) and a **Backend** (the brain that does the heavy lifting). 

1. **You log in:** You can sign in using your Email or a Google account. The frontend talks to Firebase and the backend to securely log you in. You can also view and manage your profile details securely in the **Profile** page.
2. **You pick a Learning Space:** You select an exam (like NEET) and a subject (like Physics). This opens up your personalized study dashboard.
3. **You chat with the AI:** When you ask a question, the backend searches through its database (ChromaDB) to find relevant paragraphs from the official syllabus books. It sends these paragraphs to a super-smart AI model (Llama 3 via Groq) which reads them and answers your question. You can use the **Language Toggle** to force the AI to respond purely in English or purely in Tamil.
4. **You upload your own notes:** If you have special PDF notes or question banks, you can upload them! The backend reads the text, chops it into smaller chunks, and saves it. Now, the AI will use your notes to answer your questions too!
5. **You practice:** You can generate flashcards and quizzes. The AI creates them instantly based on the books and your uploads. When you take a quiz, you get graded and receive a personalized AI review of your performance. All your quiz history is saved and neatly tracked in the **Reports** tab.

---

## 🛠️ The Technology Stack

We keep things modern, fast, and lightweight:

*   **Frontend (The Face):** Built with **Streamlit** (Python). It’s super fast for building AI apps without needing complex JavaScript frameworks.
*   **Backend (The Brain):** Built with **FastAPI** (Python). It handles all the API requests, user uploads, and talks to the AI.
*   **Main Database:** We use **SQLite** (`vinavalai.db`). It stores user accounts, chat history, quiz attempts, and saved flashcards. 
*   **Vector Database (For AI Memory):** We use **ChromaDB**. When you upload a book or notes, it converts the text into "embeddings" (a format the AI understands) so it can search through thousands of pages in milliseconds. We use a special multilingual model so it understands Tamil perfectly.
*   **The AI Engine:** Powered by **Groq** using the **Llama 3 70B** model. It's incredibly fast and smart.

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
