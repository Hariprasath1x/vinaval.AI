from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "VinavalAI"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Firebase Admin SDK
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "./firebase-service-account.json"

    # Groq
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # ChromaDB — must match the directory where chroma_db/ was pre-built
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # Firebase Web API Key (public client-side key — not the service account)
    # Used for the forgot-password email flow via Firebase REST API
    FIREBASE_WEB_API_KEY: str = ""

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
