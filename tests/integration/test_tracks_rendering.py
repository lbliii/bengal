"""Integration tests for track page rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.rendering.template_functions.get_page import (
    _get_render_cache,
    clear_get_page_cache,
)
from bengal.utils.io.file_io import write_text_file


@pytest.fixture
def site_with_tracks(tmp_path: Path) -> Site:
    """Create a site with tracks.yaml and track content."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()

    # Create config
    config_path = site_dir / "bengal.toml"
    write_text_file(
        str(config_path),
        """[site]
title = "Test Site"
baseurl = "/"

[build]
output_dir = "public"
""",
    )

    # Create tracks.yaml
    data_dir = site_dir / "data"
    data_dir.mkdir()
    tracks_yaml = data_dir / "tracks.yaml"
    tracks_yaml.write_text("""getting-started:
  title: "Getting Started"
  description: "Learn the basics"
  items:
    - docs/getting-started/page1.md
    - docs/getting-started/page2.md

content-mastery:
  title: "Content Mastery"
  description: "Advanced content techniques"
  items:
    - docs/guides/workflow.md
    - docs/guides/reuse.md
""")

    # Create track pages
    content_dir = site_dir / "content"
    content_dir.mkdir()

    # Getting started pages
    getting_started_dir = content_dir / "docs" / "getting-started"
    getting_started_dir.mkdir(parents=True)
    (getting_started_dir / "page1.md").write_text(
        "---\ntitle: Page 1\n---\n# Page 1\n\nContent here."
    )
    (getting_started_dir / "page2.md").write_text(
        "---\ntitle: Page 2\n---\n# Page 2\n\nMore content."
    )

    # Guide pages
    guides_dir = content_dir / "docs" / "guides"
    guides_dir.mkdir(parents=True)
    (guides_dir / "workflow.md").write_text("---\ntitle: Workflow\n---\n# Workflow Guide")
    (guides_dir / "reuse.md").write_text("---\ntitle: Content Reuse\n---\n# Reuse Guide")

    # Create track landing page
    tracks_dir = content_dir / "tracks"
    tracks_dir.mkdir()
    track_page = tracks_dir / "getting-started.md"
    track_page.write_text("""---
title: Getting Started Track
template: tracks/single.html
track_id: getting-started
---
# Getting Started Track

This is the track introduction.
""")

    # Create site and discover content
    site = Site.from_config(site_dir, config_path=config_path)
    site.discover_content()
    site.discover_assets()

    return site


@pytest.fixture
def site_without_tracks(tmp_path: Path) -> Site:
    """Create a site without tracks.yaml."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()

    config_path = site_dir / "bengal.toml"
    write_text_file(
        str(config_path),
        """[site]
title = "Test Site"
baseurl = "/"

[build]
output_dir = "public"
""",
    )

    content_dir = site_dir / "content"
    content_dir.mkdir()
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

    site = Site.from_config(site_dir, config_path=config_path)
    site.discover_content()
    site.discover_assets()

    return site


@pytest.fixture
def site_with_invalid_tracks(tmp_path: Path) -> Site:
    """Create a site with invalid tracks.yaml."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()

    config_path = site_dir / "bengal.toml"
    write_text_file(
        str(config_path),
        """[site]
title = "Test Site"
baseurl = "/"

[build]
output_dir = "public"
""",
    )

    # Create invalid tracks.yaml (missing 'items' field)
    data_dir = site_dir / "data"
    data_dir.mkdir()
    tracks_yaml = data_dir / "tracks.yaml"
    tracks_yaml.write_text("""invalid:
  title: "Invalid Track"
  # Missing 'items' field
""")

    content_dir = site_dir / "content"
    content_dir.mkdir()

    site = Site.from_config(site_dir, config_path=config_path)
    site.discover_content()
    site.discover_assets()

    return site


class TestTrackRendering:
    """Integration tests for track page rendering."""

    def test_tracks_yaml_loaded(self, site_with_tracks: Site):
        """Test tracks.yaml is loaded into site.data.tracks."""
        assert hasattr(site_with_tracks.data, "tracks")
        assert "getting-started" in site_with_tracks.data.tracks
        assert "content-mastery" in site_with_tracks.data.tracks

        track = site_with_tracks.data.tracks["getting-started"]
        assert track["title"] == "Getting Started"
        assert track["description"] == "Learn the basics"
        assert isinstance(track["items"], list)
        assert len(track["items"]) == 2

    def test_tracks_missing_yaml_handles_gracefully(self, site_without_tracks: Site):
        """Test site without tracks.yaml doesn't crash."""
        # site.data.tracks should be empty dict or None
        if hasattr(site_without_tracks.data, "tracks"):
            # If tracks exists, it should be empty
            assert not site_without_tracks.data.tracks or len(site_without_tracks.data.tracks) == 0

    def test_track_with_missing_page_shows_warning(self, site_with_tracks: Site):
        """Test track with non-existent page handles gracefully."""
        from jinja2 import Environment

        from bengal.rendering.template_functions.get_page import register

        env = Environment()
        register(env, site_with_tracks)
        get_page = env.globals["get_page"]

        # Try to get a page that doesn't exist
        page = get_page("docs/getting-started/nonexistent.md")
        assert page is None

    def test_track_section_content_rendering(self, site_with_tracks: Site):
        """Test that track section content can be accessed."""
        from jinja2 import Environment

        from bengal.rendering.template_functions.get_page import register

        env = Environment()
        register(env, site_with_tracks)
        get_page = env.globals["get_page"]

        # Get a track item page
        page = get_page("docs/getting-started/page1.md")
        assert page is not None
        assert page.title == "Page 1"
        # Content should be available (may be parsed or raw)
        assert hasattr(page, "content") or hasattr(page, "html_content")

    def test_track_with_empty_items_list(self, tmp_path: Path):
        """Test track with no items handles gracefully."""
        # Create a new site with empty items track
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        config_path = site_dir / "bengal.toml"
        write_text_file(
            str(config_path),
            """[site]
title = "Test Site"
baseurl = "/"

[build]
output_dir = "public"
""",
        )

        # Create tracks.yaml with empty items
        data_dir = site_dir / "data"
        data_dir.mkdir()
        tracks_yaml = data_dir / "tracks.yaml"
        tracks_yaml.write_text("""empty-track:
  title: "Empty Track"
  items: []
""")

        content_dir = site_dir / "content"
        content_dir.mkdir()

        site = Site.from_config(site_dir, config_path=config_path)
        site.discover_content()
        site.discover_assets()

        # Verify empty track is loaded
        assert hasattr(site.data, "tracks")
        track = site.data.tracks.get("empty-track")
        assert track is not None
        assert track["items"] == []

    def test_get_page_resolves_track_items(self, site_with_tracks: Site):
        """Test that get_page can resolve all track items."""
        from jinja2 import Environment

        from bengal.rendering.template_functions.get_page import register

        env = Environment()
        register(env, site_with_tracks)
        get_page = env.globals["get_page"]

        track = site_with_tracks.data.tracks["getting-started"]
        for item_path in track["items"]:
            page = get_page(item_path)
            assert page is not None, f"Failed to resolve track item: {item_path}"
            assert page.title is not None

    def test_per_render_cache_reduces_lookups(self, site_with_tracks: Site):
        """Test per-render cache reduces redundant get_page() calls.

        This simulates how tracks/single.html uses get_page() multiple times
        for the same track items (contents overview, main content, sidebar, TOC).
        """
        from jinja2 import Environment

        from bengal.rendering.template_functions.get_page import register

        clear_get_page_cache()  # Start fresh

        env = Environment()
        register(env, site_with_tracks)
        get_page = env.globals["get_page"]

        track = site_with_tracks.data.tracks["getting-started"]
        items = track["items"]

        # Simulate multiple template passes over the same items
        # Pass 1: Contents overview
        for item_path in items:
            page = get_page(item_path)
            assert page is not None

        # Check cache is populated
        cache = _get_render_cache()
        assert len(cache) >= len(items)

        # Pass 2: Main content rendering (should hit cache)
        for item_path in items:
            page = get_page(item_path)
            assert page is not None

        # Pass 3: Sidebar (should hit cache)
        for item_path in items:
            page = get_page(item_path)
            assert page is not None

        # Cache size should not have grown significantly
        # (might grow slightly due to path normalization creating additional entries)
        assert len(cache) <= len(items) * 2

    def test_cache_cleared_between_page_renders(self, site_with_tracks: Site):
        """Test that cache is cleared between page renders.

        Simulates the rendering pipeline processing multiple pages.
        """
        from jinja2 import Environment

        from bengal.rendering.template_functions.get_page import register

        env = Environment()
        register(env, site_with_tracks)
        get_page = env.globals["get_page"]

        track = site_with_tracks.data.tracks["getting-started"]

        # Simulate first page render
        clear_get_page_cache()
        get_page(track["items"][0])
        cache = _get_render_cache()
        assert len(cache) >= 1

        # Simulate cache clear at start of next page render
        clear_get_page_cache()
        cache = _get_render_cache()
        assert len(cache) == 0

        # Second page render starts fresh
        page2 = get_page(track["items"][1])
        assert page2 is not None
        cache = _get_render_cache()
        assert len(cache) >= 1

    def test_track_embedded_cards_have_correct_hrefs(self, tmp_path: Path):
        """Track embeds pages with cards; card links resolve to source page URLs.

        When a track embeds docs/guides/parent.md which has :::{card} :link: ./child,
        the rendered HTML should have href="/docs/guides/child/" (source page URL),
        not /tracks/xxx/child/. Cards are resolved when the source page is built.
        """
        from bengal.orchestration.build.options import BuildOptions

        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "bengal.toml").write_text("""
[site]
title = "Track Cards Test"
baseurl = "/"

[build]
output_dir = "public"

[theme]
name = "default"
""")

        data_dir = site_dir / "data"
        data_dir.mkdir()
        (data_dir / "tracks.yaml").write_text("""cards-track:
  title: "Cards Track"
  items:
    - docs/guides/parent.md
""")

        content_dir = site_dir / "content"
        content_dir.mkdir()
        guides_dir = content_dir / "docs" / "guides"
        guides_dir.mkdir(parents=True)

        (guides_dir / "parent.md").write_text("""---
title: Parent
---
# Parent

::::{cards}
:::{card} Go to Child
:link: ./child

See the child page.
:::
::::
""")

        (guides_dir / "child.md").write_text("""---
title: Child
---
# Child

Child content.
""")

        tracks_dir = content_dir / "tracks"
        tracks_dir.mkdir()
        (tracks_dir / "cards-track.md").write_text("""---
title: Cards Track
template: tracks/single.html
track_id: cards-track
---
# Cards Track
""")

        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        html_path = site_dir / "public" / "tracks" / "cards-track" / "index.html"
        assert html_path.exists(), f"Expected {html_path}"
        html = html_path.read_text()

        # Card link must point to docs URL, not tracks URL
        assert 'href="/docs/guides/child/"' in html or 'href="/docs/guides/child"' in html, (
            f"Expected card href to resolve to /docs/guides/child/, got: {html[:2000]}"
        )
        assert "/tracks/cards-track/child" not in html
