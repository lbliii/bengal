"""
URL Ownership System - Claim-time enforcement for URL coordination.

Provides URLRegistry for centralized URL claim management with priority-based
conflict resolution. Enables explicit ownership tracking across content,
autodoc, taxonomy, special pages, and redirects.

Public API:
    URLClaim: Immutable record of URL ownership (owner, source, priority)
    URLCollisionError: Exception raised when URL collision detected
    URLRegistry: Central authority for URL claims with conflict resolution

Key Concepts:
    Claim-Time Enforcement: URLs are claimed before file writes. Conflicts
        detected early prevent silent overwrites and broken navigation.

    Priority-Based Resolution: Higher priority claims win. This allows
        user content (priority 100) to override generated pages (priority 50).

    Priority Levels (by convention):
        100: User content (content/ pages)
         80: User redirects (explicit aliases)
         50: Generated content (autodoc, taxonomy)
         40: System pages (404, sitemap)

    Ownership Tracking: Each claim records owner (e.g., "content",
        "autodoc:python"), source file, and optional version/lang.

Usage:
    registry = URLRegistry()
    registry.claim("/about/", owner="content", source="content/about.md", priority=100)
    registry.claim("/api/", owner="autodoc:python", source="bengal.core", priority=50)

    # Check for existing claim
    claim = registry.get_claim("/about/")
    if claim:
        print(f"Owned by {claim.owner}")

Related Packages:
    bengal.config.url_policy: Reserved namespace definitions
    bengal.health.validators.ownership_policy: Policy validation
    bengal.utils.url_strategy: URL computation utilities
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.errors import BengalContentError

if TYPE_CHECKING:
    from bengal.core.site import Site


@dataclass(frozen=True)
class URLClaim:
    """
    Immutable record of URL ownership claim.

    Represents a single producer's claim to a URL, including ownership
    metadata and priority for conflict resolution.

    Attributes:
        owner: Owner identifier (e.g., "content", "autodoc:python", "taxonomy")
        source: Source file path or qualified name
        priority: Priority level (higher = wins conflicts)
        version: Version identifier if applicable (None for unversioned)
        lang: Language code if applicable (None for monolingual)
    """

    owner: str
    source: str
    priority: int
    version: str | None = None
    lang: str | None = None

    def __str__(self) -> str:
        """Human-readable representation."""
        parts = [f"{self.owner} (priority {self.priority})"]
        if self.version:
            parts.append(f"version={self.version}")
        if self.lang:
            parts.append(f"lang={self.lang}")
        return f"URLClaim({', '.join(parts)}, source={self.source})"


class URLCollisionError(BengalContentError):
    """
    Exception raised when URL collision detected at claim time.

    Provides detailed diagnostics including both claims, priority comparison,
    and suggested fixes.

    Extends BengalContentError for consistent error handling.
    """

    def __init__(
        self,
        url: str,
        existing: URLClaim,
        new_owner: str,
        new_source: str,
        new_priority: int,
        *,
        file_path: Path | None = None,
        suggestion: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize collision error with diagnostic context.

        Args:
            url: The conflicting URL
            existing: Existing claim that conflicts
            new_owner: Owner attempting to claim URL
            new_source: Source of new claim
            new_priority: Priority of new claim
            file_path: Path to file causing collision (if applicable)
            suggestion: Custom suggestion (defaults to standard tip)
            original_error: Original exception that caused this error
        """
        self.url = url
        self.existing = existing
        self.new_owner = new_owner
        self.new_source = new_source
        self.new_priority = new_priority

        # Build diagnostic message
        if new_priority == existing.priority:
            priority_msg = "Same priority - both claims rejected"
        elif new_priority > existing.priority:
            priority_msg = f"New claim has higher priority ({new_priority} > {existing.priority}) - would override"
        else:
            priority_msg = f"Existing claim has higher priority ({existing.priority} > {new_priority}) - new claim rejected"

        msg = (
            f"URL collision detected: {url}\n"
            f"  Existing claim: {existing.owner} (priority {existing.priority})\n"
            f"    Source: {existing.source}\n"
            f"  New claim: {new_owner} (priority {new_priority})\n"
            f"    Source: {new_source}\n"
            f"  Priority: {priority_msg}"
        )

        # Use provided suggestion or default
        if suggestion is None:
            suggestion = (
                "Check for duplicate slugs, conflicting autodoc output, or namespace violations"
            )

        super().__init__(
            message=msg,
            file_path=file_path or Path(new_source) if new_source else None,
            suggestion=suggestion,
            original_error=original_error,
        )


class URLRegistry:
    """
    Central authority for URL claims with claim-time enforcement.

    Maintains a registry of all URL claims and enforces ownership policy
    at claim time (before file writes). Provides priority-based conflict
    resolution and diagnostic error messages.

    Usage:
        registry = URLRegistry()
        registry.claim("/about/", owner="content", source="content/about.md", priority=100)
        url = registry.claim_output_path(output_path, site=site, owner="taxonomy", source="tags/python", priority=40)
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._claims: dict[str, URLClaim] = {}

    def _normalize(self, url: str) -> str:
        """
        Normalize URL for consistent lookup.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL (lowercase, trailing slash, etc.)
        """
        # Ensure leading slash
        if not url.startswith("/"):
            url = "/" + url

        # Ensure trailing slash for directory-like URLs
        # (except root which stays as "/")
        if url != "/" and not url.endswith("/"):
            url = url + "/"

        return url.lower()

    def claim(
        self,
        url: str,
        owner: str,
        source: str,
        priority: int = 50,
        version: str | None = None,
        lang: str | None = None,
    ) -> None:
        """
        Claim a URL for output.

        Raises URLCollisionError if URL is already claimed by a higher or equal priority owner.

        Args:
            url: URL to claim (e.g., "/about/", "/tags/python/")
            owner: Owner identifier (e.g., "content", "autodoc:python")
            source: Source file path or qualified name
            priority: Priority level (higher wins conflicts)
            version: Version identifier if applicable
            lang: Language code if applicable

        Raises:
            URLCollisionError: If URL is already claimed with higher or equal priority
        """
        normalized = self._normalize(url)

        if normalized in self._claims:
            existing = self._claims[normalized]

            # Same priority collision (e.g., two content files with same slug)
            if existing.priority == priority and existing.source != source:
                raise URLCollisionError(
                    url=url,
                    existing=existing,
                    new_owner=owner,
                    new_source=source,
                    new_priority=priority,
                )

            # Higher priority wins - override silently (user content can override generated)
            if priority > existing.priority:
                # Override existing claim
                self._claims[normalized] = URLClaim(
                    owner=owner,
                    source=source,
                    priority=priority,
                    version=version,
                    lang=lang,
                )
                return

            # Lower priority - reject new claim
            if priority < existing.priority:
                raise URLCollisionError(
                    url=url,
                    existing=existing,
                    new_owner=owner,
                    new_source=source,
                    new_priority=priority,
                )

            # Same priority, same source - idempotent, allow
            if existing.source == source:
                return

        # No existing claim or override successful
        self._claims[normalized] = URLClaim(
            owner=owner,
            source=source,
            priority=priority,
            version=version,
            lang=lang,
        )

    def claim_output_path(
        self,
        output_path: Path,
        *,
        site: Site,
        owner: str,
        source: str,
        priority: int = 50,
        version: str | None = None,
        lang: str | None = None,
    ) -> str:
        """
        Claim an output file path and return its canonical URL.

        This enables claim-time protection for producers that do not create Page objects
        (e.g., redirects and special pages).

        Args:
            output_path: Absolute path to output file
            site: Site object (for URL computation)
            owner: Owner identifier
            source: Source file path or qualified name
            priority: Priority level
            version: Version identifier if applicable
            lang: Language code if applicable

        Returns:
            Canonical URL for the output path

        Raises:
            URLCollisionError: If URL is already claimed with higher or equal priority
        """
        from bengal.utils.url_strategy import URLStrategy

        url = URLStrategy.url_from_output_path(output_path, site)
        self.claim(
            url=url,
            owner=owner,
            source=source,
            priority=priority,
            version=version,
            lang=lang,
        )
        return url

    def get_claim(self, url: str) -> URLClaim | None:
        """
        Get existing claim for URL.

        Args:
            url: URL to look up

        Returns:
            URLClaim if found, None otherwise
        """
        normalized = self._normalize(url)
        return self._claims.get(normalized)

    def all_claims(self) -> dict[str, URLClaim]:
        """
        Return all current claims.

        Returns:
            Dict mapping normalized URLs to URLClaim objects
        """
        return dict(self._claims)

    def clear(self) -> None:
        """Clear all claims (useful for testing or reset)."""
        self._claims.clear()

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """
        Serialize all claims to dictionary format for caching.

        Returns:
            Dict mapping normalized URLs to claim dictionaries
        """
        return {
            url: {
                "owner": claim.owner,
                "source": claim.source,
                "priority": claim.priority,
                "version": claim.version,
                "lang": claim.lang,
            }
            for url, claim in self._claims.items()
        }

    def load_from_dict(self, claims_dict: dict[str, dict[str, Any]]) -> None:
        """
        Load claims from dictionary format (from cache).

        Args:
            claims_dict: Dict mapping URLs to claim dictionaries
        """
        for url, claim_data in claims_dict.items():
            self._claims[url] = URLClaim(
                owner=claim_data["owner"],
                source=claim_data["source"],
                priority=claim_data["priority"],
                version=claim_data.get("version"),
                lang=claim_data.get("lang"),
            )
