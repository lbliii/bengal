"""
Unit tests for MenuOrchestrator.
"""

from pathlib import Path
from bengal.core.site import Site
from bengal.orchestration.menu import MenuOrchestrator

def test_auto_dev_menu_creation():
    """Test that Dev menu is automatically created when params exist."""
    config = {
        "params": {
            "repo_url": "https://github.com/example/repo",
            "api_url": "https://api.example.com",
            "cli_url": "https://cli.example.com",
        }
    }
    site = Site.for_testing(config=config)
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
    assert "API" in children_names
    assert "CLI" in children_names
    
    # Check URLs
    github_item = next(c for c in dev_item.children if c.name == "GitHub")
    assert github_item.url == "https://github.com/example/repo"

def test_no_dev_menu_when_no_params():
    """Test that Dev menu is NOT created when params are missing."""
    config = {
        "params": {}
    }
    site = Site.for_testing(config=config)
    orchestrator = MenuOrchestrator(site)
    
    orchestrator.build()
    
    if "main" in site.menu:
        main_menu = site.menu["main"]
        dev_item = next((item for item in main_menu if item.name == "Dev"), None)
        assert dev_item is None

def test_dev_menu_appends_to_existing_main():
    """Test that Dev menu is appended to existing main menu."""
    config = {
        "menu": {
            "main": [
                {"name": "Home", "url": "/", "weight": 10}
            ]
        },
        "params": {
            "repo_url": "https://github.com/example/repo"
        }
    }
    site = Site.for_testing(config=config)
    orchestrator = MenuOrchestrator(site)
    
    orchestrator.build()
    
    assert "main" in site.menu
    main_menu = site.menu["main"]
    
    # Should have Home and Dev
    names = {item.name for item in main_menu}
    assert "Home" in names
    assert "Dev" in names
    
    dev_item = next(item for item in main_menu if item.name == "Dev")
    assert len(dev_item.children) == 1
    assert dev_item.children[0].name == "GitHub"

def test_dev_menu_skipped_if_exists():
    """Test that we don't duplicate/overwrite if user manually defined Dev."""
    config = {
        "menu": {
            "main": [
                {"name": "Dev", "url": "/manual-dev", "identifier": "dev-manual", "weight": 50}
            ]
        },
        "params": {
            "repo_url": "https://github.com/example/repo"
        }
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
    config1 = {
        "params": {"repo_url": "https://github.com/repo1"}
    }
    site1 = Site.for_testing(config=config1)
    orch1 = MenuOrchestrator(site1)
    key1 = orch1._compute_menu_cache_key()
    
    config2 = {
        "params": {"repo_url": "https://github.com/repo2"}
    }
    site2 = Site.for_testing(config=config2)
    orch2 = MenuOrchestrator(site2)
    key2 = orch2._compute_menu_cache_key()
    
    assert key1 != key2

def test_dev_menu_preserves_auto_nav():
    """Test that injecting Dev menu preserves auto-discovered items."""
    from unittest.mock import MagicMock
    
    # Setup config with dev params but NO menu config (triggering auto mode)
    config = {
        "params": {
            "repo_url": "https://github.com/example/repo"
        }
    }
    site = Site.for_testing(config=config)
    
    # Mock sections for auto-discovery
    section1 = MagicMock()
    section1.path = site.root_path / "content" / "blog"
    section1.name = "blog"
    section1.url = "/blog/"
    section1.weight = 10
    # Ensure index_page attributes don't cause errors
    section1.index_page = None
    # Explicitly set title to None so it falls back to name, or set it to "Blog"
    # MagicMock creates attributes on access, so getattr(s, 'title') returns a Mock unless set
    del section1.title
    
    section2 = MagicMock()
    section2.path = site.root_path / "content" / "about"
    section2.name = "about"
    section2.url = "/about/"
    section2.weight = 20
    section2.index_page = None
    del section2.title
    
    site.sections = [section1, section2]
    
    orchestrator = MenuOrchestrator(site)
    orchestrator.build()
    
    main_menu = site.menu["main"]
    names = {item.name for item in main_menu}
    
    # Should contain auto-discovered sections AND Dev menu
    assert "Blog" in names  # Auto-discovered (capitalized from "blog")
    assert "About" in names # Auto-discovered
    assert "Dev" in names   # Injected
    
    dev_item = next(item for item in main_menu if item.name == "Dev")
    assert len(dev_item.children) == 1

