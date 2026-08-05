from playwright.sync_api import Page, expect

def test_signup_and_login_flow(page: Page, base_url: str, generate_random_user):
    user = generate_random_user()
    
    # Navigate to app
    page.goto(base_url)
    
    # Wait for the app to load
    expect(page.locator(".brand-title")).to_be_visible(timeout=15000)
    
    # Switch to Sign Up tab
    page.get_by_role("tab", name="📝 Sign Up").click()
    
    # Fill in the Sign Up form
    # Streamlit inputs can be found by their placeholder or label
    page.get_by_placeholder("e.g. Ravi Kumar").fill(user["name"])
    page.get_by_label("Email Address").nth(1).fill(user["email"]) # Second email input is in Signup
    page.get_by_placeholder("Minimum 6 characters").fill(user["password"])
    page.get_by_placeholder("Repeat your password").fill(user["password"])
    
    # Submit Sign Up
    page.get_by_role("button", name="🚀 Create Account").click()
    
    # Verify successful login/redirect — backend signup can take up to 30s on first call
    expect(page.get_by_text(f"Logged in as {user['name']}")).to_be_visible(timeout=40000)
    
    # Logout
    page.get_by_role("button", name="🚪 Logout").click()
    
    # Verify logout success
    expect(page.get_by_role("tab", name="🔑 Log In")).to_be_visible(timeout=15000)
    
    # Test Login with the created account
    page.get_by_label("Email Address").nth(0).fill(user["email"])
    page.get_by_placeholder("Your password").nth(0).fill(user["password"])
    page.get_by_role("button", name="🔑 Log In").click()
    
    # Verify successful login
    expect(page.get_by_text(f"Logged in as {user['name']}")).to_be_visible(timeout=15000)
