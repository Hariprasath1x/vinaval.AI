import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.api import signup, login, login_with_firebase, forgot_password
from utils.firebase_auth import render_google_signin_button


st.set_page_config(
    page_title="Vinaval AI — Sign In",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Hide Streamlit chrome on the login page */
  #MainMenu, header, footer { visibility: hidden; }
  section[data-testid="stSidebar"] { display: none; }

  /* Page background */
  .stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }

  /* Hero card */
  .auth-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 20px;
    padding: 2.5rem 2rem 2rem;
    backdrop-filter: blur(12px);
    margin-top: 0.5rem;
  }

  /* Logo / brand text */
  .brand { text-align: center; margin-bottom: 0.25rem; }
  .brand-title {
    font-size: 2.2rem; font-weight: 800;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .brand-sub { color: #94a3b8; font-size: 0.9rem; margin-top: 0.15rem; }

  /* Divider */
  .or-divider {
    display: flex; align-items: center; gap: 10px;
    color: #64748b; font-size: 12px; margin: 1rem 0;
  }
  .or-divider::before, .or-divider::after {
    content: ''; flex: 1; height: 1px; background: rgba(255,255,255,0.1);
  }

  /* Tab styling */
  .stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.04);
    border-radius: 10px; padding: 4px; gap: 4px;
    border: 1px solid rgba(255,255,255,0.08);
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 8px; padding: 8px 16px; font-size: 13px;
    color: #94a3b8 !important;
  }
  .stTabs [aria-selected="true"] {
    background: rgba(167,139,250,0.18) !important;
    color: #a78bfa !important; font-weight: 600;
  }

  /* Input fields */
  input[type="text"], input[type="password"], input[type="email"] {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 8px !important; color: #f1f5f9 !important;
  }
  input:focus { border-color: #a78bfa !important; }
  label { color: #cbd5e1 !important; font-size: 13px !important; }

  /* Primary button */
  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    border: none !important; border-radius: 9px !important;
    font-weight: 600 !important; letter-spacing: 0.02em !important;
    padding: 0.65rem !important; font-size: 14px !important;
    transition: all 0.2s !important;
  }
  .stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(124,58,237,0.4) !important;
  }

  /* Secondary button */
  .stButton > button[kind="secondary"] {
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 9px !important; color: #94a3b8 !important;
    background: transparent !important;
  }

  /* Feature pills */
  .pill-row { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin:1.2rem 0 0.5rem; }
  .pill {
    background: rgba(167,139,250,0.12); border:1px solid rgba(167,139,250,0.25);
    color: #c4b5fd; border-radius:20px; padding:4px 12px; font-size:12px;
  }
</style>
""", unsafe_allow_html=True)


# ── Handle Firebase token redirect ───────────────────────────────────────────
# After Google sign-in the Firebase JS component sets ?firebase_token=<idToken>
# We detect it here, exchange with backend, then clean the URL.

params = st.query_params
firebase_token = params.get("firebase_token")

if firebase_token and "token" not in st.session_state:
    with st.spinner("🔐 Completing Google sign-in…"):
        user = login_with_firebase(firebase_token)
    if user:
        # Clean the token from the URL immediately
        st.query_params.clear()
        st.rerun()
    else:
        st.query_params.clear()

# ── Already logged in ────────────────────────────────────────────────────────
if "token" in st.session_state:
    user = st.session_state.get("user", {})
    name = user.get("name") or user.get("email", "Student")
    st.success(f"✅ Logged in as **{name}**")
    st.page_link("pages/1_Dashboard.py", label="📊 Go to Dashboard →")
    if st.button("🚪 Logout", type="secondary"):
        st.session_state.clear()
        st.rerun()
    st.stop()


# ── Hero / Brand ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="brand">
  <div class="brand-title">🎓 Vinaval AI</div>
  <div class="brand-sub">AI-Powered Learning Arena for NEET Aspirants</div>
  <div class="pill-row">
    <span class="pill">🧠 AI Tutor</span>
    <span class="pill">🃏 Flashcards</span>
    <span class="pill">📝 Exam Lab</span>
    <span class="pill">📊 Reports</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Auth Tabs ─────────────────────────────────────────────────────────────────
tab_login, tab_signup, tab_forgot = st.tabs(["🔑 Log In", "📝 Sign Up", "🔒 Forgot Password"])


# ──────────────────────────────────────────────────────────────────────────────
# TAB 1 — LOG IN
# ──────────────────────────────────────────────────────────────────────────────
with tab_login:
    st.markdown("#### Welcome back!")

    # ── Google Sign-In ────────────────────────────────────────────
    render_google_signin_button(label="Continue with Google")

    st.markdown('<div class="or-divider">or sign in with email</div>', unsafe_allow_html=True)

    # ── Email / Password ──────────────────────────────────────────
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input(
            "Email Address",
            placeholder="yourname@example.com",
            key="login_email",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Your password",
            key="login_password",
        )
        submit_login = st.form_submit_button(
            "🔑 Log In", type="primary", use_container_width=True
        )

    if submit_login:
        if not email or not password:
            st.error("Please enter both email and password.")
        else:
            with st.spinner("Logging in…"):
                user = login(email.strip(), password)
            if user:
                st.success(f"Welcome back, **{user.get('name', email)}**! 🎉")
                st.rerun()

    st.caption("Don't have an account? Use the **Sign Up** tab. · Forgot your password? Use **Forgot Password** tab.")


# ──────────────────────────────────────────────────────────────────────────────
# TAB 2 — SIGN UP
# ──────────────────────────────────────────────────────────────────────────────
with tab_signup:
    st.markdown("#### Create your free account")

    # ── Google Sign-In also works for sign-up ─────────────────────
    render_google_signin_button(label="Sign up with Google")

    st.markdown('<div class="or-divider">or create an account with email</div>', unsafe_allow_html=True)

    # ── Email / Password Sign-Up ──────────────────────────────────
    with st.form("signup_form", clear_on_submit=False):
        name = st.text_input(
            "Full Name",
            placeholder="e.g. Ravi Kumar",
            key="signup_name",
        )
        email_s = st.text_input(
            "Email Address",
            placeholder="yourname@example.com",
            key="signup_email",
        )
        password_s = st.text_input(
            "Password",
            type="password",
            placeholder="Minimum 6 characters",
            key="signup_password",
        )
        password_c = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Repeat your password",
            key="signup_confirm",
        )
        submit_signup = st.form_submit_button(
            "🚀 Create Account", type="primary", use_container_width=True
        )

    if submit_signup:
        if not name or not email_s or not password_s or not password_c:
            st.error("Please fill in all fields.")
        elif len(password_s) < 6:
            st.error("Password must be at least 6 characters.")
        elif password_s != password_c:
            st.error("Passwords do not match.")
        else:
            with st.spinner("Creating your account…"):
                user = signup(name.strip(), email_s.strip(), password_s)
            if user:
                st.success(f"Account created! Welcome, **{user.get('name')}**! 🎉")
                st.rerun()

    st.caption("Already have an account? Use the **Log In** tab above.")


# ──────────────────────────────────────────────────────────────────────────────
# TAB 3 — FORGOT PASSWORD
# ──────────────────────────────────────────────────────────────────────────────
with tab_forgot:
    st.markdown("#### Reset your password")
    st.markdown(
        "<p style='color:#94a3b8; font-size:13px;'>"
        "Enter the email you used to sign up. We'll send a reset link to your inbox. "
        "The link expires in 1 hour."
        "</p>",
        unsafe_allow_html=True,
    )

    with st.form("forgot_form", clear_on_submit=False):
        reset_email = st.text_input(
            "Email Address",
            placeholder="yourname@example.com",
            key="forgot_email",
        )
        submit_forgot = st.form_submit_button(
            "📧 Send Reset Link", type="primary", use_container_width=True
        )

    if submit_forgot:
        if not reset_email or "@" not in reset_email:
            st.error("Please enter a valid email address.")
        else:
            with st.spinner("Sending reset link…"):
                ok = forgot_password(reset_email.strip())
            if ok:
                st.success(
                    f"✅ Reset link sent to **{reset_email}**! "
                    "Check your inbox (and spam folder). "
                    "The link expires in 1 hour."
                )

    st.info(
        "🔵 **Signed up with Google?** Password reset is handled by your Google account — "
        "you don't need a separate password. Use **Continue with Google** on the Log In tab.",
        icon=None,
    )
