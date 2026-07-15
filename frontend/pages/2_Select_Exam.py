import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api import create_space

st.set_page_config(page_title="Select Exam", page_icon="🎯", layout="wide")

if "token" not in st.session_state:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("Select Your Path")
st.markdown("Choose the examination you are preparing for to create a dedicated learning space.")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.header("NEET")
        st.write("National Eligibility cum Entrance Test for medical aspirants.")
        if st.button("Create NEET Space"):
            with st.spinner("Setting up your NEET workspace..."):
                space = create_space("NEET")
                if space:
                    st.success("Space created successfully!")
                    st.session_state["current_space_id"] = space["id"]
                    st.switch_page("pages/3_Space.py")

with col2:
    with st.container(border=True):
        st.header("TNPSC")
        st.write("Tamil Nadu Public Service Commission exams for state services.")
        if st.button("Create TNPSC Space"):
            with st.spinner("Setting up your TNPSC workspace..."):
                space = create_space("TNPSC")
                if space:
                    st.success("Space created successfully!")
                    st.session_state["current_space_id"] = space["id"]
                    st.switch_page("pages/3_Space.py")
