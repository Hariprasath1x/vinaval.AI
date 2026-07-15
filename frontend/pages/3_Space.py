import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api import get_space

st.set_page_config(page_title="Learning Space", page_icon="📖", layout="wide")

if "token" not in st.session_state:
    st.warning("Please log in from the Home page first.")
    st.stop()

space_id = st.session_state.get("current_space_id")

if not space_id:
    st.warning("No space selected. Please select a space from the Dashboard.")
    st.stop()

with st.spinner("Loading space details..."):
    space = get_space(space_id)

if not space:
    st.error("Space not found.")
    st.stop()

st.title(f"Space: {space.get('title', 'Untitled')}")
st.caption(f"Exam: {space.get('exam_type', 'N/A')} | Status: {space.get('status', 'Active')}")

# Create tabs for different functionalities
tab_learn, tab_materials, tab_flashcards, tab_quiz, tab_reports = st.tabs([
    "🧠 Learn", "📚 Materials", "🃏 Flashcards", "📝 Exam Lab", "📈 Reports"
])

with tab_learn:
    st.header("Learn & Chat")
    st.write("Interact with your AI tutor based on the uploaded materials.")
    # Implement Chat UI
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    if prompt := st.chat_input("Ask a question about your study materials..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            st.markdown("I am your AI tutor. (Integration with backend RAG pending)")
        st.session_state.messages.append({"role": "assistant", "content": "I am your AI tutor. (Integration with backend RAG pending)"})

with tab_materials:
    st.header("Study Materials")
    st.write("Upload your PDFs and documents here to generate context for the AI.")
    uploaded_file = st.file_uploader("Upload a PDF document", type=["pdf"])
    if uploaded_file is not None:
        st.success("File uploaded! (Backend integration pending)")
    
    st.subheader("Existing Documents")
    documents = space.get("documents", [])
    if not documents:
        st.info("No documents uploaded yet.")
    else:
        for doc in documents:
            st.write(f"- {doc.get('filename')}")

with tab_flashcards:
    st.header("Flashcards")
    st.write("Review auto-generated flashcards from your study materials.")
    st.info("Flashcard generator coming soon.")

with tab_quiz:
    st.header("Exam Lab")
    st.write("Take mock quizzes based on your selected exam.")
    st.info("Quiz module coming soon.")

with tab_reports:
    st.header("Reports & Analytics")
    st.write("Track your progress.")
    st.info("Analytics coming soon.")
