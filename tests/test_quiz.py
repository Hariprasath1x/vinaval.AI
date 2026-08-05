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


def test_quiz_flow(authenticated_page: Page):
    page = authenticated_page
    _navigate_to_space(page)

    # Go to Exam Lab tab
    page.get_by_role("tab", name="📝 Exam Lab").click()

    # Generate a Practice Quiz (default settings — first topic in dropdown)
    page.get_by_role("button", name="🎯 Generate Quiz/Exam").click()

    # Wait for questions to appear — AI call can take up to 60s
    # The quiz section header contains "Quiz —"
    expect(page.locator("text=Quiz —")).to_be_visible(timeout=60000)

    # Answer ALL questions — each stRadio group has input[type='radio'] for each option
    # We need to select one answer per question before submitting
    radio_groups = page.locator("[data-testid='stRadio']")
    count = radio_groups.count()
    assert count > 0, "No quiz questions were rendered"

    for i in range(count):
        group = radio_groups.nth(i)
        # Use JS click to bypass Playwright's viewport constraint on Streamlit's radio widgets
        first_radio = group.locator("input[type='radio']").first
        first_radio.evaluate("el => el.click()")

    # Submit quiz
    page.get_by_role("button", name="📩 Submit Quiz").click()

    # Wait for results screen
    expect(page.get_by_text("🎉 Quiz Completed!")).to_be_visible(timeout=30000)
    expect(page.get_by_text("Detailed Results")).to_be_visible()
    expect(page.get_by_text("Score").first).to_be_visible()
