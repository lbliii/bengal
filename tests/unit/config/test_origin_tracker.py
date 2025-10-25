"""Tests for origin tracking."""

from bengal.config.origin_tracker import ConfigWithOrigin


class TestConfigWithOrigin:
    """Test ConfigWithOrigin class."""

    def test_initial_state(self):
        """Test initial state is empty."""
        tracker = ConfigWithOrigin()

        assert tracker.config == {}
        assert tracker.origins == {}

    def test_merge_single_source(self):
        """Test merging from single source."""
        tracker = ConfigWithOrigin()

        config = {"site": {"title": "Test", "baseurl": "https://example.com"}}
        tracker.merge(config, "_default/site.yaml")

        assert tracker.config == config
        assert tracker.origins["site.title"] == "_default/site.yaml"
        assert tracker.origins["site.baseurl"] == "_default/site.yaml"

    def test_merge_multiple_sources(self):
        """Test merging from multiple sources tracks correctly."""
        tracker = ConfigWithOrigin()

        # First merge: defaults
        tracker.merge({"site": {"title": "Default Title"}}, "_default/site.yaml")

        # Second merge: environment override
        tracker.merge(
            {"site": {"baseurl": "https://prod.example.com"}}, "environments/production.yaml"
        )

        assert tracker.config["site"]["title"] == "Default Title"
        assert tracker.config["site"]["baseurl"] == "https://prod.example.com"

        assert tracker.origins["site.title"] == "_default/site.yaml"
        assert tracker.origins["site.baseurl"] == "environments/production.yaml"

    def test_merge_overrides_track_last_source(self):
        """Test that overrides update origin tracking."""
        tracker = ConfigWithOrigin()

        # First merge
        tracker.merge({"parallel": True}, "_default/build.yaml")

        # Second merge overrides
        tracker.merge({"parallel": False}, "environments/production.yaml")

        assert tracker.config["parallel"] is False
        assert tracker.origins["parallel"] == "environments/production.yaml"

    def test_merge_nested_dicts(self):
        """Test merging nested dicts tracks correctly."""
        tracker = ConfigWithOrigin()

        # Base config
        tracker.merge({"theme": {"name": "default", "appearance": "light"}}, "_default/theme.yaml")

        # Override some nested keys
        tracker.merge({"theme": {"appearance": "dark"}}, "profiles/dev.yaml")

        assert tracker.config["theme"]["name"] == "default"
        assert tracker.config["theme"]["appearance"] == "dark"

        assert tracker.origins["theme.name"] == "_default/theme.yaml"
        assert tracker.origins["theme.appearance"] == "profiles/dev.yaml"

    def test_get_origin(self):
        """Test get_origin method."""
        tracker = ConfigWithOrigin()

        tracker.merge({"title": "Test"}, "_default/site.yaml")

        assert tracker.get_origin("title") == "_default/site.yaml"
        assert tracker.get_origin("nonexistent") is None

    def test_show_with_origin_flat(self):
        """Test showing flat config with origins."""
        tracker = ConfigWithOrigin()

        tracker.merge({"title": "Test", "parallel": True}, "_default/config.yaml")

        output = tracker.show_with_origin()

        assert "title: Test  # _default/config.yaml" in output
        assert "parallel: True  # _default/config.yaml" in output

    def test_show_with_origin_nested(self):
        """Test showing nested config with origins."""
        tracker = ConfigWithOrigin()

        tracker.merge({"site": {"title": "Test"}}, "_default/site.yaml")
        tracker.merge({"site": {"baseurl": "https://example.com"}}, "environments/production.yaml")

        output = tracker.show_with_origin()

        assert "site:" in output
        assert "title: Test  # _default/site.yaml" in output
        assert "baseurl: https://example.com  # environments/production.yaml" in output

    def test_show_with_origin_lists(self):
        """Test showing lists with origins."""
        tracker = ConfigWithOrigin()

        tracker.merge({"tags": ["python", "rust"]}, "_default/config.yaml")

        output = tracker.show_with_origin()

        assert "tags:  # _default/config.yaml" in output
        assert "- python" in output
        assert "- rust" in output

    def test_deeply_nested_origins(self):
        """Test origin tracking for deeply nested keys."""
        tracker = ConfigWithOrigin()

        tracker.merge({"a": {"b": {"c": {"d": "value"}}}}, "test.yaml")

        assert tracker.origins["a.b.c.d"] == "test.yaml"

    def test_merge_list_replaces_not_merges(self):
        """Test that lists are replaced, not merged."""
        tracker = ConfigWithOrigin()

        tracker.merge({"tags": ["a", "b"]}, "file1.yaml")
        tracker.merge({"tags": ["c", "d"]}, "file2.yaml")

        assert tracker.config["tags"] == ["c", "d"]
        assert tracker.origins["tags"] == "file2.yaml"
