"""Tests for config validator wrapper.

Tests health/validators/config.py:
- ConfigValidatorWrapper: config validation in health check system
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.config import ConfigValidatorWrapper


@pytest.fixture
def validator():
    """Create ConfigValidatorWrapper instance."""
    return ConfigValidatorWrapper()


@pytest.fixture
def mock_site():
    """Create mock site with configurable config."""
    site = MagicMock()
    site.config = {
        "output_dir": "public",
        "theme": "default",
        "baseurl": "",
        "max_workers": None,
        "incremental": True,
        "parallel": True,
    }
    return site


class TestConfigValidatorWrapperBasics:
    """Tests for ConfigValidatorWrapper basic attributes."""

    def test_has_name(self, validator):
        """Validator has a name."""
        assert validator.name == "Configuration"

    def test_has_description(self, validator):
        """Validator has a description."""
        assert validator.description == "Validates site configuration"

    def test_enabled_by_default(self, validator):
        """Validator is enabled by default."""
        assert validator.enabled_by_default is True


class TestConfigValidatorWrapperEssentialFields:
    """Tests for essential field checking."""

    def test_no_warning_when_fields_present(self, validator, mock_site):
        """No warning when essential fields are present."""
        results = validator.validate(mock_site)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        # Should not warn about missing essential fields
        missing_field_warnings = [
            r for r in warning_results if "Missing configuration" in r.message
        ]
        assert len(missing_field_warnings) == 0

    def test_warns_when_output_dir_missing(self, validator, mock_site):
        """Warns when output_dir is missing."""
        del mock_site.config["output_dir"]
        results = validator.validate(mock_site)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("output_dir" in r.message for r in warning_results)

    def test_warns_when_theme_missing(self, validator, mock_site):
        """Warns when theme is missing."""
        del mock_site.config["theme"]
        results = validator.validate(mock_site)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("theme" in r.message for r in warning_results)


class TestConfigValidatorWrapperCommonIssues:
    """Tests for common configuration issue detection."""

    def test_info_when_baseurl_has_trailing_slash(self, validator, mock_site):
        """Returns info when baseurl has trailing slash."""
        mock_site.config["baseurl"] = "https://example.com/"
        results = validator.validate(mock_site)
        info_results = [r for r in results if r.status == CheckStatus.INFO]
        assert any("trailing slash" in r.message.lower() for r in info_results)

    def test_warns_when_max_workers_very_high(self, validator, mock_site):
        """Warns when max_workers is very high."""
        mock_site.config["max_workers"] = 50
        results = validator.validate(mock_site)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("max_workers" in r.message for r in warning_results)

    def test_no_warning_for_reasonable_max_workers(self, validator, mock_site):
        """No warning for reasonable max_workers value."""
        mock_site.config["max_workers"] = 8
        results = validator.validate(mock_site)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        max_workers_warnings = [r for r in warning_results if "max_workers" in r.message]
        assert len(max_workers_warnings) == 0

    def test_info_when_incremental_without_parallel(self, validator, mock_site):
        """Returns info when incremental enabled without parallel."""
        mock_site.config["incremental"] = True
        mock_site.config["parallel"] = False
        results = validator.validate(mock_site)
        info_results = [r for r in results if r.status == CheckStatus.INFO]
        assert any("parallel" in r.message.lower() for r in info_results)


class TestConfigValidatorWrapperSilenceIsGolden:
    """Tests that validator follows 'silence is golden' principle."""

    def test_no_success_for_essential_fields(self, validator, mock_site):
        """No explicit success message for present essential fields."""
        results = validator.validate(mock_site)
        # Should not have success messages for "fields present"
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        field_success = [
            r for r in success_results
            if "essential" in r.message.lower() or "fields" in r.message.lower()
        ]
        assert len(field_success) == 0

    def test_no_success_for_no_issues(self, validator, mock_site):
        """No explicit success message when no issues found."""
        results = validator.validate(mock_site)
        # Most results should be informational or empty when config is good
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        # Validator should not flood with success messages
        assert len(success_results) <= 1


class TestConfigValidatorWrapperRecommendations:
    """Tests for recommendation messages."""

    def test_trailing_slash_has_recommendation(self, validator, mock_site):
        """Trailing slash info includes recommendation."""
        mock_site.config["baseurl"] = "https://example.com/"
        results = validator.validate(mock_site)
        info_results = [r for r in results if r.status == CheckStatus.INFO]
        slash_result = next(
            (r for r in info_results if "trailing slash" in r.message.lower()),
            None
        )
        assert slash_result is not None
        assert slash_result.recommendation is not None
        assert "removing" in slash_result.recommendation.lower()

    def test_high_workers_has_recommendation(self, validator, mock_site):
        """High max_workers warning includes recommendation."""
        mock_site.config["max_workers"] = 50
        results = validator.validate(mock_site)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        workers_warning = next(
            (r for r in warning_results if "max_workers" in r.message),
            None
        )
        assert workers_warning is not None
        assert workers_warning.recommendation is not None


class TestConfigValidatorWrapperEdgeCases:
    """Tests for edge cases."""

    def test_empty_config_handles_gracefully(self, validator):
        """Handles empty config gracefully."""
        site = MagicMock()
        site.config = {}
        # Should not raise
        results = validator.validate(site)
        assert isinstance(results, list)

    def test_none_baseurl_no_slash_warning(self, validator, mock_site):
        """No trailing slash warning when baseurl is empty."""
        mock_site.config["baseurl"] = ""
        results = validator.validate(mock_site)
        info_results = [r for r in results if r.status == CheckStatus.INFO]
        slash_results = [r for r in info_results if "trailing slash" in r.message.lower()]
        assert len(slash_results) == 0

    def test_max_workers_none_uses_default(self, validator, mock_site):
        """None max_workers uses auto-detection (no warning)."""
        mock_site.config["max_workers"] = None
        results = validator.validate(mock_site)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        workers_warnings = [r for r in warning_results if "max_workers" in r.message]
        assert len(workers_warnings) == 0



