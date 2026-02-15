"""
Tests for menu orchestration features in auto menu mode.

Tests:
- Dev dropdown auto-registration (bundles GitHub + API + CLI into "Dev" dropdown)
- menu.extra config (appending extra items to auto-generated menu)
"""

from __future__ import annotations

from unittest.mock import MagicMock

from bengal.core.section import Section
from bengal.orchestration.menu import MenuOrchestrator


def test_auto_menu_bundles_github_and_api_into_dev_dropdown() -> None:
    """
    When repo_url is set and an 'api' section exists, auto-menu should:
    - create a 'Dev' parent item
    - add 'GitHub' and section title (or fallback) as children of Dev

    """
    site = MagicMock()
    site.config = {"menu": {}, "params": {"repo_url": "https://example.com/repo"}}
    site.menu = {}
    site.menu_localized = {}
    site.pages = []
    site._dev_menu_metadata = None

    # Section with explicit title - this title should be used in the menu
    api_section = Section.create_virtual(name="api", relative_url="/api/", title="API", metadata={})
    docs_section = Section.create_virtual(
        name="docs", relative_url="/docs/", title="Docs", metadata={}
    )
    site.sections = [api_section, docs_section]

    items = MenuOrchestrator(site)._build_auto_menu_with_dev_bundling()

    assert any(i.get("identifier") == "dev-auto" and i.get("name") == "Dev" for i in items)
    assert any(i.get("parent") == "dev-auto" and i.get("name") == "GitHub" for i in items)
    # Uses section.title ("API") since it's explicitly set
    assert any(i.get("parent") == "dev-auto" and i.get("name") == "API" for i in items)


def test_auto_menu_api_only_no_dev_dropdown() -> None:
    """
    If there is only one dev asset (API), we do not create a Dev dropdown.

    Note: This tests _create_default_dev_bundle directly since the full
    _build_auto_menu_with_dev_bundling relies on get_auto_nav which needs
    real sections with paths.

    """
    site = MagicMock()
    site.config = {"menu": {}, "params": {}}
    site.menu = {}
    site.menu_localized = {}
    site.pages = []
    site._dev_menu_metadata = None

    # Section with explicit title
    api_section = Section.create_virtual(name="api", relative_url="/api/", title="API", metadata={})
    docs_section = Section.create_virtual(
        name="docs", relative_url="/docs/", title="Docs", metadata={}
    )
    site.sections = [api_section, docs_section]

    orch = MenuOrchestrator(site)

    # Get bundleable assets - should only have API (no GitHub since no repo_url)
    assets = orch._detect_bundleable_assets()
    assert "api" in assets
    assert "github" not in assets  # No repo_url in params
    assert len(assets) == 1  # Only API

    # Dev bundle should NOT be created with only 1 asset
    dev_bundle = orch._create_default_dev_bundle(assets)
    assert dev_bundle is None  # Needs 2+ assets for bundling


def test_auto_menu_cli_only_no_dev_dropdown() -> None:
    """
    If there is only one dev asset (CLI), we do not create a Dev dropdown.

    Note: This tests _create_default_dev_bundle directly since the full
    _build_auto_menu_with_dev_bundling relies on get_auto_nav which needs
    real sections with paths.

    """
    site = MagicMock()
    site.config = {"menu": {}, "params": {}}
    site.menu = {}
    site.menu_localized = {}
    site.pages = []
    site._dev_menu_metadata = None

    # Section with explicit title
    cli_section = Section.create_virtual(name="cli", relative_url="/cli/", title="CLI", metadata={})
    docs_section = Section.create_virtual(
        name="docs", relative_url="/docs/", title="Docs", metadata={}
    )
    site.sections = [cli_section, docs_section]

    orch = MenuOrchestrator(site)

    # Get bundleable assets - should only have CLI (no GitHub since no repo_url)
    assets = orch._detect_bundleable_assets()
    assert "cli" in assets
    assert "github" not in assets  # No repo_url in params
    assert len(assets) == 1  # Only CLI

    # Dev bundle should NOT be created with only 1 asset
    dev_bundle = orch._create_default_dev_bundle(assets)
    assert dev_bundle is None  # Needs 2+ assets for bundling


# =============================================================================
# menu.extra tests - Appending items to auto-generated menu
# =============================================================================


def test_menu_extra_appends_items_to_auto_menu() -> None:
    """
    menu.extra config should append items to the auto-generated menu.

    This allows users to add one-off links (like forums) without
    replacing the entire auto-discovered menu.
    """
    site = MagicMock()
    site.config = {
        "menu": {
            "extra": [
                {"name": "Forum", "url": "https://forum.example.com/", "weight": 100},
                {"name": "Discord", "url": "https://discord.gg/example", "weight": 101},
            ]
        },
        "params": {},
    }
    site.menu = {}
    site.menu_localized = {}
    site.pages = []
    site._dev_menu_metadata = None

    # Only have a docs section (no dev assets)
    docs_section = Section.create_virtual(
        name="docs", relative_url="/docs/", title="Docs", metadata={}
    )
    site.sections = [docs_section]

    items = MenuOrchestrator(site)._build_auto_menu_with_dev_bundling()

    # Extra items should be appended
    assert any(
        i.get("name") == "Forum" and i.get("url") == "https://forum.example.com/" for i in items
    )
    assert any(
        i.get("name") == "Discord" and i.get("url") == "https://discord.gg/example" for i in items
    )


def test_menu_extra_deduplicates_by_url() -> None:
    """
    menu.extra items with duplicate URLs should be skipped.
    """
    site = MagicMock()
    site.config = {
        "menu": {
            "extra": [
                {"name": "Forum", "url": "https://forum.example.com/", "weight": 100},
                # Duplicate URL
                {"name": "Forum Copy", "url": "https://forum.example.com/", "weight": 101},
            ]
        },
        "params": {},
    }
    site.menu = {}
    site.menu_localized = {}
    site.pages = []
    site._dev_menu_metadata = None
    site.sections = []

    items = MenuOrchestrator(site)._build_auto_menu_with_dev_bundling()

    # Only one Forum item should exist (not the duplicate)
    forum_items = [i for i in items if "forum" in i.get("url", "").lower()]
    assert len(forum_items) == 1
    assert forum_items[0]["name"] == "Forum"


def test_menu_extra_requires_name_and_url() -> None:
    """
    menu.extra items missing name or url should be skipped.
    """
    site = MagicMock()
    site.config = {
        "menu": {
            "extra": [
                {"name": "Valid", "url": "https://example.com/"},  # Valid
                {"name": "Missing URL"},  # Invalid - no url
                {"url": "https://example.com/no-name"},  # Invalid - no name
                "not a dict",  # Invalid - not a dict
            ]
        },
        "params": {},
    }
    site.menu = {}
    site.menu_localized = {}
    site.pages = []
    site._dev_menu_metadata = None
    site.sections = []

    items = MenuOrchestrator(site)._build_auto_menu_with_dev_bundling()

    # Only the valid item should be added
    assert len(items) == 1
    assert items[0]["name"] == "Valid"


def test_add_data_children_produces_absolute_urls() -> None:
    """
    _add_data_children builds item URLs with leading slash.

    When section has _path="/tracks/", track items get url="/tracks/content-mastery/"
    (absolute). Ensures sidebar/nav links work regardless of current page.
    """
    site = MagicMock()
    site.data = MagicMock()
    site.data.tracks = {
        "content-mastery": {"title": "Content Mastery", "items": []},
        "getting-started": {"title": "Getting Started", "items": []},
    }

    section = MagicMock()
    section.name = "tracks"
    section._path = "/tracks/"

    menu_items: list[dict] = []
    seen_identifiers: set[str] = set()
    seen_urls: set[str] = set()
    seen_names: set[str] = set()

    orch = MenuOrchestrator(site)
    orch._add_data_children(
        section, "tracks-parent", "tracks", menu_items, seen_identifiers, seen_urls, seen_names
    )

    assert len(menu_items) == 2
    urls = [i["url"] for i in menu_items]
    assert "/tracks/content-mastery/" in urls
    assert "/tracks/getting-started/" in urls
    assert all(u.startswith("/") for u in urls)
