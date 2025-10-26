"""
Tests for autodoc configuration loader.
"""

from pathlib import Path
from textwrap import dedent

from bengal.autodoc.config import get_python_config, load_autodoc_config


def test_load_default_config_when_no_file(tmp_path):
    """Test loading default config when no file exists."""
    config_path = tmp_path / "bengal.toml"

    config = load_autodoc_config(config_path)

    assert "python" in config
    assert config["python"]["enabled"] is False  # Disabled by default (opt-in)
    assert config["python"]["output_dir"] == "content/api"
    assert config["python"]["docstring_style"] == "auto"


def test_load_config_from_file(tmp_path):
    """Test loading config from TOML file."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(
        dedent("""
        [autodoc.python]
        enabled = true
        source_dirs = ["src", "lib"]
        output_dir = "docs/api"
        docstring_style = "google"
        include_private = true
    """)
    )

    config = load_autodoc_config(config_path)

    assert config["python"]["source_dirs"] == ["src", "lib"]
    assert config["python"]["output_dir"] == "docs/api"
    assert config["python"]["docstring_style"] == "google"
    assert config["python"]["include_private"] is True


def test_config_merges_with_defaults(tmp_path):
    """Test that file config merges with defaults."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(
        dedent("""
        [autodoc.python]
        enabled = true
        output_dir = "custom/api"
    """)
    )

    config = load_autodoc_config(config_path)

    # Custom value
    assert config["python"]["output_dir"] == "custom/api"

    # Explicitly enabled in config
    assert config["python"]["enabled"] is True
    # Default values preserved
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
    config_path.write_text(
        dedent("""
        [autodoc.python]
        exclude = ["custom/pattern/*"]
    """)
    )

    config = load_autodoc_config(config_path)

    assert config["python"]["exclude"] == ["custom/pattern/*"]


def test_get_python_config():
    """Test getting Python-specific config."""
    config = {"python": {"enabled": True, "output_dir": "api"}, "openapi": {"enabled": False}}

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
    assert config["python"]["enabled"] is False  # Disabled by default


def test_config_supports_multiple_source_dirs(tmp_path):
    """Test config with multiple source directories."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(
        dedent("""
        [autodoc.python]
        source_dirs = ["src", "lib", "vendor"]
    """)
    )

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


def test_config_alias_and_inherited_defaults():
    """Test default values for alias and inherited member features."""
    config = load_autodoc_config(Path("nonexistent.toml"))

    assert config["python"]["include_inherited"] is False
    assert config["python"]["include_inherited_by_type"]["class"] is False
    assert config["python"]["include_inherited_by_type"]["exception"] is False
    assert config["python"]["alias_strategy"] == "canonical"


def test_config_load_include_inherited(tmp_path):
    """Test loading include_inherited configuration."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(
        dedent("""
        [autodoc.python]
        include_inherited = true
    """)
    )

    config = load_autodoc_config(config_path)

    assert config["python"]["include_inherited"] is True


def test_config_load_include_inherited_by_type(tmp_path):
    """Test loading per-type inherited member configuration."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(
        dedent("""
        [autodoc.python.include_inherited_by_type]
        class = true
        exception = false
    """)
    )

    config = load_autodoc_config(config_path)

    assert config["python"]["include_inherited_by_type"]["class"] is True
    assert config["python"]["include_inherited_by_type"]["exception"] is False


def test_config_load_alias_strategy(tmp_path):
    """Test loading alias strategy configuration."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(
        dedent("""
        [autodoc.python]
        alias_strategy = "list-only"
    """)
    )

    config = load_autodoc_config(config_path)

    assert config["python"]["alias_strategy"] == "list-only"


def test_config_partial_include_inherited_by_type_merge(tmp_path):
    """Test that partial per-type config merges with defaults."""
    config_path = tmp_path / "bengal.toml"
    config_path.write_text(
        dedent("""
        [autodoc.python.include_inherited_by_type]
        class = true
    """)
    )

    config = load_autodoc_config(config_path)

    # User override
    assert config["python"]["include_inherited_by_type"]["class"] is True
    # Default preserved
    assert config["python"]["include_inherited_by_type"]["exception"] is False


def test_config_loads_from_directory_structure(tmp_path, monkeypatch):
    """Test loading autodoc config from config/ directory structure."""
    import yaml

    # Change to tmp_path for config/ to be found
    monkeypatch.chdir(tmp_path)

    # Create directory-based config
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    default_dir = config_dir / "_default"
    default_dir.mkdir()

    autodoc_config = {
        "autodoc": {
            "python": {
                "enabled": True,
                "source_dirs": ["../bengal"],
                "output_dir": "content/api",
            },
            "cli": {
                "enabled": True,
                "app_module": "bengal.cli:main",
            },
        }
    }

    (default_dir / "autodoc.yaml").write_text(yaml.dump(autodoc_config))

    # Load config - should find config/ directory
    config = load_autodoc_config()

    # Verify directory config was loaded
    assert config["python"]["enabled"] is True
    assert config["python"]["source_dirs"] == ["../bengal"]
    assert config["cli"]["enabled"] is True
    assert config["cli"]["app_module"] == "bengal.cli:main"


def test_config_directory_takes_precedence_over_toml(tmp_path, monkeypatch):
    """Test that config/ directory takes precedence over bengal.toml."""
    import yaml

    monkeypatch.chdir(tmp_path)

    # Create both config/ directory and bengal.toml
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    default_dir = config_dir / "_default"
    default_dir.mkdir()

    # Directory config says enabled
    autodoc_config = {
        "autodoc": {
            "python": {
                "enabled": True,
                "output_dir": "content/api-from-dir",
            }
        }
    }
    (default_dir / "autodoc.yaml").write_text(yaml.dump(autodoc_config))

    # TOML config says disabled
    bengal_toml = tmp_path / "bengal.toml"
    bengal_toml.write_text(
        dedent("""
        [autodoc.python]
        enabled = false
        output_dir = "content/api-from-toml"
    """)
    )

    config = load_autodoc_config()

    # Directory config should win
    assert config["python"]["enabled"] is True
    assert config["python"]["output_dir"] == "content/api-from-dir"
