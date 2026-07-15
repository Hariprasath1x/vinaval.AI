import os
import requests
import streamlit as st
from typing import Dict, Any, List, Optional

# Base URL for the FastAPI backend
BASE_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

def get_headers() -> Dict[str, str]:
    """Returns headers with JWT token if available."""
    headers = {"Content-Type": "application/json"}
    token = st.session_state.get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def login(email: str) -> Optional[Dict[str, Any]]:
    """Mock login using email."""
    try:
        response = requests.post(f"{BASE_URL}/auth/mock", json={"email": email})
        response.raise_for_status()
        data = response.json()
        st.session_state["token"] = data["access_token"]
        st.session_state["user"] = data["user"]
        return data["user"]
    except requests.exceptions.RequestException as e:
        st.error(f"Login failed: {e}")
        return None

def get_spaces() -> List[Dict[str, Any]]:
    """Fetch user's learning spaces."""
    try:
        response = requests.get(f"{BASE_URL}/space/", headers=get_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch spaces: {e}")
        return []

def create_space(exam_type: str) -> Optional[Dict[str, Any]]:
    """Create a new learning space."""
    try:
        # Assuming we need to pass exam_type. Let's check backend schema later.
        response = requests.post(
            f"{BASE_URL}/space/", 
            json={"title": f"{exam_type} Prep Space", "exam_type": exam_type}, 
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to create space: {e}")
        return None

def get_space(space_id: str) -> Optional[Dict[str, Any]]:
    """Fetch details of a specific space."""
    try:
        response = requests.get(f"{BASE_URL}/space/{space_id}", headers=get_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch space details: {e}")
        return None
