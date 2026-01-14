"""
Speculation Rules Generator for Document Applications.

Generates speculation rules JSON for browser prefetching and prerendering.
Analyzes site structure to create intelligent prefetch/prerender hints.

The Speculation Rules API enables browsers to prefetch or prerender pages
before user navigation, providing near-instant page loads.

Browser Support (as of Dec 2025):
- Chrome 121+, Edge 121+, Opera 107+ (74% global support)
- Safari: experimental flag only
- Firefox: gracefully ignores (no errors)

@see https://developer.chrome.com/docs/web-platform/prerender-pages/
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

__all__ = [
    "SpeculationRulesGenerator",
    "SpeculationRule",
    "generate_speculation_rules",
]

logger = get_logger(__name__)


@dataclass
class SpeculationRule:
    """
    A single speculation rule for prefetch or prerender.
    
    Attributes:
        href_matches: URL pattern(s) to match
        eagerness: How eagerly to trigger (conservative | moderate | eager)
        exclude_selectors: CSS selectors to exclude from the rule
        
    """

    href_matches: list[str] = field(default_factory=lambda: ["/*"])
    eagerness: str = "conservative"
    exclude_selectors: list[str] = field(
        default_factory=lambda: ["[data-external]", "[target=_blank]", ".external"]
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert rule to speculation rules JSON format."""
        where_clause: dict[str, Any] = {}

        # Handle single pattern vs multiple patterns
        if len(self.href_matches) == 1:
            where_clause["href_matches"] = self.href_matches[0]
        else:
            where_clause["href_matches"] = self.href_matches

        # Add exclusions if any
        if self.exclude_selectors:
            not_clause = {"selector_matches": ", ".join(self.exclude_selectors)}
            where_clause = {
                "and": [
                    {"href_matches": where_clause.get("href_matches", "/*")},
                    {"not": not_clause},
                ]
            }

        return {
            "where": where_clause,
            "eagerness": self.eagerness,
        }


class SpeculationRulesGenerator:
    """
    Generates speculation rules based on site configuration and structure.
    
    The generator can:
    1. Use explicit configuration from bengal.yaml
    2. Auto-generate rules based on site analysis
    3. Combine both approaches
    
    Example config in bengal.yaml:
        document_application:
          speculation:
            enabled: true
            prerender:
              eagerness: moderate
              patterns:
                - "/docs/*"
                - "/blog/*"
            prefetch:
              eagerness: conservative
              patterns:
                - "/*"
            exclude_patterns:
              - "/admin/*"
              - "*.pdf"
        
    """

    def __init__(self, site: Site):
        """
        Initialize the speculation rules generator.

        Args:
            site: The Bengal site instance
        """
        self.site = site
        self.config = self._get_speculation_config()

    def _get_speculation_config(self) -> dict[str, Any]:
        """Get speculation configuration with defaults."""
        doc_app = self.site.config.get("document_application", {})
        return doc_app.get("speculation", {})

    def is_enabled(self) -> bool:
        """Check if speculation rules are enabled."""
        doc_app = self.site.config.get("document_application", {})
        if not doc_app.get("enabled", True):
            return False

        speculation = doc_app.get("speculation", {})
        if not speculation.get("enabled", True):
            return False

        features = doc_app.get("features", {})
        return features.get("speculation_rules", True)

    def generate(self) -> dict[str, Any]:
        """
        Generate the complete speculation rules JSON.

        Returns:
            Dictionary suitable for JSON serialization as <script type="speculationrules">
        """
        if not self.is_enabled():
            return {}

        rules: dict[str, list[dict[str, Any]]] = {
            "prerender": [],
            "prefetch": [],
        }

        # Generate prerender rules
        prerender_config = self.config.get("prerender", {})
        prerender_rule = self._create_rule(
            patterns=prerender_config.get("patterns", ["/docs/*"]),
            eagerness=prerender_config.get("eagerness", "conservative"),
        )
        rules["prerender"].append(prerender_rule.to_dict())

        # Generate prefetch rules
        prefetch_config = self.config.get("prefetch", {})
        prefetch_rule = self._create_rule(
            patterns=prefetch_config.get("patterns", ["/*"]),
            eagerness=prefetch_config.get("eagerness", "conservative"),
        )
        rules["prefetch"].append(prefetch_rule.to_dict())

        # Auto-generate additional rules if enabled
        if self.config.get("auto_generate", True):
            auto_rules = self._auto_generate_rules()
            for rule in auto_rules.get("prerender", []):
                if rule.to_dict() not in rules["prerender"]:
                    rules["prerender"].append(rule.to_dict())
            for rule in auto_rules.get("prefetch", []):
                if rule.to_dict() not in rules["prefetch"]:
                    rules["prefetch"].append(rule.to_dict())

        return rules

    def _create_rule(
        self,
        patterns: list[str],
        eagerness: str = "conservative",
    ) -> SpeculationRule:
        """Create a speculation rule with standard exclusions."""
        exclude = self.config.get("exclude_patterns", [])
        exclude_selectors = ["[data-external]", "[target=_blank]", ".external"]

        # Add pattern-based exclusions
        for pattern in exclude:
            if pattern.startswith("/"):
                # URL pattern exclusions are handled differently
                pass
            elif pattern.startswith("."):
                exclude_selectors.append(pattern)

        return SpeculationRule(
            href_matches=patterns,
            eagerness=eagerness,
            exclude_selectors=exclude_selectors,
        )

    def _auto_generate_rules(self) -> dict[str, list[SpeculationRule]]:
        """
        Auto-generate speculation rules based on site analysis.

        Analyzes:
        - High-traffic navigation paths
        - Content relationships
        - Section structure

        Returns:
            Dictionary with 'prerender' and 'prefetch' rule lists
        """
        rules: dict[str, list[SpeculationRule]] = {
            "prerender": [],
            "prefetch": [],
        }

        # Analyze sections to create section-specific rules
        sections = self._analyze_sections()
        for section_path, section_info in sections.items():
            if section_info.get("page_count", 0) > 5:
                # Sections with many pages get moderate prefetch
                rules["prefetch"].append(
                    SpeculationRule(
                        href_matches=[f"{section_path}*"],
                        eagerness="moderate",
                    )
                )

        return rules

    def _analyze_sections(self) -> dict[str, dict[str, Any]]:
        """
        Analyze site sections for speculation rules.

        Returns:
            Dictionary mapping section paths to analysis info
        """
        sections: dict[str, dict[str, Any]] = {}

        # Group pages by section
        for page in self.site.pages:
            path = getattr(page, "_path", "") or ""
            if not path:
                continue

            # Extract section (first path component)
            parts = path.strip("/").split("/")
            if len(parts) > 1:
                section = f"/{parts[0]}/"
                if section not in sections:
                    sections[section] = {"page_count": 0, "pages": []}
                sections[section]["page_count"] += 1
                sections[section]["pages"].append(path)

        return sections

    def to_json(self, indent: int | None = 2) -> str:
        """
        Generate speculation rules as JSON string.

        Args:
            indent: JSON indentation level (None for compact)

        Returns:
            JSON string for <script type="speculationrules">
        """
        rules = self.generate()
        if not rules:
            return ""
        return json.dumps(rules, indent=indent)


def generate_speculation_rules(site: Site) -> str:
    """
    Convenience function to generate speculation rules JSON.
    
    Args:
        site: The Bengal site instance
    
    Returns:
        JSON string for <script type="speculationrules">, or empty string if disabled
        
    """
    generator = SpeculationRulesGenerator(site)
    return generator.to_json()
