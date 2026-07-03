from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.firebase import init_firebase
from app.api.v1 import router as api_v1_router

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="VinavalAI API",
        description="AI-powered Learning Arena for Tamil Nadu Aspirants",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — allow the Vite dev server and production frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize Firebase Admin SDK at startup
    @app.on_event("startup")
    async def startup():
        init_firebase()

    # Register all API routes
    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "app": settings.APP_NAME}

    return app


app = create_app()
