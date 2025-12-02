"""Tests for theme feature registry."""

from __future__ import annotations

import pytest

from bengal.themes.default.features import (
    FEATURES,
    FeatureInfo,
    get_all_feature_keys,
    get_default_features,
    get_feature_info,
    get_features_by_category,
    validate_features,
)


class TestFeatureInfo:
    """Tests for FeatureInfo dataclass."""

    def test_feature_info_basic(self):
        """Test basic FeatureInfo creation."""
        info = FeatureInfo(
            key="test.feature",
            description="A test feature",
            default=True,
            category="test",
        )

        assert info.key == "test.feature"
        assert info.description == "A test feature"
        assert info.default is True
        assert info.category == "test"

    def test_feature_info_defaults(self):
        """Test FeatureInfo default values."""
        info = FeatureInfo(
            key="test.feature",
            description="A test feature",
        )

        assert info.default is False
        assert info.category == "general"

    def test_feature_info_is_frozen(self):
        """Test that FeatureInfo is immutable (frozen)."""
        info = FeatureInfo(key="test", description="test")

        with pytest.raises(AttributeError):
            info.key = "modified"  # type: ignore[misc]


class TestFeaturesRegistry:
    """Tests for the FEATURES registry."""

    def test_registry_has_expected_features(self):
        """Test that registry contains expected core features."""
        expected_features = [
            "navigation.breadcrumbs",
            "navigation.toc",
            "navigation.toc.sticky",
            "navigation.prev_next",
            "navigation.back_to_top",
            "navigation.tabs",
            "content.code.copy",
            "content.lightbox",
            "content.reading_time",
            "content.author",
            "content.excerpts",
            "content.children",
            "search.suggest",
            "search.highlight",
            "accessibility.skip_link",
        ]

        for feature in expected_features:
            assert feature in FEATURES, f"Expected feature missing: {feature}"

    def test_all_features_have_required_fields(self):
        """Test that all features have required fields."""
        for key, info in FEATURES.items():
            assert info.key == key, f"Key mismatch for {key}"
            assert isinstance(info.description, str), f"Missing description for {key}"
            assert len(info.description) > 0, f"Empty description for {key}"
            assert isinstance(info.default, bool), f"Invalid default for {key}"
            assert isinstance(info.category, str), f"Invalid category for {key}"

    def test_feature_keys_are_namespaced(self):
        """Test that all feature keys use dotted namespace."""
        for key in FEATURES:
            assert "." in key, f"Feature key should be namespaced: {key}"

    def test_feature_categories_are_valid(self):
        """Test that feature categories are from expected set."""
        valid_categories = {
            "navigation",
            "content",
            "search",
            "header",
            "footer",
            "accessibility",
            "general",
        }

        for key, info in FEATURES.items():
            assert info.category in valid_categories, (
                f"Invalid category '{info.category}' for {key}"
            )


class TestGetDefaultFeatures:
    """Tests for get_default_features()."""

    def test_returns_list_of_strings(self):
        """Test that get_default_features returns list of strings."""
        defaults = get_default_features()

        assert isinstance(defaults, list)
        assert all(isinstance(f, str) for f in defaults)

    def test_includes_default_true_features(self):
        """Test that default=True features are included."""
        defaults = get_default_features()

        # These should all be default=True in the registry
        expected_defaults = [
            "navigation.breadcrumbs",
            "navigation.toc",
            "content.code.copy",
            "content.lightbox",
        ]

        for feature in expected_defaults:
            assert feature in defaults, f"Expected default feature missing: {feature}"

    def test_excludes_default_false_features(self):
        """Test that default=False features are not included."""
        defaults = get_default_features()

        # These should all be default=False in the registry
        non_defaults = [
            "navigation.tabs",
            "content.code.annotate",
            "header.autohide",
        ]

        for feature in non_defaults:
            assert feature not in defaults, f"Non-default feature included: {feature}"


class TestValidateFeatures:
    """Tests for validate_features()."""

    def test_empty_list_returns_empty(self):
        """Test that empty input returns empty output."""
        result = validate_features([])
        assert result == []

    def test_valid_features_return_empty(self):
        """Test that all valid features return empty list."""
        valid = ["navigation.toc", "content.code.copy"]
        result = validate_features(valid)
        assert result == []

    def test_invalid_features_returned(self):
        """Test that invalid features are returned."""
        features = ["navigation.toc", "invalid.feature", "another.invalid"]
        result = validate_features(features)

        assert "invalid.feature" in result
        assert "another.invalid" in result
        assert "navigation.toc" not in result

    def test_mixed_valid_invalid(self):
        """Test with mix of valid and invalid features."""
        features = [
            "navigation.toc",
            "bad.feature",
            "content.code.copy",
            "very.bad",
        ]
        result = validate_features(features)

        assert len(result) == 2
        assert "bad.feature" in result
        assert "very.bad" in result


class TestGetFeaturesByCategory:
    """Tests for get_features_by_category()."""

    def test_returns_dict(self):
        """Test that function returns a dictionary."""
        result = get_features_by_category()
        assert isinstance(result, dict)

    def test_contains_expected_categories(self):
        """Test that result contains expected categories."""
        result = get_features_by_category()

        expected_categories = ["navigation", "content", "search"]
        for cat in expected_categories:
            assert cat in result, f"Expected category missing: {cat}"

    def test_category_lists_contain_feature_info(self):
        """Test that category lists contain FeatureInfo objects."""
        result = get_features_by_category()

        for _category, features in result.items():
            assert isinstance(features, list)
            assert all(isinstance(f, FeatureInfo) for f in features)

    def test_features_are_in_correct_category(self):
        """Test that features are grouped by their category."""
        result = get_features_by_category()

        for category, features in result.items():
            for feature in features:
                assert feature.category == category, f"Feature {feature.key} in wrong category"


class TestGetFeatureInfo:
    """Tests for get_feature_info()."""

    def test_returns_info_for_valid_feature(self):
        """Test that valid feature returns FeatureInfo."""
        info = get_feature_info("navigation.toc")

        assert info is not None
        assert info.key == "navigation.toc"
        assert isinstance(info.description, str)

    def test_returns_none_for_invalid_feature(self):
        """Test that invalid feature returns None."""
        info = get_feature_info("invalid.feature")
        assert info is None

    def test_returns_correct_info(self):
        """Test that returned info matches registry."""
        info = get_feature_info("content.code.copy")

        assert info is not None
        assert info.key == "content.code.copy"
        assert info.category == "content"
        assert info.default is True


class TestGetAllFeatureKeys:
    """Tests for get_all_feature_keys()."""

    def test_returns_list_of_strings(self):
        """Test that function returns list of strings."""
        keys = get_all_feature_keys()

        assert isinstance(keys, list)
        assert all(isinstance(k, str) for k in keys)

    def test_returns_all_features(self):
        """Test that all features are included."""
        keys = get_all_feature_keys()

        assert len(keys) == len(FEATURES)
        for key in FEATURES:
            assert key in keys

    def test_returns_sorted_keys(self):
        """Test that keys are sorted alphabetically."""
        keys = get_all_feature_keys()
        assert keys == sorted(keys)
