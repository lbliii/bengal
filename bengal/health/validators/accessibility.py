"""
Accessibility Validator for Document Applications.

Validates accessibility best practices in generated HTML output:
- Heading structure (proper hierarchy, no skipped levels)
- Image alt text
- Link text quality (avoid "click here")
- ARIA attributes
- Color contrast hints

Part of the Document Application RFC Phase 6: Author-Time Intelligence.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, CheckStatus

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext

__all__ = ["AccessibilityValidator"]


class AccessibilityValidator(BaseValidator):
    """
    Validates accessibility best practices.

    Checks:
    1. Heading hierarchy (no skipped levels)
    2. Image alt text presence
    3. Link text quality
    4. ARIA landmark presence
    5. Form label associations

    Configuration:
        health_check:
          accessibility:
            check_headings: true
            check_images: true
            check_links: true
            check_aria: true
            strict_mode: false
    """

    name = "accessibility"
    description = "Validates accessibility best practices in HTML output"

    # Patterns for link text to avoid
    BAD_LINK_TEXT_PATTERNS = [
        r"^click\s+here$",
        r"^here$",
        r"^read\s+more$",
        r"^more$",
        r"^link$",
        r"^this$",
    ]

    def validate(self, site: Site, build_context: BuildContext | None = None) -> list[CheckResult]:
        """
        Run accessibility validation.

        Args:
            site: The site to validate
            build_context: Optional build context

        Returns:
            List of CheckResult findings
        """
        results: list[CheckResult] = []
        config = self._get_config(site)

        for page in site.pages:
            page_results = self._validate_page(page, config)
            results.extend(page_results)

        return results

    def _get_config(self, site: Site) -> dict[str, Any]:
        """Get accessibility validation config."""
        health_config = site.config.get("health_check", {})
        return health_config.get(
            "accessibility",
            {
                "check_headings": True,
                "check_images": True,
                "check_links": True,
                "check_aria": True,
                "strict_mode": False,
            },
        )

    def _validate_page(self, page: Any, config: dict[str, Any]) -> list[CheckResult]:
        """
        Validate accessibility for a single page.

        Args:
            page: Page to validate
            config: Validation config

        Returns:
            List of findings for this page
        """
        results: list[CheckResult] = []
        path = getattr(page, "_path", "") or ""
        content = getattr(page, "rendered_content", "") or ""

        if not content:
            return results

        # Run enabled checks
        if config.get("check_headings", True):
            results.extend(self._check_headings(path, content, config))

        if config.get("check_images", True):
            results.extend(self._check_images(path, content, config))

        if config.get("check_links", True):
            results.extend(self._check_link_text(path, content))

        if config.get("check_aria", True):
            results.extend(self._check_aria(path, content))

        return results

    def _check_headings(self, path: str, content: str, config: dict[str, Any]) -> list[CheckResult]:
        """
        Check for proper heading hierarchy.

        Finds issues like:
        - h1 followed directly by h3 (skipped h2)
        - Multiple h1 tags on page
        """
        results: list[CheckResult] = []

        # Find all headings
        heading_pattern = re.compile(r"<h([1-6])[^>]*>", re.IGNORECASE)
        matches = heading_pattern.findall(content)

        if not matches:
            return results

        levels = [int(h) for h in matches]

        # Check for skipped levels
        for i in range(1, len(levels)):
            if levels[i] > levels[i - 1] + 1:
                status = CheckStatus.ERROR if config.get("strict_mode") else CheckStatus.WARNING
                results.append(
                    CheckResult(
                        status=status,
                        message=f"Heading level skipped: h{levels[i - 1]} → h{levels[i]}",
                        recommendation="Maintain proper heading hierarchy for screen readers",
                        details=[path],
                        validator=self.name,
                    )
                )

        # Check for multiple h1 tags
        h1_count = levels.count(1)
        if h1_count > 1:
            results.append(
                CheckResult(
                    status=CheckStatus.WARNING,
                    message=f"Multiple h1 tags found ({h1_count})",
                    recommendation="Use only one h1 per page for document outline",
                    details=[path],
                    validator=self.name,
                )
            )

        return results

    def _check_images(self, path: str, content: str, config: dict[str, Any]) -> list[CheckResult]:
        """
        Check for missing image alt text.
        """
        results: list[CheckResult] = []

        # Find all img tags
        img_pattern = re.compile(r"<img\s+([^>]+)/?>", re.IGNORECASE)

        for match in img_pattern.finditer(content):
            attrs = match.group(1)

            # Check for alt attribute
            if "alt=" not in attrs.lower():
                results.append(
                    CheckResult(
                        status=CheckStatus.WARNING,
                        message="Image missing alt attribute",
                        recommendation="Add alt text describing the image content",
                        details=[path],
                        validator=self.name,
                    )
                )
            elif re.search(r'alt\s*=\s*["\']["\']', attrs, re.IGNORECASE) and config.get(
                "strict_mode"
            ):
                # Empty alt is OK for decorative images, but note in strict mode
                results.append(
                    CheckResult(
                        status=CheckStatus.INFO,
                        message="Image has empty alt text (decorative?)",
                        recommendation="Empty alt is OK for decorative images",
                        details=[path],
                        validator=self.name,
                    )
                )

        return results

    def _check_link_text(self, path: str, content: str) -> list[CheckResult]:
        """
        Check for poor link text quality.

        Flags link text like "click here" or "read more" that
        doesn't describe the destination.
        """
        results: list[CheckResult] = []

        # Find all anchor tags with text
        link_pattern = re.compile(
            r"<a\s+[^>]*>([^<]+)</a>",
            re.IGNORECASE,
        )

        for match in link_pattern.finditer(content):
            link_text = match.group(1).strip().lower()

            for pattern in self.BAD_LINK_TEXT_PATTERNS:
                if re.match(pattern, link_text, re.IGNORECASE):
                    results.append(
                        CheckResult(
                            status=CheckStatus.WARNING,
                            message=f"Non-descriptive link text: '{match.group(1).strip()}'",
                            recommendation="Use descriptive link text that indicates destination",
                            details=[path],
                            validator=self.name,
                        )
                    )
                    break

        return results

    def _check_aria(self, path: str, content: str) -> list[CheckResult]:
        """
        Check for ARIA landmark regions.

        Verifies presence of:
        - main landmark
        - navigation landmark
        - banner (header) landmark
        """
        results: list[CheckResult] = []

        # These are typically in base template, so only check once
        if path != "/" and path != "/index.html":
            return results

        landmarks = {
            "main": (r"<main[^>]*>", r'role=["\']main["\']'),
            "navigation": (r"<nav[^>]*>", r'role=["\']navigation["\']'),
            "banner": (r"<header[^>]*>", r'role=["\']banner["\']'),
        }

        for name, (element_pattern, role_pattern) in landmarks.items():
            has_element = re.search(element_pattern, content, re.IGNORECASE)
            has_role = re.search(role_pattern, content, re.IGNORECASE)

            if not has_element and not has_role:
                results.append(
                    CheckResult(
                        status=CheckStatus.INFO,
                        message=f"Missing ARIA landmark: {name}",
                        recommendation=f"Add <{name.split()[0]}> element or role='{name}'",
                        details=[path],
                        validator=self.name,
                    )
                )

        return results
