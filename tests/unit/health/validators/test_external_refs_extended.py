"""
Extended tests for ExternalRefValidator.

Tests that would have caught the duplicate H701 code bug.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.external_refs import ExternalRefValidator


@pytest.fixture
def mock_site():
    """Create mock site for testing."""
    site = MagicMock()
    site.pages = []
    return site


class TestExternalRefValidatorCodes:
    """Tests for health check code uniqueness."""

    def test_uses_code_h710_not_h701(self):
        """ExternalRefValidator uses H710, not H701 (which is used by connectivity)."""
        validator = ExternalRefValidator()

        # H701 is used by ConnectivityValidator for isolated pages
        # H710 should be used for unresolved external refs
        assert validator.name == "external_references"

        # Create a mock site with unresolved refs via resolver
        site = MagicMock()
        site.config = {"external_refs": {"enabled": True}}

        # ExternalRefValidator reads from site.external_ref_resolver.unresolved
        unresolved_ref = MagicMock()
        unresolved_ref.project = "other-project"
        unresolved_ref.target = "some-page"
        unresolved_ref.source_file = "/content/docs/test.md"
        unresolved_ref.line = 10

        resolver = MagicMock()
        resolver.unresolved = [unresolved_ref]
        site.external_ref_resolver = resolver
        site.pages = []

        results = validator.validate(site)

        # Check that any errors/warnings use H710, not H701
        for result in results:
            if result.code:
                assert result.code != "H701", (
                    "ExternalRefValidator should not use H701 (reserved for connectivity)"
                )

    def test_code_is_in_h7xx_range(self, mock_site):
        """ExternalRefValidator codes are in H7xx range."""
        validator = ExternalRefValidator()

        # Create unresolved refs via resolver
        mock_site.config = {"external_refs": {"enabled": True}}

        unresolved_ref = MagicMock()
        unresolved_ref.project = "proj"
        unresolved_ref.target = "page"
        unresolved_ref.source_file = "/content/test.md"
        unresolved_ref.line = 5

        resolver = MagicMock()
        resolver.unresolved = [unresolved_ref]
        mock_site.external_ref_resolver = resolver

        results = validator.validate(mock_site)

        for result in results:
            if result.code:
                assert result.code.startswith("H7"), f"Expected H7xx code, got {result.code}"


class TestExternalRefValidatorBehavior:
    """Tests for validator behavior."""

    def test_reports_unresolved_refs(self, mock_site):
        """Reports unresolved external references."""
        mock_site.config = {"external_refs": {"enabled": True}}

        # Create unresolved refs via resolver
        unresolved_ref = MagicMock()
        unresolved_ref.project = "missing"
        unresolved_ref.target = "page"
        unresolved_ref.source_file = "/content/docs/test.md"
        unresolved_ref.line = 15

        resolver = MagicMock()
        resolver.unresolved = [unresolved_ref]
        mock_site.external_ref_resolver = resolver

        validator = ExternalRefValidator()
        results = validator.validate(mock_site)

        warning_results = [
            r for r in results if r.status in (CheckStatus.WARNING, CheckStatus.ERROR)
        ]
        assert len(warning_results) >= 1
        assert any("unresolved" in r.message.lower() for r in warning_results)

    def test_ignores_resolved_refs(self, mock_site):
        """Does not report resolved references (empty unresolved list)."""
        mock_site.config = {"external_refs": {"enabled": True}}

        # Empty unresolved list means all refs were resolved
        resolver = MagicMock()
        resolver.unresolved = []
        mock_site.external_ref_resolver = resolver

        validator = ExternalRefValidator()
        results = validator.validate(mock_site)

        # Should have no warnings about unresolved refs
        warning_results = [
            r for r in results if r.status in (CheckStatus.WARNING, CheckStatus.ERROR)
        ]
        assert len(warning_results) == 0 or not any(
            "unresolved" in r.message.lower() for r in warning_results
        )

    def test_handles_site_without_resolver(self, mock_site):
        """Handles site that has no external_ref_resolver."""
        mock_site.config = {"external_refs": {"enabled": True}}
        mock_site.external_ref_resolver = None

        validator = ExternalRefValidator()
        results = validator.validate(mock_site)

        # Should not crash and return empty results
        assert isinstance(results, list)
        warning_results = [
            r for r in results if r.status in (CheckStatus.WARNING, CheckStatus.ERROR)
        ]
        assert len(warning_results) == 0

    def test_handles_disabled_external_refs(self, mock_site):
        """Handles site with external_refs disabled."""
        mock_site.config = {"external_refs": {"enabled": False}}

        validator = ExternalRefValidator()
        results = validator.validate(mock_site)

        # Should return empty results when disabled
        assert isinstance(results, list)
        assert len(results) == 0
