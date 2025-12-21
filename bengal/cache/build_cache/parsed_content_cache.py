"""
Parsed content caching mixin for BuildCache.

Provides methods for caching parsed markdown content (HTML, TOC, AST) to skip
re-parsing when only templates change. Optimization #2 from the cache RFC.

Key Concepts:
    - Caches rendered HTML (post-markdown, pre-template)
    - Caches TOC and structured TOC items
    - Optionally caches true AST for parse-once, use-many patterns
    - Validates against metadata, template, and parser version

Related Modules:
    - bengal.cache.build_cache.core: Main BuildCache class
    - bengal.rendering.pipeline: Markdown parsing pipeline
    - plan/active/rfc-content-ast-architecture.md: AST caching RFC
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.hashing import hash_str

if TYPE_CHECKING:
    pass


class ParsedContentCacheMixin:
    """
    Mixin providing parsed content caching (Optimization #2).

    Requires these attributes on the host class:
        - parsed_content: dict[str, dict[str, Any]]
        - dependencies: dict[str, set[str]]
        - is_changed: Callable[[Path], bool]  (from FileTrackingMixin)
    """

    # Type hints for mixin attributes (provided by host class)
    parsed_content: dict[str, dict[str, Any]]
    dependencies: dict[str, set[str]]

    def is_changed(self, file_path: Path) -> bool:
        """Check if file changed (provided by FileTrackingMixin)."""
        raise NotImplementedError("Must be provided by FileTrackingMixin")

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
    ) -> None:
        """
        Store parsed content in cache (Optimization #2 + AST caching).

        This allows skipping markdown parsing when only templates change,
        resulting in 20-30% faster builds in that scenario.

        Phase 3 Enhancement (RFC-content-ast-architecture):
        - Also caches the true AST for parse-once, use-many patterns
        - AST enables faster TOC/link extraction and plain text generation

        RFC: rfc-incremental-hot-reload-invariants Phase 3:
        - Also caches nav_metadata_hash for fine-grained section index change detection

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
        self.parsed_content[str(file_path)] = {
            "html": html,
            "toc": toc,
            "toc_items": toc_items,
            "links": links or [],
            "ast": ast,  # Phase 3: Store true AST tokens
            "metadata_hash": metadata_hash,
            "nav_metadata_hash": nav_metadata_hash,  # RFC: incremental-hot-reload-invariants
            "template": template,
            "parser_version": parser_version,
            "timestamp": datetime.now().isoformat(),
            "size_bytes": size_bytes,
        }

    def get_parsed_content(
        self, file_path: Path, metadata: dict[str, Any], template: str, parser_version: str
    ) -> dict[str, Any] | None:
        """
        Get cached parsed content if valid (Optimization #2).

        Validates that:
        1. Content file hasn't changed (via file_fingerprints)
        2. Metadata hasn't changed (via metadata_hash)
        3. Template hasn't changed (via template name)
        4. Parser version matches (avoid incompatibilities)
        5. Template file hasn't changed (via dependencies)

        Args:
            file_path: Path to source file
            metadata: Current page metadata
            template: Current template name
            parser_version: Current parser version

        Returns:
            Cached data dict if valid, None if invalid or not found
        """
        key = str(file_path)

        # Check if cached
        if key not in self.parsed_content:
            return None

        cached = self.parsed_content[key]

        # Validate file hasn't changed
        if self.is_changed(file_path):
            return None

        # Validate metadata hasn't changed
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hash_str(metadata_str)
        if cached.get("metadata_hash") != metadata_hash:
            return None

        # Validate template hasn't changed (name)
        if cached.get("template") != template:
            return None

        # Validate parser version (invalidate on upgrades)
        if cached.get("parser_version") != parser_version:
            return None

        # Validate template file hasn't changed (via dependencies)
        # Check if any of the page's dependencies (templates) have changed
        if key in self.dependencies:
            for dep_path in self.dependencies[key]:
                dep = Path(dep_path)
                if dep.exists() and self.is_changed(dep):
                    # Template file changed - invalidate cache
                    return None

        return cached

    def invalidate_parsed_content(self, file_path: Path) -> None:
        """
        Remove cached parsed content for a file.

        Args:
            file_path: Path to file
        """
        self.parsed_content.pop(str(file_path), None)

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
