from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.config.loader import ConfigLoader
from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine


@pytest.fixture
def temp_site_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        site_dir = Path(tmp_dir) / "site"
        site_dir.mkdir()
        (site_dir / "bengal.toml").write_text(
            """
[site]
title = "Test Site"
baseurl = ""
            """
        )
        yield site_dir


@pytest.fixture
def mock_site(temp_site_dir):
    config_loader = ConfigLoader(temp_site_dir)
    config = config_loader.load()
    # The template expects config.site.favicon structure
    # Wrap the flat config in a "site" key for template compatibility
    # Include favicon: None to satisfy Kida strict mode
    site_config = config.copy()
    site_config["favicon"] = None  # Explicit None for strict mode
    wrapped_config = {"site": site_config}
    site = Site(root_path=temp_site_dir, config=wrapped_config)
    # Point to default theme for template loading
    bengal_root = Path(__file__).parent.parent.parent.parent / "bengal"
    site.theme_dir = bengal_root / "themes" / "default"
    site.theme = "default"
    return site


def _create_mock_page(**kwargs):
    """Create a Mock page with proper defaults for template rendering."""
    defaults = {
        "title": "Test Page",
        "url": "/",
        "href": "/",
        "_path": "/",
        "kind": "page",
        "keywords": [],
        "tags": [],
        "lang": None,  # Prevent Mock from being stringified in lang=""
        "content": None,
        "date": None,
        "output_path": None,
        "metadata": {},
    }
    defaults.update(kwargs)
    return Mock(**defaults)


def test_default_favicon_inclusion(mock_site):
    # Arrange: No favicon in config, use default theme
    engine = TemplateEngine(mock_site)

    # Mock a simple page context with proper defaults
    context = {
        "site": mock_site,
        "page": _create_mock_page(),
        "meta_desc": "Test description",
    }

    # Act: Render base.html
    html_output = engine.render("base.html", context)

    # Assert: Default favicon links are present
    assert '<link rel="icon" type="image/x-icon" href="' in html_output
    assert "favicon.ico" in html_output
    assert "favicon-16x16.png" in html_output
    assert "favicon-32x32.png" in html_output


def test_custom_favicon_override(mock_site):
    # Arrange: Custom favicon in config
    # Modify config after site creation
    if "site" not in mock_site.config:
        mock_site.config["site"] = {}
    mock_site.config["site"]["favicon"] = "/assets/custom-favicon.png"

    # Recreate engine with updated config
    engine = TemplateEngine(mock_site)

    context = {
        "site": mock_site,
        "page": _create_mock_page(),
        "meta_desc": "Test description",
    }

    # Act
    html_output = engine.render("base.html", context)

    # Assert: Custom favicon link is present, no default
    assert '<link rel="icon" type="image/png" href="' in html_output
    assert "/assets/custom-favicon.png" in html_output
    # Default favicons should not be present when custom is specified
    assert "favicon.ico" not in html_output or "/assets/custom-favicon.png" in html_output
