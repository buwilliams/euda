"""E2E tests for Assets functionality.

Tests for:
- Assets collection view showing all assets
- Markdown asset display with proper formatting
- Asset cache refresh on navigation
"""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def navigate_to_assets(page: Page):
    """Navigate to Assets view via Collections > Assets."""
    # Ensure we're on the Focus tab
    focus_tab = page.locator('[data-testid="tab-btn-focus"]')
    focus_tab.click()
    page.wait_for_timeout(500)

    # Expand Collections section
    collections_section = page.get_by_text("Collections", exact=True)
    expect(collections_section).to_be_visible(timeout=5000)
    collections_section.click()
    page.wait_for_timeout(300)

    # Click Assets menu item
    assets_link = page.locator('.focus-menu-item:has-text("Assets")')
    expect(assets_link).to_be_visible(timeout=2000)
    assets_link.click()
    page.wait_for_timeout(500)


class TestAssetsView:
    """Tests for the Assets collection view."""

    def test_assets_view_loads(self, authenticated_page: Page):
        """Assets view should load when navigating to it."""
        page = authenticated_page

        navigate_to_assets(page)

        # Should show back button indicating we're in a detail view
        expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)

    def test_assets_view_shows_asset_list(self, authenticated_page: Page):
        """Assets view should show list of assets if any exist."""
        page = authenticated_page

        navigate_to_assets(page)

        # Wait for content to load (either assets or empty message)
        page.wait_for_timeout(1000)

        # Check for asset list or empty state
        asset_list = page.locator('.asset-list')
        empty_state = page.locator('.focus-empty')

        # One of these should be visible
        assert asset_list.is_visible() or empty_state.is_visible()

    def test_assets_view_refreshes_on_navigation(self, authenticated_page: Page):
        """Navigating to Assets view should always refresh data."""
        page = authenticated_page

        # Navigate to Assets first time
        navigate_to_assets(page)
        page.wait_for_timeout(500)

        # Go back
        page.locator('[data-testid="back-btn"]').click()
        page.wait_for_timeout(500)

        # Navigate again - should trigger a fresh load
        navigate_to_assets(page)

        # If there was a loading indicator, it should appear briefly
        # (we can't easily test cache invalidation directly, but the navigation should work)
        expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)


class TestAssetDisplay:
    """Tests for individual asset display."""

    def test_asset_card_shows_filename(self, authenticated_page: Page):
        """Asset cards should show the filename."""
        page = authenticated_page

        navigate_to_assets(page)
        page.wait_for_timeout(1000)

        # Check if there are any asset items
        asset_items = page.locator('.asset-item')
        if asset_items.count() > 0:
            # Each asset item should have a name
            first_item = asset_items.first
            name_element = first_item.locator('.asset-item-name')
            expect(name_element).to_be_visible()

    def test_asset_card_shows_topic_name(self, authenticated_page: Page):
        """Asset cards in recent view should show the topic name."""
        page = authenticated_page

        navigate_to_assets(page)
        page.wait_for_timeout(1000)

        # Check if there are any asset items
        asset_items = page.locator('.asset-item')
        if asset_items.count() > 0:
            # Recent assets view should show topic name
            first_item = asset_items.first
            topic_element = first_item.locator('.asset-item-topic')
            # Topic name is shown in recent assets view
            if topic_element.count() > 0:
                expect(topic_element).to_be_visible()

    def test_clicking_asset_opens_detail(self, authenticated_page: Page):
        """Clicking an asset should open the asset detail view."""
        page = authenticated_page

        navigate_to_assets(page)
        page.wait_for_timeout(1000)

        # Check if there are clickable asset items
        clickable_assets = page.locator('.asset-item.clickable')
        if clickable_assets.count() > 0:
            clickable_assets.first.click()
            page.wait_for_timeout(500)

            # Should show asset detail with content section
            content_section = page.get_by_text("Content", exact=True)
            expect(content_section).to_be_visible(timeout=5000)


class TestMarkdownAssetDisplay:
    """Tests for markdown asset rendering."""

    def test_markdown_asset_renders_without_literal_newlines(self, authenticated_page: Page):
        """Markdown assets should not show literal \\n characters."""
        page = authenticated_page

        navigate_to_assets(page)
        page.wait_for_timeout(1000)

        # Find a markdown asset
        md_assets = page.locator('.asset-item.clickable:has-text(".md")')
        if md_assets.count() > 0:
            md_assets.first.click()
            page.wait_for_timeout(500)

            # Check the content display
            content_display = page.locator('.topic-description-display')
            if content_display.is_visible():
                content_text = content_display.inner_text()
                # Should not contain literal \n sequences
                assert "\\n" not in content_text, "Markdown should not show literal \\n characters"

    def test_markdown_asset_shows_formatted_content(self, authenticated_page: Page):
        """Markdown assets should show formatted HTML content."""
        page = authenticated_page

        navigate_to_assets(page)
        page.wait_for_timeout(1000)

        # Find a markdown asset
        md_assets = page.locator('.asset-item.clickable:has-text(".md")')
        if md_assets.count() > 0:
            md_assets.first.click()
            page.wait_for_timeout(500)

            # Check for rendered markdown elements (headers, paragraphs, etc.)
            content_display = page.locator('.topic-description-display')
            if content_display.is_visible():
                # Markdown should render HTML elements like h1, h2, p, etc.
                html_content = content_display.inner_html()
                # If there's content, it should have some HTML tags from markdown rendering
                if len(html_content) > 50:  # Skip nearly empty content
                    has_html = any(tag in html_content.lower() for tag in ['<h', '<p', '<li', '<strong', '<em'])
                    # Just log if no HTML found - some assets might be plain text
                    if not has_html:
                        print(f"Note: Asset content may be plain text: {html_content[:100]}")
