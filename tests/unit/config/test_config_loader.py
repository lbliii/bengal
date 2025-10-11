"""
Tests for configuration loader.
"""


from bengal.config.loader import ConfigLoader


class TestConfigLoader:
    """Test ConfigLoader class."""
    
    def test_section_alias_menus_to_menu(self, tmp_path):
        """Test that [menus] is normalized to [menu]."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"

[[menus.main]]
name = "Home"
url = "/"
weight = 1

[[menus.main]]
name = "About"
url = "/about/"
weight = 2
""")
        
        loader = ConfigLoader(tmp_path)
        config = loader.load(config_file)
        
        # Should be normalized to 'menu'
        assert 'menu' in config
        assert 'main' in config['menu']
        assert len(config['menu']['main']) == 2
        assert config['menu']['main'][0]['name'] == "Home"
        
        # Should have warning about using [menus]
        warnings = loader.get_warnings()
        assert len(warnings) > 0
        assert any('menus' in w and 'menu' in w for w in warnings)
    
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
        
        loader = ConfigLoader(tmp_path)
        config = loader.load(config_file)
        
        assert 'menu' in config
        assert 'main' in config['menu']
        
        # Should have no warnings for canonical form
        warnings = loader.get_warnings()
        # Filter out warnings not about menu/menus
        menu_warnings = [w for w in warnings if 'menu' in w.lower()]
        assert len(menu_warnings) == 0
    
    def test_unknown_section_detection(self, tmp_path):
        """Test that unknown sections are detected with suggestions."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"

[menuz]
# Typo: should be 'menu'
""")
        
        loader = ConfigLoader(tmp_path)
        loader.load(config_file)
        
        warnings = loader.get_warnings()
        assert len(warnings) > 0
        # Should suggest 'menu' for 'menuz'
        assert any('menuz' in w and 'menu' in w for w in warnings)
    
    def test_both_menu_and_menus_defined(self, tmp_path):
        """Test handling when both [menu] and [menus] are present."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[[menu.main]]
name = "Home"
url = "/"

[[menus.main]]
name = "About"
url = "/about/"
""")
        
        loader = ConfigLoader(tmp_path)
        config = loader.load(config_file)
        
        # Should normalize menus to menu
        assert 'menu' in config
        assert 'main' in config['menu']
        # Both items should be present (merged during TOML parsing)
        assert len(config['menu']['main']) >= 1
        
        # Should warn about using menus
        warnings = loader.get_warnings()
        assert any('menus' in w.lower() and 'menu' in w.lower() for w in warnings)
    
    def test_get_warnings(self, tmp_path):
        """Test get_warnings() method."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test"

[[menus.main]]
name = "Test"
url = "/"
""")
        
        loader = ConfigLoader(tmp_path)
        loader.load(config_file)
        
        warnings = loader.get_warnings()
        assert isinstance(warnings, list)
        assert len(warnings) > 0
    
    def test_print_warnings_verbose_false(self, tmp_path, capsys):
        """Test that print_warnings doesn't print when verbose=False."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[[menus.main]]
name = "Test"
url = "/"
""")
        
        loader = ConfigLoader(tmp_path)
        loader.load(config_file)
        loader.print_warnings(verbose=False)
        
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_print_warnings_verbose_true(self, tmp_path, capsys):
        """Test that print_warnings prints when verbose=True."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[[menus.main]]
name = "Test"
url = "/"
""")
        
        loader = ConfigLoader(tmp_path)
        loader.load(config_file)
        loader.print_warnings(verbose=True)
        
        captured = capsys.readouterr()
        assert 'menus' in captured.out.lower()
        assert 'menu' in captured.out.lower()


class TestSectionAliases:
    """Test section alias mappings."""
    
    def test_section_aliases_defined(self):
        """Test that SECTION_ALIASES is properly defined."""
        assert hasattr(ConfigLoader, 'SECTION_ALIASES')
        assert isinstance(ConfigLoader.SECTION_ALIASES, dict)
        assert 'menus' in ConfigLoader.SECTION_ALIASES
        assert ConfigLoader.SECTION_ALIASES['menus'] == 'menu'
    
    def test_known_sections_defined(self):
        """Test that KNOWN_SECTIONS is properly defined."""
        assert hasattr(ConfigLoader, 'KNOWN_SECTIONS')
        assert isinstance(ConfigLoader.KNOWN_SECTIONS, set)
        assert 'menu' in ConfigLoader.KNOWN_SECTIONS
        assert 'site' in ConfigLoader.KNOWN_SECTIONS
        assert 'build' in ConfigLoader.KNOWN_SECTIONS


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
        
        loader = ConfigLoader(tmp_path)
        config = loader.load(config_file)
        
        # Canonical sections should be accessible (flattened)
        # 'site' and 'build' get flattened, so check their values
        assert config.get('title') == "Test"
        assert config.get('parallel')
        assert 'menu' in config
    
    def test_user_defined_sections_preserved(self, tmp_path):
        """Test that user-defined sections are preserved."""
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test"

[custom_section]
my_value = "test"
""")
        
        loader = ConfigLoader(tmp_path)
        config = loader.load(config_file)
        
        # User-defined section should be preserved
        assert 'custom_section' in config
        assert config['custom_section']['my_value'] == "test"
        
        # Unknown sections may generate warnings (but not required)
        # since they could be intentional user-defined config

