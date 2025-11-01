"""Unit tests for autodoc configuration."""

from __future__ import annotations

from bengal.autodoc.config import (
    _merge_autodoc_config,
    get_grouping_config,
)


def test_default_grouping_config():
    """Test that default grouping config is mode='off' with empty prefix_map."""
    default_config = {
        "python": {
            "enabled": True,
            "strip_prefix": None,
            "grouping": {
                "mode": "off",
                "prefix_map": {},
            },
        },
    }

    grouping = get_grouping_config(default_config)
    assert grouping["mode"] == "off"
    assert grouping["prefix_map"] == {}


def test_merge_grouping_config_auto_mode():
    """Test merging grouping config with auto mode."""
    default_config = {
        "python": {
            "enabled": True,
            "strip_prefix": None,
            "grouping": {
                "mode": "off",
                "prefix_map": {},
            },
        },
    }

    user_config = {
        "python": {
            "strip_prefix": "mypackage.",
            "grouping": {
                "mode": "auto",
            },
        },
    }

    merged = _merge_autodoc_config(default_config, user_config)

    assert merged["python"]["strip_prefix"] == "mypackage."
    assert merged["python"]["grouping"]["mode"] == "auto"
    assert merged["python"]["grouping"]["prefix_map"] == {}  # Not overwritten


def test_merge_grouping_config_explicit_mode():
    """Test merging grouping config with explicit mode and prefix_map."""
    default_config = {
        "python": {
            "enabled": True,
            "grouping": {
                "mode": "off",
                "prefix_map": {},
            },
        },
    }

    user_config = {
        "python": {
            "grouping": {
                "mode": "explicit",
                "prefix_map": {
                    "cli.templates": "templates",
                    "core": "core",
                },
            },
        },
    }

    merged = _merge_autodoc_config(default_config, user_config)

    assert merged["python"]["grouping"]["mode"] == "explicit"
    assert merged["python"]["grouping"]["prefix_map"] == {
        "cli.templates": "templates",
        "core": "core",
    }


def test_merge_grouping_config_preserves_other_fields():
    """Test that merging grouping config preserves other Python config fields."""
    default_config = {
        "python": {
            "enabled": True,
            "source_dirs": ["."],
            "include_private": False,
            "grouping": {
                "mode": "off",
                "prefix_map": {},
            },
        },
    }

    user_config = {
        "python": {
            "include_private": True,
            "grouping": {
                "mode": "auto",
            },
        },
    }

    merged = _merge_autodoc_config(default_config, user_config)

    assert merged["python"]["enabled"] is True
    assert merged["python"]["source_dirs"] == ["."]
    assert merged["python"]["include_private"] is True
    assert merged["python"]["grouping"]["mode"] == "auto"


def test_invalid_grouping_mode_uses_off(capsys):
    """Test that invalid grouping mode falls back to 'off' with warning."""
    default_config = {
        "python": {
            "grouping": {
                "mode": "off",
                "prefix_map": {},
            },
        },
    }

    user_config = {
        "python": {
            "grouping": {
                "mode": "invalid_mode",
            },
        },
    }

    merged = _merge_autodoc_config(default_config, user_config)

    assert merged["python"]["grouping"]["mode"] == "off"

    # Check warning was printed
    captured = capsys.readouterr()
    assert "Warning: Invalid grouping mode 'invalid_mode'" in captured.out


def test_get_grouping_config_returns_defaults_when_missing():
    """Test get_grouping_config returns safe defaults when config is missing."""
    config = {
        "python": {
            "enabled": True,
            # No grouping key
        },
    }

    grouping = get_grouping_config(config)

    assert grouping["mode"] == "off"
    assert grouping["prefix_map"] == {}


def test_merge_grouping_partial_config():
    """Test merging when user only provides mode without prefix_map."""
    default_config = {
        "python": {
            "grouping": {
                "mode": "off",
                "prefix_map": {},
            },
        },
    }

    user_config = {
        "python": {
            "grouping": {
                "mode": "auto",
                # No prefix_map provided
            },
        },
    }

    merged = _merge_autodoc_config(default_config, user_config)

    assert merged["python"]["grouping"]["mode"] == "auto"
    assert merged["python"]["grouping"]["prefix_map"] == {}


def test_merge_grouping_nested_dict_not_overwritten():
    """Test that nested grouping dict is merged, not replaced."""
    default_config = {
        "python": {
            "grouping": {
                "mode": "off",
                "prefix_map": {},
            },
        },
    }

    user_config = {
        "python": {
            "grouping": {
                "prefix_map": {
                    "core": "core",
                },
            },
        },
    }

    merged = _merge_autodoc_config(default_config, user_config)

    # Mode should remain as default since user didn't specify
    assert merged["python"]["grouping"]["mode"] == "off"
    # prefix_map should be updated
    assert merged["python"]["grouping"]["prefix_map"] == {"core": "core"}


def test_strip_prefix_optional():
    """Test that strip_prefix can be None or a string."""
    default_config = {
        "python": {
            "strip_prefix": None,
            "grouping": {"mode": "off", "prefix_map": {}},
        },
    }

    # Test with None (default)
    user_config1 = {"python": {}}
    merged1 = _merge_autodoc_config(default_config, user_config1)
    assert merged1["python"]["strip_prefix"] is None

    # Test with string
    user_config2 = {"python": {"strip_prefix": "mypackage."}}
    merged2 = _merge_autodoc_config(default_config, user_config2)
    assert merged2["python"]["strip_prefix"] == "mypackage."


def test_multiple_nested_dicts_merge_correctly():
    """Test that both include_inherited_by_type and grouping merge correctly."""
    default_config = {
        "python": {
            "include_inherited_by_type": {
                "class": False,
                "exception": False,
            },
            "grouping": {
                "mode": "off",
                "prefix_map": {},
            },
        },
    }

    user_config = {
        "python": {
            "include_inherited_by_type": {
                "class": True,
            },
            "grouping": {
                "mode": "auto",
            },
        },
    }

    merged = _merge_autodoc_config(default_config, user_config)

    # Both nested dicts should be updated
    assert merged["python"]["include_inherited_by_type"]["class"] is True
    assert merged["python"]["include_inherited_by_type"]["exception"] is False
    assert merged["python"]["grouping"]["mode"] == "auto"
    assert merged["python"]["grouping"]["prefix_map"] == {}
