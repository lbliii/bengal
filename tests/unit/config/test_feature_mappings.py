"""Tests for feature group mappings."""

from bengal.config.feature_mappings import (
    expand_features,
    get_available_features,
    get_feature_expansion,
)


class TestExpandFeatures:
    """Test expand_features function."""

    def test_expand_rss_feature(self):
        """Test RSS feature expansion."""
        config = {"features": {"rss": True}}

        result = expand_features(config)

        assert result["generate_rss"] is True
        assert "rss" in result.get("output_formats", {}).get("site_wide", [])
        assert "features" not in result  # Features removed after expansion

    def test_expand_search_feature(self):
        """Test search feature expansion."""
        config = {"features": {"search": True}}

        result = expand_features(config)

        assert result["search"]["enabled"] is True
        assert result["search"]["preload"] == "smart"

    def test_expand_json_feature(self):
        """Test JSON feature expansion."""
        config = {"features": {"json": True}}

        result = expand_features(config)

        assert "json" in result.get("output_formats", {}).get("per_page", [])

    def test_expand_multiple_features(self):
        """Test expanding multiple features."""
        config = {
            "features": {
                "rss": True,
                "sitemap": True,
                "search": True,
            }
        }

        result = expand_features(config)

        assert result["generate_rss"] is True
        assert result["generate_sitemap"] is True
        assert result["search"]["enabled"] is True

    def test_disabled_features_not_expanded(self):
        """Test disabled features are not expanded."""
        config = {
            "features": {
                "rss": False,
                "sitemap": True,
            }
        }

        result = expand_features(config)

        assert "generate_rss" not in result
        assert result["generate_sitemap"] is True

    def test_explicit_config_overrides_feature(self):
        """Test explicit config takes priority over feature expansion."""
        config = {
            "features": {"search": True},
            "search": {"enabled": True, "preload": "immediate"},
        }

        result = expand_features(config)

        # Explicit "immediate" should be preserved, not overridden to "smart"
        assert result["search"]["preload"] == "immediate"

    def test_unknown_feature_ignored(self):
        """Test unknown features are silently ignored."""
        config = {
            "features": {
                "unknown_feature": True,
                "rss": True,
            }
        }

        result = expand_features(config)

        # Should still expand known features
        assert result["generate_rss"] is True
        # Unknown feature has no effect
        assert "unknown_feature" not in result

    def test_no_features_section(self):
        """Test config without features section is unchanged."""
        config = {"site": {"title": "Test"}}

        result = expand_features(config)

        assert result == {"site": {"title": "Test"}}

    def test_features_not_dict(self):
        """Test features that's not a dict is handled gracefully."""
        config = {"features": "not_a_dict"}

        result = expand_features(config)

        # Should remove invalid features and return rest of config
        assert "features" not in result

    def test_list_features_append_not_replace(self):
        """Test list-type features append to existing lists."""
        config = {
            "features": {"json": True, "llm_txt": True},
            "output_formats": {"per_page": ["html"]},
        }

        result = expand_features(config)

        # Should append json and llm_txt to existing html
        per_page = result["output_formats"]["per_page"]
        assert "html" in per_page
        assert "json" in per_page
        assert "llm_txt" in per_page


class TestGetAvailableFeatures:
    """Test get_available_features function."""

    def test_returns_sorted_list(self):
        """Test returns sorted list of feature names."""
        features = get_available_features()

        assert isinstance(features, list)
        assert len(features) > 0
        assert features == sorted(features)

    def test_contains_expected_features(self):
        """Test returned list contains expected features."""
        features = get_available_features()

        expected = ["rss", "sitemap", "search", "json", "llm_txt", "validate_links"]
        for feature in expected:
            assert feature in features


class TestGetFeatureExpansion:
    """Test get_feature_expansion function."""

    def test_get_rss_expansion(self):
        """Test getting RSS feature expansion."""
        expansion = get_feature_expansion("rss")

        assert expansion is not None
        assert "generate_rss" in expansion
        assert "output_formats.site_wide" in expansion

    def test_get_search_expansion(self):
        """Test getting search feature expansion."""
        expansion = get_feature_expansion("search")

        assert expansion is not None
        assert "search.enabled" in expansion
        assert "search.preload" in expansion

    def test_get_unknown_feature(self):
        """Test getting unknown feature returns None."""
        expansion = get_feature_expansion("unknown")

        assert expansion is None
