"""
Anchor validator for validating explicit anchors and cross-references.

Part of the explicit anchor system (RFC: plan/active/rfc-explicit-anchor-targets.md).
Validates:
1. Duplicate anchor IDs within pages
2. Broken [[#anchor]] cross-references

Key Features:
    - Detect duplicate anchor IDs in rendered HTML
    - Validate [[#anchor]] references against xref_index
    - Support for both heading anchors and {target} directive anchors

Related Modules:
    - bengal.health.base: BaseValidator interface
    - bengal.health.report: CheckResult for reporting
    - bengal.directives.target: Target directive
    - bengal.rendering.parsers.mistune: Heading {#id} syntax

See Also:
    - bengal/health/validators/cross_ref.py: General cross-reference validation
    - bengal/rendering/plugins/cross_references.py: [[link]] resolution
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, CheckStatus

if TYPE_CHECKING:
    from bengal.core.site import Site


class AnchorValidator(BaseValidator):
    """
    Validates explicit anchors and [[#anchor]] cross-references.

    Performs two main validations:
    1. Duplicate anchors: Scans rendered HTML for duplicate id="..." attributes
    2. Broken references: Validates [[#anchor]] syntax against known anchors

    Creation:
        health_check.register(AnchorValidator())

    Configuration:
        In bengal.yaml:
        health_check:
          validators:
            anchors: true  # Enable/disable anchor validation

    Attributes:
        strict: If True, treat warnings as errors (for CI builds)
    """

    name = "anchors"
    description = "Validates anchor IDs and [[#anchor]] cross-references"

    # Pattern to find all id="..." attributes in HTML
    ID_PATTERN = re.compile(r'\bid="([^"]+)"')

    # Pattern to find [[#anchor]] cross-references in source content
    # Matches: [[#anchor]] or [[#anchor|text]]
    XREF_ANCHOR_PATTERN = re.compile(r"\[\[#([^\]|]+)")

    def __init__(self, strict: bool = False):
        """
        Initialize anchor validator.

        Args:
            strict: If True, report duplicate anchors as errors instead of warnings
        """
        super().__init__()
        self.strict = strict

    def validate(self, site: Site, build_context: Any | None = None) -> list[CheckResult]:
        """
        Validate anchors across all site pages.

        Args:
            site: Site to validate
            build_context: Optional BuildContext (not used by this validator)

        Returns:
            List of CheckResults for anchor issues
        """
        results: list[CheckResult] = []

        # Build set of valid anchors from xref_index
        valid_anchors = self._build_valid_anchor_set(site)

        # Validate each page
        for page in site.pages:
            # Check for duplicate anchors within the page
            duplicate_results = self._validate_duplicate_anchors(page)
            results.extend(duplicate_results)

            # Check for broken [[#anchor]] references
            broken_results = self._validate_anchor_references(page, valid_anchors)
            results.extend(broken_results)

        return results

    def _build_valid_anchor_set(self, site: Site) -> set[str]:
        """
        Build set of all valid anchor IDs from xref_index.

        Combines both explicit anchors (from {#id} and {target}) and
        heading anchors for comprehensive validation.

        Args:
            site: Site with built xref_index

        Returns:
            Set of lowercase anchor IDs
        """
        valid_anchors: set[str] = set()

        # Get xref_index (may not exist if site hasn't been built)
        xref_index = getattr(site, "xref_index", None)
        if not xref_index:
            return valid_anchors

        # Add explicit anchors (from {#id} heading syntax and {target} directive)
        by_anchor = xref_index.get("by_anchor", {})
        valid_anchors.update(by_anchor.keys())

        # Add heading anchors (auto-generated from heading text)
        by_heading = xref_index.get("by_heading", {})
        valid_anchors.update(by_heading.keys())

        return valid_anchors

    def _validate_duplicate_anchors(self, page: Any) -> list[CheckResult]:
        """
        Check for duplicate anchor IDs within a single page.

        Scans rendered HTML for all id="..." attributes and reports
        any duplicates. Duplicate anchors cause navigation issues and
        invalid HTML.

        Args:
            page: Page to validate

        Returns:
            List of CheckResults for duplicate anchors
        """
        results: list[CheckResult] = []
        rendered_html = getattr(page, "rendered_html", None) or ""
        page_path = str(getattr(page, "source_path", "unknown"))

        if not rendered_html:
            return results

        # Count occurrences of each anchor ID
        seen_anchors: dict[str, int] = {}
        for match in self.ID_PATTERN.finditer(rendered_html):
            anchor = match.group(1)
            seen_anchors[anchor] = seen_anchors.get(anchor, 0) + 1

        # Report duplicates
        for anchor, count in seen_anchors.items():
            if count > 1:
                status = CheckStatus.ERROR if self.strict else CheckStatus.WARNING
                results.append(
                    CheckResult(
                        status=status,
                        validator=self.name,
                        message=f"Duplicate anchor ID '{anchor}' ({count} occurrences)",
                        recommendation=(
                            f"Each anchor ID must be unique within a page. "
                            f"Rename one of the '{anchor}' anchors to avoid conflicts."
                        ),
                        metadata={
                            "anchor": anchor,
                            "count": count,
                            "file_path": page_path,
                        },
                    )
                )

        return results

    def _validate_anchor_references(self, page: Any, valid_anchors: set[str]) -> list[CheckResult]:
        """
        Check that all [[#anchor]] references resolve to existing anchors.

        Validates cross-reference syntax against the set of known anchors
        from the xref_index.

        Args:
            page: Page to validate
            valid_anchors: Set of valid anchor IDs (lowercase)

        Returns:
            List of CheckResults for broken references
        """
        results: list[CheckResult] = []
        content = getattr(page, "content", "") or ""
        page_path = str(getattr(page, "source_path", "unknown"))

        if not content:
            return results

        # Find all [[#anchor]] references
        for match in self.XREF_ANCHOR_PATTERN.finditer(content):
            anchor = match.group(1)
            anchor_lower = anchor.lower()

            if anchor_lower not in valid_anchors:
                # Calculate line number
                line = content[: match.start()].count("\n") + 1

                results.append(
                    CheckResult(
                        status=CheckStatus.WARNING,
                        validator=self.name,
                        message=f"Broken anchor reference '[[#{anchor}]]'",
                        recommendation=(
                            f"The anchor '#{anchor}' does not exist. "
                            f"Check that the target heading or {{{{target}}}} directive exists, "
                            f"or use {{#id}} syntax to create an explicit anchor."
                        ),
                        metadata={
                            "anchor": anchor,
                            "file_path": page_path,
                            "line": line,
                            "similar_anchors": self._find_similar_anchors(
                                anchor_lower, valid_anchors
                            ),
                        },
                    )
                )

        return results

    def _find_similar_anchors(self, anchor: str, valid_anchors: set[str]) -> list[str]:
        """
        Find anchors similar to the broken reference (for suggestions).

        Uses simple substring matching to suggest possible fixes.

        Args:
            anchor: The broken anchor reference
            valid_anchors: Set of valid anchors

        Returns:
            List of up to 3 similar anchor names
        """
        similar: list[str] = []

        # Find anchors that share a common substring
        anchor_parts = set(anchor.split("-"))
        for valid in valid_anchors:
            valid_parts = set(valid.split("-"))
            # Check if any parts overlap
            if anchor_parts & valid_parts:
                similar.append(valid)
                if len(similar) >= 3:
                    break

        return similar


def create_anchor_validator(strict: bool = False) -> AnchorValidator:
    """
    Factory function to create an AnchorValidator.

    Args:
        strict: If True, report duplicate anchors as errors

    Returns:
        Configured AnchorValidator
    """
    return AnchorValidator(strict=strict)
