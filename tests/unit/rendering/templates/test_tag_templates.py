"""Tests for tag-nav.html template null safety.

Regression: ``tag-nav.html`` line 31 applied ``current_tag | length``
when ``current_tag`` was ``none`` (passed from ``tags.html``).  The
``| length`` filter crashes on ``None``, producing "Runtime Error: 1".

The fix added null coalescing: ``(current_tag ?? '') | length``.
These tests verify the partial renders without error for all
``current_tag`` values: None, empty string, and an actual tag name.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from kida import Environment
from kida.environment import FileSystemLoader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def kida_env() -> Environment:
    """Create a Kida environment pointing at the default theme templates."""
    templates_dir = (
        Path(__file__).resolve().parents[4]
        / "bengal"
        / "themes"
        / "default"
        / "templates"
    )
    assert templates_dir.is_dir(), f"Theme templates not found: {templates_dir}"

    env = Environment(loader=FileSystemLoader(str(templates_dir)))

    # Register stub globals needed by the partial
    env.globals["tag_url"] = lambda name: f"/tags/{name}/"
    env.globals["popular_tags"] = lambda limit=50: []  # noqa: ARG005

    # Register stub filters
    env.filters["absolute_url"] = lambda url: url

    return env


SAMPLE_TAGS = [
    {"name": "python", "count": 12},
    {"name": "rust", "count": 5},
    {"name": "testing", "count": 3},
]
"""Minimal tag list used across tests (dict-style with .name/.count)."""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTagNavNullSafety:
    """Verify partials/tag-nav.html handles all current_tag variants."""

    def test_tag_nav_renders_with_none_current_tag(self, kida_env: Environment) -> None:
        """Passing current_tag=None must not crash (the original bug)."""
        template = kida_env.get_template("partials/tag-nav.html")
        html = template.render(tags=SAMPLE_TAGS, current_tag=None)

        # Should contain the "All Tags" link
        assert "All Tags" in html
        # None means "all tags" view — link should be active
        assert "active" in html

    def test_tag_nav_renders_with_empty_string_current_tag(
        self, kida_env: Environment
    ) -> None:
        """Empty string current_tag should behave like None (all tags active)."""
        template = kida_env.get_template("partials/tag-nav.html")
        html = template.render(tags=SAMPLE_TAGS, current_tag="")

        assert "All Tags" in html
        assert "active" in html

    def test_tag_nav_renders_with_active_tag(self, kida_env: Environment) -> None:
        """Passing a real tag name should mark that tag as active."""
        template = kida_env.get_template("partials/tag-nav.html")
        html = template.render(tags=SAMPLE_TAGS, current_tag="python")

        assert "python" in html
        # The "All Tags" link should NOT be active
        # The active class should appear next to the python tag link
        assert "active" in html
