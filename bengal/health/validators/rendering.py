"""
Rendering validator - checks output HTML quality.

Validates:
- HTML structure is valid
- No unrendered Jinja2 variables (outside code blocks)
- SEO metadata present

Note: Template function validation was removed as redundant - missing filters
cause immediate template errors during build.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult
from bengal.parsing.factory import ParserFactory
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import SiteLike


class RenderingValidator(BaseValidator):
    """
    Validates HTML rendering quality.

    Checks:
    - Basic HTML structure (<html>, <head>, <body>)
    - No unrendered Jinja2 variables in output
    - Basic SEO metadata present

    Note: Template function validation was removed as redundant - missing filters
    cause immediate template errors during build.

    """

    name = "Rendering"
    description = "Validates HTML output quality and completeness"
    enabled_by_default = True

    @override
    def validate(
        self, site: SiteLike, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run rendering validation checks."""
        results = []

        # Check 1: HTML structure
        results.extend(self._check_html_structure(site))

        # Check 2: Unrendered Jinja2 (catches silent template failures)
        results.extend(self._check_unrendered_jinja2(site))

        # Note: _check_template_functions removed - redundant with build success
        # (missing filters cause immediate template errors during build)

        # Check 3: SEO metadata (catches missing titles/descriptions)
        results.extend(self._check_seo_metadata(site))

        return results

    def _check_html_structure(self, site: SiteLike) -> list[CheckResult]:
        """Check basic HTML structure in output pages."""
        results = []
        issues = []

        # Sample a few pages (check first 10 to avoid slowing down)
        # Type narrowing: output_path may not be on PageLike protocol
        pages_to_check = []
        for p in site.pages:
            output_path = getattr(p, "output_path", None)
            if output_path and hasattr(output_path, "exists") and output_path.exists():
                pages_to_check.append(p)
                if len(pages_to_check) >= 10:
                    break

        for page in pages_to_check:
            output_path = getattr(page, "output_path", None)
            if output_path is None:
                continue
            try:
                content = output_path.read_text(encoding="utf-8")

                # Check for basic HTML5 structure
                if not content.strip().startswith(("<!DOCTYPE html>", "<!doctype html>")):
                    issues.append(f"{output_path.name}: Missing DOCTYPE")

                # Check for essential tags
                if "<html" not in content.lower():
                    issues.append(f"{output_path.name}: Missing <html> tag")
                elif "<head" not in content.lower():
                    issues.append(f"{output_path.name}: Missing <head> tag")
                elif "<body" not in content.lower():
                    issues.append(f"{output_path.name}: Missing <body> tag")

            except Exception as e:
                issues.append(
                    f"{output_path.name if output_path else 'unknown'}: Error reading file - {e}"
                )

        if issues:
            results.append(
                CheckResult.warning(
                    f"{len(issues)} page(s) have HTML structure issues",
                    code="H030",
                    recommendation="Check template files for proper HTML5 structure.",
                    details=issues[:5],
                )
            )
        else:
            results.append(
                CheckResult.success(
                    f"HTML structure validated (sampled {len(pages_to_check)} pages)"
                )
            )

        return results

    def _check_unrendered_jinja2(self, site: SiteLike) -> list[CheckResult]:
        """Check for unrendered Jinja2 syntax in output."""
        results = []
        issues = []

        # Sample pages (first 20 to be thorough but not too slow)
        # Type narrowing: output_path may not be on PageLike protocol
        pages_to_check = []
        for p in site.pages:
            output_path = getattr(p, "output_path", None)
            if output_path and hasattr(output_path, "exists") and output_path.exists():
                pages_to_check.append(p)
                if len(pages_to_check) >= 20:
                    break

        for page in pages_to_check:
            output_path = getattr(page, "output_path", None)
            if output_path is None:
                continue
            try:
                content = output_path.read_text(encoding="utf-8")
                has_unrendered = self._detect_unrendered_jinja2(content)

                if has_unrendered:
                    issues.append(output_path.name)

            except Exception as e:
                # Skip pages we can't read
                logger.debug(
                    "rendering_validator_page_skip",
                    page=str(output_path),
                    error=str(e),
                    error_type=type(e).__name__,
                )

        if issues:
            results.append(
                CheckResult.warning(
                    f"{len(issues)} page(s) may have unrendered Jinja2 syntax",
                    code="H031",
                    recommendation="Check for template rendering errors. May be documentation examples (which is OK).",
                    details=issues[:5],
                )
            )
        else:
            results.append(
                CheckResult.success(
                    f"No unrendered Jinja2 detected (sampled {len(pages_to_check)} pages)"
                )
            )

        return results

    def _detect_unrendered_jinja2(self, html_content: str) -> bool:
        """
        Detect if HTML has unrendered Jinja2 syntax (not in code blocks).

        Distinguishes between:
        - Actual unrendered templates (bad)
        - Documented/escaped syntax in code blocks (ok)

        Args:
            html_content: HTML content to check

        Returns:
            True if unrendered Jinja2 found (not in code blocks)
        """
        try:
            parser = ParserFactory.get_html_parser("native")
            soup = parser(html_content)
            remaining_text = soup.get_text()

            # Check patterns
            jinja2_patterns = ["{{ page.", "{{ site."]
            return any(pattern in remaining_text for pattern in jinja2_patterns)
        except Exception as e:
            # Fallback regex (no bs4)
            logger.debug(
                "rendering_validator_bs4_check_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="using_regex_fallback",
            )
            return any(p in html_content for p in ["{{ page.", "{{ site."])

    # Note: _check_template_functions was removed (H032).
    # It created a new TemplateEngine (~137ms) just to verify filters exist.
    # This is redundant: if filters were missing, templates would error during build.

    def _check_seo_metadata(self, site: SiteLike) -> list[CheckResult]:
        """Check for basic SEO metadata in pages."""
        results = []
        issues = []

        # Sample first 10 pages
        # Type narrowing: output_path may not be on PageLike protocol
        pages_to_check = []
        for p in site.pages:
            output_path = getattr(p, "output_path", None)
            if (
                output_path
                and hasattr(output_path, "exists")
                and output_path.exists()
                and not p.metadata.get("_generated")
            ):
                pages_to_check.append(p)
                if len(pages_to_check) >= 10:
                    break

        for page in pages_to_check:
            output_path = getattr(page, "output_path", None)
            if output_path is None:
                continue
            try:
                content = output_path.read_text(encoding="utf-8")

                # Check for basic SEO elements
                missing_elements = []

                if "<title>" not in content:
                    missing_elements.append("title")

                if (
                    'meta name="description"' not in content
                    and 'meta property="og:description"' not in content
                ):
                    missing_elements.append("description")

                if missing_elements:
                    issues.append(f"{output_path.name}: missing {', '.join(missing_elements)}")

            except Exception as e:
                logger.debug(
                    "health_seo_page_check_skipped",
                    page=str(getattr(page, "output_path", "unknown")),
                    error=str(e),
                    error_type=type(e).__name__,
                    action="skipping_page",
                )

        if issues:
            results.append(
                CheckResult.warning(
                    f"{len(issues)} page(s) missing basic SEO metadata",
                    code="H033",
                    recommendation="Add <title> and meta description tags to improve SEO.",
                    details=issues[:5],
                )
            )
        else:
            results.append(
                CheckResult.success(f"SEO metadata validated (sampled {len(pages_to_check)} pages)")
            )

        return results
