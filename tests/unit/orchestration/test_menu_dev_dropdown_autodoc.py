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
