"""
Unit tests for ConfigService.

Verifies that ConfigService provides correct immutable access to all
configuration-derived properties. Tests both direct construction and
the from_config factory method.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.services.config import ConfigService


@pytest.fixture
def basic_config() -> dict:
    """Basic configuration for testing."""
    return {
        "title": "Test Blog",
        "site": {
            "description": "A test blog",
            "author": "Jane Doe",
            "favicon": "/favicon.ico",
            "logo_image": "/logo.png",
            "logo_text": "Test Logo",
        },
        "baseurl": "/blog",
        "params": {"repo_url": "https://github.com/test/repo"},
        "content": {"dir": "docs"},
        "build": {"parallel": True, "output_dir": "dist"},
        "assets": {"pipeline": True},
        "i18n": {"default_language": "en"},
        "menu": {"main": [{"name": "Home", "url": "/"}]},
        "output": {"dir": "public"},
    }


@pytest.fixture
def config_service(basic_config: dict, tmp_path: Path) -> ConfigService:
    """Create a ConfigService instance for testing."""
    return ConfigService.from_config(basic_config, tmp_path)


class TestConfigServiceConstruction:
    """Test ConfigService construction."""

    def test_from_config_returns_frozen_instance(self, config_service: ConfigService) -> None:
        """ConfigService should be frozen (immutable)."""
        with pytest.raises(AttributeError):
            config_service.config = {}  # type: ignore[misc]

    def test_from_config_computes_paths(self, config_service: ConfigService) -> None:
        """Paths should be eagerly computed."""
        from bengal.cache.paths import BengalPaths

        assert isinstance(config_service.paths, BengalPaths)

    def test_from_config_computes_config_hash(self, config_service: ConfigService) -> None:
        """Config hash should be eagerly computed as a hex string."""
        assert isinstance(config_service.config_hash, str)
        assert len(config_service.config_hash) > 0

    def test_from_config_computes_theme(self, config_service: ConfigService) -> None:
        """Theme should be eagerly computed."""
        from bengal.core.theme import Theme

        assert isinstance(config_service.theme_obj, Theme)

    def test_same_config_produces_same_hash(self, basic_config: dict, tmp_path: Path) -> None:
        """Same config should produce deterministic hash."""
        svc1 = ConfigService.from_config(basic_config, tmp_path)
        svc2 = ConfigService.from_config(basic_config, tmp_path)
        assert svc1.config_hash == svc2.config_hash

    def test_different_config_produces_different_hash(self, tmp_path: Path) -> None:
        """Different config should produce different hash."""
        svc1 = ConfigService.from_config({"title": "A"}, tmp_path)
        svc2 = ConfigService.from_config({"title": "B"}, tmp_path)
        assert svc1.config_hash != svc2.config_hash


class TestPureAccessors:
    """Test pure config accessor properties."""

    def test_title(self, config_service: ConfigService) -> None:
        """Title should come from config."""
        assert config_service.title == "Test Blog"

    def test_title_missing(self, tmp_path: Path) -> None:
        """Title should be None when not configured."""
        svc = ConfigService.from_config({}, tmp_path)
        assert svc.title is None

    def test_description(self, config_service: ConfigService) -> None:
        """Description should come from site section."""
        assert config_service.description == "A test blog"

    def test_description_missing(self, tmp_path: Path) -> None:
        """Description should be None when not configured."""
        svc = ConfigService.from_config({}, tmp_path)
        assert svc.description is None

    def test_baseurl(self, config_service: ConfigService) -> None:
        """Baseurl should come from flat config."""
        assert config_service.baseurl == "/blog"

    def test_baseurl_missing(self, tmp_path: Path) -> None:
        """Baseurl should be None when not configured."""
        svc = ConfigService.from_config({}, tmp_path)
        assert svc.baseurl is None

    def test_content_dir(self, config_service: ConfigService, tmp_path: Path) -> None:
        """Content dir should be computed from config."""
        assert config_service.content_dir == tmp_path / "docs"

    def test_content_dir_default(self, tmp_path: Path) -> None:
        """Content dir should default to 'content'."""
        svc = ConfigService.from_config({}, tmp_path)
        assert svc.content_dir == tmp_path / "content"

    def test_author(self, config_service: ConfigService) -> None:
        """Author should come from site section."""
        assert config_service.author == "Jane Doe"

    def test_favicon(self, config_service: ConfigService) -> None:
        """Favicon should come from site section."""
        assert config_service.favicon == "/favicon.ico"

    def test_logo_image(self, config_service: ConfigService) -> None:
        """Logo image should come from site section."""
        assert config_service.logo_image == "/logo.png"

    def test_logo_text(self, config_service: ConfigService) -> None:
        """Logo text should come from site section."""
        assert config_service.logo_text == "Test Logo"

    def test_params(self, config_service: ConfigService) -> None:
        """Params should come from params section."""
        assert config_service.params == {"repo_url": "https://github.com/test/repo"}

    def test_params_empty(self, tmp_path: Path) -> None:
        """Params should default to empty dict."""
        svc = ConfigService.from_config({}, tmp_path)
        assert svc.params == {}

    def test_logo(self, tmp_path: Path) -> None:
        """Logo should come from config."""
        svc = ConfigService.from_config({"logo_image": "/logo.svg"}, tmp_path)
        assert svc.logo == "/logo.svg"

    def test_logo_empty(self, tmp_path: Path) -> None:
        """Logo should be empty string when not configured."""
        svc = ConfigService.from_config({}, tmp_path)
        assert svc.logo == ""


class TestConfigSectionAccessors:
    """Test config section accessor properties."""

    def test_assets_config(self, config_service: ConfigService) -> None:
        """Assets config should come from assets section."""
        assert config_service.assets_config == {"pipeline": True}

    def test_build_config(self, config_service: ConfigService) -> None:
        """Build config should come from build section."""
        assert config_service.build_config == {"parallel": True, "output_dir": "dist"}

    def test_i18n_config(self, config_service: ConfigService) -> None:
        """I18n config should come from i18n section."""
        assert config_service.i18n_config == {"default_language": "en"}

    def test_menu_config(self, config_service: ConfigService) -> None:
        """Menu config should come from menu section."""
        assert "main" in config_service.menu_config

    def test_content_config(self, config_service: ConfigService) -> None:
        """Content config should come from content section."""
        assert config_service.content_config == {"dir": "docs"}

    def test_output_config(self, config_service: ConfigService) -> None:
        """Output config should come from output section."""
        assert config_service.output_config == {"dir": "public"}

    def test_missing_sections_return_empty_dict(self, tmp_path: Path) -> None:
        """Missing config sections should return empty dicts."""
        svc = ConfigService.from_config({}, tmp_path)
        assert svc.assets_config == {}
        assert svc.build_config == {}
        assert svc.i18n_config == {}
        assert svc.menu_config == {}
        assert svc.content_config == {}
        assert svc.output_config == {}


class TestThemeConfig:
    """Test theme configuration access."""

    def test_theme_config_returns_theme(self, config_service: ConfigService) -> None:
        """theme_config should return a Theme instance."""
        from bengal.core.theme import Theme

        assert isinstance(config_service.theme_config, Theme)

    def test_theme_config_matches_theme_obj(self, config_service: ConfigService) -> None:
        """theme_config should return the eagerly computed theme_obj."""
        assert config_service.theme_config is config_service.theme_obj
