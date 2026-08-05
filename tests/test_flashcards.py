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

    expect(page.get_by_role("heading", name="📖 Physics")).to_be_visible(timeout=20000)


def test_flashcards_flow(authenticated_page: Page):
    page = authenticated_page
    _navigate_to_space(page)

    # Go to Flashcards tab
    page.get_by_role("tab", name="🃏 Flashcards").click()

    # Generate flashcards for the first default topic (no need to change the selectbox)
    page.get_by_role("button", name="✨ Generate Flashcards").click()

    # Wait for success message — AI call can take up to 45s
    expect(page.get_by_text("✅ Generated")).to_be_visible(timeout=60000)

    # Verify the Leitner session UI is visible (front of first card)
    expect(page.get_by_text("Front")).to_be_visible()

    # Flip the card
    page.get_by_role("button", name="🔄 Flip Card").click()

    # Verify back is now visible
    expect(page.get_by_text("Back")).to_be_visible()

    # Mark card as known
    page.get_by_role("button", name="✅ Got it!").click()
