import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv

# Explicitly load the backend/.env file from its absolute path
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_env_path = os.path.join(_backend_dir, ".env")
load_dotenv(dotenv_path=_env_path)

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

    # Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.6-flash"

    # Groq Fallback
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama3-70b-8192"

    # ChromaDB — must match the directory where chroma_db/ was pre-built
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # Vector Store Config
    VECTOR_STORE_PROVIDER: str = "chroma"

    # Pinecone
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX_NAME: Optional[str] = None

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
