"""Unit tests for ConfigValidator structure preservation and type handling."""

from __future__ import annotations

from typing import Any

import pytest

from bengal.config.validators import ConfigValidator


@pytest.mark.unit
class TestConfigValidatorStructure:
    """
    Tests for ConfigValidator ensuring it preserves nested structure and handles None.
    """

    def test_preserves_nested_structure(self):
        """Test that the validator returns the original nested structure, not flattened."""
        validator = ConfigValidator()
        config = {
            "site": {"title": "My Site"},
            "build": {
                "parallel": "true",
                "max_workers": 4,
                "incremental": None
            }
        }
        
        validated = validator.validate(config)
        
        # Structure check: should still have site and build keys
        assert "site" in validated
        assert "build" in validated
        assert isinstance(validated["site"], dict)
        assert isinstance(validated["build"], dict)
        
        # Content check: values inside nested sections should be coerced
        assert validated["site"]["title"] == "My Site"
        assert validated["build"]["parallel"] is True
        assert validated["build"]["max_workers"] == 4
        assert validated["build"]["incremental"] is None

    def test_allows_none_for_auto_detection(self):
        """Test that None values are allowed for fields that support auto-detection."""
        validator = ConfigValidator()
        config = {
            "build": {
                "incremental": None,
                "max_workers": None
            }
        }
        
        validated = validator.validate(config)
        assert validated["build"]["incremental"] is None
        assert validated["build"]["max_workers"] is None

    def test_handles_bool_or_dict_features(self):
        """Test that features like 'search' can be either bool or dict."""
        validator = ConfigValidator()
        
        # Case 1: Boolean
        config1 = {"features": {"search": False}}
        validated1 = validator.validate(config1)
        assert validated1["features"]["search"] is False
        
        # Case 2: Dictionary
        config2 = {"features": {"search": {"enabled": True, "lunr": {"prebuilt": True}}}}
        validated2 = validator.validate(config2)
        assert isinstance(validated2["features"]["search"], dict)
        assert validated2["features"]["search"]["enabled"] is True

    def test_coercion_in_nested_dict(self):
        """Test that coercion works even when values are deeply nested."""
        validator = ConfigValidator()
        config = {
            "build": {
                "parallel": "yes",
                "max_workers": "8"
            }
        }
        
        validated = validator.validate(config)
        assert validated["build"]["parallel"] is True
        assert validated["build"]["max_workers"] == 8

    def test_flattening_still_works_internally(self):
        """
        Verify that even if input is flat, it's accepted (backward compatibility)
        but types are still validated.
        """
        validator = ConfigValidator()
        config = {
            "parallel": "true",
            "title": "Flat Site"
        }
        
        validated = validator.validate(config)
        assert validated["parallel"] is True
        assert validated["title"] == "Flat Site"
