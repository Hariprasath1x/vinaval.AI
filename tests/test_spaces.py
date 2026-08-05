from playwright.sync_api import Page, expect


def test_create_and_view_space(authenticated_page: Page):
    page = authenticated_page

    # Go to Dashboard
    page.get_by_text("📊 Go to Dashboard →").click()

    # Create a new space (or add one if spaces already exist)
    if page.get_by_text("You don't have any Learning Spaces yet.").is_visible(timeout=5000):
        page.get_by_text("➕ Create Your First Space →").click()
    else:
        page.get_by_text("➕ Add a New Learning Space").click()

    # We are now on the Select Exam page
    expect(page.get_by_text("📚 Choose Your Exam & Subject")).to_be_visible()

    # Select NEET
    page.get_by_role("button", name="🩺 NEET Medical Entrance").click()

    # Select Physics
    page.get_by_role("button", name="⚛️ Physics").click()

    # Click "Open Learning Space"
    page.get_by_role("button", name="🚀 Open Learning Space").click()

    # Streamlit immediately does st.switch_page, so skip the transient success message.
    # Just wait for the Space page heading to appear.
    expect(page.get_by_role("heading", name="📖 Physics")).to_be_visible(timeout=20000)

    # Verify all 6 tabs are rendered
    expect(page.get_by_role("tab", name="🧠 Learn (AI Chat)")).to_be_visible()
    expect(page.get_by_role("tab", name="📚 Materials")).to_be_visible()
    expect(page.get_by_role("tab", name="🃏 Flashcards")).to_be_visible()
    expect(page.get_by_role("tab", name="📝 Exam Lab")).to_be_visible()
    expect(page.get_by_role("tab", name="📈 Reports")).to_be_visible()
    expect(page.get_by_role("tab", name="📓 My Notes")).to_be_visible()
