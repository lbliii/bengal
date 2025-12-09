"""Tests for link validator wrapper.

Tests health/validators/links.py:
- LinkValidatorWrapper: link validation in health check system
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.links import LinkValidatorWrapper


@pytest.fixture
def validator():
    """Create LinkValidatorWrapper instance."""
    return LinkValidatorWrapper()


@pytest.fixture
def mock_site():
    """Create mock site with pages."""
    site = MagicMock()
    site.config = {"validate_links": True}

    # Create mock pages
    page1 = MagicMock()
    page1.links = ["/about", "/contact"]
    page2 = MagicMock()
    page2.links = ["/blog"]
    site.pages = [page1, page2]

    return site


class TestLinkValidatorWrapperBasics:
    """Tests for LinkValidatorWrapper basic attributes."""

    def test_has_name(self, validator):
        """Validator has a name."""
        assert validator.name == "Links"

    def test_has_description(self, validator):
        """Validator has a description."""
        assert validator.description == "Validates internal and external links"

    def test_enabled_by_default(self, validator):
        """Validator is enabled by default."""
        assert validator.enabled_by_default is True


class TestLinkValidatorWrapperDisabled:
    """Tests when link validation is disabled."""

    def test_info_when_disabled(self, validator, mock_site):
        """Returns info when link validation disabled."""
        mock_site.config["validate_links"] = False
        results = validator.validate(mock_site)
        assert len(results) == 1
        assert results[0].status == CheckStatus.INFO
        assert "disabled" in results[0].message.lower()

    def test_stats_updated_when_disabled(self, validator, mock_site):
        """Stats are updated when validation disabled."""
        mock_site.config["validate_links"] = False
        validator.validate(mock_site)
        assert validator.last_stats is not None
        assert validator.last_stats.pages_skipped.get("disabled") == len(mock_site.pages)


class TestLinkValidatorWrapperValidation:
    """Tests for link validation execution."""

    def test_calls_link_validator(self, validator, mock_site):
        """Calls LinkValidator.validate_site."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = []
            MockLinkValidator.return_value = mock_validator_instance

            validator.validate(mock_site)

            mock_validator_instance.validate_site.assert_called_once_with(mock_site)

    def test_no_results_when_all_links_valid(self, validator, mock_site):
        """No error/warning results when all links valid."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = []
            MockLinkValidator.return_value = mock_validator_instance

            results = validator.validate(mock_site)

            error_results = [r for r in results if r.status == CheckStatus.ERROR]
            warning_results = [r for r in results if r.status == CheckStatus.WARNING]
            assert len(error_results) == 0
            assert len(warning_results) == 0


class TestLinkValidatorWrapperBrokenLinks:
    """Tests for broken link detection."""

    def test_error_for_internal_broken_links(self, validator, mock_site):
        """Returns error for broken internal links."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            # Return broken internal links as (page_path, link_url) tuples
            mock_validator_instance.validate_site.return_value = [
                ("/index.html", "/nonexistent"),
                ("/about.html", "/missing-page"),
            ]
            MockLinkValidator.return_value = mock_validator_instance

            results = validator.validate(mock_site)

            error_results = [r for r in results if r.status == CheckStatus.ERROR]
            assert len(error_results) >= 1
            assert "internal" in error_results[0].message.lower()

    def test_warning_for_external_broken_links(self, validator, mock_site):
        """Returns warning for broken external links."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = [
                ("/index.html", "https://broken-external.com/404"),
            ]
            MockLinkValidator.return_value = mock_validator_instance

            results = validator.validate(mock_site)

            warning_results = [r for r in results if r.status == CheckStatus.WARNING]
            assert len(warning_results) >= 1
            assert "external" in warning_results[0].message.lower()

    def test_broken_links_have_details(self, validator, mock_site):
        """Broken link results include details."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = [
                ("/index.html", "/broken-link"),
            ]
            MockLinkValidator.return_value = mock_validator_instance

            results = validator.validate(mock_site)

            error_results = [r for r in results if r.status == CheckStatus.ERROR]
            assert len(error_results) >= 1
            assert error_results[0].details is not None
            assert len(error_results[0].details) >= 1


class TestLinkValidatorWrapperStats:
    """Tests for validator stats tracking."""

    def test_tracks_pages_total(self, validator, mock_site):
        """Tracks total pages in stats."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = []
            MockLinkValidator.return_value = mock_validator_instance

            validator.validate(mock_site)

            assert validator.last_stats is not None
            assert validator.last_stats.pages_total == len(mock_site.pages)

    def test_tracks_pages_processed(self, validator, mock_site):
        """Tracks processed pages in stats."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = []
            MockLinkValidator.return_value = mock_validator_instance

            validator.validate(mock_site)

            assert validator.last_stats.pages_processed == len(mock_site.pages)

    def test_tracks_link_count_metrics(self, validator, mock_site):
        """Tracks link count in metrics."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = []
            MockLinkValidator.return_value = mock_validator_instance

            validator.validate(mock_site)

            assert "total_links" in validator.last_stats.metrics

    def test_tracks_broken_link_count(self, validator, mock_site):
        """Tracks broken link count in metrics."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = [
                ("/index.html", "/broken"),
            ]
            MockLinkValidator.return_value = mock_validator_instance

            validator.validate(mock_site)

            assert validator.last_stats.metrics["broken_links"] == 1

    def test_tracks_validation_timing(self, validator, mock_site):
        """Tracks validation timing in sub_timings."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = []
            MockLinkValidator.return_value = mock_validator_instance

            validator.validate(mock_site)

            assert "validate" in validator.last_stats.sub_timings


class TestLinkValidatorWrapperRecommendations:
    """Tests for recommendation messages."""

    def test_internal_broken_has_recommendation(self, validator, mock_site):
        """Internal broken links have fix recommendation."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = [
                ("/index.html", "/broken"),
            ]
            MockLinkValidator.return_value = mock_validator_instance

            results = validator.validate(mock_site)

            error_results = [r for r in results if r.status == CheckStatus.ERROR]
            assert error_results[0].recommendation is not None

    def test_external_broken_has_recommendation(self, validator, mock_site):
        """External broken links have recommendation."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = [
                ("/index.html", "https://example.com/404"),
            ]
            MockLinkValidator.return_value = mock_validator_instance

            results = validator.validate(mock_site)

            warning_results = [r for r in results if r.status == CheckStatus.WARNING]
            assert warning_results[0].recommendation is not None


class TestLinkValidatorWrapperSilenceIsGolden:
    """Tests that validator follows 'silence is golden' principle."""

    def test_no_success_when_all_valid(self, validator, mock_site):
        """No explicit success message when all links valid."""
        with patch("bengal.rendering.link_validator.LinkValidator") as MockLinkValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_site.return_value = []
            MockLinkValidator.return_value = mock_validator_instance

            results = validator.validate(mock_site)

            success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
            assert len(success_results) == 0
