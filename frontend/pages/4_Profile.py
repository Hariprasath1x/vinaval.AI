import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api import update_profile, change_password

st.set_page_config(page_title="My Profile", page_icon="👤", layout="centered")

if "token" not in st.session_state:
    st.warning("⚠️ Please log in from the Home page first.")
    st.page_link("app.py", label="Go to Login →")
    st.stop()

user = st.session_state.get("user", {})

st.title("👤 My Profile")
st.markdown("Manage your personal details and account security.")
st.divider()

# ── Profile Header ────────────────────────────────────────────────────────────

col_av, col_info = st.columns([1, 4])
with col_av:
    # Use avatar_url if available, else initial
    avatar_url = user.get("avatar_url")
    if avatar_url:
        st.image(avatar_url, width=100)
    else:
        # Fallback to an initial-based avatar image placeholder
        initial = user.get("name", "U")[0].upper()
        st.markdown(
            f"""
            <div style="width: 100px; height: 100px; border-radius: 50%; 
                        background: linear-gradient(135deg, #a78bfa, #60a5fa);
                        display: flex; align-items: center; justify-content: center;
                        font-size: 40px; font-weight: bold; color: white;">
                {initial}
            </div>
            """, 
            unsafe_allow_html=True
        )

with col_info:
    st.subheader(user.get("name", "Student"))
    st.caption(f"📧 {user.get('email', 'No email')}")
    st.caption(f"🗓️ Joined: {user.get('created_at', '')[:10]}")

st.divider()

# ── Update Profile ────────────────────────────────────────────────────────────

st.subheader("Edit Profile")
with st.form("profile_form"):
    new_name = st.text_input("Display Name", value=user.get("name", ""))
    submit_profile = st.form_submit_button("💾 Save Name", type="primary")

    if submit_profile:
        if not new_name.strip():
            st.error("Name cannot be empty.")
        else:
            with st.spinner("Saving..."):
                updated_user = update_profile(new_name)
            if updated_user:
                st.success("✅ Profile updated successfully!")
                st.rerun()

st.divider()

# ── Change Password ───────────────────────────────────────────────────────────

st.subheader("Security")

if "google_id" in user and user["google_id"]:
    st.info("ℹ️ You signed in with Google. Password changes are managed through your Google account.")
else:
    with st.form("password_form"):
        curr_pw = st.text_input("Current Password", type="password")
        new_pw = st.text_input("New Password", type="password")
        confirm_pw = st.text_input("Confirm New Password", type="password")
        
        submit_pw = st.form_submit_button("🔒 Change Password", type="primary")

        if submit_pw:
            if not curr_pw:
                st.error("Please enter your current password.")
            elif len(new_pw) < 6:
                st.error("New password must be at least 6 characters.")
            elif new_pw != confirm_pw:
                st.error("New passwords do not match.")
            else:
                with st.spinner("Changing password..."):
                    if change_password(curr_pw, new_pw):
                        st.success("✅ Password changed successfully!")
                    else:
                        st.error("❌ Failed to change password. Please check your current password.")
