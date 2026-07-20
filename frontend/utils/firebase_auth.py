"""
Firebase auth helpers for Streamlit.

Root cause of all iframe issues:
  st.components.v1.html() renders in a sandboxed about:srcdoc iframe.
  The sandbox does NOT have 'allow-top-navigation', so JS cannot navigate
  window.parent, and Firebase JS rejects the about:srcdoc origin.

Fix: render the Google button as a plain HTML <a> link via st.markdown()
  inside the main Streamlit page (not an iframe). Regular anchor tags in
  st.markdown() work fine — they navigate the current tab when clicked.

Flow:
  1. User clicks the Google button (an <a> link in the main page).
  2. Browser navigates to http://localhost:8000/auth/google-popup (FastAPI).
  3. That page runs Firebase signInWithPopup from a real HTTP origin.
  4. On success, it redirects to http://localhost:8501/?firebase_token=<token>.
  5. app.py detects the query param, exchanges with backend, logs user in.
"""
import streamlit as st

_BACKEND_URL = "http://localhost:8000"
_STREAMLIT_URL = "http://localhost:8501"


def render_google_signin_button(label: str = "Continue with Google") -> None:
    """
    Render a Google Sign-In button as a plain anchor tag via st.markdown().
    No iframe involved — this lives in the main Streamlit page context and
    can navigate the tab freely.
    """
    popup_url = f"{_BACKEND_URL}/auth/google-popup?return_url={_STREAMLIT_URL}"

    # Inline styles keep us independent of Streamlit theme changes.
    st.markdown(f"""
<style>
  .g-signin-btn {{
    display: flex; align-items: center; justify-content: center; gap: 10px;
    width: 100%; padding: 12px 20px;
    background: #ffffff; color: #1f1f1f;
    border: 1px solid #dadce0; border-radius: 8px;
    font-size: 14px; font-weight: 500;
    text-decoration: none;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    box-shadow: 0 1px 3px rgba(0,0,0,0.10);
    transition: box-shadow 0.15s, background 0.15s;
    cursor: pointer;
    box-sizing: border-box;
  }}
  .g-signin-btn:hover {{
    background: #f8f9ff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.14);
    color: #1f1f1f;
    text-decoration: none;
  }}
</style>
<a href="{popup_url}" target="_top" class="g-signin-btn">
  <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
  </svg>
  {label}
</a>
""", unsafe_allow_html=True)
