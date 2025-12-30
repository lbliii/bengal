"""
Tests for the anchor validator.

The anchor validator checks for:
1. Duplicate anchor IDs within pages
2. Broken [[#anchor]] cross-references

Related: bengal/health/validators/anchors.py
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.anchors import AnchorValidator


class TestAnchorValidatorDuplicateDetection:
    """Test duplicate anchor ID detection."""

    @pytest.fixture
    def validator(self):
        """Create an AnchorValidator instance."""
        return AnchorValidator()

    @pytest.fixture
    def mock_site(self):
        """Create a mock site with xref_index."""
        site = MagicMock()
        site.xref_index = {
            "by_anchor": {},
            "by_heading": {},
        }
        site.pages = []
        return site

    def test_no_duplicates_passes(self, validator, mock_site):
        """Test that pages without duplicate anchors pass validation."""
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = "# Test Page\n\nContent here."
        page.rendered_html = '<h2 id="heading-1">Heading 1</h2><h2 id="heading-2">Heading 2</h2>'
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        # No issues for unique anchors
        assert len(results) == 0

    def test_duplicate_anchor_detected(self, validator, mock_site):
        """Test that duplicate anchor IDs are detected."""
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = ""
        page.rendered_html = '<h2 id="install">Install</h2><h2 id="install">Install Again</h2>'
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        assert len(results) == 1
        assert results[0].status == CheckStatus.WARNING
        assert "Duplicate anchor ID 'install'" in results[0].message
        assert "(2 occurrences)" in results[0].message

    def test_multiple_duplicates_detected(self, validator, mock_site):
        """Test that multiple different duplicate anchors are all detected."""
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = ""
        page.rendered_html = """
            <h2 id="setup">Setup</h2>
            <h2 id="setup">Setup Again</h2>
            <h3 id="config">Config</h3>
            <h3 id="config">Config Again</h3>
            <h3 id="config">Config Third</h3>
        """
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        assert len(results) == 2
        # Find results by anchor
        setup_result = next(r for r in results if "setup" in r.message.lower())
        config_result = next(r for r in results if "config" in r.message.lower())

        assert "(2 occurrences)" in setup_result.message
        assert "(3 occurrences)" in config_result.message

    def test_strict_mode_reports_errors(self, mock_site):
        """Test that strict mode reports duplicates as errors."""
        validator = AnchorValidator(strict=True)

        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = ""
        page.rendered_html = '<h2 id="dupe">First</h2><h2 id="dupe">Second</h2>'
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        assert len(results) == 1
        assert results[0].status == CheckStatus.ERROR  # Not WARNING

    def test_empty_html_no_crash(self, validator, mock_site):
        """Test that pages with no rendered HTML don't crash."""
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = ""
        page.rendered_html = None
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        assert len(results) == 0


class TestAnchorValidatorReferenceValidation:
    """Test [[#anchor]] reference validation."""

    @pytest.fixture
    def validator(self):
        """Create an AnchorValidator instance."""
        return AnchorValidator()

    @pytest.fixture
    def mock_site(self):
        """Create a mock site with xref_index."""
        site = MagicMock()
        site.xref_index = {
            "by_anchor": {
                "install": (MagicMock(), "install"),
                "setup": (MagicMock(), "setup"),
            },
            "by_heading": {
                "configuration": [(MagicMock(), "configuration")],
            },
        }
        site.pages = []
        return site

    def test_valid_reference_passes(self, validator, mock_site):
        """Test that valid [[#anchor]] references pass."""
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = "See [[#install]] for details."
        page.rendered_html = ""
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        # No broken reference issues
        assert len(results) == 0

    def test_valid_heading_reference_passes(self, validator, mock_site):
        """Test that references to heading anchors pass."""
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = "See [[#configuration]] for details."
        page.rendered_html = ""
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        assert len(results) == 0

    def test_broken_reference_detected(self, validator, mock_site):
        """Test that broken [[#anchor]] references are detected."""
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = "See [[#nonexistent]] for details."
        page.rendered_html = ""
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        assert len(results) == 1
        assert results[0].status == CheckStatus.WARNING
        assert "Broken anchor reference '[[#nonexistent]]'" in results[0].message

    def test_multiple_broken_references(self, validator, mock_site):
        """Test that multiple broken references are all detected."""
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = """
See [[#missing1]] for first part.
Then [[#missing2]] for second part.
        """
        page.rendered_html = ""
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        assert len(results) == 2
        assert any("missing1" in r.message for r in results)
        assert any("missing2" in r.message for r in results)

    def test_case_insensitive_matching(self, validator, mock_site):
        """Test that anchor matching is case-insensitive."""
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = "See [[#INSTALL]] for details."  # Uppercase
        page.rendered_html = ""
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        # Should match "install" case-insensitively
        assert len(results) == 0

    def test_reference_with_custom_text(self, validator, mock_site):
        """Test that [[#anchor|text]] syntax is validated."""
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = "See [[#missing|the link]] for details."
        page.rendered_html = ""
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        assert len(results) == 1
        assert "missing" in results[0].message

    def test_empty_xref_index_graceful(self, validator):
        """Test that missing xref_index doesn't crash."""
        site = MagicMock()
        site.xref_index = None  # No xref_index built yet
        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = "See [[#something]] here."
        page.rendered_html = ""
        site.pages = [page]

        results = validator.validate(site)

        # Should report as broken (can't validate without index)
        assert len(results) == 1
        assert "Broken anchor reference" in results[0].message


class TestAnchorValidatorMetadata:
    """Test that validator metadata is correct."""

    def test_validator_name(self):
        """Test that validator has correct name."""
        validator = AnchorValidator()
        assert validator.name == "anchors"

    def test_validator_description(self):
        """Test that validator has description."""
        validator = AnchorValidator()
        assert "anchor" in validator.description.lower()

    def test_result_includes_file_path(self):
        """Test that results include file path in metadata."""
        validator = AnchorValidator()
        site = MagicMock()
        site.xref_index = {"by_anchor": {}, "by_heading": {}}

        page = MagicMock()
        page.source_path = Path("content/docs/guide.md")
        page._raw_content = "See [[#broken]]."
        page.rendered_html = ""
        site.pages = [page]

        results = validator.validate(site)

        assert len(results) == 1
        assert "file_path" in results[0].metadata
        assert "guide.md" in results[0].metadata["file_path"]

    def test_result_includes_line_number(self):
        """Test that broken reference results include line number."""
        validator = AnchorValidator()
        site = MagicMock()
        site.xref_index = {"by_anchor": {}, "by_heading": {}}

        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = "Line 1\nLine 2\nSee [[#broken]] here.\nLine 4"
        page.rendered_html = ""
        site.pages = [page]

        results = validator.validate(site)

        assert len(results) == 1
        assert "line" in results[0].metadata
        assert results[0].metadata["line"] == 3  # [[#broken]] is on line 3


class TestAnchorValidatorSimilarSuggestions:
    """Test similar anchor suggestions for broken references."""

    @pytest.fixture
    def validator(self):
        """Create an AnchorValidator instance."""
        return AnchorValidator()

    def test_suggests_similar_anchors(self, validator):
        """Test that similar anchors are suggested."""
        site = MagicMock()
        site.xref_index = {
            "by_anchor": {
                "install-guide": (MagicMock(), "install-guide"),
                "install-quick": (MagicMock(), "install-quick"),
                "setup": (MagicMock(), "setup"),
            },
            "by_heading": {},
        }

        page = MagicMock()
        page.source_path = Path("content/test.md")
        page._raw_content = "See [[#install]] for details."  # Partial match
        page.rendered_html = ""
        site.pages = [page]

        results = validator.validate(site)

        assert len(results) == 1
        assert "similar_anchors" in results[0].metadata
        # Should suggest anchors containing "install"
        similar = results[0].metadata["similar_anchors"]
        assert any("install" in s for s in similar)
