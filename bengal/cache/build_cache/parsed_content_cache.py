"""
Parsed content caching mixin for BuildCache.

Provides methods for caching parsed markdown content (HTML, TOC, AST) to skip
re-parsing when only templates change. Optimization #2 from the cache RFC.

Key Concepts:
- Caches rendered HTML (post-markdown, pre-template)
- Caches TOC and structured TOC items
- Optionally caches true AST for parse-once, use-many patterns
- Validates against metadata, template, and parser version
- Uses content hash for dependency validation

Related Modules:
- bengal.cache.build_cache.core: Main BuildCache class
- bengal.rendering.pipeline: Markdown parsing pipeline

"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.hashing import hash_str
from bengal.utils.primitives.sentinel import MISSING

logger = get_logger(__name__)


class ParsedContentCacheMixin:
    """
    Mixin providing parsed content caching (Optimization #2).

    Requires these attributes on the host class:
        - parsed_content: dict[str, dict[str, Any]]
        - dependencies: dict[str, set[str]]
        - file_fingerprints: dict (from FileTrackingMixin, for is_changed)
        - is_changed: Callable[[Path], bool]  (from FileTrackingMixin)
        - _cache_key: Callable[[Path], str]  # Canonical path key
        - site_root: Path | None  # For resolving dep keys to paths

    """

    # Type hints for mixin attributes (provided by host class)
    parsed_content: dict[str, dict[str, Any]]  # Keys are CacheKey at runtime
    dependencies: dict[str, set[str]]

    def is_changed(self, file_path: Path) -> bool:
        """Check if file changed (provided by FileTrackingMixin)."""
        raise NotImplementedError("Must be provided by FileTrackingMixin")

    def _resolve_dep_path(self, dep_key: str) -> Path | None:
        """
        Resolve CacheKey to filesystem Path for is_changed().

        dep_key is from dependencies[key] (e.g. templates/base.html or
        /Users/.../theme/templates/base.html for external themes).
        """
        if getattr(self, "site_root", None) is None:
            return None
        site_root = self.site_root
        # Absolute path (external theme)
        if dep_key.startswith("/") or (len(dep_key) > 1 and dep_key[1] == ":"):
            p = Path(dep_key)
            return p if p.exists() else None
        # Relative to site_root
        full = site_root / dep_key
        return full if full.exists() else None

    def store_parsed_content(
        self,
        file_path: Path,
        html: str,
        toc: str,
        toc_items: list[dict[str, Any]],
        links: list[str] | None,
        metadata: dict[str, Any],
        template: str,
        parser_version: str,
        ast: list[dict[str, Any]] | None = None,
        excerpt: str = "",
        meta_description: str = "",
    ) -> None:
        """
        Store parsed content in cache (Optimization #2 + AST caching).

        This allows skipping markdown parsing when only templates change,
        resulting in 20-30% faster builds in that scenario.

        Args:
            file_path: Path to source file
            html: Rendered HTML (post-markdown, pre-template)
            toc: Table of contents HTML
            toc_items: Structured TOC data
            links: Extracted links from the page (raw markdown extraction)
            metadata: Page metadata (frontmatter)
            template: Template name used
            parser_version: Parser version string (e.g., "mistune-3.0-toc2")
            ast: True AST tokens from parser (optional, for Phase 3)
        """
        from bengal.orchestration.constants import extract_nav_metadata

        # Hash full metadata to detect any changes
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hash_str(metadata_str)

        # Hash only nav-affecting metadata for fine-grained section index change detection
        nav_metadata = extract_nav_metadata(metadata)
        nav_metadata_str = json.dumps(nav_metadata, sort_keys=True, default=str)
        nav_metadata_hash = hash_str(nav_metadata_str)

        # Hash only cascade metadata for fine-grained cascade change detection
        # RFC: Output Cache Architecture - Skip cascade rebuild on body-only changes
        cascade_metadata = metadata.get("cascade", {})
        cascade_metadata_str = json.dumps(cascade_metadata, sort_keys=True, default=str)
        cascade_metadata_hash = hash_str(cascade_metadata_str)

        # Calculate size for cache management
        size_bytes = len(html.encode("utf-8")) + len(toc.encode("utf-8"))
        if links:
            # Rough estimate for link list size (strings + separators)
            size_bytes += sum(len(link.encode("utf-8")) for link in links)
        if ast:
            # Estimate AST size (JSON serialization)
            ast_str = json.dumps(ast, default=str)
            size_bytes += len(ast_str.encode("utf-8"))

        # Store as dict (will be serialized to JSON)
        key = self._cache_key(file_path)
        self.parsed_content[key] = {
            "html": html,
            "toc": toc,
            "toc_items": toc_items,
            "links": links or [],
            "excerpt": excerpt,
            "meta_description": meta_description,
            "ast": ast,  # Phase 3: Store true AST tokens
            "metadata_hash": metadata_hash,
            "nav_metadata_hash": nav_metadata_hash,
            "cascade_metadata_hash": cascade_metadata_hash,
            "template": template,
            "parser_version": parser_version,
            "timestamp": datetime.now(UTC).isoformat(),
            "size_bytes": size_bytes,
        }

    def get_parsed_content(
        self, file_path: Path, metadata: dict[str, Any], template: str, parser_version: str
    ) -> dict[str, Any] | Any:
        """
        Get cached parsed content if valid (Optimization #2).

        Uses is_changed for dependency validation (mtime-first, then hash).
        This prevents false invalidations when files are touched but not modified.

        Validates that:
        1. Content file hasn't changed (via is_changed)
        2. Metadata hasn't changed (via metadata_hash)
        3. Template hasn't changed (via template name)
        4. Parser version matches (avoid incompatibilities)
        5. Template file content hasn't changed (via is_changed on deps)

        Args:
            file_path: Path to source file
            metadata: Current page metadata
            template: Current template name
            parser_version: Current parser version

        Returns:
            Cached data dict if valid, MISSING if invalid or not found
        """
        key = self._cache_key(file_path)

        # Check if cached
        cached = self.parsed_content.get(key, MISSING)
        if cached is MISSING:
            return MISSING

        # Validate file hasn't changed
        if self.is_changed(file_path):
            return MISSING

        # Validate metadata hasn't changed
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hash_str(metadata_str)
        if cached.get("metadata_hash") != metadata_hash:
            return MISSING

        # Validate template hasn't changed (name)
        if cached.get("template") != template:
            return MISSING

        # Validate parser version (invalidate on upgrades)
        if cached.get("parser_version") != parser_version:
            return MISSING

        # Validate dependencies via is_changed (mtime-first, then hash).
        if key in self.dependencies:
            for dep_path in self.dependencies[key]:
                full_dep = self._resolve_dep_path(dep_path)
                if full_dep is None:
                    logger.debug(
                        "dependency_unresolvable",
                        page=key,
                        dependency=dep_path,
                    )
                    return MISSING
                if self.is_changed(full_dep):
                    logger.debug(
                        "dependency_changed",
                        page=key,
                        dependency=dep_path,
                    )
                    return MISSING

        return cached

    def get_parsed_page(self, file_path: Path) -> Any:
        """Lightweight lookup returning a ``ParsedPage`` record if cached.

        No validation is performed — the caller is responsible for ensuring
        the cache entry is still fresh (e.g. via file fingerprints).  Returns
        ``None`` when no entry exists.

        This method is used by incremental discovery to reconstruct pages
        from cache without re-parsing the source file.
        """
        from bengal.core.records import ParsedPage

        key = self._cache_key(file_path)
        entry = self.parsed_content.get(key)
        if not entry:
            return None
        try:
            return ParsedPage.from_cache_dict(entry)
        except Exception:
            logger.debug("parsed_page_reconstruction_failed", page=str(file_path))
            return None

    def store_parsed_page(
        self,
        file_path: Path,
        parsed_page: Any,
        metadata: dict[str, Any],
        template: str,
        parser_version: str,
    ) -> None:
        """Store a ``ParsedPage`` record in the parsed content cache.

        Convenience wrapper around ``store_parsed_content()`` that reads
        fields from the immutable ``ParsedPage`` record.
        """
        self.store_parsed_content(
            file_path=file_path,
            html=parsed_page.html_content,
            toc=parsed_page.toc,
            toc_items=list(parsed_page.toc_items),
            links=list(parsed_page.links),
            metadata=metadata,
            template=template,
            parser_version=parser_version,
            ast=parsed_page.ast_cache,
            excerpt=parsed_page.excerpt,
            meta_description=parsed_page.meta_description,
        )

    def get_excerpt_for_path(self, file_path: Path) -> str:
        """
        Lightweight excerpt lookup (no validation).

        Returns excerpt or meta_description from parsed_content cache.
        Use for lightweight excerpt access without full page load.

        Returns:
            Excerpt string, or '' if not found
        """
        key = self._cache_key(file_path)
        entry = self.parsed_content.get(key)
        if not entry:
            return ""
        return entry.get("excerpt") or entry.get("meta_description") or ""

    def invalidate_parsed_content(self, file_path: Path) -> bool:
        """
        Remove cached parsed content for a file.

        Args:
            file_path: Path to file

        Returns:
            True if cache entry was removed, False if not present
        """
        key = self._cache_key(file_path)
        if key in self.parsed_content:
            del self.parsed_content[key]
            return True
        return False

    def get_parsed_content_stats(self) -> dict[str, Any]:
        """
        Get parsed content cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.parsed_content:
            return {"cached_pages": 0, "total_size_mb": 0, "avg_size_kb": 0}

        total_size = sum(c.get("size_bytes", 0) for c in self.parsed_content.values())
        return {
            "cached_pages": len(self.parsed_content),
            "total_size_mb": total_size / 1024 / 1024,
            "avg_size_kb": (total_size / len(self.parsed_content) / 1024)
            if self.parsed_content
            else 0,
        }
