"""Tests for config defaults and feature helpers.

Tests config/defaults.py:
- get_max_workers: auto-detection and config value handling
- get_default: nested key access and fallbacks
- get_pagination_per_page: pagination defaults
- normalize_bool_or_dict: bool/dict normalization
- is_feature_enabled: feature enable checks
- get_feature_config: full feature config access
"""

from __future__ import annotations

import pytest

from bengal.config.defaults import (
    BOOL_OR_DICT_KEYS,
    DEFAULT_MAX_WORKERS,
    DEFAULTS,
    get_default,
    get_feature_config,
    get_max_workers,
    get_pagination_per_page,
    is_feature_enabled,
    normalize_bool_or_dict,
)


class TestGetMaxWorkers:
    """Tests for get_max_workers function."""

    def test_none_returns_default(self):
        """None config value returns auto-detected default."""
        result = get_max_workers(None)
        assert result == DEFAULT_MAX_WORKERS
        assert result >= 4  # Minimum is 4

    def test_zero_returns_default(self):
        """Zero config value returns auto-detected default."""
        result = get_max_workers(0)
        assert result == DEFAULT_MAX_WORKERS

    def test_positive_value_used(self):
        """Positive config value is used directly."""
        result = get_max_workers(8)
        assert result == 8

    def test_small_value_clamped_to_one(self):
        """Values less than 1 are clamped to 1."""
        result = get_max_workers(-5)
        assert result == 1

    def test_one_is_minimum(self):
        """Value of 1 is returned as-is."""
        result = get_max_workers(1)
        assert result == 1

    def test_large_value_accepted(self):
        """Large values are accepted without clamping."""
        result = get_max_workers(100)
        assert result == 100


class TestGetDefault:
    """Tests for get_default function."""

    def test_top_level_key(self):
        """Get top-level default value."""
        assert get_default("title") == "Bengal Site"
        assert get_default("language") == "en"

    def test_nested_key_with_separate_arg(self):
        """Get nested value with separate nested_key arg."""
        assert get_default("content", "excerpt_length") == 200
        assert get_default("theme", "name") == "default"

    def test_dot_notation_in_nested_key(self):
        """Get deeply nested value with dot notation."""
        assert get_default("search", "lunr.prebuilt") is True
        assert get_default("search", "ui.modal") is True

    def test_missing_top_level_returns_none(self):
        """Missing top-level key returns None."""
        assert get_default("nonexistent_key") is None

    def test_missing_nested_key_returns_none(self):
        """Missing nested key returns None."""
        assert get_default("content", "nonexistent") is None

    def test_nested_key_on_non_dict_returns_none(self):
        """Nested key on non-dict value returns None."""
        assert get_default("title", "something") is None

    def test_deeply_nested_missing_returns_none(self):
        """Deeply nested missing path returns None."""
        assert get_default("search", "nonexistent.path.deep") is None


class TestGetPaginationPerPage:
    """Tests for get_pagination_per_page function."""

    def test_none_returns_default(self):
        """None returns pagination default from DEFAULTS."""
        result = get_pagination_per_page(None)
        assert result == DEFAULTS["pagination"]["per_page"]
        assert result == 10

    def test_positive_value_used(self):
        """Positive value is used directly."""
        assert get_pagination_per_page(25) == 25

    def test_zero_clamped_to_one(self):
        """Zero is clamped to minimum of 1."""
        assert get_pagination_per_page(0) == 1

    def test_negative_clamped_to_one(self):
        """Negative values are clamped to 1."""
        assert get_pagination_per_page(-5) == 1


class TestNormalizeBoolOrDict:
    """Tests for normalize_bool_or_dict function."""

    def test_false_disables_feature(self):
        """False value creates dict with enabled=False."""
        result = normalize_bool_or_dict(False, "health_check")
        assert result["enabled"] is False

    def test_true_enables_with_defaults(self):
        """True value creates dict with enabled=True and defaults."""
        result = normalize_bool_or_dict(True, "search")
        assert result["enabled"] is True
        # Should have search defaults
        assert "lunr" in result

    def test_none_uses_defaults(self):
        """None uses full defaults including enabled state."""
        result = normalize_bool_or_dict(None, "graph")
        assert result["enabled"] is True
        assert result["path"] == "/graph/"

    def test_dict_merges_with_defaults(self):
        """Dict merges with defaults, user values take precedence."""
        result = normalize_bool_or_dict({"verbose": True}, "health_check")
        assert result["enabled"] is True
        assert result["verbose"] is True

    def test_dict_without_enabled_adds_default(self):
        """Dict without 'enabled' key gets default enabled state."""
        result = normalize_bool_or_dict({"custom": "value"}, "health_check")
        assert result["enabled"] is True
        assert result["custom"] == "value"

    def test_dict_with_enabled_preserves_it(self):
        """Dict with explicit 'enabled' preserves user value."""
        result = normalize_bool_or_dict({"enabled": False, "verbose": True}, "health_check")
        assert result["enabled"] is False
        assert result["verbose"] is True

    def test_unknown_key_uses_default_enabled(self):
        """Unknown key uses default_enabled parameter."""
        result = normalize_bool_or_dict(None, "unknown_feature", default_enabled=False)
        assert result["enabled"] is False

    def test_non_dict_defaults_returns_enabled_dict(self):
        """When DEFAULTS[key] is not a dict, returns simple enabled dict."""
        # Use a key that's not in DEFAULTS or has non-dict value
        result = normalize_bool_or_dict(True, "nonexistent_key")
        assert result["enabled"] is True


class TestIsFeatureEnabled:
    """Tests for is_feature_enabled function."""

    def test_false_value_returns_false(self):
        """Boolean False returns False."""
        config = {"health_check": False}
        assert is_feature_enabled(config, "health_check") is False

    def test_true_value_returns_true(self):
        """Boolean True returns True."""
        config = {"search": True}
        assert is_feature_enabled(config, "search") is True

    def test_dict_with_enabled_true(self):
        """Dict with enabled=True returns True."""
        config = {"search": {"enabled": True, "ui": {"modal": True}}}
        assert is_feature_enabled(config, "search") is True

    def test_dict_with_enabled_false(self):
        """Dict with enabled=False returns False."""
        config = {"graph": {"enabled": False}}
        assert is_feature_enabled(config, "graph") is False

    def test_missing_key_returns_default(self):
        """Missing key returns default parameter."""
        config = {}
        assert is_feature_enabled(config, "graph", default=True) is True
        assert is_feature_enabled(config, "graph", default=False) is False

    def test_dict_without_enabled_uses_default(self):
        """Dict without 'enabled' key uses default."""
        config = {"search": {"ui": {"modal": False}}}
        assert is_feature_enabled(config, "search", default=True) is True


class TestGetFeatureConfig:
    """Tests for get_feature_config function."""

    def test_false_returns_disabled_dict(self):
        """Boolean False returns dict with enabled=False."""
        config = {"health_check": False}
        result = get_feature_config(config, "health_check")
        assert result["enabled"] is False

    def test_true_returns_defaults_enabled(self):
        """Boolean True returns defaults with enabled=True."""
        config = {"search": True}
        result = get_feature_config(config, "search")
        assert result["enabled"] is True
        assert "lunr" in result  # Default search config

    def test_dict_merges_with_defaults(self):
        """Dict config merges with defaults."""
        config = {"search": {"ui": {"modal": False}}}
        result = get_feature_config(config, "search")
        assert result["enabled"] is True
        assert result["ui"]["modal"] is False  # User override
        assert "lunr" in result  # Default preserved

    def test_missing_key_uses_defaults(self):
        """Missing key uses full defaults."""
        config = {}
        result = get_feature_config(config, "graph")
        assert result["enabled"] is True
        assert result["path"] == "/graph/"


class TestBoolOrDictKeys:
    """Tests for BOOL_OR_DICT_KEYS constant."""

    def test_known_keys_present(self):
        """Known bool/dict config keys are in the set."""
        assert "health_check" in BOOL_OR_DICT_KEYS
        assert "search" in BOOL_OR_DICT_KEYS
        assert "graph" in BOOL_OR_DICT_KEYS
        assert "output_formats" in BOOL_OR_DICT_KEYS

    def test_is_frozen_set(self):
        """BOOL_OR_DICT_KEYS is a frozenset."""
        assert isinstance(BOOL_OR_DICT_KEYS, frozenset)


class TestDefaults:
    """Tests for DEFAULTS dictionary structure."""

    def test_has_essential_keys(self):
        """DEFAULTS has essential configuration keys."""
        essential_keys = ["title", "baseurl", "output_dir", "content_dir", "theme"]
        for key in essential_keys:
            assert key in DEFAULTS

    def test_theme_has_required_fields(self):
        """Theme config has required fields."""
        theme = DEFAULTS["theme"]
        assert "name" in theme
        assert "default_appearance" in theme
        assert theme["name"] == "default"

    def test_content_has_required_fields(self):
        """Content config has required fields."""
        content = DEFAULTS["content"]
        assert "excerpt_length" in content
        assert "reading_speed" in content
        assert content["reading_speed"] == 200

    def test_search_has_nested_structure(self):
        """Search config has proper nested structure."""
        search = DEFAULTS["search"]
        assert "enabled" in search
        assert "lunr" in search
        assert "ui" in search
        assert search["lunr"]["prebuilt"] is True

    def test_health_check_has_tiered_validators(self):
        """Health check config has tiered validator lists."""
        health = DEFAULTS["health_check"]
        assert "build_validators" in health
        assert "full_validators" in health
        assert "ci_validators" in health
        # Tier 1 validators
        assert "config" in health["build_validators"]
        assert "links" in health["build_validators"]
        # Tier 2 validators
        assert "connectivity" in health["full_validators"]
        assert "cache" in health["full_validators"]

    def test_features_has_output_generators(self):
        """Features config has output generator flags."""
        features = DEFAULTS["features"]
        assert features["rss"] is True
        assert features["sitemap"] is True
        assert features["search"] is True



