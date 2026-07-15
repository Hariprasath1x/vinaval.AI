import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api import get_spaces

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

if "token" not in st.session_state:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("Your Learning Dashboard")

with st.spinner("Loading your spaces..."):
    spaces = get_spaces()

if not spaces:
    st.info("You don't have any learning spaces yet. Go to 'Select Exam' to create one!")
else:
    st.write("### Your Active Spaces")
    
    # Create a grid layout
    cols = st.columns(3)
    for i, space in enumerate(spaces):
        with cols[i % 3]:
            with st.container(border=True):
                st.subheader(space.get("title", "Untitled Space"))
                st.write(f"**Exam Type:** {space.get('exam_type', 'N/A')}")
                st.write(f"**Status:** {space.get('status', 'Active')}")
                if st.button("Enter Space", key=f"enter_{space['id']}"):
                    st.session_state["current_space_id"] = space["id"]
                    st.switch_page("pages/3_Space.py")
