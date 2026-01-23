"""Base page object for common test operations."""

from playwright.sync_api import Page


class BasePage:
    """Base page with common selectors and methods."""

    def __init__(self, page: Page):
        self.page = page

    def get_by_testid(self, testid: str):
        """Get element by data-testid attribute."""
        return self.page.locator(f'[data-testid="{testid}"]')

    def wait_for_testid(self, testid: str, timeout: float = 5000):
        """Wait for element with data-testid to be visible."""
        return self.get_by_testid(testid).wait_for(state="visible", timeout=timeout)

    def click_testid(self, testid: str):
        """Click element with data-testid."""
        self.get_by_testid(testid).click()

    def fill_testid(self, testid: str, value: str):
        """Fill input with data-testid."""
        self.get_by_testid(testid).fill(value)

    def is_visible(self, testid: str) -> bool:
        """Check if element with data-testid is visible."""
        return self.get_by_testid(testid).is_visible()
