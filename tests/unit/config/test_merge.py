"""Tests for deep merge utilities."""

from bengal.config.merge import (
    batch_deep_merge,
    deep_merge,
    get_nested_key,
    set_nested_key,
)


class TestBatchDeepMerge:
    """Test batch_deep_merge function."""

    def test_batch_merge_empty_list(self):
        """Test batch merge with empty list."""
        result = batch_deep_merge([])
        assert result == {}

    def test_batch_merge_single_config(self):
        """Test batch merge with single config."""
        config = {"site": {"title": "Test"}}
        result = batch_deep_merge([config])
        assert result == config

    def test_batch_merge_two_configs(self):
        """Test batch merge with two configs."""
        config1 = {"site": {"title": "Base"}}
        config2 = {"site": {"baseurl": "/"}}

        result = batch_deep_merge([config1, config2])

        assert result == {"site": {"title": "Base", "baseurl": "/"}}

    def test_batch_merge_multiple_configs(self):
        """Test batch merge with multiple overlapping configs."""
        configs = [
            {"site": {"title": "First"}},
            {"build": {"parallel": True}},
            {"site": {"title": "Second", "baseurl": "/"}},
            {"build": {"incremental": True}},
        ]

        result = batch_deep_merge(configs)

        assert result == {
            "site": {"title": "Second", "baseurl": "/"},
            "build": {"parallel": True, "incremental": True},
        }

    def test_batch_merge_deeply_nested(self):
        """Test batch merge with deeply nested dicts."""
        configs = [
            {"level1": {"level2": {"level3": {"a": 1}}}},
            {"level1": {"level2": {"level3": {"b": 2}}}},
            {"level1": {"level2": {"level3": {"c": 3}}}},
        ]

        result = batch_deep_merge(configs)

        assert result["level1"]["level2"]["level3"] == {"a": 1, "b": 2, "c": 3}

    def test_batch_merge_identical_to_sequential(self):
        """Test that batch merge produces same result as sequential deep_merge."""
        configs = [
            {"site": {"title": "Base", "nested": {"a": 1}}},
            {"site": {"baseurl": "/", "nested": {"b": 2}}},
            {"build": {"parallel": True}},
            {"site": {"nested": {"c": 3}}, "build": {"incremental": True}},
        ]

        # Sequential merge
        sequential_result = {}
        for config in configs:
            sequential_result = deep_merge(sequential_result, config)

        # Batch merge
        batch_result = batch_deep_merge(configs)

        assert batch_result == sequential_result

    def test_batch_merge_does_not_mutate_inputs(self):
        """Test that batch merge does not mutate input configs."""
        import copy

        configs = [
            {"site": {"title": "Base"}},
            {"site": {"baseurl": "/"}},
        ]
        original = copy.deepcopy(configs)

        batch_deep_merge(configs)

        assert configs == original

    def test_batch_merge_replaces_lists(self):
        """Test that lists are replaced, not merged."""
        configs = [
            {"tags": ["python", "django"]},
            {"tags": ["rust", "go"]},
        ]

        result = batch_deep_merge(configs)

        assert result == {"tags": ["rust", "go"]}

    def test_batch_merge_type_mismatch(self):
        """Test merging with type mismatches (later config wins)."""
        configs = [
            {"config": {"value": "string"}},
            {"config": ["list", "of", "values"]},
        ]

        result = batch_deep_merge(configs)

        assert result == {"config": ["list", "of", "values"]}


class TestDeepMerge:
    """Test deep_merge function."""

    def test_merge_flat_dicts(self):
        """Test merging flat dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}
        # Ensure base not mutated
        assert base == {"a": 1, "b": 2}

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {
            "site": {"title": "Base", "description": "Base desc"},
            "build": {"parallel": True},
        }
        override = {
            "site": {"baseurl": "https://example.com"},
            "build": {"parallel": False},
        }

        result = deep_merge(base, override)

        assert result == {
            "site": {
                "title": "Base",
                "description": "Base desc",
                "baseurl": "https://example.com",
            },
            "build": {"parallel": False},
        }

    def test_merge_replaces_lists(self):
        """Test that lists are replaced, not merged."""
        base = {"tags": ["python", "django"]}
        override = {"tags": ["rust", "go"]}

        result = deep_merge(base, override)

        assert result == {"tags": ["rust", "go"]}

    def test_merge_replaces_primitives(self):
        """Test that primitives are replaced."""
        base = {"parallel": True, "workers": 4}
        override = {"parallel": False}

        result = deep_merge(base, override)

        assert result == {"parallel": False, "workers": 4}

    def test_merge_type_mismatch(self):
        """Test merging with type mismatches (override wins)."""
        base = {"config": {"value": "string"}}
        override = {"config": ["list", "of", "values"]}

        result = deep_merge(base, override)

        assert result == {"config": ["list", "of", "values"]}

    def test_merge_deeply_nested(self):
        """Test deeply nested dictionary merge."""
        base = {
            "level1": {
                "level2": {
                    "level3": {"a": 1, "b": 2},
                    "other": "value",
                }
            }
        }
        override = {"level1": {"level2": {"level3": {"b": 3, "c": 4}}}}

        result = deep_merge(base, override)

        assert result["level1"]["level2"]["level3"] == {"a": 1, "b": 3, "c": 4}
        assert result["level1"]["level2"]["other"] == "value"

    def test_merge_empty_dicts(self):
        """Test merging with empty dictionaries."""
        assert deep_merge({}, {"a": 1}) == {"a": 1}
        assert deep_merge({"a": 1}, {}) == {"a": 1}
        assert deep_merge({}, {}) == {}


class TestSetNestedKey:
    """Test set_nested_key function."""

    def test_set_single_level(self):
        """Test setting single-level key."""
        config = {}
        set_nested_key(config, "title", "My Site")

        assert config == {"title": "My Site"}

    def test_set_nested_key(self):
        """Test setting nested key."""
        config = {}
        set_nested_key(config, "site.theme.name", "default")

        assert config == {"site": {"theme": {"name": "default"}}}

    def test_set_existing_path(self):
        """Test setting key in existing path."""
        config = {"site": {"title": "Test"}}
        set_nested_key(config, "site.baseurl", "https://example.com")

        assert config == {"site": {"title": "Test", "baseurl": "https://example.com"}}

    def test_set_overwrites_value(self):
        """Test setting key overwrites existing value."""
        config = {"site": {"title": "Old"}}
        set_nested_key(config, "site.title", "New")

        assert config["site"]["title"] == "New"

    def test_set_deeply_nested(self):
        """Test setting deeply nested key."""
        config = {}
        set_nested_key(config, "a.b.c.d.e", "value")

        assert config["a"]["b"]["c"]["d"]["e"] == "value"

    def test_set_cannot_traverse_non_dict(self):
        """Test that setting skips if intermediate is not dict."""
        config = {"site": "string_value"}
        set_nested_key(config, "site.theme.name", "default")

        # Should skip, site is not a dict
        assert config == {"site": "string_value"}


class TestGetNestedKey:
    """Test get_nested_key function."""

    def test_get_single_level(self):
        """Test getting single-level key."""
        config = {"title": "My Site"}

        assert get_nested_key(config, "title") == "My Site"

    def test_get_nested_key(self):
        """Test getting nested key."""
        config = {"site": {"theme": {"name": "default"}}}

        assert get_nested_key(config, "site.theme.name") == "default"

    def test_get_missing_key(self):
        """Test getting missing key returns default."""
        config = {"site": {"title": "Test"}}

        assert get_nested_key(config, "site.missing") is None
        assert get_nested_key(config, "site.missing", "fallback") == "fallback"

    def test_get_partial_path(self):
        """Test getting partial path returns default."""
        config = {"site": {"title": "Test"}}

        assert get_nested_key(config, "site.theme.name") is None

    def test_get_from_non_dict(self):
        """Test getting from non-dict returns default."""
        config = {"site": "string_value"}

        assert get_nested_key(config, "site.theme") is None

    def test_get_deeply_nested(self):
        """Test getting deeply nested value."""
        config = {"a": {"b": {"c": {"d": {"e": "value"}}}}}

        assert get_nested_key(config, "a.b.c.d.e") == "value"
