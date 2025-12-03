"""Tests for Theme configuration object and feature flags."""

from __future__ import annotations

import pytest

from bengal.core.theme import Theme


class TestThemeBasics:
    """Tests for basic Theme configuration."""

    def test_default_theme_values(self):
        """Test default Theme values."""
        theme = Theme()

        assert theme.name == "default"
        assert theme.default_appearance == "system"
        assert theme.default_palette == ""
        assert theme.features == []
        assert theme.config == {}

    def test_theme_with_custom_values(self):
        """Test Theme with custom values."""
        theme = Theme(
            name="my-theme",
            default_appearance="dark",
            default_palette="blue",
            features=["navigation.toc"],
            config={"custom_key": "value"},
        )

        assert theme.name == "my-theme"
        assert theme.default_appearance == "dark"
        assert theme.default_palette == "blue"
        assert theme.features == ["navigation.toc"]
        assert theme.config == {"custom_key": "value"}

    def test_invalid_appearance_raises_error(self):
        """Test that invalid appearance raises ValueError."""
        with pytest.raises(ValueError, match="Invalid default_appearance"):
            Theme(default_appearance="invalid")

    def test_valid_appearances(self):
        """Test that valid appearances are accepted."""
        for appearance in ("light", "dark", "system"):
            theme = Theme(default_appearance=appearance)
            assert theme.default_appearance == appearance

    def test_none_features_normalized_to_list(self):
        """Test that None features are normalized to empty list."""
        theme = Theme(features=None)  # type: ignore[arg-type]
        assert theme.features == []

    def test_none_config_normalized_to_dict(self):
        """Test that None config is normalized to empty dict."""
        theme = Theme(config=None)
        assert theme.config == {}


class TestThemeFeatures:
    """Tests for Theme feature flags."""

    def test_has_feature_returns_true_when_present(self):
        """Test has_feature returns True for enabled features."""
        theme = Theme(features=["navigation.toc", "content.code.copy"])

        assert theme.has_feature("navigation.toc") is True
        assert theme.has_feature("content.code.copy") is True

    def test_has_feature_returns_false_when_absent(self):
        """Test has_feature returns False for disabled features."""
        theme = Theme(features=["navigation.toc"])

        assert theme.has_feature("navigation.tabs") is False
        assert theme.has_feature("content.code.copy") is False

    def test_has_feature_with_empty_features(self):
        """Test has_feature returns False with empty features list."""
        theme = Theme(features=[])

        assert theme.has_feature("navigation.toc") is False

    def test_feature_check_is_exact_match(self):
        """Test that feature matching is exact, not prefix-based."""
        theme = Theme(features=["navigation.toc"])

        # Exact match should work
        assert theme.has_feature("navigation.toc") is True

        # Partial matches should not work
        assert theme.has_feature("navigation") is False
        assert theme.has_feature("navigation.toc.sticky") is False
        assert theme.has_feature("toc") is False

    def test_features_in_operator_works_in_templates(self):
        """Test that 'in' operator works (for template usage)."""
        theme = Theme(features=["navigation.toc", "content.code.copy"])

        # This is how templates check features
        assert "navigation.toc" in theme.features
        assert "content.code.copy" in theme.features
        assert "navigation.tabs" not in theme.features


class TestThemeFromConfig:
    """Tests for Theme.from_config() factory method."""

    def test_from_config_with_empty_config(self):
        """Test from_config with empty configuration."""
        theme = Theme.from_config({})

        assert theme.name == "default"
        assert theme.default_appearance == "system"
        assert theme.default_palette == ""
        assert theme.features == []
        assert theme.config == {}

    def test_from_config_with_string_theme(self):
        """Test from_config with legacy string theme."""
        config = {"theme": "my-theme"}
        theme = Theme.from_config(config)

        assert theme.name == "my-theme"
        assert theme.default_appearance == "system"
        assert theme.default_palette == ""
        assert theme.features == []
        assert theme.config == {}

    def test_from_config_with_dict_theme(self):
        """Test from_config with dict theme configuration."""
        config = {
            "theme": {
                "name": "my-theme",
                "default_appearance": "dark",
                "default_palette": "blue",
            }
        }
        theme = Theme.from_config(config)

        assert theme.name == "my-theme"
        assert theme.default_appearance == "dark"
        assert theme.default_palette == "blue"
        assert theme.features == []

    def test_from_config_with_features(self):
        """Test from_config parses features list."""
        config = {
            "theme": {
                "name": "default",
                "features": [
                    "navigation.toc",
                    "navigation.breadcrumbs",
                    "content.code.copy",
                ],
            }
        }
        theme = Theme.from_config(config)

        assert theme.features == [
            "navigation.toc",
            "navigation.breadcrumbs",
            "content.code.copy",
        ]
        assert theme.has_feature("navigation.toc") is True
        assert theme.has_feature("navigation.breadcrumbs") is True
        assert theme.has_feature("content.code.copy") is True
        assert theme.has_feature("navigation.tabs") is False

    def test_from_config_with_empty_features(self):
        """Test from_config with empty features list."""
        config = {
            "theme": {
                "name": "default",
                "features": [],
            }
        }
        theme = Theme.from_config(config)

        assert theme.features == []

    def test_from_config_features_not_list_normalized(self):
        """Test from_config normalizes non-list features to empty list."""
        config = {
            "theme": {
                "name": "default",
                "features": "not-a-list",  # Invalid type
            }
        }
        theme = Theme.from_config(config)

        assert theme.features == []

    def test_from_config_preserves_additional_config(self):
        """Test from_config preserves additional theme config."""
        config = {
            "theme": {
                "name": "default",
                "features": ["navigation.toc"],
                "custom_option": "value",
                "another_option": 123,
            }
        }
        theme = Theme.from_config(config)

        assert theme.config == {
            "custom_option": "value",
            "another_option": 123,
        }
        # Features should NOT be in config
        assert "features" not in theme.config

    def test_from_config_full_example(self):
        """Test from_config with full configuration example."""
        config = {
            "theme": {
                "name": "my-theme",
                "default_appearance": "system",
                "default_palette": "blue-bengal",
                "features": [
                    "navigation.breadcrumbs",
                    "navigation.toc",
                    "navigation.toc.sticky",
                    "navigation.prev_next",
                    "navigation.back_to_top",
                    "content.code.copy",
                    "content.lightbox",
                    "search.suggest",
                    "search.highlight",
                    "accessibility.skip_link",
                ],
                "sidebar_width": "280px",
            }
        }
        theme = Theme.from_config(config)

        assert theme.name == "my-theme"
        assert theme.default_appearance == "system"
        assert theme.default_palette == "blue-bengal"
        assert len(theme.features) == 10
        assert theme.has_feature("navigation.toc") is True
        assert theme.has_feature("content.code.copy") is True
        assert theme.config == {"sidebar_width": "280px"}


class TestThemeToDict:
    """Tests for Theme.to_dict() method."""

    def test_to_dict_includes_features(self):
        """Test to_dict includes features in output."""
        theme = Theme(
            name="default",
            features=["navigation.toc", "content.code.copy"],
        )
        result = theme.to_dict()

        assert result == {
            "name": "default",
            "default_appearance": "system",
            "default_palette": "",
            "features": ["navigation.toc", "content.code.copy"],
            "config": {},
        }

    def test_to_dict_empty_features(self):
        """Test to_dict with empty features."""
        theme = Theme(name="default", features=[])
        result = theme.to_dict()

        assert result["features"] == []

    def test_to_dict_round_trip(self):
        """Test that to_dict output can be used to recreate Theme."""
        original = Theme(
            name="my-theme",
            default_appearance="dark",
            default_palette="blue",
            features=["navigation.toc", "content.code.copy"],
            config={"custom": "value"},
        )

        # to_dict produces values that could reconstruct the theme
        result = original.to_dict()

        assert result["name"] == original.name
        assert result["default_appearance"] == original.default_appearance
        assert result["default_palette"] == original.default_palette
        assert result["features"] == original.features
        assert result["config"] == original.config

