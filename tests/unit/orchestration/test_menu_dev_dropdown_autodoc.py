"""
Tests for Dev dropdown auto-registration in auto menu mode.

These tests exercise MenuOrchestrator's auto-menu path, which bundles dev assets
(GitHub + API + CLI) into a "Dev" dropdown when 2+ are present.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from bengal.core.section import Section
from bengal.orchestration.menu import MenuOrchestrator


def test_auto_menu_bundles_github_and_api_into_dev_dropdown() -> None:
    """
    When repo_url is set and an 'api' section exists, auto-menu should:
    - create a 'Dev' parent item
    - add 'GitHub' and 'API Reference' as children of Dev
    """
    site = MagicMock()
    site.config = {"menu": {}, "params": {"repo_url": "https://example.com/repo"}}
    site.menu = {}
    site.menu_localized = {}
    site.pages = []
    site._dev_menu_metadata = None

    api_section = Section.create_virtual(name="api", relative_url="/api/", title="API", metadata={})
    docs_section = Section.create_virtual(
        name="docs", relative_url="/docs/", title="Docs", metadata={}
    )
    site.sections = [api_section, docs_section]

    items = MenuOrchestrator(site)._build_auto_menu_with_dev_bundling()

    assert any(i.get("identifier") == "dev-auto" and i.get("name") == "Dev" for i in items)
    assert any(i.get("parent") == "dev-auto" and i.get("name") == "GitHub" for i in items)
    assert any(i.get("parent") == "dev-auto" and i.get("name") == "API Reference" for i in items)


def test_auto_menu_api_only_keeps_api_as_top_level_item() -> None:
    """
    If there is only one dev asset (API), we do not create a Dev dropdown.
    API should remain as a normal top-level nav entry.
    """
    site = MagicMock()
    site.config = {"menu": {}, "params": {}}
    site.menu = {}
    site.menu_localized = {}
    site.pages = []
    site._dev_menu_metadata = None

    api_section = Section.create_virtual(name="api", relative_url="/api/", title="API", metadata={})
    docs_section = Section.create_virtual(
        name="docs", relative_url="/docs/", title="Docs", metadata={}
    )
    site.sections = [api_section, docs_section]

    items = MenuOrchestrator(site)._build_auto_menu_with_dev_bundling()

    assert any(i.get("identifier") == "api" and i.get("name") == "API Reference" for i in items)
    assert not any(i.get("identifier") == "dev-auto" for i in items)


def test_auto_menu_cli_only_keeps_cli_as_top_level_item() -> None:
    """
    If there is only one dev asset (CLI), we do not create a Dev dropdown.
    CLI should remain as a normal top-level nav entry.
    """
    site = MagicMock()
    site.config = {"menu": {}, "params": {}}
    site.menu = {}
    site.menu_localized = {}
    site.pages = []
    site._dev_menu_metadata = None

    cli_section = Section.create_virtual(name="cli", relative_url="/cli/", title="CLI", metadata={})
    docs_section = Section.create_virtual(
        name="docs", relative_url="/docs/", title="Docs", metadata={}
    )
    site.sections = [cli_section, docs_section]

    items = MenuOrchestrator(site)._build_auto_menu_with_dev_bundling()

    assert any(i.get("identifier") == "cli" and i.get("name") == "bengal CLI" for i in items)
    assert not any(i.get("identifier") == "dev-auto" for i in items)
