from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
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

    # Middleware to fix Firebase signInWithPopup Cross-Origin-Opener-Policy issue
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        return response

    # Initialize Firebase Admin SDK at startup
    @app.on_event("startup")
    async def startup():
        init_firebase()

    # Register all API routes
    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "app": settings.APP_NAME}

    # Serve static files from the frontend build
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
    
    if os.path.isdir(static_dir):
        # Mount the assets directory directly
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
            
        @app.get("/{catchall:path}")
        async def serve_react_app(catchall: str):
            # If the user is requesting a specific file (e.g., favicon.ico, manifest.json)
            file_path = os.path.join(static_dir, catchall)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            
            # For all other routes, serve index.html for client-side routing
            index_path = os.path.join(static_dir, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path)
            
            return {"error": "Frontend build not found."}

    return app


app = create_app()
