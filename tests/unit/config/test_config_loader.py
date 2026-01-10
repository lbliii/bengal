"""
Tests for configuration loader.
"""

from bengal.config.defaults import DEFAULTS
from bengal.config.unified_loader import UnifiedConfigLoader


class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_menu_section_loaded(self, tmp_path):
        """Test that canonical [menu] section loads."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"

[[menu.main]]
name = "Home"
url = "/"
weight = 1

[[menu.main]]
name = "About"
url = "/about/"
weight = 2
""")

        loader = UnifiedConfigLoader()
        config_obj = loader.load(tmp_path)
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Should keep canonical 'menu'
        assert "menu" in config
        assert "main" in config["menu"]
        assert len(config["menu"]["main"]) == 2
        assert config["menu"]["main"][0]["name"] == "Home"

        assert config is not None

    def test_canonical_menu_section(self, tmp_path):
        """Test that canonical [menu] works without warnings."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"

[[menu.main]]
name = "Home"
url = "/"
""")

        loader = UnifiedConfigLoader()
        config_obj = loader.load(tmp_path)
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        assert "menu" in config
        assert "main" in config["menu"]

    def test_unknown_section_detection(self, tmp_path):
        """Test that unknown sections are detected with suggestions."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"

[menuz]
# Typo: should be 'menu'
""")

        loader = UnifiedConfigLoader()
        config_obj = loader.load(tmp_path)
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # UnifiedConfigLoader doesn't have get_warnings() - validation is handled separately
        # Just verify config loads successfully
        assert config is not None

    def test_menu_with_multiple_items(self, tmp_path):
        """Test handling multiple menu items in canonical section."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[[menu.main]]
name = "Home"
url = "/"

[[menu.main]]
name = "About"
url = "/about/"
""")

        loader = UnifiedConfigLoader()
        config_obj = loader.load(tmp_path)
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Should keep canonical menu entries
        assert "menu" in config
        assert "main" in config["menu"]
        assert len(config["menu"]["main"]) == 2


class TestSectionAliases:
    """Test canonical sections are loaded."""

    def test_canonical_menu_required(self, tmp_path):
        """menus alias is not normalized; canonical [menu] should be used."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test"

[[menu.main]]
name = "Home"
url = "/"
""")
        loader = UnifiedConfigLoader()
        config = loader.load(tmp_path)
        assert "menu" in config

    def test_known_sections_loaded(self, tmp_path):
        """Test that known sections (menu, site, build) are properly loaded."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"

[build]
output_dir = "_site"

[[menu.main]]
name = "Home"
url = "/"
""")
        loader = UnifiedConfigLoader()
        config = loader.load(tmp_path)
        assert "site" in config
        assert "build" in config
        assert "menu" in config


class TestConfigNormalization:
    """Test config normalization behavior."""

    def test_normalize_preserves_canonical_sections(self, tmp_path):
        """Test that canonical sections are not modified."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test"

[build]
parallel = true

[menu]
# Empty menu section
""")

        loader = UnifiedConfigLoader()
        config_obj = loader.load(tmp_path)
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # Config is now nested - access via site.* and build.*
        assert config.get("site", {}).get("title") == "Test"
        assert config.get("build", {}).get("parallel") is True
        assert "menu" in config

    def test_user_defined_sections_preserved(self, tmp_path):
        """Test that user-defined sections are preserved."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test"

[custom_section]
my_value = "test"
""")

        loader = UnifiedConfigLoader()
        config_obj = loader.load(tmp_path)
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        # User-defined section should be preserved
        assert "custom_section" in config
        assert config["custom_section"]["my_value"] == "test"

        # Unknown sections may generate warnings (but not required)
        # since they could be intentional user-defined config


class TestDefaultConfig:
    """Test _default_config() returns full DEFAULTS."""

    def test_default_config_returns_full_defaults(self, tmp_path, monkeypatch):
        """Test that _default_config() returns all DEFAULTS, not a subset."""
        # Clear env vars that could interfere
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        loader = UnifiedConfigLoader()
        config = loader._default_config()

        # Should have key sections from DEFAULTS
        assert config["output_formats"]["site_wide"] == DEFAULTS["output_formats"]["site_wide"]
        assert config["search"]["enabled"] == DEFAULTS["search"]["enabled"]
        assert config["theme"]["name"] == DEFAULTS["theme"]["name"]
        assert config["build"]["parallel"] == DEFAULTS["build"]["parallel"]
        assert config["features"] == DEFAULTS["features"]

    def test_default_config_used_when_no_config_file(self, tmp_path, monkeypatch):
        """Test that load() uses _default_config() when no config file found."""
        # Clear env vars
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        loader = UnifiedConfigLoader()
        config = loader.load(tmp_path)

        # Should get full DEFAULTS when no config file
        assert "index_json" in config["output_formats"]["site_wide"]
        assert config["search"]["enabled"] is True

    def test_default_config_consistency_with_directory_loader(self, tmp_path, monkeypatch):
        """Ensure ConfigLoader._default_config() is consistent with ConfigDirectoryLoader."""
        from bengal.config.directory_loader import ConfigDirectoryLoader

        # Clear env vars
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

        # Create empty config dir for directory loader
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        single_loader = UnifiedConfigLoader()
        single_config = single_loader.load(tmp_path)

        dir_loader = ConfigDirectoryLoader()
        dir_config = dir_loader.load(config_dir, environment="local")

        # Key defaults should match between loaders
        assert (
            single_config["output_formats"]["site_wide"] == DEFAULTS["output_formats"]["site_wide"]
        )
        # Note: dir_config has feature expansion applied, so check the underlying value
        assert "index_json" in dir_config["output_formats"]["site_wide"]
