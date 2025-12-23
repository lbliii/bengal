"""
Integration tests for CSS optimization.

Tests the end-to-end CSS tree shaking functionality using actual test site fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.css_optimizer import CSSOptimizer, optimize_css_for_site


@pytest.fixture
def blog_only_site(tmp_path: Path) -> Site:
    """Create a minimal blog-only site for testing CSS optimization."""
    # Create site structure
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create blog section
    blog_dir = content_dir / "blog"
    blog_dir.mkdir()

    # Create _index.md
    (content_dir / "_index.md").write_text(
        """\
---
title: Test Site
---

Welcome to the test site.
""",
        encoding="utf-8",
    )

    # Create blog index
    (blog_dir / "_index.md").write_text(
        """\
---
title: Blog
type: blog
---

Blog posts.
""",
        encoding="utf-8",
    )

    # Create blog post
    (blog_dir / "post-1.md").write_text(
        """\
---
title: First Post
type: blog
---

First blog post content.
""",
        encoding="utf-8",
    )

    # Create bengal.toml
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(
        """\
[site]
title = "Test Blog"
baseurl = "/"
""",
        encoding="utf-8",
    )

    # Create site using from_config
    site = Site.from_config(tmp_path, config_path=config_path)

    return site


@pytest.fixture
def multi_type_site(tmp_path: Path) -> Site:
    """Create a site with multiple content types."""
    # Create site structure
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create _index.md
    (content_dir / "_index.md").write_text(
        """\
---
title: Multi-Type Site
type: landing
---

Welcome.
""",
        encoding="utf-8",
    )

    # Create blog section
    blog_dir = content_dir / "blog"
    blog_dir.mkdir()

    (blog_dir / "_index.md").write_text(
        """\
---
title: Blog
type: blog
---

Blog posts.
""",
        encoding="utf-8",
    )

    # Create docs section
    docs_dir = content_dir / "docs"
    docs_dir.mkdir()

    (docs_dir / "_index.md").write_text(
        """\
---
title: Documentation
type: doc
---

Documentation section.
""",
        encoding="utf-8",
    )

    # Create tutorial section
    tutorial_dir = content_dir / "tutorials"
    tutorial_dir.mkdir()

    (tutorial_dir / "_index.md").write_text(
        """\
---
title: Tutorials
type: tutorial
---

Tutorials section.
""",
        encoding="utf-8",
    )

    # Create bengal.toml
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(
        """\
[site]
title = "Multi-Type Site"
baseurl = "/"
""",
        encoding="utf-8",
    )

    # Create site using from_config
    site = Site.from_config(tmp_path, config_path=config_path)

    return site


@pytest.fixture
def site_with_mermaid(tmp_path: Path) -> Site:
    """Create a site with mermaid diagram content."""
    # Create site structure
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create _index.md with mermaid
    (content_dir / "_index.md").write_text(
        """\
---
title: Site with Diagrams
---

Here's a diagram:

```mermaid
graph TD
    A --> B
```

End of content.
""",
        encoding="utf-8",
    )

    # Create bengal.toml
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(
        """\
[site]
title = "Mermaid Site"
baseurl = "/"
""",
        encoding="utf-8",
    )

    # Create site using from_config
    site = Site.from_config(tmp_path, config_path=config_path)

    return site


class TestCSSOptimizationIntegration:
    """Integration tests for CSS optimization with full site discovery."""

    def test_blog_only_site_includes_blog_css(self, blog_only_site: Site) -> None:
        """Test that a blog-only site includes blog CSS and excludes doc CSS."""
        from bengal.orchestration.content import ContentOrchestrator

        # Run content discovery to populate pages
        orchestrator = ContentOrchestrator(blog_only_site)
        orchestrator.discover()

        # Create optimizer and get required files
        optimizer = CSSOptimizer(blog_only_site)
        required_files = optimizer.get_required_css_files()

        # Should include blog CSS
        assert any("blog.css" in f for f in required_files), "Should include blog.css"

        # Should NOT include doc CSS
        assert not any("docs-nav.css" in f for f in required_files), (
            "Should not include docs-nav.css"
        )

        # Should NOT include tutorial CSS (not used)
        assert not any("tutorial.css" in f for f in required_files), (
            "Should not include tutorial.css"
        )

    def test_multi_type_site_includes_all_type_css(self, multi_type_site: Site) -> None:
        """Test that a multi-type site includes CSS for all detected types."""
        from bengal.orchestration.content import ContentOrchestrator

        # Run content discovery
        orchestrator = ContentOrchestrator(multi_type_site)
        orchestrator.discover()

        # Create optimizer
        optimizer = CSSOptimizer(multi_type_site)
        content_types = optimizer.get_used_content_types()

        # Should detect all content types
        assert "blog" in content_types
        assert "doc" in content_types
        assert "tutorial" in content_types
        assert "landing" in content_types

        # Get required files
        required_files = optimizer.get_required_css_files()

        # Should include CSS for all types
        assert any("blog.css" in f for f in required_files)
        assert any("docs-nav.css" in f for f in required_files)
        assert any("tutorial.css" in f for f in required_files)
        assert any("landing.css" in f for f in required_files)

    def test_mermaid_detection_during_discovery(self, site_with_mermaid: Site) -> None:
        """Test that mermaid feature is detected during content discovery."""
        from bengal.orchestration.content import ContentOrchestrator

        # Run content discovery
        orchestrator = ContentOrchestrator(site_with_mermaid)
        orchestrator.discover()

        # Features should be detected and stored in site
        assert "mermaid" in site_with_mermaid.features_detected

        # Optimizer should include mermaid CSS
        optimizer = CSSOptimizer(site_with_mermaid)
        required_files = optimizer.get_required_css_files()

        assert any("mermaid.css" in f for f in required_files), "Should include mermaid.css"

    def test_css_generation_returns_valid_css(self, blog_only_site: Site) -> None:
        """Test that generated CSS is valid (non-empty with proper structure)."""
        from bengal.orchestration.content import ContentOrchestrator

        # Run content discovery
        orchestrator = ContentOrchestrator(blog_only_site)
        orchestrator.discover()

        # Generate CSS
        optimizer = CSSOptimizer(blog_only_site)
        css_content = optimizer.generate()

        # Should return valid CSS
        assert css_content is not None
        assert len(css_content) > 0

        # Should include @layer directive for proper CSS cascade
        assert "@layer" in css_content

    def test_css_report_provides_useful_metrics(self, multi_type_site: Site) -> None:
        """Test that the CSS optimization report contains useful metrics."""
        from bengal.orchestration.content import ContentOrchestrator

        # Run content discovery
        orchestrator = ContentOrchestrator(multi_type_site)
        orchestrator.discover()

        # Generate with report
        optimizer = CSSOptimizer(multi_type_site)
        _, report = optimizer.generate(report=True)

        # Report should contain expected keys
        assert "types_detected" in report
        assert "features_detected" in report
        assert "included_files" in report
        assert "excluded_files" in report

        # Types should match what we created
        assert "blog" in report["types_detected"]
        assert "doc" in report["types_detected"]

    def test_optimize_css_for_site_convenience_function(self, blog_only_site: Site) -> None:
        """Test the convenience function works end-to-end."""
        from bengal.orchestration.content import ContentOrchestrator

        # Run content discovery
        orchestrator = ContentOrchestrator(blog_only_site)
        orchestrator.discover()

        # Use convenience function
        css = optimize_css_for_site(blog_only_site)

        assert css is not None
        assert len(css) > 0
        assert "@layer" in css


class TestCSSConfigOverrides:
    """Test CSS optimization config overrides."""

    def test_force_include_adds_extra_css(self, blog_only_site: Site) -> None:
        """Test that force_include config adds additional CSS files."""
        from bengal.orchestration.content import ContentOrchestrator

        # Add force_include config
        blog_only_site.config["css"] = {
            "optimize": True,
            "include": ["doc"],
        }

        # Run content discovery
        orchestrator = ContentOrchestrator(blog_only_site)
        orchestrator.discover()

        # Get optimizer
        optimizer = CSSOptimizer(blog_only_site)
        required_files = optimizer.get_required_css_files()

        # Should include doc CSS even though no doc content exists
        assert any("docs-nav.css" in f for f in required_files)

    def test_force_exclude_removes_css(self, multi_type_site: Site) -> None:
        """Test that force_exclude config removes CSS files."""
        from bengal.orchestration.content import ContentOrchestrator

        # Add force_exclude config
        multi_type_site.config["css"] = {
            "optimize": True,
            "exclude": ["blog"],
        }

        # Run content discovery
        orchestrator = ContentOrchestrator(multi_type_site)
        orchestrator.discover()

        # Get optimizer
        optimizer = CSSOptimizer(multi_type_site)
        required_files = optimizer.get_required_css_files()

        # Should NOT include blog CSS
        assert not any("blog.css" in f for f in required_files)

        # Should still include doc CSS
        assert any("docs-nav.css" in f for f in required_files)
