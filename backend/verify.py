"""Comprehensive functional verification script for Vinaval AI backend."""
import asyncio
import sys
import json
import urllib.request
import urllib.error

# Ensure stdout supports UTF-8 on Windows command line
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


BASE = "http://localhost:8000"

results = []

def check(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}]  {name}" + (f"  [{detail}]" if detail else ""))
    results.append((name, passed))

def get(path):
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {}

def post(path, data=None, headers=None):
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {}

print("\n" + "="*60)
print("  VINAVAL AI — FULL BACKEND VERIFICATION")
print("="*60 + "\n")

# 1. Server reachable
status, data = get("/api/v1/exams")
check("Backend is reachable (GET /api/v1/exams)", status == 200)

# 2. Exams data
check("NEET exam present", any(e.get("id") == "NEET" for e in data))
check("TNPSC exam present", any(e.get("id") == "TNPSC" for e in data))
neet = next((e for e in data if e["id"] == "NEET"), None)
if neet:
    check("NEET has 4 subjects", len(neet.get("subjects", [])) == 4)
tnpsc = next((e for e in data if e["id"] == "TNPSC"), None)
if tnpsc:
    check("TNPSC has 6 subjects", len(tnpsc.get("subjects", [])) == 6)

# 3. Auth protection
status, _ = get("/api/v1/spaces")
check("GET /spaces requires auth (401)", status == 401)

status, _ = post("/api/v1/spaces", {"exam_id": "NEET", "subject": "Physics"})
check("POST /spaces requires auth (401)", status == 401)

# 4. Auth endpoint exists
status, body = post("/api/v1/auth/firebase", None)
check("POST /auth/firebase endpoint exists (422=validation, not 404)", status in [422, 400])

# 5. OpenAPI spec check — all routes registered
status, spec = get("/openapi.json")
if status == 200:
    paths = list(spec.get("paths", {}).keys())
    check("Spaces routes present", any("/spaces" in p for p in paths))
    check("Quiz routes present", any("quiz" in p for p in paths))
    check("Flashcard routes present", any("flashcard" in p for p in paths))
    check("Auth routes present", any("auth" in p for p in paths))
    check("Exam routes present", any("exam" in p for p in paths))

    # Check specific flashcard endpoints
    fc_paths = [p for p in paths if "flashcard" in p]
    check("Flashcard generate endpoint", any("generate" in p for p in fc_paths))
    check("Flashcard list endpoint", any(p.endswith("flashcards") for p in fc_paths))
    check("Flashcard topics endpoint", any("topics" in p for p in fc_paths))
    print(f"\n  Flashcard routes: {fc_paths}")
    print(f"  Total routes: {len(paths)}\n")

# 6. DB tables check
import sqlite3
try:
    conn = sqlite3.connect("vinavalai.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    check("users table exists", "users" in tables)
    check("learning_spaces table exists", "learning_spaces" in tables)
    check("chat_messages table exists", "chat_messages" in tables)
    check("space_notes table exists", "space_notes" in tables)
    check("quiz_questions table exists", "quiz_questions" in tables)
    check("quiz_attempts table exists", "quiz_attempts" in tables)
    check("flashcards table exists", "flashcards" in tables, f"tables={tables}")
    
    # Check flashcards schema
    cursor.execute("PRAGMA table_info(flashcards)")
    cols = [r[1] for r in cursor.fetchall()]
    check("flashcards.front column", "front" in cols)
    check("flashcards.back column", "back" in cols)
    check("flashcards.topic column", "topic" in cols)
    check("flashcards.space_id column (FK)", "space_id" in cols)
    conn.close()
except Exception as e:
    check("DB accessible", False, str(e))

print("\n" + "="*60)
passed = sum(1 for _, p in results if p)
total = len(results)
print(f"  RESULT: {passed}/{total} checks passed")
if passed < total:
    print("  FAILURES:")
    for name, p in results:
        if not p:
            print(f"    ❌ {name}")
print("="*60 + "\n")
sys.exit(0 if passed == total else 1)
