"""
Tests for autodoc configuration loader.
"""

from pathlib import Path
from textwrap import dedent


from bengal.autodoc.config import load_autodoc_config, get_python_config


def test_load_default_config_when_no_file(tmp_path):
    """Test loading default config when no file exists."""
    config_path = tmp_path / "bengal.toml"
    
    config = load_autodoc_config(config_path)
    
    assert "python" in config
    assert config["python"]["enabled"] is True
    assert config["python"]["output_dir"] == "content/api"
    assert config["python"]["docstring_style"] == "auto"


def test_load_config_from_file(tmp_path):
    """Test loading config from TOML file."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(dedent("""
        [autodoc.python]
        enabled = true
        source_dirs = ["src", "lib"]
        output_dir = "docs/api"
        docstring_style = "google"
        include_private = true
    """))
    
    config = load_autodoc_config(config_path)
    
    assert config["python"]["source_dirs"] == ["src", "lib"]
    assert config["python"]["output_dir"] == "docs/api"
    assert config["python"]["docstring_style"] == "google"
    assert config["python"]["include_private"] is True


def test_config_merges_with_defaults(tmp_path):
    """Test that file config merges with defaults."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(dedent("""
        [autodoc.python]
        output_dir = "custom/api"
    """))
    
    config = load_autodoc_config(config_path)
    
    # Custom value
    assert config["python"]["output_dir"] == "custom/api"
    
    # Default values preserved
    assert config["python"]["enabled"] is True
    assert config["python"]["docstring_style"] == "auto"
    assert config["python"]["include_private"] is False


def test_config_has_default_excludes(tmp_path):
    """Test that default config includes sensible excludes."""
    config_path = tmp_path / "nonexistent.toml"
    
    config = load_autodoc_config(config_path)
    
    excludes = config["python"]["exclude"]
    
    assert any("tests" in e for e in excludes)
    assert any("__pycache__" in e for e in excludes)


def test_config_override_excludes(tmp_path):
    """Test overriding exclude patterns."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(dedent("""
        [autodoc.python]
        exclude = ["custom/pattern/*"]
    """))
    
    config = load_autodoc_config(config_path)
    
    assert config["python"]["exclude"] == ["custom/pattern/*"]


def test_get_python_config():
    """Test getting Python-specific config."""
    config = {
        "python": {"enabled": True, "output_dir": "api"},
        "openapi": {"enabled": False}
    }
    
    py_config = get_python_config(config)
    
    assert py_config["enabled"] is True
    assert py_config["output_dir"] == "api"


def test_config_handles_invalid_toml(tmp_path):
    """Test handling of invalid TOML gracefully."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text("this is not [ valid toml")
    
    # Should return defaults and not crash
    config = load_autodoc_config(config_path)
    
    assert "python" in config
    assert config["python"]["enabled"] is True


def test_config_supports_multiple_source_dirs(tmp_path):
    """Test config with multiple source directories."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(dedent("""
        [autodoc.python]
        source_dirs = ["src", "lib", "vendor"]
    """))
    
    config = load_autodoc_config(config_path)
    
    assert len(config["python"]["source_dirs"]) == 3
    assert "src" in config["python"]["source_dirs"]


def test_config_openapi_disabled_by_default():
    """Test that OpenAPI is disabled by default."""
    config = load_autodoc_config(Path("nonexistent.toml"))
    
    assert config["openapi"]["enabled"] is False


def test_config_cli_disabled_by_default():
    """Test that CLI autodoc is disabled by default."""
    config = load_autodoc_config(Path("nonexistent.toml"))
    
    assert config["cli"]["enabled"] is False

