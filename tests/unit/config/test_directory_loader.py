"""Tests for directory-based config loader."""

import pytest
import yaml

from bengal.config.unified_loader import UnifiedConfigLoader, ConfigLoadError
from bengal.errors import BengalConfigError, ErrorCode


@pytest.fixture
def config_dir(tmp_path):
    """Create a test config directory structure."""
    # UnifiedConfigLoader expects site_root, so config_dir is tmp_path / "config"
    # and site_root is tmp_path
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
        loader = UnifiedConfigLoader()

        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="local", profile=None)
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Check defaults loaded (nested structure)
        assert config["site"]["title"] == "Test Site"
        assert config["build"]["parallel"] is True

    def test_load_with_environment(self, config_dir):
        """Test loading with environment override."""
        loader = UnifiedConfigLoader()

        config = loader.load(config_dir, environment="production")

        # Check environment override applied
        assert config["site"]["baseurl"] == "https://example.com"
        assert config["build"]["strict_mode"] is True
        # Check defaults still present
        assert config["site"]["title"] == "Test Site"

    def test_load_with_profile(self, config_dir):
        """Test loading with profile."""
        loader = UnifiedConfigLoader()

        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="local", profile="dev")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Check profile settings applied
        assert config["observability"]["track_memory"] is True
        assert config["observability"]["verbose"] is True

    def test_load_precedence(self, config_dir):
        """Test merge precedence: defaults < environment < profile."""
        loader = UnifiedConfigLoader()

        # Add conflicting key in all three layers
        (config_dir / "_default" / "test.yaml").write_text(yaml.dump({"value": "default"}))
        (config_dir / "environments" / "production.yaml").write_text(
            yaml.dump({"value": "production"})
        )
        (config_dir / "profiles" / "dev.yaml").write_text(yaml.dump({"value": "profile"}))

        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="production", profile="dev")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Profile should win (highest precedence)
        assert config["value"] == "profile"

    def test_load_auto_detect_environment(self, config_dir, monkeypatch):
        """Test environment auto-detection."""
        monkeypatch.setenv("NETLIFY", "true")
        monkeypatch.setenv("CONTEXT", "production")

        loader = UnifiedConfigLoader()
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment=None)  # Auto-detect
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Should use production environment
        assert config["site"]["baseurl"] == "https://example.com"

    def test_load_with_features(self, config_dir):
        """Test feature expansion works."""
        # Add features config
        (config_dir / "_default" / "features.yaml").write_text(
            yaml.dump({"features": {"rss": True, "search": True}})
        )

        loader = UnifiedConfigLoader()
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="local")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Features should be expanded
        assert config["generate_rss"] is True
        assert config["search"]["enabled"] is True
        # Features section should be removed
        assert "features" not in config

    def test_load_origin_tracking(self, config_dir):
        """Test origin tracking when enabled."""
        loader = ConfigDirectoryLoader(track_origins=True)

        # Load config (we only care about origin tracking, not the config itself)
        site_root = config_dir.parent
        loader.load(site_root, environment="production")

        tracker = loader.get_origin_tracker()
        assert tracker is not None

        # Check origins tracked correctly
        assert tracker.get_origin("site.title") == "_default"
        assert tracker.get_origin("site.baseurl") == "environments/production"

    def test_load_nonexistent_directory(self, tmp_path):
        """Test loading from nonexistent directory raises error."""
        loader = UnifiedConfigLoader()

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

        loader = UnifiedConfigLoader()

        with pytest.raises(ConfigLoadError, match="Not a directory"):
            loader.load(config_file)

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error."""
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)

        # Write invalid YAML
        (defaults / "bad.yaml").write_text("invalid: yaml: syntax: error:")

        loader = UnifiedConfigLoader()

        with pytest.raises(ConfigLoadError, match="Invalid YAML"):
            loader.load(config_dir, environment="local")

    def test_load_missing_defaults_inherits_bengal_defaults(self, tmp_path, monkeypatch):
        """Test loading without _default/ directory inherits Bengal DEFAULTS."""
        # Clear environment variables to avoid baseurl overrides
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        loader = UnifiedConfigLoader()

        # Should not raise, and should have Bengal DEFAULTS applied
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="local")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Should inherit key defaults that enable search by default
        # Note: features.rss expands to add 'rss' to site_wide
        assert "index_json" in config["output_formats"]["site_wide"]
        assert config["search"]["enabled"] is True

    def test_load_multiple_yaml_files_merged(self, config_dir):
        """Test multiple .yaml files in _default/ are merged."""
        loader = UnifiedConfigLoader()

        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="local")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Both site.yaml and build.yaml should be merged
        assert "site" in config
        assert "build" in config

    def test_load_yml_extension_supported(self, tmp_path):
        """Test .yml extension is supported."""
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)

        (defaults / "config.yml").write_text(yaml.dump({"title": "Test"}))

        loader = UnifiedConfigLoader()
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="local")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Config is now nested - access via site.title
        assert config["site"]["title"] == "Test"

    def test_load_environment_aliases(self, tmp_path):
        """Test environment file aliases (prod.yaml for production)."""
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)
        (defaults / "site.yaml").write_text(yaml.dump({"site": {"title": "Test"}}))

        envs = config_dir / "environments"
        envs.mkdir()

        # Use alias "prod" instead of "production"
        (envs / "prod.yaml").write_text(yaml.dump({"site": {"baseurl": "https://example.com"}}))

        loader = UnifiedConfigLoader()
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="production")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Should find prod.yaml when looking for production
        assert config["site"]["baseurl"] == "https://example.com"

    def test_load_profile_not_found(self, config_dir):
        """Test loading with nonexistent profile continues gracefully."""
        loader = UnifiedConfigLoader()

        # Should not raise, just skip profile
        config = loader.load(config_dir, environment="local", profile="nonexistent")

        # Should have defaults and environment, just no profile
        assert "site" in config
        assert "build" in config

    def test_load_environment_not_found(self, config_dir):
        """Test loading with nonexistent environment continues gracefully."""
        loader = UnifiedConfigLoader()

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

        loader = UnifiedConfigLoader()
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

        loader = UnifiedConfigLoader()
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="production")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Check nested structure is preserved
        assert config["assets"]["minify"] is False
        assert config["assets"]["fingerprint"] is False
        assert config["assets"]["optimize"] is True

        # No flattening - access via assets.* only
        assert "minify_assets" not in config  # Should not be flattened
        assert config["assets"]["minify"] is False
        assert config["assets"]["fingerprint"] is False
        assert config["assets"]["optimize"] is True

    def test_load_dev_config_nested(self, config_dir):
        """Test that dev config fields are accessed via nested structure."""
        # Add dev config to production environment (nested structure)
        (config_dir / "environments" / "production.yaml").write_text(
            yaml.dump(
                {
                    "dev": {
                        "cache_templates": False,
                        "watch_backend": "auto",
                    },
                }
            )
        )

        loader = UnifiedConfigLoader()
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="production")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Check nested structure is preserved for dev-specific settings
        assert config["dev"]["watch_backend"] == "auto"
        assert config["dev"]["cache_templates"] is False

        # No flattening - access via dev.* only
        assert "watch_backend" not in config  # Should not be flattened


class TestDefaultsInheritance:
    """Test that directory configs inherit from Bengal DEFAULTS."""

    def test_directory_config_inherits_all_defaults(self, tmp_path, monkeypatch):
        """Directory-based configs should inherit from DEFAULTS as base layer."""
        # Clear environment variables to avoid overrides
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        config_dir = tmp_path / "config"
        defaults_dir = config_dir / "_default"
        defaults_dir.mkdir(parents=True)

        # Create minimal user config (just site title)
        (defaults_dir / "site.yaml").write_text(yaml.dump({"site": {"title": "My Site"}}))

        loader = UnifiedConfigLoader()
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="local")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # User config should be applied
        assert config["site"]["title"] == "My Site"

        # But should also have all DEFAULTS applied
        # Note: features.rss expands and adds 'rss' to site_wide list
        assert "index_json" in config["output_formats"]["site_wide"]
        assert config["search"]["enabled"] is True
        assert config["theme"]["name"] == "default"
        # Config is now nested - access via build.parallel
        assert config["build"]["parallel"] is True

    def test_user_config_overrides_defaults(self, tmp_path, monkeypatch):
        """User config should override inherited defaults."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        config_dir = tmp_path / "config"
        defaults_dir = config_dir / "_default"
        defaults_dir.mkdir(parents=True)

        # Explicitly disable search output AND disable features to prevent expansion
        (defaults_dir / "output.yaml").write_text(
            yaml.dump(
                {
                    "output_formats": {"site_wide": []},
                    "features": {"rss": False, "search": False},  # Disable feature expansion
                }
            )
        )

        loader = UnifiedConfigLoader()
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="local")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # User override should win - empty list since features are disabled
        assert config["output_formats"]["site_wide"] == []

    def test_explicit_search_disabled_respected(self, tmp_path, monkeypatch):
        """User can explicitly disable search via config."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        config_dir = tmp_path / "config"
        defaults_dir = config_dir / "_default"
        defaults_dir.mkdir(parents=True)

        # Explicitly disable search
        (defaults_dir / "search.yaml").write_text(yaml.dump({"search": {"enabled": False}}))

        loader = UnifiedConfigLoader()
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="local")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # User disabled search
        assert config["search"]["enabled"] is False

    def test_origin_tracking_shows_bengal_defaults(self, tmp_path, monkeypatch):
        """Origin tracking should show _bengal_defaults as base layer."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        config_dir = tmp_path / "config"
        defaults_dir = config_dir / "_default"
        defaults_dir.mkdir(parents=True)

        # Minimal user config
        (defaults_dir / "site.yaml").write_text(yaml.dump({"site": {"title": "My Site"}}))

        loader = ConfigDirectoryLoader(track_origins=True)
        loader.load(config_dir, environment="local")

        tracker = loader.get_origin_tracker()
        assert tracker is not None

        # User-provided value should be from _default
        assert tracker.get_origin("site.title") == "_default"

        # DEFAULTS-provided value should be from _bengal_defaults
        assert tracker.get_origin("output_formats.site_wide") == "_bengal_defaults"

    def test_search_works_without_features_yaml(self, tmp_path, monkeypatch):
        """Search should work even without features.yaml (Rosettes case)."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        config_dir = tmp_path / "config"
        defaults_dir = config_dir / "_default"
        defaults_dir.mkdir(parents=True)

        # Simulate Rosettes-style config: theme.yaml with search UI, but no features.yaml
        (defaults_dir / "theme.yaml").write_text(
            yaml.dump(
                {
                    "theme": {
                        "name": "default",
                        "features": ["search", "search.suggest", "search.highlight"],
                    }
                }
            )
        )
        (defaults_dir / "site.yaml").write_text(yaml.dump({"site": {"title": "Rosettes Docs"}}))

        loader = UnifiedConfigLoader()
        site_root = config_dir.parent
        config_obj = loader.load(site_root, environment="local")
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Search should work because DEFAULTS provides output_formats.site_wide
        # Note: features.rss from DEFAULTS will also add 'rss' to the list
        assert "index_json" in config["output_formats"]["site_wide"]
        assert config["search"]["enabled"] is True

        # Theme features are preserved (UI flags)
        assert "search" in config["theme"]["features"]


class TestSearchUIWarning:
    """Test warning when theme.features has search but no index will be generated."""

    def test_warns_when_search_ui_enabled_but_no_index(self, tmp_path, monkeypatch, capsys):
        """Should warn if theme.features has search but no index_json in site_wide."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        config_dir = tmp_path / "config"
        defaults_dir = config_dir / "_default"
        defaults_dir.mkdir(parents=True)

        # theme.yaml with search UI enabled
        (defaults_dir / "theme.yaml").write_text(
            yaml.dump(
                {
                    "theme": {
                        "features": ["search", "search.suggest"],
                    }
                }
            )
        )
        # Disable search feature to prevent index_json
        (defaults_dir / "output.yaml").write_text(
            yaml.dump(
                {
                    "output_formats": {"site_wide": []},
                    "features": {"search": False, "rss": False},
                }
            )
        )

        loader = UnifiedConfigLoader()
        loader.load(config_dir, environment="local")

        # Bengal's custom logger prints warnings to stdout
        # Check that the warning was printed
        captured = capsys.readouterr()
        assert "search_ui_without_index" in captured.out

    def test_no_warning_when_index_json_present(self, tmp_path, monkeypatch, capsys):
        """Should NOT warn if index_json is in site_wide."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        config_dir = tmp_path / "config"
        defaults_dir = config_dir / "_default"
        defaults_dir.mkdir(parents=True)

        # theme.yaml with search UI enabled
        (defaults_dir / "theme.yaml").write_text(
            yaml.dump(
                {
                    "theme": {
                        "features": ["search"],
                    }
                }
            )
        )
        # Output formats includes index_json
        (defaults_dir / "output.yaml").write_text(
            yaml.dump({"output_formats": {"site_wide": ["index_json"]}})
        )

        loader = UnifiedConfigLoader()
        loader.load(config_dir, environment="local")

        # Should NOT have warned
        captured = capsys.readouterr()
        assert "search_ui_without_index" not in captured.out

    def test_no_warning_when_no_search_in_theme_features(self, tmp_path, monkeypatch, capsys):
        """Should NOT warn if search is not in theme.features."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        config_dir = tmp_path / "config"
        defaults_dir = config_dir / "_default"
        defaults_dir.mkdir(parents=True)

        # theme.yaml WITHOUT search in features
        (defaults_dir / "theme.yaml").write_text(
            yaml.dump(
                {
                    "theme": {
                        "features": ["navigation.toc"],
                    }
                }
            )
        )
        # No index_json
        (defaults_dir / "output.yaml").write_text(
            yaml.dump(
                {
                    "output_formats": {"site_wide": []},
                    "features": {"search": False, "rss": False},
                }
            )
        )

        loader = UnifiedConfigLoader()
        loader.load(config_dir, environment="local")

        # Should NOT have warned (no search UI to trigger the warning)
        captured = capsys.readouterr()
        assert "search_ui_without_index" not in captured.out


class TestConfigLoadErrorCodes:
    """Test that ConfigLoadError includes appropriate error codes."""

    def test_missing_directory_has_error_code(self, tmp_path):
        """Verify ConfigLoadError includes C005 for missing directory."""
        loader = UnifiedConfigLoader()
        missing_dir = tmp_path / "nonexistent"

        with pytest.raises(ConfigLoadError) as exc_info:
            loader.load(missing_dir)

        assert exc_info.value.code == ErrorCode.C005
        assert "not found" in str(exc_info.value).lower()

    def test_not_a_directory_has_error_code(self, tmp_path):
        """Verify ConfigLoadError includes C003 for path that is not a directory."""
        loader = UnifiedConfigLoader()
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test: value")

        with pytest.raises(ConfigLoadError) as exc_info:
            loader.load(config_file)

        assert exc_info.value.code == ErrorCode.C003
        assert "not a directory" in str(exc_info.value).lower()

    def test_yaml_parse_error_has_error_code(self, tmp_path):
        """Verify ConfigLoadError includes C001 for YAML parse errors."""
        loader = UnifiedConfigLoader()
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)

        # Create invalid YAML
        (defaults / "bad.yaml").write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigLoadError) as exc_info:
            loader.load(config_dir, environment="local")

        assert exc_info.value.code == ErrorCode.C001
        assert "invalid yaml" in str(exc_info.value).lower()
