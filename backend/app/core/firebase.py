import os
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from app.core.config import get_settings

settings = get_settings()
_initialized = False
_init_error: str | None = None


def init_firebase() -> None:
    """Initialize Firebase Admin SDK once at application startup.
    In development, if the service account file is missing, we skip
    initialization and log a warning instead of crashing the server.
    """
    global _initialized, _init_error
    if _initialized:
        return

    path = settings.FIREBASE_SERVICE_ACCOUNT_PATH
    if not os.path.exists(path):
        _init_error = (
            f"Firebase service account not found at '{path}'. "
            "Auth endpoints will return 503 until configured. "
            "See README for setup instructions."
        )
        print(f"WARNING: {_init_error}")
        return

    try:
        cred = credentials.Certificate(path)
        try:
            firebase_admin.initialize_app(cred)
        except ValueError:
            # App already initialized (e.g., during hot-reload) — just reuse it
            pass
        _initialized = True
        print("Firebase Admin SDK initialized successfully.")
    except Exception as exc:
        _init_error = str(exc)
        print(f"Firebase init failed: {_init_error}")



def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token and return the decoded claims.
    Raises ValueError if Firebase is not configured or the token is invalid.
    """
    if not _initialized:
        raise ValueError(
            _init_error or "Firebase is not initialized. Add firebase-service-account.json."
        )
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return {
            "uid": decoded["uid"],
            "email": decoded.get("email", ""),
            "name": decoded.get("name", decoded.get("email", "").split("@")[0]),
            "picture": decoded.get("picture"),
        }
    except Exception as exc:
        raise ValueError(f"Invalid Firebase token: {exc}") from exc
