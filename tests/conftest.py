"""Shared pytest fixtures for Bengal SSG tests."""

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from bengal.config.loader import ConfigLoader
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site


@pytest.fixture
def tmp_site(tmp_path: Path) -> Path:
    """Create a temporary site directory with basic structure."""
    site_dir = tmp_path / "test_site"
    site_dir.mkdir()

    # Create basic structure
    (site_dir / "content").mkdir()
    (site_dir / "assets").mkdir()
    (site_dir / "templates").mkdir()

    # Create minimal config
    config_content = """[site]
title = "Test Site"
base_url = "https://example.com"
"""
    (site_dir / "bengal.toml").write_text(config_content)

    return site_dir


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Sample configuration dictionary."""
    return {
        "title": "Test Site",
        "base_url": "https://example.com",
        "author": {"name": "Test Author", "email": "test@example.com"},
        "theme": "default",
        "pagination": {"per_page": 10}
    }


@pytest.fixture
def sample_page(tmp_path: Path) -> Page:
    """Create a sample page with frontmatter."""
    content_file = tmp_path / "test.md"
    content_file.write_text("""---
title: Test Page
date: 2025-10-01
tags: ["test", "sample"]
---

# Test Content

This is a test page.
""")

    return Page(
        source_path=content_file,
        content="# Test Content\n\nThis is a test page.",
        metadata={
            "title": "Test Page",
            "date": datetime(2025, 10, 1),
            "tags": ["test", "sample"]
        }
    )


@pytest.fixture
def sample_section(tmp_path: Path) -> Section:
    """Create a sample section."""
    section_path = tmp_path / "posts"
    section_path.mkdir()

    return Section(
        name="posts",
        title="Posts",
        path=section_path
    )


@pytest.fixture
def site_with_content(tmp_site: Path) -> Site:
    """Create a site with sample content."""
    # Create sample pages
    posts_dir = tmp_site / "content" / "posts"
    posts_dir.mkdir()

    for i in range(5):
        post_file = posts_dir / f"post-{i}.md"
        post_file.write_text(f"""---
title: Post {i}
date: 2025-10-{i+1:02d}
tags: ["test"]
---

# Post {i}

Content for post {i}.
""")

    # Load site
    loader = ConfigLoader(tmp_site)
    config = loader.load()
    site = Site(root_path=tmp_site, config=config)
    site.discover_content()

    return site


@pytest.fixture
def mock_template_engine(mocker):
    """Mock template engine for testing rendering."""
    mock = mocker.Mock()
    mock.render.return_value = "<html>Rendered</html>"
    return mock

