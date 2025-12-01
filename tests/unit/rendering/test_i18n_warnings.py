"""
Tests for i18n missing translation warnings.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


class TestI18nMissingTranslationWarning:
    """Tests for missing translation key warnings."""

    def test_missing_translation_logs_debug_warning(self, tmp_path: Path) -> None:
        """Test that missing translation keys log a debug warning."""
        from bengal.core.site import Site
        from bengal.rendering.template_functions.i18n import (
            _make_t,
            reset_translation_warnings,
        )

        # Create minimal site structure
        (tmp_path / "content").mkdir()
        (tmp_path / "bengal.toml").write_text('title = "Test"')

        site = Site.from_config(tmp_path)
        reset_translation_warnings()

        t = _make_t(site)

        # Capture log output
        with patch("bengal.rendering.template_functions.i18n.logger") as mock_logger:
            result = t("missing.key")

            # Should return the key
            assert result == "missing.key"

            # Should log debug warning
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args
            assert call_args[0][0] == "translation_missing"
            assert call_args[1]["key"] == "missing.key"

    def test_missing_translation_warns_only_once(self, tmp_path: Path) -> None:
        """Test that same key only logs once per build."""
        from bengal.core.site import Site
        from bengal.rendering.template_functions.i18n import (
            _make_t,
            reset_translation_warnings,
        )

        (tmp_path / "content").mkdir()
        (tmp_path / "bengal.toml").write_text('title = "Test"')

        site = Site.from_config(tmp_path)
        reset_translation_warnings()

        t = _make_t(site)

        with patch("bengal.rendering.template_functions.i18n.logger") as mock_logger:
            # Call multiple times with same key
            t("missing.key")
            t("missing.key")
            t("missing.key")

            # Should only log once
            assert mock_logger.debug.call_count == 1

    def test_different_missing_keys_each_logged(self, tmp_path: Path) -> None:
        """Test that different missing keys are each logged."""
        from bengal.core.site import Site
        from bengal.rendering.template_functions.i18n import (
            _make_t,
            reset_translation_warnings,
        )

        (tmp_path / "content").mkdir()
        (tmp_path / "bengal.toml").write_text('title = "Test"')

        site = Site.from_config(tmp_path)
        reset_translation_warnings()

        t = _make_t(site)

        with patch("bengal.rendering.template_functions.i18n.logger") as mock_logger:
            t("key.one")
            t("key.two")
            t("key.three")

            # Should log each unique key
            assert mock_logger.debug.call_count == 3

    def test_reset_translation_warnings(self, tmp_path: Path) -> None:
        """Test that reset_translation_warnings clears the warned set."""
        from bengal.core.site import Site
        from bengal.rendering.template_functions.i18n import (
            _make_t,
            reset_translation_warnings,
        )

        (tmp_path / "content").mkdir()
        (tmp_path / "bengal.toml").write_text('title = "Test"')

        site = Site.from_config(tmp_path)
        reset_translation_warnings()

        t = _make_t(site)

        with patch("bengal.rendering.template_functions.i18n.logger") as mock_logger:
            t("test.key")
            assert mock_logger.debug.call_count == 1

            # Reset and call again
            reset_translation_warnings()
            t("test.key")
            assert mock_logger.debug.call_count == 2

    def test_existing_translation_no_warning(self, tmp_path: Path) -> None:
        """Test that existing translations don't log warnings."""
        from bengal.core.site import Site
        from bengal.rendering.template_functions.i18n import (
            _make_t,
            reset_translation_warnings,
        )

        # Create i18n directory with translations
        (tmp_path / "content").mkdir()
        (tmp_path / "bengal.toml").write_text('title = "Test"')
        (tmp_path / "i18n").mkdir()
        (tmp_path / "i18n" / "en.yaml").write_text("greeting: Hello")

        site = Site.from_config(tmp_path)
        reset_translation_warnings()

        t = _make_t(site)

        with patch("bengal.rendering.template_functions.i18n.logger") as mock_logger:
            result = t("greeting")

            # Should return translation
            assert result == "Hello"

            # Should NOT log warning
            mock_logger.debug.assert_not_called()
