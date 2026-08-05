"""
Vinaval AI — Frontend API Client
All HTTP communication between Streamlit and the FastAPI backend lives here.
"""
import os
import requests
import streamlit as st
from typing import Dict, Any, List, Optional, Generator

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _headers(json: bool = True) -> Dict[str, str]:
    h = {}
    if json:
        h["Content-Type"] = "application/json"
    token = st.session_state.get("token")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _handle(resp: requests.Response) -> Any:
    """Raise a user-friendly error on non-2xx responses."""
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = resp.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        st.error(f"❌ API Error {resp.status_code}: {detail}")
        return None
    return resp.json()


# ── Auth ─────────────────────────────────────────────────────────────────────

def signup(name: str, email: str, password: str) -> Optional[Dict[str, Any]]:
    """Register a new account. Returns user info and stores JWT on success."""
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/signup",
            json={"name": name, "email": email, "password": password},
            timeout=30,
        )
        data = _handle(resp)
        if data:
            st.session_state["token"] = data["access_token"]
            st.session_state["user"] = data["user"]
            return data["user"]
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach the backend. Is it running on port 8000?")
    except requests.exceptions.ReadTimeout:
        st.error("❌ The backend took too long to respond. Please try again.")
    return None


def login(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate with email and password. Stores JWT on success."""
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        data = _handle(resp)
        if data:
            st.session_state["token"] = data["access_token"]
            st.session_state["user"] = data["user"]
            return data["user"]
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach the backend. Is it running on port 8000?")
    except requests.exceptions.ReadTimeout:
        st.error("❌ The backend took too long to respond. Please try again.")
    return None


def login_with_firebase(id_token: str) -> Optional[Dict[str, Any]]:
    """Exchange a Firebase ID token for a backend JWT. Stores session on success."""
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/firebase",
            json={"id_token": id_token},
            timeout=15,
        )
        data = _handle(resp)
        if data:
            st.session_state["token"] = data["access_token"]
            st.session_state["user"] = data["user"]
            return data["user"]
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach the backend. Is it running on port 8000?")
    return None


def forgot_password(email: str) -> bool:
    """
    Send a Firebase password-reset email via the backend.
    Returns True on success, False on failure.
    """
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/forgot-password",
            json={"email": email},
            timeout=15,
        )
        if resp.status_code == 200:
            return True
        detail = ""
        try:
            detail = resp.json().get("detail", str(resp.status_code))
        except Exception:
            detail = str(resp.status_code)
        st.error(f"❌ {detail}")
        return False
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach the backend. Is it running on port 8000?")
        return False

def update_profile(name: str) -> Optional[Dict[str, Any]]:
    """Update the user's name."""
    try:
        resp = requests.put(
            f"{BASE_URL}/auth/profile",
            json={"name": name},
            headers=_headers(),
            timeout=10,
        )
        data = _handle(resp)
        if data:
            st.session_state["user"] = data
            return data
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach the backend.")
        return None


def change_password(current_password: str, new_password: str) -> bool:
    """Change the user's password."""
    try:
        resp = requests.put(
            f"{BASE_URL}/auth/change-password",
            json={"current_password": current_password, "new_password": new_password},
            headers=_headers(),
            timeout=10,
        )
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach the backend.")
        return False



# ── Spaces ────────────────────────────────────────────────────────────────────

def get_spaces() -> List[Dict[str, Any]]:
    """Return all spaces for the logged-in user."""
    try:
        resp = requests.get(f"{BASE_URL}/spaces", headers=_headers(), timeout=10)
        return _handle(resp) or []
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return []


def create_space(exam_id: str, subject: str) -> Optional[Dict[str, Any]]:
    """Create (or return existing) space for exam+subject."""
    try:
        resp = requests.post(
            f"{BASE_URL}/spaces",
            json={"exam_id": exam_id, "subject": subject},
            headers=_headers(),
            timeout=10,
        )
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return None


def get_space(space_id: int) -> Optional[Dict[str, Any]]:
    """Return details + chat history of a single space."""
    try:
        resp = requests.get(f"{BASE_URL}/spaces/{space_id}", headers=_headers(), timeout=10)
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return None


def delete_space(space_id: int) -> bool:
    """Permanently delete a Learning Space and all its data."""
    try:
        resp = requests.delete(f"{BASE_URL}/spaces/{space_id}", headers=_headers(), timeout=10)
        if resp.status_code == 204:
            return True
        _handle(resp)
        return False
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return False


def get_note(space_id: int) -> str:
    """Return the note content for a space (empty string if none)."""
    try:
        resp = requests.get(f"{BASE_URL}/spaces/{space_id}/note", headers=_headers(), timeout=10)
        data = _handle(resp)
        return data.get("content", "") if data else ""
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return ""


def save_note(space_id: int, content: str) -> bool:
    """Save (upsert) a note for a space. Returns True on success."""
    try:
        resp = requests.put(
            f"{BASE_URL}/spaces/{space_id}/note",
            json={"content": content},
            headers=_headers(),
            timeout=10,
        )
        return _handle(resp) is not None
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return False


# ── Documents (User Uploads) ──────────────────────────────────────────────────

def upload_document(space_id: int, file_bytes: bytes, filename: str) -> Optional[Dict]:
    """
    Upload a user document (question bank, topic notes, practice PDF).
    Indexing into ChromaDB happens server-side after this call.
    """
    try:
        resp = requests.post(
            f"{BASE_URL}/spaces/{space_id}/documents",
            files={"file": (filename, file_bytes)},
            headers=_headers(json=False),  # Let requests set multipart boundary
            timeout=60,
        )
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return None


def list_documents(space_id: int) -> List[Dict]:
    """Return all user-uploaded documents for this space."""
    try:
        resp = requests.get(
            f"{BASE_URL}/spaces/{space_id}/documents",
            headers=_headers(),
            timeout=10,
        )
        return _handle(resp) or []
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return []


def delete_document(space_id: int, doc_id: int) -> bool:
    """Delete a user-uploaded document and its ChromaDB chunks."""
    try:
        resp = requests.delete(
            f"{BASE_URL}/spaces/{space_id}/documents/{doc_id}",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        st.error(f"❌ Delete failed: {e}")
        return False


# ── Chat (RAG) ────────────────────────────────────────────────────────────────

def stream_chat(
    space_id: int,
    message: str,
    lang: str = "auto",
    active_doc_id: Optional[int] = None,
    active_doc_filename: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Stream the AI response from the RAG chain.
    Passes active_doc_id so the backend restricts retrieval to that file.
    Yields text chunks as they arrive (Server-Sent Events format).
    """
    payload: Dict[str, Any] = {"content": message, "lang": lang}
    if active_doc_id is not None:
        payload["active_doc_id"] = active_doc_id
    if active_doc_filename is not None:
        payload["active_doc_filename"] = active_doc_filename
    try:
        with requests.post(
            f"{BASE_URL}/spaces/{space_id}/chat",
            json=payload,
            headers=_headers(),
            stream=True,
            timeout=60,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: "):
                        payload_data = decoded[6:]
                        if payload_data == "[DONE]":
                            break
                        import json as _json
                        try:
                            chunk = _json.loads(payload_data)
                            if isinstance(chunk, str):
                                yield chunk
                            elif isinstance(chunk, dict) and "error" in chunk:
                                yield f"\n\n\u274c Error: {chunk['error']}"
                        except _json.JSONDecodeError:
                            yield payload_data
    except requests.exceptions.ConnectionError:
        yield "\u274c Backend unreachable."
    except requests.exceptions.Timeout:
        yield "\u274c Request timed out. The AI might be taking too long."


# ── Flashcards ────────────────────────────────────────────────────────────────

def generate_flashcards(space_id: int, topic: str, count: int = 8, lang: str = "en") -> List[Dict]:
    """
    Ask the AI to generate flashcard pairs (front/back) for a topic.
    The AI is grounded by book + user-uploaded content from ChromaDB.
    """
    try:
        resp = requests.post(
            f"{BASE_URL}/spaces/{space_id}/flashcards/generate",
            json={"topic": topic, "count": count, "lang": lang},
            headers=_headers(),
            timeout=60,
        )
        return _handle(resp) or []
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return []


def list_flashcards(space_id: int, topic: Optional[str] = None) -> List[Dict]:
    """Return existing flashcards, optionally filtered by topic."""
    params = {}
    if topic:
        params["topic"] = topic
    try:
        resp = requests.get(
            f"{BASE_URL}/spaces/{space_id}/flashcards",
            params=params,
            headers=_headers(),
            timeout=10,
        )
        return _handle(resp) or []
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return []


def list_flashcard_topics(space_id: int) -> List[str]:
    """Return distinct topics that have flashcards in this space."""
    try:
        resp = requests.get(
            f"{BASE_URL}/spaces/{space_id}/flashcards/topics",
            headers=_headers(),
            timeout=10,
        )
        return _handle(resp) or []
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return []


def delete_flashcard_topic(space_id: int, topic: str) -> bool:
    """Delete all flashcards for a given topic in this space."""
    try:
        import urllib.parse
        encoded_topic = urllib.parse.quote(topic, safe="")
        resp = requests.delete(
            f"{BASE_URL}/spaces/{space_id}/flashcards/{encoded_topic}",
            headers=_headers(),
            timeout=10,
        )
        if resp.status_code in (200, 204):
            return True
        _handle(resp)
        return False
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return False



# ── Quiz ──────────────────────────────────────────────────────────────────────


def generate_quiz(space_id: int, topic: Optional[str] = None, count: int = 5, lang: str = "en") -> Dict:
    """
    Generate MCQ questions for a topic, grounded in ChromaDB context.
    """
    try:
        payload = {"count": count, "lang": lang}
        if topic:
            payload["topic"] = topic
            
        resp = requests.post(
            f"{BASE_URL}/spaces/{space_id}/quiz/generate",
            json=payload,
            headers=_headers(),
            timeout=60,
        )
        return _handle(resp) or {}
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return {}


def submit_answer(space_id: int, question_id: int, answer: str, is_exam: bool = False, session_id: Optional[int] = None) -> Optional[Dict]:
    """Submit an answer for a quiz question. Returns result with explanation."""
    try:
        resp = requests.post(
            f"{BASE_URL}/spaces/{space_id}/quiz/attempt",
            json={"question_id": question_id, "user_answer": answer, "is_exam": is_exam, "session_id": session_id},
            headers=_headers(),
            timeout=10,
        )
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return None


def get_quiz_stats(space_id: int) -> Optional[Dict]:
    """Return practice and exam performance statistics."""
    try:
        resp = requests.get(
            f"{BASE_URL}/spaces/{space_id}/quiz/stats",
            headers=_headers(),
            timeout=10,
        )
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return None


def get_quiz_history(space_id: int) -> List[Dict]:
    """Get the history of quiz sessions for this space."""
    try:
        resp = requests.get(
            f"{BASE_URL}/spaces/{space_id}/quiz/history",
            headers=_headers(),
            timeout=10,
        )
        return _handle(resp) or []
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return []


def generate_quiz_review(space_id: int, results: List[Dict]) -> Optional[str]:
    """Get an AI-generated performance review based on test results."""
    try:
        resp = requests.post(
            f"{BASE_URL}/spaces/{space_id}/quiz/review",
            json={"results": results},
            headers=_headers(),
            timeout=30,
        )
        data = _handle(resp)
        if data:
            return data.get("review")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return None


def get_messages(space_id: int) -> List[Dict]:
    """Return full chat message history for a space."""
    try:
        resp = requests.get(
            f"{BASE_URL}/spaces/{space_id}/messages",
            headers=_headers(),
            timeout=10,
        )
        return _handle(resp) or []
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend unreachable.")
        return []
