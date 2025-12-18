"""
Unit tests for MenuOrchestrator.
"""

from unittest.mock import MagicMock

from bengal.core.site import Site
from bengal.orchestration.menu import MenuOrchestrator


def test_auto_dev_menu_creation():
    """Test that Dev menu is automatically created when 2+ dev assets exist."""
    config = {
        "params": {
            "repo_url": "https://github.com/example/repo",
        }
    }
    site = Site.for_testing(config=config)

    # Create api and cli sections (dev assets)
    api_section = MagicMock()
    api_section.path = site.root_path / "content" / "api"
    api_section.name = "api"
    api_section.url = "/api/"
    api_section.index_page = None

    cli_section = MagicMock()
    cli_section.path = site.root_path / "content" / "cli"
    cli_section.name = "cli"
    cli_section.url = "/cli/"
    cli_section.index_page = None

    site.sections = [api_section, cli_section]

    orchestrator = MenuOrchestrator(site)
    orchestrator.build()

    assert "main" in site.menu
    main_menu = site.menu["main"]

    # Find "Dev" item
    dev_item = next((item for item in main_menu if item.name == "Dev"), None)
    assert dev_item is not None
    assert len(dev_item.children) == 3

    children_names = {c.name for c in dev_item.children}
    assert "GitHub" in children_names
    assert "API Reference" in children_names
    assert "bengal CLI" in children_names

    # Check URLs
    github_item = next(c for c in dev_item.children if c.name == "GitHub")
    assert github_item.url == "https://github.com/example/repo"


def test_no_dev_menu_when_less_than_two_assets():
    """Test that Dev menu is NOT created when less than 2 dev assets exist."""
    config = {"params": {"repo_url": "https://github.com/example/repo"}}
    site = Site.for_testing(config=config)
    # No api/cli sections, only GitHub - need 2+ assets
    site.sections = []

    orchestrator = MenuOrchestrator(site)
    orchestrator.build()

    if "main" in site.menu:
        main_menu = site.menu["main"]
        dev_item = next((item for item in main_menu if item.name == "Dev"), None)
        assert dev_item is None


def test_dev_menu_not_injected_when_manual_menu_exists():
    """Test that Dev menu is NOT auto-injected when manual menu exists."""
    config = {
        "menu": {"main": [{"name": "Home", "url": "/", "weight": 10}]},
        "params": {"repo_url": "https://github.com/example/repo"},
    }
    site = Site.for_testing(config=config)

    # Create api and cli sections (would trigger Dev menu in auto mode)
    api_section = MagicMock()
    api_section.path = site.root_path / "content" / "api"
    api_section.name = "api"
    api_section.url = "/api/"
    api_section.index_page = None

    cli_section = MagicMock()
    cli_section.path = site.root_path / "content" / "cli"
    cli_section.name = "cli"
    cli_section.url = "/cli/"
    cli_section.index_page = None

    site.sections = [api_section, cli_section]

    orchestrator = MenuOrchestrator(site)
    orchestrator.build()

    assert "main" in site.menu
    main_menu = site.menu["main"]

    # Should have Home but NOT Dev (manual menu takes precedence)
    names = {item.name for item in main_menu}
    assert "Home" in names
    assert "Dev" not in names


def test_dev_menu_skipped_if_exists():
    """Test that we don't duplicate/overwrite if user manually defined Dev."""
    config = {
        "menu": {
            "main": [
                {"name": "Dev", "url": "/manual-dev", "identifier": "dev-manual", "weight": 50}
            ]
        },
        "params": {"repo_url": "https://github.com/example/repo"},
    }
    site = Site.for_testing(config=config)
    orchestrator = MenuOrchestrator(site)

    orchestrator.build()

    main_menu = site.menu["main"]
    dev_item = next(item for item in main_menu if item.name == "Dev")

    # Should be the manual one
    assert dev_item.identifier == "dev-manual"
    assert dev_item.url == "/manual-dev"

    # Should NOT have auto-added children (assuming user handles it manually)
    assert len(dev_item.children) == 0


def test_menu_cache_key_includes_params():
    """Test that cache key changes when dev params change."""
    config1 = {"params": {"repo_url": "https://github.com/repo1"}}
    site1 = Site.for_testing(config=config1)
    orch1 = MenuOrchestrator(site1)
    key1 = orch1._compute_menu_cache_key()

    config2 = {"params": {"repo_url": "https://github.com/repo2"}}
    site2 = Site.for_testing(config=config2)
    orch2 = MenuOrchestrator(site2)
    key2 = orch2._compute_menu_cache_key()

    assert key1 != key2


def test_dev_menu_preserves_auto_nav():
    """Test that injecting Dev menu preserves auto-discovered items and excludes dev sections."""
    # Setup config with dev params but NO menu config (triggering auto mode)
    config = {"params": {"repo_url": "https://github.com/example/repo"}}
    site = Site.for_testing(config=config)

    # Mock sections for auto-discovery
    # Note: nav_title must be explicitly set to None so _get_nav_title falls through to name
    blog_section = MagicMock()
    blog_section.path = site.root_path / "content" / "blog"
    blog_section.name = "blog"
    blog_section.url = "/blog/"
    blog_section.weight = 10
    blog_section.index_page = None
    blog_section.parent = None
    blog_section.subsections = []
    blog_section.nav_title = None
    del blog_section.title

    about_section = MagicMock()
    about_section.path = site.root_path / "content" / "about"
    about_section.name = "about"
    about_section.url = "/about/"
    about_section.weight = 20
    about_section.index_page = None
    about_section.parent = None
    about_section.subsections = []
    about_section.nav_title = None
    del about_section.title

    # Dev sections (should be bundled, not shown separately)
    api_section = MagicMock()
    api_section.path = site.root_path / "content" / "api"
    api_section.name = "api"
    api_section.url = "/api/"
    api_section.index_page = None
    api_section.parent = None
    api_section.subsections = []
    api_section.nav_title = None

    cli_section = MagicMock()
    cli_section.path = site.root_path / "content" / "cli"
    cli_section.name = "cli"
    cli_section.url = "/cli/"
    cli_section.index_page = None
    cli_section.parent = None
    cli_section.subsections = []
    cli_section.nav_title = None

    site.sections = [blog_section, about_section, api_section, cli_section]

    orchestrator = MenuOrchestrator(site)
    orchestrator.build()

    main_menu = site.menu["main"]
    names = {item.name for item in main_menu}

    # Should contain auto-discovered sections (blog, about) AND Dev menu
    # But NOT api/cli separately (they're in Dev dropdown)
    assert "Blog" in names  # Auto-discovered (capitalized from "blog")
    assert "About" in names  # Auto-discovered
    assert "Dev" in names  # Injected

    # Dev sections should NOT appear separately
    assert "Api" not in names
    assert "Cli" not in names

    dev_item = next(item for item in main_menu if item.name == "Dev")
    # Should have GitHub, API Reference, and bengal CLI
    assert len(dev_item.children) == 3
    children_names = {c.name for c in dev_item.children}
    assert "GitHub" in children_names
    assert "API Reference" in children_names
    assert "bengal CLI" in children_names


def test_auto_menu_includes_nested_sections():
    """Test that auto menu includes nested sections (not just top-level)."""
    config = {}
    site = Site.for_testing(config=config)

    # Create parent section
    # Note: nav_title must be explicitly set to None so _get_nav_title falls through to name
    docs_section = MagicMock()
    docs_section.path = site.root_path / "content" / "docs"
    docs_section.name = "docs"
    docs_section.url = "/docs/"
    docs_section.relative_url = "/docs/"
    docs_section.weight = 10
    docs_section.index_page = None
    docs_section.parent = None
    docs_section.subsections = []
    docs_section.nav_title = None
    del docs_section.title

    # Create nested subsection
    guides_section = MagicMock()
    guides_section.path = site.root_path / "content" / "docs" / "guides"
    guides_section.name = "guides"
    guides_section.url = "/docs/guides/"
    guides_section.relative_url = "/docs/guides/"
    guides_section.weight = 20
    guides_section.index_page = None
    guides_section.parent = docs_section
    guides_section.subsections = []
    guides_section.nav_title = None
    del guides_section.title

    # Link parent and child
    docs_section.subsections = [guides_section]

    # Create another top-level section
    blog_section = MagicMock()
    blog_section.path = site.root_path / "content" / "blog"
    blog_section.name = "blog"
    blog_section.url = "/blog/"
    blog_section.relative_url = "/blog/"
    blog_section.weight = 30
    blog_section.index_page = None
    blog_section.parent = None
    blog_section.subsections = []
    blog_section.nav_title = None
    del blog_section.title

    site.sections = [docs_section, guides_section, blog_section]

    orchestrator = MenuOrchestrator(site)
    orchestrator.build()

    assert "main" in site.menu
    main_menu = site.menu["main"]

    # Should have both top-level sections
    names = {item.name for item in main_menu}
    assert "Docs" in names
    assert "Blog" in names

    # Docs should have Guides as a child
    docs_item = next(item for item in main_menu if item.name == "Docs")
    assert len(docs_item.children) == 1
    assert docs_item.children[0].name == "Guides"
    assert docs_item.children[0].url == "/docs/guides/"
    assert docs_item.children[0].parent == "docs"
