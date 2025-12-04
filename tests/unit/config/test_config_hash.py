"""
Unit tests for configuration hashing.

Tests the deterministic hashing of configuration dictionaries
for cache invalidation purposes.
"""

from __future__ import annotations

from pathlib import Path

from bengal.config.hash import compute_config_hash


class TestComputeConfigHash:
    """Test suite for compute_config_hash function."""

    def test_same_config_same_hash(self):
        """Same config values produce same hash."""
        config1 = {"title": "My Site", "baseurl": "/"}
        config2 = {"title": "My Site", "baseurl": "/"}

        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_different_key_order_same_hash(self):
        """Different key ordering produces same hash (deterministic)."""
        config1 = {"title": "My Site", "baseurl": "/", "author": "Jane"}
        config2 = {"author": "Jane", "title": "My Site", "baseurl": "/"}

        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_different_values_different_hash(self):
        """Different config values produce different hash."""
        config1 = {"title": "My Site", "baseurl": "/"}
        config2 = {"title": "My Site", "baseurl": "/blog"}

        assert compute_config_hash(config1) != compute_config_hash(config2)

    def test_nested_dicts_same_hash_with_different_order(self):
        """Nested dicts with different key order produce same hash."""
        config1 = {
            "site": {"title": "My Site", "author": "Jane"},
            "build": {"parallel": True},
        }
        config2 = {
            "build": {"parallel": True},
            "site": {"author": "Jane", "title": "My Site"},
        }

        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_hash_length(self):
        """Hash is 16 characters (truncated SHA256)."""
        config = {"title": "My Site"}
        hash_value = compute_config_hash(config)

        assert len(hash_value) == 16
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_path_objects_handled(self):
        """Path objects are converted to strings for hashing."""
        config1 = {"output_dir": Path("/tmp/public")}
        config2 = {"output_dir": Path("/tmp/public")}

        # Should produce same hash
        assert compute_config_hash(config1) == compute_config_hash(config2)

        # Different paths should produce different hash
        config3 = {"output_dir": Path("/tmp/other")}
        assert compute_config_hash(config1) != compute_config_hash(config3)

    def test_set_objects_handled(self):
        """Set objects are converted to sorted strings for hashing."""
        config1 = {"tags": {"python", "web", "api"}}
        config2 = {"tags": {"api", "python", "web"}}  # Different order

        # Should produce same hash (sets are sorted)
        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_list_order_matters(self):
        """List ordering does matter for hash (unlike sets)."""
        config1 = {"items": ["a", "b", "c"]}
        config2 = {"items": ["c", "b", "a"]}

        # Different order = different hash for lists
        assert compute_config_hash(config1) != compute_config_hash(config2)

    def test_empty_config(self):
        """Empty config produces consistent hash."""
        config1 = {}
        config2 = {}

        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_none_values(self):
        """None values are handled correctly."""
        config1 = {"title": None, "author": None}
        config2 = {"author": None, "title": None}

        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_boolean_values(self):
        """Boolean values affect hash."""
        config1 = {"enabled": True}
        config2 = {"enabled": False}

        assert compute_config_hash(config1) != compute_config_hash(config2)

    def test_numeric_values(self):
        """Numeric values affect hash."""
        config1 = {"port": 8080}
        config2 = {"port": 8081}

        assert compute_config_hash(config1) != compute_config_hash(config2)

    def test_complex_nested_config(self):
        """Complex nested config produces consistent hash."""
        config = {
            "site": {
                "title": "My Site",
                "baseurl": "/",
                "author": "Jane Doe",
            },
            "build": {
                "parallel": True,
                "max_workers": 4,
                "incremental": True,
            },
            "theme": {
                "name": "default",
                "config": {"dark_mode": True},
            },
            "taxonomies": ["tags", "categories"],
        }

        # Hash should be consistent across calls
        hash1 = compute_config_hash(config)
        hash2 = compute_config_hash(config)
        assert hash1 == hash2

    def test_adding_key_changes_hash(self):
        """Adding a new key changes the hash."""
        config1 = {"title": "My Site"}
        config2 = {"title": "My Site", "author": "Jane"}

        assert compute_config_hash(config1) != compute_config_hash(config2)

    def test_removing_key_changes_hash(self):
        """Removing a key changes the hash."""
        config1 = {"title": "My Site", "author": "Jane"}
        config2 = {"title": "My Site"}

        assert compute_config_hash(config1) != compute_config_hash(config2)


class TestConfigHashIntegration:
    """Integration tests for config hash with Site."""

    def test_site_has_config_hash(self, tmp_path):
        """Site computes config_hash on initialization."""
        from bengal.core.site import Site

        site = Site(root_path=tmp_path, config={"title": "Test"})

        assert site.config_hash is not None
        assert len(site.config_hash) == 16

    def test_same_config_same_site_hash(self, tmp_path):
        """Sites with same config have same hash."""
        from bengal.core.site import Site

        config = {"title": "Test", "baseurl": "/"}

        site1 = Site(root_path=tmp_path, config=config.copy())
        site2 = Site(root_path=tmp_path, config=config.copy())

        assert site1.config_hash == site2.config_hash

    def test_different_config_different_site_hash(self, tmp_path):
        """Sites with different config have different hash."""
        from bengal.core.site import Site

        site1 = Site(root_path=tmp_path, config={"title": "Test1"})
        site2 = Site(root_path=tmp_path, config={"title": "Test2"})

        assert site1.config_hash != site2.config_hash

