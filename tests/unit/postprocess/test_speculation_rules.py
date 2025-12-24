"""
Unit tests for Speculation Rules Generator (Document Application RFC).

Tests the speculation rules generation including:
- JSON schema validity
- Pattern matching logic
- Exclusion of external links
- Configuration options
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from bengal.postprocess.speculation import (
    SpeculationRule,
    SpeculationRulesGenerator,
    generate_speculation_rules,
)


class TestSpeculationRule:
    """Tests for SpeculationRule dataclass."""

    def test_default_rule(self):
        """Default rule should have sensible defaults."""
        rule = SpeculationRule()
        assert rule.href_matches == ["/*"]
        assert rule.eagerness == "conservative"
        assert "[data-external]" in rule.exclude_selectors

    def test_to_dict_single_pattern(self):
        """Single pattern should not be wrapped in array."""
        rule = SpeculationRule(
            href_matches=["/docs/*"],
            eagerness="moderate",
            exclude_selectors=[],
        )
        result = rule.to_dict()
        assert result["eagerness"] == "moderate"
        assert result["where"]["href_matches"] == "/docs/*"

    def test_to_dict_with_exclusions(self):
        """Exclusions should create 'and' clause with 'not'."""
        rule = SpeculationRule(
            href_matches=["/docs/*"],
            eagerness="moderate",
            exclude_selectors=["[data-external]", ".external"],
        )
        result = rule.to_dict()

        # Should have 'and' clause
        assert "and" in result["where"]
        and_clauses = result["where"]["and"]

        # Should have href_matches
        assert any("href_matches" in c for c in and_clauses)

        # Should have 'not' clause with selector_matches
        not_clause = next(c for c in and_clauses if "not" in c)
        assert "selector_matches" in not_clause["not"]


class TestSpeculationRulesGenerator:
    """Tests for SpeculationRulesGenerator class."""

    def _create_mock_site(self, config: dict):
        """Create a mock site with given config."""
        site = MagicMock()
        site.config = config
        site.pages = []
        return site

    def test_is_enabled_default(self):
        """Generator should be enabled by default."""
        site = self._create_mock_site({})
        generator = SpeculationRulesGenerator(site)
        assert generator.is_enabled()

    def test_is_enabled_when_doc_app_disabled(self):
        """Generator should be disabled when document_application is disabled."""
        site = self._create_mock_site(
            {
                "document_application": {
                    "enabled": False,
                }
            }
        )
        generator = SpeculationRulesGenerator(site)
        assert not generator.is_enabled()

    def test_is_enabled_when_speculation_disabled(self):
        """Generator should be disabled when speculation is disabled."""
        site = self._create_mock_site(
            {
                "document_application": {
                    "enabled": True,
                    "speculation": {
                        "enabled": False,
                    },
                }
            }
        )
        generator = SpeculationRulesGenerator(site)
        assert not generator.is_enabled()

    def test_is_enabled_when_feature_flag_disabled(self):
        """Generator should be disabled when feature flag is off."""
        site = self._create_mock_site(
            {
                "document_application": {
                    "enabled": True,
                    "speculation": {
                        "enabled": True,
                    },
                    "features": {
                        "speculation_rules": False,
                    },
                }
            }
        )
        generator = SpeculationRulesGenerator(site)
        assert not generator.is_enabled()

    def test_generate_returns_empty_when_disabled(self):
        """Generate should return empty dict when disabled."""
        site = self._create_mock_site(
            {
                "document_application": {
                    "enabled": False,
                }
            }
        )
        generator = SpeculationRulesGenerator(site)
        result = generator.generate()
        assert result == {}

    def test_generate_basic_rules(self):
        """Generate should create prerender and prefetch rules."""
        site = self._create_mock_site({})
        generator = SpeculationRulesGenerator(site)
        result = generator.generate()

        assert "prerender" in result
        assert "prefetch" in result
        assert len(result["prerender"]) >= 1
        assert len(result["prefetch"]) >= 1

    def test_generate_uses_config_patterns(self):
        """Generate should use patterns from config."""
        site = self._create_mock_site(
            {
                "document_application": {
                    "speculation": {
                        "prerender": {
                            "patterns": ["/docs/*", "/api/*"],
                            "eagerness": "eager",
                        },
                        "prefetch": {
                            "patterns": ["/blog/*"],
                            "eagerness": "moderate",
                        },
                    },
                }
            }
        )
        generator = SpeculationRulesGenerator(site)
        result = generator.generate()

        # Check prerender rule
        prerender_rule = result["prerender"][0]
        assert prerender_rule["eagerness"] == "eager"

        # Check prefetch rule
        prefetch_rule = result["prefetch"][0]
        assert prefetch_rule["eagerness"] == "moderate"

    def test_to_json_valid_json(self):
        """to_json should produce valid JSON."""
        site = self._create_mock_site({})
        generator = SpeculationRulesGenerator(site)
        json_str = generator.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "prerender" in parsed
        assert "prefetch" in parsed

    def test_to_json_empty_when_disabled(self):
        """to_json should return empty string when disabled."""
        site = self._create_mock_site(
            {
                "document_application": {
                    "enabled": False,
                }
            }
        )
        generator = SpeculationRulesGenerator(site)
        json_str = generator.to_json()
        assert json_str == ""


class TestConvenienceFunction:
    """Tests for generate_speculation_rules function."""

    def test_generate_speculation_rules_function(self):
        """Convenience function should work like generator."""
        site = MagicMock()
        site.config = {}
        site.pages = []

        result = generate_speculation_rules(site)

        # Should be valid JSON
        parsed = json.loads(result)
        assert "prerender" in parsed
        assert "prefetch" in parsed


class TestSpeculationRulesJSONSchema:
    """Tests for JSON schema compliance."""

    def test_valid_speculation_rules_schema(self):
        """Generated rules should match speculation rules schema."""
        site = MagicMock()
        site.config = {}
        site.pages = []

        generator = SpeculationRulesGenerator(site)
        result = generator.generate()

        # Schema validation
        assert isinstance(result, dict)

        for key in ["prerender", "prefetch"]:
            assert key in result
            assert isinstance(result[key], list)

            for rule in result[key]:
                assert isinstance(rule, dict)
                assert "where" in rule
                assert "eagerness" in rule
                assert rule["eagerness"] in ["immediate", "eager", "moderate", "conservative"]
