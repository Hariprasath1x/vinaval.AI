from playwright.sync_api import Page, expect

def _navigate_to_space(page: Page):
    """Helper: navigate from logged-in home page to a NEET Physics space."""
    page.get_by_text("📊 Go to Dashboard →").click()

    if page.get_by_text("You don't have any Learning Spaces yet.").is_visible(timeout=5000):
        page.get_by_text("➕ Create Your First Space →").click()
    else:
        page.get_by_text("➕ Add a New Learning Space").click()

    page.get_by_role("button", name="🩺 NEET Medical Entrance").click()
    page.get_by_role("button", name="⚛️ Physics").click()
    page.get_by_role("button", name="🚀 Open Learning Space").click()

    # Wait for the Space page to load — heading is "📖 Physics"
    expect(page.get_by_role("heading", name="📖 Physics")).to_be_visible(timeout=20000)


def test_chat_flow(authenticated_page: Page):
    page = authenticated_page
    _navigate_to_space(page)

    # Learn tab is open by default — find the chat input
    chat_input = page.get_by_placeholder("Ask your AI tutor...")
    chat_input.fill("What is Newton's first law?")
    page.keyboard.press("Enter")

    # Wait for the user message to appear
    expect(page.get_by_text("What is Newton's first law?")).to_be_visible(timeout=10000)

    # Wait for the AI to start and finish responding — look for "Newton" in any casing
    expect(page.locator("text=/Newton/")).to_be_visible(timeout=60000)
