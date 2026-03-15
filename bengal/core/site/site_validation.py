"""
Site Validation Mixin - URL collision detection.

Provides validate_no_url_collisions for detecting when multiple pages
output to the same URL during the build process.

See Also:
- bengal/health/validators/url_collisions.py: Health check validator
- bengal/core/site/__init__.py: Site class that uses this mixin
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.page import Page


class SiteValidationMixin:
    """
    Mixin providing URL collision validation.

    Handles:
    - validate_no_url_collisions: Detect duplicate output URLs
    """

    pages: list[Page]
    url_registry: object

    def validate_no_url_collisions(self, *, strict: bool = False) -> list[str]:
        """
        Detect when multiple pages output to the same URL.

        Uses URLRegistry if available for enhanced ownership context, otherwise
        falls back to page iteration if URLRegistry is not available.

        Args:
            strict: If True, raise ValueError on collision instead of warning.

        Returns:
            List of collision warning messages (empty if no collisions)

        Raises:
            ValueError: If strict=True and collisions are detected
        """
        collisions: list[str] = []

        if hasattr(self, "url_registry") and self.url_registry:
            urls_seen: dict[str, str] = {}

            for page in self.pages:
                url = page._path
                source = str(getattr(page, "source_path", page.title))

                if url in urls_seen:
                    claim = self.url_registry.get_claim(url)
                    owner_info = f" ({claim.owner}, priority {claim.priority})" if claim else ""

                    msg = (
                        f"URL collision detected: {url}\n"
                        f"  Already claimed by: {urls_seen[url]}{owner_info}\n"
                        f"  Also claimed by: {source}\n"
                        f"Tip: Check for duplicate slugs or conflicting autodoc output"
                    )
                    collisions.append(msg)

                    emit_diagnostic(
                        self,
                        "warning",
                        "url_collision",
                        url=url,
                        first_source=urls_seen[url],
                        second_source=source,
                    )
                else:
                    urls_seen[url] = source
        else:
            urls_seen = {}

            for page in self.pages:
                url = page._path
                source = str(getattr(page, "source_path", page.title))

                if url in urls_seen:
                    msg = (
                        f"URL collision detected: {url}\n"
                        f"  Already claimed by: {urls_seen[url]}\n"
                        f"  Also claimed by: {source}\n"
                        f"Tip: Check for duplicate slugs or conflicting autodoc output"
                    )
                    collisions.append(msg)

                    emit_diagnostic(
                        self,
                        "warning",
                        "url_collision",
                        url=url,
                        first_source=urls_seen[url],
                        second_source=source,
                    )
                else:
                    urls_seen[url] = source

        if collisions and strict:
            from bengal.errors import BengalContentError, ErrorCode

            raise BengalContentError(
                "URL collisions detected (strict mode):\n\n" + "\n\n".join(collisions),
                code=ErrorCode.D005,
                suggestion=(
                    "Check for duplicate slugs, conflicting autodoc output, "
                    "or use different URLs for conflicting pages"
                ),
            )

        return collisions
