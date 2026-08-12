from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.core.config import get_settings
from app.core.firebase import init_firebase
from app.api.v1 import router as api_v1_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter


settings = get_settings()

_FIREBASE_CONFIG_JS = (
    "{\n"
    f'  apiKey: "{settings.FIREBASE_WEB_API_KEY}",\n'
    '  authDomain: "vinavalai.firebaseapp.com",\n'
    '  projectId: "vinavalai",\n'
    '  storageBucket: "vinavalai.firebasestorage.app",\n'
    '  messagingSenderId: "513537593204",\n'
    '  appId: "1:513537593204:web:252db2e288e39dddc0e621",\n'
    '  measurementId: "G-RPL46P737E"\n'
    "}"
)



_CDN = "https://www.gstatic.com/firebasejs/10.12.0"

_GOOGLE_POPUP_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Signing in with Google…</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      flex-direction: column; gap: 20px; color: #f1f5f9;
    }}
    .card {{
      background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.10);
      border-radius: 20px; padding: 2.5rem 2rem; max-width: 360px; width: 90%;
      text-align: center; backdrop-filter: blur(12px);
    }}
    .logo {{ font-size: 2rem; margin-bottom: 0.5rem; }}
    h1 {{ font-size: 1.1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.35rem; }}
    .sub {{ color: #94a3b8; font-size: 13px; margin-bottom: 1.5rem; }}
    .spinner {{
      width: 40px; height: 40px; margin: 0 auto;
      border: 3px solid rgba(167,139,250,0.3);
      border-top-color: #a78bfa; border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    #status {{ color: #94a3b8; font-size: 13px; margin-top: 12px; }}
    .err-msg {{ color: #f87171; font-size: 13px; margin-top: 12px; }}
    .btn {{
      margin-top: 16px; padding: 10px 24px;
      background: linear-gradient(135deg, #7c3aed, #4f46e5);
      color: #fff; border: none; border-radius: 9px;
      font-size: 14px; font-weight: 500; cursor: pointer;
      transition: opacity 0.2s;
    }}
    .btn:hover {{ opacity: 0.85; }}
    .btn-ghost {{
      background: transparent; border: 1px solid rgba(255,255,255,0.15);
      color: #94a3b8; margin-left: 8px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">🎓</div>
    <h1>Vinaval AI</h1>
    <p class="sub">Signing you in with Google…</p>
    <div class="spinner" id="spinner"></div>
    <p id="status">Opening sign-in window…</p>
    <div id="actions" style="display:none"></div>
  </div>

  <script type="module">
    import {{ initializeApp }}   from '{_CDN}/firebase-app.js';
    import {{ getAuth, signInWithPopup, GoogleAuthProvider }} from '{_CDN}/firebase-auth.js';

    const firebaseConfig = {_FIREBASE_CONFIG_JS};
    const app      = initializeApp(firebaseConfig);
    const auth     = getAuth(app);
    const provider = new GoogleAuthProvider();
    provider.addScope('email');
    provider.addScope('profile');

    const params    = new URLSearchParams(window.location.search);
    const returnUrl = params.get('return_url') || '{settings.FRONTEND_URL}';

    const statusEl  = document.getElementById('status');
    const spinnerEl = document.getElementById('spinner');
    const actionsEl = document.getElementById('actions');

    function showError(msg) {{
      spinnerEl.style.display = 'none';
      statusEl.innerHTML = '<span class="err-msg">' + msg + '</span>';
      actionsEl.style.display = 'block';
      actionsEl.innerHTML = `
        <button class="btn" onclick="doSignIn()">Try Again</button>
        <button class="btn btn-ghost" onclick="window.location.href='${{returnUrl}}'">← Back</button>
      `;
    }}

    window.doSignIn = async function() {{
      actionsEl.style.display = 'none';
      spinnerEl.style.display = 'block';
      statusEl.textContent = 'Opening sign-in window…';
      try {{
        const result  = await signInWithPopup(auth, provider);
        const idToken = await result.user.getIdToken();
        statusEl.textContent = 'Success! Redirecting…';
        window.location.href = returnUrl + '/?firebase_token=' + encodeURIComponent(idToken);
      }} catch (e) {{
        if (e.code === 'auth/popup-closed-by-user' || e.code === 'auth/cancelled-popup-request') {{
          showError('Sign-in was cancelled. Please try again.');
        }} else {{
          showError('Sign-in failed: ' + (e.message || 'Unknown error'));
        }}
      }}
    }};

    doSignIn();
  </script>
</body>
</html>"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise Firebase on startup."""
    init_firebase()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="VinavalAI API",
        description="AI-powered Learning Arena for Tamil Nadu Aspirants",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS — allow the Vite dev server, Streamlit dev server, and production frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.FRONTEND_URL,
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:3000",
        ],
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

    # Register all API routes
    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "app": settings.APP_NAME}

    # ── Google OAuth popup page — served from localhost:8000 so Firebase JS
    # has a valid HTTP origin (not about:srcdoc like Streamlit iframes).
    @app.get("/auth/google-popup", response_class=HTMLResponse, include_in_schema=False)
    async def google_popup_page():
        return HTMLResponse(content=_GOOGLE_POPUP_HTML)

    @app.get("/", tags=["Root"])
    async def root():
        return {"message": "Welcome to VinavalAI API", "docs": "/docs", "health": "/health"}


    return app


app = create_app()
