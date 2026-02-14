"""
Integration tests for content.math theme feature.

Tests that enabling content.math includes KaTeX in the output and that
math content is parsed and rendered with correct HTML structure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


class TestMathFeature:
    """Test content.math theme feature."""

    def test_content_math_includes_katex_in_output(self, tmp_path: Path) -> None:
        """When content.math is enabled, KaTeX CSS and JS are in the output."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "bengal.toml").write_text("""
[site]
title = "Math Test"
baseurl = "/"

[build]
output_dir = "public"

[theme]
name = "default"
features = ["content.math"]
""")

        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
The equation $E = mc^2$ is famous.
""")

        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        index_html = (site_dir / "public" / "index.html").read_text()

        assert "katex.min.css" in index_html
        assert "katex.min.js" in index_html
        assert "math.js" in index_html
        assert 'class="math"' in index_html
        assert "E = mc^2" in index_html

    def test_content_math_disabled_excludes_katex(self, tmp_path: Path) -> None:
        """When content.math is not enabled, KaTeX is not in the output."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "bengal.toml").write_text("""
[site]
title = "No Math Test"
baseurl = "/"

[build]
output_dir = "public"

[theme]
name = "default"
features = ["navigation.toc"]
""")

        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
The equation $E = mc^2$ is still parsed but not rendered.
""")

        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        index_html = (site_dir / "public" / "index.html").read_text()

        assert "katex.min.js" not in index_html
        assert 'class="math"' in index_html
