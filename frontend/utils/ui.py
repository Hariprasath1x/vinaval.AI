import streamlit as st

def render_sidebar():
    """Renders a common sidebar for the application pages."""
    
    st.markdown("""
        <style>
            /* Increase base text size globally to a standard medium */
            html {
                font-size: 110% !important; 
            }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        user = st.session_state.get("user", {})
        name = user.get("name") or user.get("email", "Student")
        
        st.markdown(f"👤 **Logged in as:**\n\n{name}")
        st.divider()
        
        st.page_link("pages/1_Dashboard.py", label="Dashboard", icon="📊")
        st.page_link("pages/2_Select_Exam.py", label="New Learning Space", icon="➕")
        st.page_link("pages/5_Smart_Notes.py", label="Smart Notes", icon="📓")

        current_space = st.session_state.get("current_space")
        if current_space:
            st.caption(f"Active: **{current_space.get('subject')}** ({current_space.get('exam_id')})")
            st.page_link("pages/3_Space.py", label="Active Space", icon="🚀")

        
        st.divider()
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state.clear()
            st.switch_page("app.py")
