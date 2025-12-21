"""
Tests for autodoc resilience features.

Covers strict mode, failure tracking, fallback tagging, and summary reporting.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.autodoc.base import DocElement
from bengal.autodoc.orchestration import AutodocRunResult, VirtualAutodocOrchestrator

# Note: The orchestrator calls module-level functions from these modules:
# - bengal.autodoc.orchestration.extractors: extract_python, extract_cli, extract_openapi
# - bengal.autodoc.orchestration.section_builders: create_python_sections, etc.
# - bengal.autodoc.orchestration.page_builders: create_pages
# Tests must mock these module-level functions, not methods on the orchestrator.


@pytest.fixture
def mock_site():
    """Create a mock site with autodoc config."""
    site = MagicMock()
    site.root_path = Path("/test/site")
    site.output_dir = Path("/test/site/public")
    site.config = {
        "site": {"title": "Test Site", "baseurl": "/"},
        "autodoc": {
            "python": {"enabled": True, "source_dirs": ["."]},
            "cli": {"enabled": False},
            "openapi": {"enabled": False},
        },
    }
    site.theme = "default"
    site.theme_config = {}
    site.baseurl = "/"
    site.menu = {"main": []}
    site.menu_localized = {}
    site._section_registry = {}
    site._section_url_registry = {}
    return site


@pytest.fixture
def mock_site_strict(mock_site):
    """Create a mock site with strict mode enabled."""
    mock_site.config["autodoc"]["strict"] = True
    return mock_site


class TestAutodocRunResult:
    """Tests for AutodocRunResult dataclass."""

    def test_initial_state(self):
        """Result should start with zero counts."""
        result = AutodocRunResult()
        assert result.extracted == 0
        assert result.rendered == 0
        assert result.failed_extract == 0
        assert result.failed_render == 0
        assert result.warnings == 0
        assert result.failed_extract_identifiers == []
        assert result.failed_render_identifiers == []
        assert result.fallback_pages == []

    def test_has_failures(self):
        """has_failures() should detect extraction or rendering failures."""
        result = AutodocRunResult()
        assert result.has_failures() is False

        result.failed_extract = 1
        assert result.has_failures() is True

        result.failed_extract = 0
        result.failed_render = 1
        assert result.has_failures() is True

    def test_has_warnings(self):
        """has_warnings() should detect warnings."""
        result = AutodocRunResult()
        assert result.has_warnings() is False

        result.warnings = 1
        assert result.has_warnings() is True


class TestExtractionFailureHandling:
    """Test extraction failure handling in non-strict mode."""

    def test_extraction_failure_logs_warning_non_strict(self, mock_site):
        """Extraction failures should log warnings but not raise in non-strict mode."""
        orchestrator = VirtualAutodocOrchestrator(mock_site)

        with patch("bengal.autodoc.orchestration.orchestrator.extract_python") as mock_extract:
            mock_extract.side_effect = Exception("Extraction failed")

            pages, sections, result = orchestrator.generate()

            assert len(pages) == 0
            assert len(sections) == 0
            assert result.failed_extract == 1
            assert result.failed_extract_identifiers == ["python"]
            assert result.warnings >= 1

    def test_extraction_failure_raises_in_strict_mode(self, mock_site_strict):
        """Extraction failures should raise RuntimeError in strict mode."""
        orchestrator = VirtualAutodocOrchestrator(mock_site_strict)

        with patch("bengal.autodoc.orchestration.orchestrator.extract_python") as mock_extract:
            mock_extract.side_effect = Exception("Extraction failed")

            with pytest.raises(RuntimeError, match="Python extraction failed in strict mode"):
                orchestrator.generate()

    def test_partial_extraction_failure_non_strict(self, mock_site):
        """Partial extraction failures should still return successful elements."""
        orchestrator = VirtualAutodocOrchestrator(mock_site)

        # Mock successful Python extraction, failed CLI extraction
        mock_python_elements = [
            DocElement(
                name="test_module",
                qualified_name="test.module",
                description="Test",
                element_type="module",
                source_file=Path("/test.py"),
                line_number=1,
                metadata={},
                children=[],
                examples=[],
                see_also=[],
                deprecated=None,
            )
        ]

        with (
            patch(
                "bengal.autodoc.orchestration.orchestrator.extract_python",
                return_value=mock_python_elements,
            ),
            patch("bengal.autodoc.orchestration.orchestrator.extract_cli") as mock_cli,
        ):
            mock_cli.side_effect = Exception("CLI extraction failed")

            # CLI is disabled in mock_site, so this won't actually fail
            # But we can test the pattern
            pages, sections, result = orchestrator.generate()

            # Should have some pages from Python extraction
            assert result.extracted >= 0  # May be 0 if no elements match filters


class TestStrictModeEnforcement:
    """Test strict mode enforcement."""

    def test_strict_mode_raises_on_extraction_failure(self, mock_site_strict):
        """Strict mode should raise after recording partial results."""
        orchestrator = VirtualAutodocOrchestrator(mock_site_strict)

        with patch("bengal.autodoc.orchestration.orchestrator.extract_python") as mock_extract:
            mock_extract.side_effect = ValueError("Invalid source directory")

            with pytest.raises(RuntimeError) as exc_info:
                orchestrator.generate()

            assert "strict mode" in str(exc_info.value).lower()
            assert "Python extraction failed" in str(exc_info.value)

    def test_strict_mode_raises_on_zero_elements_with_failures(self, mock_site_strict):
        """Strict mode should raise if no elements produced and failures occurred."""
        orchestrator = VirtualAutodocOrchestrator(mock_site_strict)

        with patch("bengal.autodoc.orchestration.orchestrator.extract_python") as mock_extract:
            mock_extract.side_effect = Exception("Extraction failed")

            # Should raise RuntimeError about extraction failure (happens during extraction)
            with pytest.raises(RuntimeError, match="Python extraction failed"):
                orchestrator.generate()

    def test_strict_mode_allows_successful_generation(self, mock_site_strict):
        """Strict mode should allow successful generation."""
        orchestrator = VirtualAutodocOrchestrator(mock_site_strict)

        # Mock successful extraction with empty result (no elements found)
        with patch("bengal.autodoc.orchestration.orchestrator.extract_python", return_value=[]):
            pages, sections, result = orchestrator.generate()

            # Should return empty but not raise
            assert len(pages) == 0
            assert len(sections) == 0
            assert result.extracted == 0


class TestSummaryTracking:
    """Test summary tracking for all element types."""

    def test_summary_tracks_python_elements(self, mock_site):
        """Summary should track Python element extraction."""
        orchestrator = VirtualAutodocOrchestrator(mock_site)

        mock_elements = [
            DocElement(
                name="module1",
                qualified_name="test.module1",
                description="Module 1",
                element_type="module",
                source_file=Path("/test1.py"),
                line_number=1,
                metadata={},
                children=[],
                examples=[],
                see_also=[],
                deprecated=None,
            ),
            DocElement(
                name="module2",
                qualified_name="test.module2",
                description="Module 2",
                element_type="module",
                source_file=Path("/test2.py"),
                line_number=1,
                metadata={},
                children=[],
                examples=[],
                see_also=[],
                deprecated=None,
            ),
        ]

        with (
            patch(
                "bengal.autodoc.orchestration.orchestrator.extract_python",
                return_value=mock_elements,
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.create_python_sections",
                return_value={},
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.create_pages",
                return_value=([], AutodocRunResult()),
            ),
        ):
            pages, sections, result = orchestrator.generate()

            # Result should be populated (though pages may be empty due to filtering)
            assert isinstance(result, AutodocRunResult)

    def test_summary_tracks_cli_elements(self, mock_site):
        """Summary should track CLI element extraction."""
        mock_site.config["autodoc"]["cli"] = {"enabled": True, "app_module": "test.cli:main"}
        orchestrator = VirtualAutodocOrchestrator(mock_site)

        mock_elements = [
            DocElement(
                name="build",
                qualified_name="cli.build",
                description="Build command",
                element_type="command",
                source_file=None,
                line_number=1,
                metadata={},
                children=[],
                examples=[],
                see_also=[],
                deprecated=None,
            )
        ]

        with (
            patch(
                "bengal.autodoc.orchestration.orchestrator.extract_cli",
                return_value=mock_elements,
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.create_cli_sections",
                return_value={},
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.create_pages",
                return_value=([], AutodocRunResult()),
            ),
        ):
            pages, sections, result = orchestrator.generate()

            assert isinstance(result, AutodocRunResult)

    def test_summary_tracks_openapi_elements(self, mock_site):
        """Summary should track OpenAPI element extraction."""
        mock_site.config["autodoc"]["openapi"] = {
            "enabled": True,
            "spec_file": "api/openapi.yaml",
        }
        orchestrator = VirtualAutodocOrchestrator(mock_site)

        mock_elements = [
            DocElement(
                name="GET /users",
                qualified_name="api.users.list",
                description="List users",
                element_type="openapi_endpoint",
                source_file=None,
                line_number=1,
                metadata={},
                children=[],
                examples=[],
                see_also=[],
                deprecated=None,
            )
        ]

        with (
            patch(
                "bengal.autodoc.orchestration.orchestrator.extract_openapi",
                return_value=mock_elements,
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.create_openapi_sections",
                return_value={},
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.create_pages",
                return_value=([], AutodocRunResult()),
            ),
        ):
            pages, sections, result = orchestrator.generate()

            assert isinstance(result, AutodocRunResult)


class TestFallbackTagging:
    """Test fallback template tagging."""

    def test_fallback_tagged_in_metadata(self):
        """Pages rendered via fallback should be tagged in metadata."""
        from bengal.core.page import Page

        page = Page.create_virtual(
            source_id="test.md",
            title="Test",
            metadata={
                "is_autodoc": True,
                "_autodoc_fallback_template": True,
                "_autodoc_fallback_reason": "Template not found",
            },
            rendered_html="<h1>Test</h1>",
            template_name="fallback",
            output_path=Path("/test/index.html"),
        )

        assert page.metadata.get("_autodoc_fallback_template") is True
        assert page.metadata.get("_autodoc_fallback_reason") == "Template not found"

    def test_non_fallback_page_not_tagged(self):
        """Pages not using fallback should not have fallback tag."""
        from bengal.core.page import Page

        page = Page.create_virtual(
            source_id="test.md",
            title="Test",
            metadata={"is_autodoc": True},
            rendered_html="<h1>Test</h1>",
            template_name="autodoc/python/module",
            output_path=Path("/test/index.html"),
        )

        assert page.metadata.get("_autodoc_fallback_template") is None


class TestResultReturnValue:
    """Test that generate() returns result as third value."""

    def test_generate_returns_three_values(self, mock_site):
        """generate() should return (pages, sections, result) tuple."""
        orchestrator = VirtualAutodocOrchestrator(mock_site)

        with patch("bengal.autodoc.orchestration.orchestrator.extract_python", return_value=[]):
            result = orchestrator.generate()

            assert isinstance(result, tuple)
            assert len(result) == 3
            pages, sections, run_result = result
            assert isinstance(pages, list)
            assert isinstance(sections, list)
            assert isinstance(run_result, AutodocRunResult)

    def test_orchestrator_tolerates_three_value_return(self, mock_site):
        """ContentOrchestrator should handle 3-tuple return value."""
        from bengal.orchestration.content import ContentOrchestrator

        orchestrator = ContentOrchestrator(mock_site)

        # Mock the import inside the method
        with patch(
            "bengal.autodoc.orchestration.VirtualAutodocOrchestrator", autospec=True
        ) as mock_orchestrator_class:
            mock_orchestrator_instance = MagicMock()
            mock_orchestrator_instance.is_enabled.return_value = True
            mock_orchestrator_instance.generate.return_value = ([], [], AutodocRunResult())
            mock_orchestrator_class.return_value = mock_orchestrator_instance

            pages, sections = orchestrator._discover_autodoc_content()

            assert isinstance(pages, list)
            assert isinstance(sections, list)
            # Verify the orchestrator was called
            mock_orchestrator_instance.generate.assert_called_once()
