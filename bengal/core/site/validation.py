"""
Validation mixin for Site.

Provides methods for validating site state, such as URL collision detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.url_ownership import URLRegistry


class SiteValidationMixin:
    """
    Mixin providing validation methods for Site.

    Includes URL collision detection and other validation checks.
    """

    # These attributes are defined on the Site dataclass
    pages: list[Page]
    url_registry: URLRegistry

    def validate_no_url_collisions(self, *, strict: bool = False) -> list[str]:
        """
        Detect when multiple pages output to the same URL.

        This method catches URL collisions early during the build process,
        preventing silent overwrites that cause broken navigation.

        Uses URLRegistry if available for enhanced ownership context, otherwise
        falls back to page iteration if URLRegistry is not available.

        Args:
            strict: If True, raise ValueError on collision instead of warning.
                   Set to True when site config has strict_mode=True.

        Returns:
            List of collision warning messages (empty if no collisions)

        Raises:
            ValueError: If strict=True and collisions are detected

        Example:
            >>> collisions = site.validate_no_url_collisions()
            >>> if collisions:
            ...     for msg in collisions:
            ...         print(f"Warning: {msg}")

        Note:
            This is a proactive check during Phase 12 (Update Pages List) that
            catches issues before they cause broken navigation.

        See Also:
            - bengal/health/validators/url_collisions.py: Health check validator
        """
        collisions: list[str] = []

        # Use registry if available (provides ownership context)
        if hasattr(self, "url_registry") and self.url_registry:
            # Check for duplicate URLs in pages (registry tracks all claims, including non-page)
            urls_seen: dict[str, str] = {}  # url -> source description

            for page in self.pages:
                url = page._path
                source = str(getattr(page, "source_path", page.title))

                if url in urls_seen:
                    # Get ownership context from registry
                    claim = self.url_registry.get_claim(url)
                    owner_info = f" ({claim.owner}, priority {claim.priority})" if claim else ""

                    msg = (
                        f"URL collision detected: {url}\n"
                        f"  Already claimed by: {urls_seen[url]}{owner_info}\n"
                        f"  Also claimed by: {source}\n"
                        f"Tip: Check for duplicate slugs or conflicting autodoc output"
                    )
                    collisions.append(msg)

                    # Emit diagnostic for orchestrators to surface
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
            # Fallback: iterate pages
            urls_seen = {}  # url -> source description

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

                    # Emit diagnostic for orchestrators to surface
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
