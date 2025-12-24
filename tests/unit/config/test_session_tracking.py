"""Test that config errors are tracked in error sessions.

Tests session integration for:
- ConfigLoadError from directory_loader.py
- ConfigValidationError from validators.py
- Deprecation warnings from deprecation.py
"""

from __future__ import annotations

import pytest

from bengal.config.deprecation import check_deprecated_keys
from bengal.config.directory_loader import ConfigDirectoryLoader, ConfigLoadError
from bengal.config.validators import ConfigValidationError, ConfigValidator
from bengal.errors.session import get_session, reset_session


@pytest.fixture(autouse=True)
def fresh_session():
    """Reset session before and after each test."""
    reset_session()
    yield
    reset_session()


class TestConfigErrorSessionTracking:
    """Test that config errors are recorded in error sessions."""

    def test_yaml_error_tracked_in_session(self, tmp_path):
        """Verify YAML parse errors are recorded in error session."""
        loader = ConfigDirectoryLoader()
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)
        (defaults / "bad.yaml").write_text("invalid: [")

        with pytest.raises(ConfigLoadError):
            loader.load(config_dir, environment="local")

        session = get_session()
        summary = session.get_summary()

        assert summary["total_errors"] == 1
        assert "C001" in summary["errors_by_code"]

    def test_validation_error_tracked_in_session(self):
        """Verify validation errors are recorded in error session."""
        validator = ConfigValidator()
        config = {"parallel": "not-a-bool"}

        with pytest.raises(ConfigValidationError):
            validator.validate(config)

        session = get_session()
        summary = session.get_summary()

        assert summary["total_errors"] == 1
        assert "C004" in summary["errors_by_code"]

    def test_deprecation_warning_tracked_in_session(self):
        """Verify deprecation warnings are recorded in error session."""
        config = {"minify_assets": True}

        # This should record a warning in the session
        deprecated = check_deprecated_keys(config, source="test.yaml", warn=True)

        assert len(deprecated) == 1

        session = get_session()
        summary = session.get_summary()

        assert summary["total_errors"] == 1
        assert "C008" in summary["errors_by_code"]

    def test_multiple_errors_tracked(self, tmp_path):
        """Verify multiple errors are accumulated in session."""
        # First error: validation
        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError):
            validator.validate({"parallel": "invalid"})

        # Second error: deprecation warning
        check_deprecated_keys({"generate_rss": True}, source="test.yaml", warn=True)

        session = get_session()
        summary = session.get_summary()

        assert summary["total_errors"] == 2
        assert "C004" in summary["errors_by_code"]
        assert "C008" in summary["errors_by_code"]

    def test_file_path_recorded_in_session(self, tmp_path):
        """Verify file paths are recorded with errors."""
        loader = ConfigDirectoryLoader()
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)
        bad_file = defaults / "bad.yaml"
        bad_file.write_text("invalid: yaml: [")

        with pytest.raises(ConfigLoadError):
            loader.load(config_dir, environment="local")

        session = get_session()
        summary = session.get_summary()

        assert summary["affected_files"] == 1
        assert len(summary["most_affected_files"]) == 1

    def test_session_reset_clears_errors(self, tmp_path):
        """Verify reset_session() clears all recorded errors."""
        validator = ConfigValidator()

        with pytest.raises(ConfigValidationError):
            validator.validate({"parallel": "invalid"})

        session = get_session()
        assert session.get_summary()["total_errors"] == 1

        # Reset should clear
        reset_session()
        session = get_session()
        assert session.get_summary()["total_errors"] == 0
