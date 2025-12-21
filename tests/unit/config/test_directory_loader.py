"""Tests for directory-based config loader."""

import pytest
import yaml

from bengal.config.directory_loader import ConfigDirectoryLoader, ConfigLoadError
from bengal.errors import BengalConfigError


@pytest.fixture
def config_dir(tmp_path):
    """Create a test config directory structure."""
    config_dir = tmp_path / "config"

    # Create _default/ with multiple files
    defaults = config_dir / "_default"
    defaults.mkdir(parents=True)

    (defaults / "site.yaml").write_text(
        yaml.dump({"site": {"title": "Test Site", "description": "Test description"}})
    )
    (defaults / "build.yaml").write_text(
        yaml.dump({"build": {"parallel": True, "incremental": True}})
    )

    # Create environments/
    envs = config_dir / "environments"
    envs.mkdir()

    (envs / "local.yaml").write_text(yaml.dump({"build": {"debug": True, "strict_mode": False}}))
    (envs / "production.yaml").write_text(
        yaml.dump(
            {
                "site": {"baseurl": "https://example.com"},
                "build": {"debug": False, "strict_mode": True},
            }
        )
    )

    # Create profiles/
    profiles = config_dir / "profiles"
    profiles.mkdir()

    (profiles / "dev.yaml").write_text(
        yaml.dump({"observability": {"track_memory": True, "verbose": True}})
    )
    (profiles / "writer.yaml").write_text(
        yaml.dump({"observability": {"track_memory": False, "verbose": False}})
    )

    return config_dir


class TestConfigDirectoryLoader:
    """Test ConfigDirectoryLoader class."""

    def test_load_defaults_only(self, config_dir):
        """Test loading only default config."""
        loader = ConfigDirectoryLoader()

        config = loader.load(config_dir, environment="local", profile=None)

        # Check defaults loaded
        assert config["site"]["title"] == "Test Site"
        assert config["build"]["parallel"] is True

    def test_load_with_environment(self, config_dir):
        """Test loading with environment override."""
        loader = ConfigDirectoryLoader()

        config = loader.load(config_dir, environment="production")

        # Check environment override applied
        assert config["site"]["baseurl"] == "https://example.com"
        assert config["build"]["strict_mode"] is True
        # Check defaults still present
        assert config["site"]["title"] == "Test Site"

    def test_load_with_profile(self, config_dir):
        """Test loading with profile."""
        loader = ConfigDirectoryLoader()

        config = loader.load(config_dir, environment="local", profile="dev")

        # Check profile settings applied
        assert config["observability"]["track_memory"] is True
        assert config["observability"]["verbose"] is True

    def test_load_precedence(self, config_dir):
        """Test merge precedence: defaults < environment < profile."""
        loader = ConfigDirectoryLoader()

        # Add conflicting key in all three layers
        (config_dir / "_default" / "test.yaml").write_text(yaml.dump({"value": "default"}))
        (config_dir / "environments" / "production.yaml").write_text(
            yaml.dump({"value": "production"})
        )
        (config_dir / "profiles" / "dev.yaml").write_text(yaml.dump({"value": "profile"}))

        config = loader.load(config_dir, environment="production", profile="dev")

        # Profile should win (highest precedence)
        assert config["value"] == "profile"

    def test_load_auto_detect_environment(self, config_dir, monkeypatch):
        """Test environment auto-detection."""
        monkeypatch.setenv("NETLIFY", "true")
        monkeypatch.setenv("CONTEXT", "production")

        loader = ConfigDirectoryLoader()
        config = loader.load(config_dir, environment=None)  # Auto-detect

        # Should use production environment
        assert config["site"]["baseurl"] == "https://example.com"

    def test_load_with_features(self, config_dir):
        """Test feature expansion works."""
        # Add features config
        (config_dir / "_default" / "features.yaml").write_text(
            yaml.dump({"features": {"rss": True, "search": True}})
        )

        loader = ConfigDirectoryLoader()
        config = loader.load(config_dir, environment="local")

        # Features should be expanded
        assert config["generate_rss"] is True
        assert config["search"]["enabled"] is True
        # Features section should be removed
        assert "features" not in config

    def test_load_origin_tracking(self, config_dir):
        """Test origin tracking when enabled."""
        loader = ConfigDirectoryLoader(track_origins=True)

        # Load config (we only care about origin tracking, not the config itself)
        loader.load(config_dir, environment="production")

        tracker = loader.get_origin_tracker()
        assert tracker is not None

        # Check origins tracked correctly
        assert tracker.get_origin("site.title") == "_default"
        assert tracker.get_origin("site.baseurl") == "environments/production"

    def test_load_nonexistent_directory(self, tmp_path):
        """Test loading from nonexistent directory raises error."""
        loader = ConfigDirectoryLoader()

        with pytest.raises(ConfigLoadError, match="not found"):
            loader.load(tmp_path / "nonexistent")

        # Verify it extends BengalConfigError
        try:
            loader.load(tmp_path / "nonexistent")
        except ConfigLoadError as e:
            assert isinstance(e, BengalConfigError)

    def test_load_file_not_directory(self, tmp_path):
        """Test loading from file (not directory) raises error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test: value")

        loader = ConfigDirectoryLoader()

        with pytest.raises(ConfigLoadError, match="Not a directory"):
            loader.load(config_file)

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error."""
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)

        # Write invalid YAML
        (defaults / "bad.yaml").write_text("invalid: yaml: syntax: error:")

        loader = ConfigDirectoryLoader()

        with pytest.raises(ConfigLoadError, match="Invalid YAML"):
            loader.load(config_dir, environment="local")

    def test_load_missing_defaults_warns(self, tmp_path, monkeypatch):
        """Test loading without _default/ directory warns but continues."""
        # Clear GitHub Actions env vars to get truly empty config
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        loader = ConfigDirectoryLoader()

        # Should not raise, just warn (check logs if needed)
        config = loader.load(config_dir, environment="local")

        assert config == {}  # Empty config (no env overrides)

    def test_load_multiple_yaml_files_merged(self, config_dir):
        """Test multiple .yaml files in _default/ are merged."""
        loader = ConfigDirectoryLoader()

        config = loader.load(config_dir, environment="local")

        # Both site.yaml and build.yaml should be merged
        assert "site" in config
        assert "build" in config

    def test_load_yml_extension_supported(self, tmp_path):
        """Test .yml extension is supported."""
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)

        (defaults / "config.yml").write_text(yaml.dump({"title": "Test"}))

        loader = ConfigDirectoryLoader()
        config = loader.load(config_dir, environment="local")

        assert config["title"] == "Test"

    def test_load_environment_aliases(self, tmp_path):
        """Test environment file aliases (prod.yaml for production)."""
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)
        (defaults / "site.yaml").write_text(yaml.dump({"title": "Test"}))

        envs = config_dir / "environments"
        envs.mkdir()

        # Use alias "prod" instead of "production"
        (envs / "prod.yaml").write_text(yaml.dump({"baseurl": "https://example.com"}))

        loader = ConfigDirectoryLoader()
        config = loader.load(config_dir, environment="production")

        # Should find prod.yaml when looking for production
        assert config["baseurl"] == "https://example.com"

    def test_load_profile_not_found(self, config_dir):
        """Test loading with nonexistent profile continues gracefully."""
        loader = ConfigDirectoryLoader()

        # Should not raise, just skip profile
        config = loader.load(config_dir, environment="local", profile="nonexistent")

        # Should have defaults and environment, just no profile
        assert "site" in config
        assert "build" in config

    def test_load_environment_not_found(self, config_dir):
        """Test loading with nonexistent environment continues gracefully."""
        loader = ConfigDirectoryLoader()

        # Should not raise, just skip environment
        config = loader.load(config_dir, environment="nonexistent")

        # Should have defaults
        assert "site" in config
        assert "build" in config

    def test_load_deep_merge(self, config_dir):
        """Test deep merge of nested configurations."""
        # Add nested config that should merge
        (config_dir / "_default" / "nested.yaml").write_text(
            yaml.dump({"deep": {"level1": {"a": 1, "b": 2}}})
        )
        (config_dir / "environments" / "production.yaml").write_text(
            yaml.dump(
                {
                    "deep": {
                        "level1": {
                            "b": 3,  # Override
                            "c": 4,  # Add
                        }
                    }
                }
            )
        )

        loader = ConfigDirectoryLoader()
        config = loader.load(config_dir, environment="production")

        # Check deep merge worked
        assert config["deep"]["level1"]["a"] == 1  # From default
        assert config["deep"]["level1"]["b"] == 3  # Overridden
        assert config["deep"]["level1"]["c"] == 4  # Added

    def test_load_assets_config_flattened(self, config_dir):
        """Test that assets config fields are flattened for backward compatibility."""
        # Add assets config to production environment
        (config_dir / "environments" / "production.yaml").write_text(
            yaml.dump(
                {
                    "assets": {
                        "minify": False,
                        "fingerprint": False,
                        "optimize": True,
                    }
                }
            )
        )

        loader = ConfigDirectoryLoader()
        config = loader.load(config_dir, environment="production")

        # Check nested structure is preserved
        assert config["assets"]["minify"] is False
        assert config["assets"]["fingerprint"] is False
        assert config["assets"]["optimize"] is True

        # Check flattened keys exist (for backward compatibility)
        assert config["minify_assets"] is False
        assert config["fingerprint_assets"] is False
        assert config["optimize_assets"] is True

    def test_load_dev_config_flattened(self, config_dir):
        """Test that dev config fields are flattened for backward compatibility."""
        # Add dev config to production environment
        (config_dir / "environments" / "production.yaml").write_text(
            yaml.dump(
                {
                    "dev": {
                        "cache_templates": False,
                        "watch_backend": "auto",
                    }
                }
            )
        )

        loader = ConfigDirectoryLoader()
        config = loader.load(config_dir, environment="production")

        # Check nested structure is preserved
        assert config["dev"]["cache_templates"] is False
        assert config["dev"]["watch_backend"] == "auto"

        # Check flattened keys exist (for backward compatibility)
        assert config["cache_templates"] is False
        assert config["watch_backend"] == "auto"
