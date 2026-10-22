import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
_initialized = False
_init_error: str | None = None


class FirebaseNotConfiguredError(RuntimeError):
    """Raised when Firebase authentication is called but Firebase Admin SDK is not configured."""
    pass


def _find_service_account_path() -> str | None:
    """Check configured path and known Render/deployment secret locations."""
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate_paths = [
        settings.FIREBASE_SERVICE_ACCOUNT_PATH,
        "/etc/secrets/firebase.json",
        "/etc/secrets/firebase-service-account.json",
        "/etc/secrets/firebase_service_account.json",
        os.path.join(backend_root, "firebase-service-account.json"),
        os.path.join(backend_root, "firebase.json"),
    ]
    for p in candidate_paths:
        if p and os.path.exists(p):
            return p
    return None


def init_firebase() -> None:
    """Initialize Firebase Admin SDK once at application startup.
    In development, if the service account is missing, we skip
    initialization and log a warning instead of crashing the server.
    """
    global _initialized, _init_error
    if _initialized:
        return

    # 1. Check for inline JSON in settings or environment variable
    raw_json = settings.FIREBASE_SERVICE_ACCOUNT_JSON or os.getenv("FIREBASE_CREDENTIALS")
    cred = None
    if raw_json and raw_json.strip():
        try:
            cert_dict = json.loads(raw_json.strip())
            cred = credentials.Certificate(cert_dict)
            logger.info("[AUTH] Using Firebase service account from inline environment configuration.")
        except Exception as exc:
            _init_error = f"Failed to parse inline Firebase service account JSON: {type(exc).__name__}"
            logger.error(f"[AUTH] {_init_error}")
            return

    # 2. Check for service account file
    if cred is None:
        path = _find_service_account_path()
        if not path:
            _init_error = (
                "Firebase service account not found. "
                "Upload credentials to Render Secret Files (/etc/secrets/firebase.json) "
                "or set FIREBASE_SERVICE_ACCOUNT_PATH / FIREBASE_SERVICE_ACCOUNT_JSON."
            )
            logger.warning(f"[AUTH] {_init_error}")
            return
        try:
            cred = credentials.Certificate(path)
            logger.info(f"[AUTH] Found Firebase service account at configured location.")
        except Exception as exc:
            _init_error = f"Failed to load Firebase certificate from file: {type(exc).__name__}"
            logger.error(f"[AUTH] {_init_error}")
            return

    try:
        try:
            firebase_admin.initialize_app(cred)
        except ValueError:
            # App already initialized (e.g., during hot-reload) — reuse it
            pass
        _initialized = True
        _init_error = None
        logger.info("[AUTH] Firebase Admin SDK initialized successfully.")
    except Exception as exc:
        _init_error = f"Firebase initialization failed: {type(exc).__name__}"
        logger.error(f"[AUTH] {_init_error}")


def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token and return the decoded claims.
    Raises FirebaseNotConfiguredError if Firebase is not configured.
    Raises ValueError if the token is invalid or expired.
    """
    if not _initialized:
        raise FirebaseNotConfiguredError(
            _init_error or "Firebase Admin SDK is not configured on this server."
        )
    if not id_token or not id_token.strip():
        raise ValueError("Firebase ID token cannot be empty.")

    try:
        decoded = firebase_auth.verify_id_token(id_token)
        email = decoded.get("email") or ""
        return {
            "uid": decoded["uid"],
            "email": email,
            "name": decoded.get("name") or (email.split("@")[0] if email else "Student"),
            "picture": decoded.get("picture"),
        }
    except Exception as exc:
        # Do not include the token in error messages to avoid leaking credentials
        raise ValueError(f"Invalid or expired Firebase token: {type(exc).__name__}") from exc
