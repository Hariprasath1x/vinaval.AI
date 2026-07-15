import streamlit as st
import sys
import os

# Add the root directory to path to allow absolute imports within the frontend folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.api import login

st.set_page_config(
    page_title="Vinaval AI",
    page_icon="🎓",
    layout="wide",
)

def main():
    st.title("Welcome to Vinaval AI 🎓")
    st.markdown("### AI-Powered Learning Arena for Tamil Nadu Aspirants")

    if "token" not in st.session_state:
        st.info("Please log in to continue.")
        with st.form("login_form"):
            email = st.text_input("Email (Mock Login)")
            submit = st.form_submit_button("Log In")
            if submit and email:
                user = login(email)
                if user:
                    st.success(f"Welcome, {user.get('name', email)}!")
                    st.rerun()
    else:
        st.success(f"Logged in as {st.session_state.user.get('name')}")
        st.write("Navigate to the Dashboard using the sidebar.")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()
