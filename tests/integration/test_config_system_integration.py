"""
Integration tests for config system integration with Site and CLI.

Tests verify:
- Site.from_config() correctly loads from config/ directory
- Environment and profile overrides work end-to-end
- CLI commands (build/serve) correctly pass environment/profile
- Backward compatibility with single-file configs
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

from bengal.core.site import Site


@pytest.fixture
def config_directory_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Create a test site with config/ directory structure.
    """
    # Disable environment auto-detection for tests
    monkeypatch.delenv("BENGAL_ENV", raising=False)
    monkeypatch.delenv("NETLIFY", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    
    root = tmp_path / "site"
    root.mkdir()

    # Create config directory
    config_dir = root / "config"
    config_dir.mkdir()

    # Create _default configs
    default_dir = config_dir / "_default"
    default_dir.mkdir()

    default_site = {"site": {"title": "Default Site", "baseurl": "https://example.com", "author": "Default Author"}}
    (default_dir / "site.yaml").write_text(yaml.dump(default_site))

    default_build = {"build": {"parallel": True, "max_workers": 4}}
    (default_dir / "build.yaml").write_text(yaml.dump(default_build))

    # Create environment configs
    env_dir = config_dir / "environments"
    env_dir.mkdir()

    local_env = {"site": {"baseurl": "http://localhost:8000"}, "build": {"parallel": False}}
    (env_dir / "local.yaml").write_text(yaml.dump(local_env))

    prod_env = {"site": {"baseurl": "https://prod.example.com"}, "build": {"parallel": True}}
    (env_dir / "production.yaml").write_text(yaml.dump(prod_env))

    # Create profile configs
    profile_dir = config_dir / "profiles"
    profile_dir.mkdir()

    dev_profile = {"debug": True, "build": {"parallel": False}}
    (profile_dir / "dev.yaml").write_text(yaml.dump(dev_profile))

    # Create content directory
    content_dir = root / "content"
    content_dir.mkdir()

    return root


@pytest.fixture
def single_file_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Create a test site with single bengal.yaml config (legacy).
    """
    # Disable environment auto-detection for tests
    monkeypatch.delenv("BENGAL_ENV", raising=False)
    monkeypatch.delenv("NETLIFY", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    
    root = tmp_path / "site"
    root.mkdir()

    config = {
        "site": {
            "title": "Single File Site",
            "baseurl": "https://single.example.com",
        },
        "build": {"parallel": True},
    }
    (root / "bengal.yaml").write_text(yaml.dump(config))

    # Create content directory
    content_dir = root / "content"
    content_dir.mkdir()

    return root


class TestSiteFromConfigDirectory:
    """Test Site.from_config() with config/ directory."""

    def test_load_defaults(self, config_directory_site: Path):
        """
        Test loading default configuration.
        
        Note: Without explicit environment, auto-detects to "local" and applies
        local.yaml overrides. To test pure defaults, use non-existent environment.
        """
        # Use non-existent environment to get pure defaults
        site = Site.from_config(config_directory_site, environment="testing")

        assert site.config["title"] == "Default Site"
        assert site.config["baseurl"] == "https://example.com"
        assert site.config["author"] == "Default Author"
        assert site.config["parallel"] is True  # Flattened from build.parallel
        assert site.config["max_workers"] == 4  # Flattened from build.max_workers

    def test_load_with_environment(self, config_directory_site: Path):
        """Test environment overrides."""
        site = Site.from_config(config_directory_site, environment="local")

        assert site.config["title"] == "Default Site"
        assert site.config["baseurl"] == "http://localhost:8000"  # overridden
        assert site.config["parallel"] is False  # overridden (flattened)
        assert site.config["max_workers"] == 4  # not overridden (flattened)

    def test_load_with_production_environment(self, config_directory_site: Path):
        """Test production environment overrides."""
        site = Site.from_config(config_directory_site, environment="production")

        assert site.config["baseurl"] == "https://prod.example.com"  # overridden
        assert site.config["parallel"] is True  # flattened

    def test_load_with_profile(self, config_directory_site: Path):
        """Test profile overrides."""
        site = Site.from_config(config_directory_site, environment="testing", profile="dev")

        assert site.config["debug"] is True  # from profile
        assert site.config["parallel"] is False  # from profile (flattened)
        assert site.config["max_workers"] == 4  # not overridden (flattened)

    def test_load_with_environment_and_profile(self, config_directory_site: Path):
        """Test environment + profile together (profile takes precedence)."""
        site = Site.from_config(config_directory_site, environment="production", profile="dev")

        # From production environment
        assert site.config["baseurl"] == "https://prod.example.com"

        # From dev profile (overrides environment)
        assert site.config["debug"] is True
        assert site.config["parallel"] is False  # profile wins (flattened)


class TestSiteFromSingleFile:
    """Test Site.from_config() backward compatibility with single file."""

    def test_load_single_file(self, single_file_site: Path):
        """Test loading from single bengal.yaml file."""
        site = Site.from_config(single_file_site)

        assert site.config["title"] == "Single File Site"
        assert site.config["baseurl"] == "https://single.example.com"
        assert site.config.get("parallel") is True  # Flattened from build.parallel

    def test_single_file_ignores_environment(self, single_file_site: Path):
        """Environment parameter is ignored for single-file configs."""
        site = Site.from_config(single_file_site, environment="production")

        # Should still load single file config (environment ignored)
        assert site.config["title"] == "Single File Site"

    def test_single_file_ignores_profile(self, single_file_site: Path):
        """Profile parameter is ignored for single-file configs."""
        site = Site.from_config(single_file_site, profile="dev")

        # Should still load single file config (profile ignored)
        assert site.config["title"] == "Single File Site"


class TestConfigPrecedence:
    """Test configuration precedence rules."""

    def test_precedence_environment_over_default(self, config_directory_site: Path):
        """Environment overrides defaults."""
        site = Site.from_config(config_directory_site, environment="local")

        # Local environment should override default baseurl
        assert site.config["baseurl"] == "http://localhost:8000"

    def test_precedence_profile_over_environment(self, config_directory_site: Path):
        """Profile overrides environment."""
        site = Site.from_config(config_directory_site, environment="production", profile="dev")

        # Production sets parallel=True, but dev profile sets parallel=False
        # Profile should win
        assert site.config["build"]["parallel"] is False


class TestFeatureExpansion:
    """Test feature expansion in directory configs."""

    def test_rss_feature_expands(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that rss: true expands to generate_rss and output_formats."""
        # Disable environment auto-detection
        monkeypatch.delenv("BENGAL_ENV", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        
        root = tmp_path / "site"
        root.mkdir()

        config_dir = root / "config"
        config_dir.mkdir()

        default_dir = config_dir / "_default"
        default_dir.mkdir()

        features = {"features": {"rss": True}}
        (default_dir / "features.yaml").write_text(yaml.dump(features))

        content_dir = root / "content"
        content_dir.mkdir()

        site = Site.from_config(root, environment="testing")

        # RSS should be expanded to generate_rss flag
        assert site.config.get("generate_rss") is True
        # And output formats should include rss in site_wide
        output_formats = site.config.get("output_formats", {})
        if isinstance(output_formats, dict):
            assert "rss" in output_formats.get("site_wide", [])

    def test_sitemap_feature_expands(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that sitemap: true expands to generate_sitemap and output_formats."""
        # Disable environment auto-detection
        monkeypatch.delenv("BENGAL_ENV", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        
        root = tmp_path / "site"
        root.mkdir()

        config_dir = root / "config"
        config_dir.mkdir()

        default_dir = config_dir / "_default"
        default_dir.mkdir()

        features = {"features": {"sitemap": True}}
        (default_dir / "features.yaml").write_text(yaml.dump(features))

        content_dir = root / "content"
        content_dir.mkdir()

        site = Site.from_config(root, environment="testing")

        # Sitemap should be expanded to generate_sitemap flag
        assert site.config.get("generate_sitemap") is True


class TestErrorHandling:
    """Test error handling in config loading."""

    def test_invalid_yaml_raises_error(self, tmp_path: Path):
        """Invalid YAML should raise ConfigLoadError."""
        root = tmp_path / "site"
        root.mkdir()

        config_dir = root / "config"
        config_dir.mkdir()

        default_dir = config_dir / "_default"
        default_dir.mkdir()

        # Write invalid YAML
        (default_dir / "site.yaml").write_text("invalid: yaml: syntax: error:")

        from bengal.config.directory_loader import ConfigLoadError

        with pytest.raises(ConfigLoadError):
            Site.from_config(root)

    def test_missing_config_graceful(self, tmp_path: Path):
        """Missing config directory should not crash."""
        root = tmp_path / "site"
        root.mkdir()

        # No config directory or config file
        # Should create site with empty config (or raise graceful error)
        # (Current behavior may vary, but should not crash hard)
        try:
            site = Site.from_config(root)
            assert site.config is not None  # At least empty dict
        except Exception as e:
            # Should be a friendly error, not a crash
            assert "config" in str(e).lower()

