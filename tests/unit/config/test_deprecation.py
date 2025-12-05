"""Tests for config deprecation handling.

Tests config/deprecation.py:
- check_deprecated_keys: detecting deprecated keys and warnings
- print_deprecation_warnings: user-friendly output
- migrate_deprecated_keys: migrating old to new config format
- get_deprecation_summary: documentation generation
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest

from bengal.config.deprecation import (
    DEPRECATED_KEYS,
    RENAMED_KEYS,
    check_deprecated_keys,
    get_deprecation_summary,
    migrate_deprecated_keys,
    print_deprecation_warnings,
)


class TestDeprecatedKeys:
    """Tests for DEPRECATED_KEYS constant."""

    def test_has_expected_deprecated_keys(self):
        """DEPRECATED_KEYS contains expected asset deprecations."""
        assert "minify_assets" in DEPRECATED_KEYS
        assert "optimize_assets" in DEPRECATED_KEYS
        assert "fingerprint_assets" in DEPRECATED_KEYS

    def test_has_expected_feature_deprecations(self):
        """DEPRECATED_KEYS contains expected feature deprecations."""
        assert "generate_sitemap" in DEPRECATED_KEYS
        assert "generate_rss" in DEPRECATED_KEYS

    def test_has_markdown_deprecation(self):
        """DEPRECATED_KEYS contains markdown engine deprecation."""
        assert "markdown_engine" in DEPRECATED_KEYS

    def test_deprecation_structure(self):
        """Each deprecation has (section, new_key, note) tuple."""
        for old_key, value in DEPRECATED_KEYS.items():
            assert isinstance(value, tuple)
            assert len(value) == 3
            section, new_key, note = value
            assert isinstance(section, str)
            assert isinstance(new_key, str)
            assert isinstance(note, str)


class TestCheckDeprecatedKeys:
    """Tests for check_deprecated_keys function."""

    def test_no_deprecated_keys_returns_empty(self):
        """Config without deprecated keys returns empty list."""
        config = {"title": "My Site", "baseurl": ""}
        result = check_deprecated_keys(config, warn=False)
        assert result == []

    def test_detects_deprecated_asset_key(self):
        """Detects deprecated asset configuration keys."""
        config = {"minify_assets": True}
        result = check_deprecated_keys(config, warn=False)
        assert len(result) == 1
        old_key, new_location, note = result[0]
        assert old_key == "minify_assets"
        assert new_location == "assets.minify"
        assert "assets.minify" in note

    def test_detects_multiple_deprecated_keys(self):
        """Detects multiple deprecated keys."""
        config = {"minify_assets": True, "optimize_assets": True, "generate_sitemap": True}
        result = check_deprecated_keys(config, warn=False)
        assert len(result) == 3

    def test_warns_when_warn_true(self):
        """Emits warnings when warn=True."""
        config = {"minify_assets": True}
        with patch("bengal.config.deprecation.logger") as mock_logger:
            check_deprecated_keys(config, warn=True)
            mock_logger.warning.assert_called()

    def test_no_warning_when_warn_false(self):
        """Does not emit warnings when warn=False."""
        config = {"minify_assets": True}
        with patch("bengal.config.deprecation.logger") as mock_logger:
            check_deprecated_keys(config, warn=False)
            mock_logger.warning.assert_not_called()

    def test_includes_source_in_warning(self):
        """Warning includes source file name."""
        config = {"minify_assets": True}
        with patch("bengal.config.deprecation.logger") as mock_logger:
            check_deprecated_keys(config, source="bengal.toml", warn=True)
            call_kwargs = mock_logger.warning.call_args[1]
            assert call_kwargs["source"] == "bengal.toml"


class TestPrintDeprecationWarnings:
    """Tests for print_deprecation_warnings function."""

    def test_empty_list_prints_nothing(self):
        """Empty deprecation list prints nothing."""
        with patch("builtins.print") as mock_print:
            print_deprecation_warnings([])
            mock_print.assert_not_called()

    def test_prints_warning_header(self):
        """Prints warning header with source."""
        deprecated = [("minify_assets", "assets.minify", "Use assets.minify")]
        output = StringIO()
        with patch("builtins.print", lambda *args, **kwargs: output.write(str(args[0]) + "\n")):
            print_deprecation_warnings(deprecated, source="bengal.toml")
        result = output.getvalue()
        assert "⚠️" in result
        assert "bengal.toml" in result

    def test_prints_old_to_new_mapping(self):
        """Prints old key to new location mapping."""
        deprecated = [("minify_assets", "assets.minify", "Use assets.minify: true")]
        output = StringIO()
        with patch("builtins.print", lambda *args, **kwargs: output.write(str(args[0]) + "\n")):
            print_deprecation_warnings(deprecated)
        result = output.getvalue()
        assert "minify_assets" in result
        assert "assets.minify" in result

    def test_prints_migration_note(self):
        """Prints migration note for each deprecation."""
        note = "Use assets.minify: true instead"
        deprecated = [("minify_assets", "assets.minify", note)]
        output = StringIO()
        with patch("builtins.print", lambda *args, **kwargs: output.write(str(args[0]) + "\n")):
            print_deprecation_warnings(deprecated)
        result = output.getvalue()
        assert note in result

    def test_prints_future_removal_notice(self):
        """Prints notice about future removal."""
        deprecated = [("minify_assets", "assets.minify", "Note")]
        output = StringIO()
        with patch("builtins.print", lambda *args, **kwargs: output.write(str(args[0]) + "\n")):
            print_deprecation_warnings(deprecated)
        result = output.getvalue()
        assert "may be removed in a future version" in result


class TestMigrateDeprecatedKeys:
    """Tests for migrate_deprecated_keys function."""

    def test_migrates_asset_key(self):
        """Migrates deprecated asset key to new location."""
        config = {"minify_assets": True}
        result = migrate_deprecated_keys(config)
        assert result["assets"]["minify"] is True

    def test_preserves_old_key_by_default(self):
        """Preserves old key by default for backward compatibility."""
        config = {"minify_assets": True}
        result = migrate_deprecated_keys(config)
        assert "minify_assets" in result

    def test_removes_old_key_when_in_place(self):
        """Removes old key when in_place=True."""
        config = {"minify_assets": True}
        result = migrate_deprecated_keys(config, in_place=True)
        assert "minify_assets" not in result

    def test_does_not_overwrite_existing_new_key(self):
        """Does not overwrite existing new key with deprecated value."""
        config = {"minify_assets": False, "assets": {"minify": True}}
        result = migrate_deprecated_keys(config)
        assert result["assets"]["minify"] is True  # Original preserved

    def test_creates_section_if_missing(self):
        """Creates section dict if it doesn't exist."""
        config = {"optimize_assets": True}
        result = migrate_deprecated_keys(config)
        assert "assets" in result
        assert result["assets"]["optimize"] is True

    def test_handles_multiple_deprecated_keys(self):
        """Handles multiple deprecated keys in same section."""
        config = {"minify_assets": True, "optimize_assets": True, "fingerprint_assets": True}
        result = migrate_deprecated_keys(config)
        assert result["assets"]["minify"] is True
        assert result["assets"]["optimize"] is True
        assert result["assets"]["fingerprint"] is True

    def test_handles_different_sections(self):
        """Handles deprecated keys from different sections."""
        config = {"minify_assets": True, "generate_sitemap": True}
        result = migrate_deprecated_keys(config)
        assert result["assets"]["minify"] is True
        assert result["features"]["sitemap"] is True

    def test_skips_if_section_is_not_dict(self):
        """Skips migration if section exists but is not a dict."""
        config = {"minify_assets": True, "assets": "invalid"}
        result = migrate_deprecated_keys(config)
        # Should not overwrite string with dict
        assert result["assets"] == "invalid"

    def test_does_not_modify_original_when_not_in_place(self):
        """Does not modify original config when in_place=False."""
        config = {"minify_assets": True}
        result = migrate_deprecated_keys(config, in_place=False)
        # Original should be unchanged
        assert "assets" not in config
        # Result should have migration
        assert "assets" in result


class TestGetDeprecationSummary:
    """Tests for get_deprecation_summary function."""

    def test_returns_markdown_string(self):
        """Returns markdown-formatted string."""
        result = get_deprecation_summary()
        assert isinstance(result, str)
        assert "# Deprecated Configuration Keys" in result

    def test_includes_table_header(self):
        """Includes markdown table header."""
        result = get_deprecation_summary()
        assert "| Deprecated | Use Instead | Notes |" in result
        assert "|------------|-------------|-------|" in result

    def test_includes_deprecated_keys(self):
        """Includes all deprecated keys in output."""
        result = get_deprecation_summary()
        for old_key in DEPRECATED_KEYS:
            assert f"`{old_key}`" in result

    def test_includes_new_locations(self):
        """Includes new locations for deprecated keys."""
        result = get_deprecation_summary()
        for old_key, (section, new_key, _) in DEPRECATED_KEYS.items():
            assert f"`{section}.{new_key}`" in result


class TestRenamedKeys:
    """Tests for RENAMED_KEYS constant."""

    def test_is_dict(self):
        """RENAMED_KEYS is a dictionary."""
        assert isinstance(RENAMED_KEYS, dict)

    def test_structure_if_populated(self):
        """If RENAMED_KEYS has entries, they have correct structure."""
        for old_key, value in RENAMED_KEYS.items():
            assert isinstance(value, tuple)
            assert len(value) == 2
            new_key, note = value
            assert isinstance(new_key, str)
            assert isinstance(note, str)

