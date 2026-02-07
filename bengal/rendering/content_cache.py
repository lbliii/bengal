"""
Content-only hot reload infrastructure.

Provides caching for page "shells" (rendered HTML minus content) to enable
surgical content injection when only markdown body changes (not frontmatter).

Architecture:
    When a page is rendered:
    1. Store the page shell (HTML with content placeholder)
    2. Store the rendered content separately

    On content-only change:
    1. Re-parse markdown only (skip template rendering)
    2. Inject new content into cached shell
    3. Write updated HTML (50-80% faster than full render)

Cache Storage:
    Uses in-memory LRU cache keyed by (source_path, template_hash).
    Limited to avoid memory bloat on large sites.

Thread Safety:
    Uses thread-safe LRUCache from bengal.utils.primitives.

RFC: rfc-content-only-hot-reload

"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.primitives.lru_cache import LRUCache

if TYPE_CHECKING:
    from bengal.protocols import PageLike


# Placeholder for content injection
CONTENT_PLACEHOLDER = "<!--BENGAL_CONTENT_PLACEHOLDER-->"

# Pattern to find content in rendered HTML
# Matches the content container div (common in themes)
CONTENT_PATTERN = re.compile(
    r'(<(?:article|div|main|section)[^>]*class="[^"]*(?:content|article|prose)[^"]*"[^>]*>)'
    r"(.*?)"
    r"(</(?:article|div|main|section)>)",
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class PageShell:
    """Cached page shell for content injection.

    Attributes:
        before_content: HTML before the content area
        after_content: HTML after the content area
        template_hash: Hash of template used (for invalidation)
        metadata_hash: Hash of frontmatter (for invalidation)
    """

    before_content: str
    after_content: str
    template_hash: str
    metadata_hash: str


class ContentCache:
    """
    Cache for page shells enabling content-only hot reload.

    Stores page HTML split around the content area, allowing new content
    to be injected without re-running templates.

    Usage:
        >>> cache = ContentCache()
        >>>
        >>> # During normal render, cache the shell
        >>> cache.store_shell(page, rendered_html, template_name)
        >>>
        >>> # On content-only change, check for cached shell
        >>> shell = cache.get_shell(page, template_name, page.metadata)
        >>> if shell:
        ...     new_html = shell.inject_content(new_content)

    Thread Safety:
        Uses thread-safe LRUCache internally.
    """

    def __init__(self, max_size: int = 200) -> None:
        """Initialize content cache.

        Args:
            max_size: Maximum number of cached shells (default 200)
        """
        self._cache: LRUCache[str, PageShell] = LRUCache(
            maxsize=max_size,
            name="content_shell_cache",
        )

    def _make_key(self, source_path: Path, template_name: str) -> str:
        """Create cache key from source path and template."""
        return f"{source_path}:{template_name}"

    def _hash_template(self, template_name: str) -> str:
        """Hash template name for cache invalidation."""
        return hashlib.sha256(template_name.encode()).hexdigest()[:12]

    def _hash_metadata(self, metadata: dict[str, Any]) -> str:
        """Hash metadata for cache invalidation."""
        # Only hash keys that affect rendering (not content)
        relevant_keys = sorted(
            k for k in metadata.keys()
            if k not in ("_source", "_generated", "_cascade_invalidated")
        )
        content = "|".join(f"{k}={metadata.get(k)}" for k in relevant_keys)
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def store_shell(
        self,
        page: PageLike,
        rendered_html: str,
        template_name: str,
    ) -> bool:
        """
        Store a page shell for content-only hot reload.

        Extracts the content area from rendered HTML and stores the shell.

        Args:
            page: Page that was rendered
            rendered_html: Complete rendered HTML
            template_name: Template used for rendering

        Returns:
            True if shell was stored, False if content area not found
        """
        # Try to find and extract content area
        match = CONTENT_PATTERN.search(rendered_html)
        if not match:
            return False

        before_content = rendered_html[: match.start(2)]
        after_content = rendered_html[match.end(2) :]

        shell = PageShell(
            before_content=before_content,
            after_content=after_content,
            template_hash=self._hash_template(template_name),
            metadata_hash=self._hash_metadata(page.metadata),
        )

        key = self._make_key(page.source_path, template_name)
        self._cache.set(key, shell)

        return True

    def get_shell(
        self,
        page: PageLike,
        template_name: str,
        metadata: dict[str, Any],
    ) -> PageShell | None:
        """
        Get a cached shell if valid for this page.

        Returns None if:
        - No cached shell exists
        - Template changed
        - Metadata changed (frontmatter affects rendering)

        Args:
            page: Page to get shell for
            template_name: Template being used
            metadata: Current page metadata

        Returns:
            Cached PageShell or None if not valid
        """
        key = self._make_key(page.source_path, template_name)
        shell = self._cache.get(key)

        if shell is None:
            return None

        # Validate template hasn't changed
        if shell.template_hash != self._hash_template(template_name):
            return None

        # Validate metadata hasn't changed
        if shell.metadata_hash != self._hash_metadata(metadata):
            return None

        return shell

    def inject_content(self, shell: PageShell, content: str) -> str:
        """
        Inject new content into a cached shell.

        Args:
            shell: Cached page shell
            content: New rendered content

        Returns:
            Complete HTML with new content
        """
        return shell.before_content + content + shell.after_content

    def invalidate(self, source_path: Path) -> None:
        """Invalidate all cached shells for a source path."""
        # Remove all keys matching this source path
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(str(source_path))]
        for key in keys_to_remove:
            self._cache.delete(key)

    def clear(self) -> None:
        """Clear all cached shells."""
        self._cache.clear()

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self._cache.stats()


# Global content cache instance (singleton)
_content_cache: ContentCache | None = None


def get_content_cache() -> ContentCache:
    """Get or create the global content cache."""
    global _content_cache
    if _content_cache is None:
        _content_cache = ContentCache()
    return _content_cache


def clear_content_cache() -> None:
    """Clear the global content cache."""
    if _content_cache is not None:
        _content_cache.clear()


# Register for cache cleanup
try:
    from bengal.utils.cache_registry import InvalidationReason, register_cache

    register_cache(
        "content_shell_cache",
        clear_content_cache,
        invalidate_on={
            InvalidationReason.BUILD_START,
            InvalidationReason.FULL_REBUILD,
            InvalidationReason.CONFIG_CHANGED,
            InvalidationReason.TEST_CLEANUP,
        },
    )
except ImportError:
    pass


__all__ = [
    "CONTENT_PLACEHOLDER",
    "ContentCache",
    "PageShell",
    "clear_content_cache",
    "get_content_cache",
]
