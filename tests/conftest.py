import pytest
import string
import random

@pytest.fixture(scope="session")
def base_url():
    """Return the base URL of the Streamlit application."""
    return "http://localhost:8501"

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Set default viewport and settings for all tests."""
    return {
        **browser_context_args,
        "viewport": {
            "width": 1280,
            "height": 720,
        },
        "ignore_https_errors": True,
    }

@pytest.fixture
def generate_random_user():
    """Generates random user credentials for testing."""
    def _generate():
        letters = string.ascii_lowercase
        username = ''.join(random.choice(letters) for i in range(10))
        email = f"{username}@example.com"
        password = "TestPassword123!"
        name = f"Test User {username.capitalize()}"
        return {"name": name, "email": email, "password": password}
    return _generate

@pytest.fixture
def authenticated_page(page, base_url, generate_random_user):
    """Returns a page that is already logged in with a fresh random user."""
    user = generate_random_user()
    page.goto(base_url)
    
    # Wait for the app to load
    page.locator(".brand-title").wait_for(state="visible", timeout=20000)
    
    # Switch to Sign Up tab
    page.get_by_role("tab", name="📝 Sign Up").click()
    
    # Fill in the Sign Up form - use force=True in case Streamlit briefly disables the form
    page.get_by_placeholder("e.g. Ravi Kumar").fill(user["name"], force=True)
    page.get_by_label("Email Address").nth(1).fill(user["email"], force=True)
    page.get_by_placeholder("Minimum 6 characters").fill(user["password"], force=True)
    page.get_by_placeholder("Repeat your password").fill(user["password"], force=True)
    
    # Submit Sign Up
    page.get_by_role("button", name="🚀 Create Account").click()
    
    # Verify successful login — wait up to 40s for backend signup + Streamlit rerun
    page.get_by_text(f"Logged in as {user['name']}").wait_for(state="visible", timeout=40000)
    
    return page
