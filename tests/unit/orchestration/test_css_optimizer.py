"""
Unit tests for CSS Optimizer.

Tests content-aware CSS tree shaking functionality:
- Content type detection from pages and sections
- Feature detection from content and config
- CSS file selection based on detected types/features
- Optimized CSS generation with @layer imports
- Force include/exclude configuration
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock


def _mock_site(**kwargs) -> MagicMock:
    """Create a MagicMock site with build_state=None (no BuildState during tests)."""
    site = MagicMock()
    site.build_state = None  # Prevent MagicMock auto-creation of truthy build_state
    for k, v in kwargs.items():
        setattr(site, k, v)
    return site


class TestCSSOptimizer:
    """Tests for CSSOptimizer class."""

    def test_detects_blog_type_from_page_metadata(self) -> None:
        """Should detect blog content type from page metadata."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        # Create mock site with blog pages
        site = _mock_site(theme="default", config={})
        site.features_detected = set()

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        optimizer = CSSOptimizer(site)
        types = optimizer.get_used_content_types()

        assert "blog" in types

    def test_detects_doc_type_from_section_metadata(self) -> None:
        """Should detect doc content type from section metadata."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(theme="default", config={}, features_detected=set())

        site.pages = []

        section = MagicMock()
        section.metadata = {"content_type": "doc"}
        site.sections = [section]

        optimizer = CSSOptimizer(site)
        types = optimizer.get_used_content_types()

        assert "doc" in types

    def test_detects_multiple_content_types(self) -> None:
        """Should detect multiple content types from pages."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(theme="default", config={}, features_detected=set())

        page1 = MagicMock()
        page1.metadata = {"type": "blog"}
        page2 = MagicMock()
        page2.metadata = {"type": "doc"}
        page3 = MagicMock()
        page3.metadata = {"type": "tutorial"}

        site.pages = [page1, page2, page3]
        site.sections = []

        optimizer = CSSOptimizer(site)
        types = optimizer.get_used_content_types()

        assert "blog" in types
        assert "doc" in types
        assert "tutorial" in types

    def test_detects_features_from_site_features_detected(self) -> None:
        """Should include features from site.features_detected."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(
            theme="default",
            config={},
            features_detected={"mermaid", "data_tables"},
            pages=[],
            sections=[],
        )

        optimizer = CSSOptimizer(site)
        features = optimizer.get_enabled_features()

        assert "mermaid" in features
        assert "data_tables" in features

    def test_detects_search_feature_from_config(self) -> None:
        """Should detect search feature when enabled in config."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(
            theme="default", config={"search": {"enabled": True}}, features_detected=set()
        )

        site.pages = []
        site.sections = []

        optimizer = CSSOptimizer(site)
        features = optimizer.get_enabled_features()

        assert "search" in features

    def test_detects_graph_feature_from_config(self) -> None:
        """Should detect graph feature when enabled in config."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(
            theme="default", config={"graph": {"enabled": True}}, features_detected=set()
        )

        site.pages = []
        site.sections = []

        optimizer = CSSOptimizer(site)
        features = optimizer.get_enabled_features()

        assert "graph" in features

    def test_generates_css_with_layer_imports(self) -> None:
        """Should generate CSS with @layer imports."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(theme="default", config={}, features_detected=set())

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        optimizer = CSSOptimizer(site)
        css = optimizer.generate()

        assert isinstance(css, str)
        assert "@layer tokens, base, utilities, components, pages;" in css
        assert "@layer" in css
        assert "@import url(" in css

    def test_includes_core_css_always(self) -> None:
        """Should always include core CSS files."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(theme="default", config={}, features_detected=set())

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        optimizer = CSSOptimizer(site)
        files = optimizer.get_required_css_files()

        # Core files should be included
        assert "tokens/foundation.css" in files
        assert "base/reset.css" in files
        assert "layouts/header.css" in files

    def test_includes_blog_css_for_blog_type(self) -> None:
        """Should include blog-specific CSS for blog content type."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(theme="default", config={}, features_detected=set())

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        optimizer = CSSOptimizer(site)
        files = optimizer.get_required_css_files()

        assert "components/blog.css" in files
        assert "components/author.css" in files

    def test_excludes_autodoc_css_for_blog_only(self) -> None:
        """Should not include autodoc CSS for blog-only site."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(theme="default", config={}, features_detected=set())

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        optimizer = CSSOptimizer(site)
        files = optimizer.get_required_css_files()

        assert "components/autodoc.css" not in files
        assert "components/tutorial.css" not in files

    def test_includes_mermaid_css_for_mermaid_feature(self) -> None:
        """Should include mermaid CSS when mermaid feature is detected."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site = _mock_site(
            theme="default",
            config={},
            features_detected={"mermaid"},
            pages=[page],
            sections=[],
        )

        optimizer = CSSOptimizer(site)
        files = optimizer.get_required_css_files()

        assert "components/mermaid.css" in files

    def test_force_include_config(self) -> None:
        """Should include force-included CSS from config."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(
            theme="default",
            config={"css": {"include": ["components/gallery.css"]}},
            features_detected=set(),
        )

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        optimizer = CSSOptimizer(site)
        files = optimizer.get_required_css_files()

        assert "components/gallery.css" in files

    def test_force_exclude_config(self) -> None:
        """Should exclude force-excluded CSS from config."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(
            theme="default",
            config={"css": {"exclude": ["components/blog.css"]}},
            features_detected=set(),
        )

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        optimizer = CSSOptimizer(site)
        files = optimizer.get_required_css_files()

        # Blog CSS should be excluded even though blog type is detected
        assert "components/blog.css" not in files

    def test_deduplicates_css_files(self) -> None:
        """Should deduplicate CSS files in output."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(theme="default", config={}, features_detected=set())

        # Create pages with overlapping CSS needs
        page1 = MagicMock()
        page1.metadata = {"type": "doc"}
        page2 = MagicMock()
        page2.metadata = {"type": "tutorial"}  # Also uses steps.css

        site.pages = [page1, page2]
        site.sections = []

        optimizer = CSSOptimizer(site)
        files = optimizer.get_required_css_files()

        # steps.css should appear only once
        count = files.count("components/steps.css")
        assert count == 1

    def test_generate_with_report(self) -> None:
        """Should return report when requested."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(theme="default", config={}, features_detected=set())

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        optimizer = CSSOptimizer(site)
        result = optimizer.generate(report=True)

        assert isinstance(result, tuple)
        css, report = result

        assert isinstance(css, str)
        assert isinstance(report, dict)
        assert "included_count" in report
        assert "excluded_count" in report
        assert "reduction_percent" in report
        assert "types_detected" in report
        assert "features_detected" in report

    def test_returns_empty_for_missing_manifest(self) -> None:
        """Should return empty string when theme has no manifest."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(
            theme="nonexistent-theme",
            root_path=Path("/nonexistent"),
            config={},
            features_detected=set(),
        )
        site.pages = []
        site.sections = []

        optimizer = CSSOptimizer(site)
        css = optimizer.generate()

        assert css == ""

    def test_all_palettes_by_default(self) -> None:
        """Should include all palette CSS files by default."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(theme="default", config={}, features_detected=set())

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        optimizer = CSSOptimizer(site)
        files = optimizer.get_required_css_files()

        # All palettes should be included by default
        assert "tokens/palettes/blue-bengal.css" in files
        assert "tokens/palettes/snow-lynx.css" in files

    def test_single_palette_when_configured(self) -> None:
        """Should include only active palette when all_palettes is false."""
        from bengal.orchestration.css_optimizer import CSSOptimizer

        site = _mock_site(
            theme="default",
            config={
                "css": {"all_palettes": False},
                "theme": {"palette": "snow-lynx"},
            },
            features_detected=set(),
        )

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        optimizer = CSSOptimizer(site)
        files = optimizer.get_required_css_files()

        # Only snow-lynx palette should be included
        assert "tokens/palettes/snow-lynx.css" in files
        # Other palettes should not be included
        assert "tokens/palettes/blue-bengal.css" not in files


class TestOptimizeCSSForSite:
    """Tests for optimize_css_for_site convenience function."""

    def test_returns_string(self) -> None:
        """Should return CSS string."""
        from bengal.orchestration.css_optimizer import optimize_css_for_site

        site = _mock_site(theme="default", config={}, features_detected=set())

        page = MagicMock()
        page.metadata = {"type": "blog"}
        site.pages = [page]
        site.sections = []

        css = optimize_css_for_site(site)

        assert isinstance(css, str)
        assert len(css) > 0
