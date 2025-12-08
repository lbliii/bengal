"""
Rendered output caching mixin for BuildCache.

Provides methods for caching fully rendered HTML output to skip both markdown
parsing AND template rendering. Optimization #3 from the cache RFC.

Key Concepts:
    - Caches final HTML (post-template, ready to write)
    - Validates against content, metadata, template, and dependencies
    - Expected 20-40% faster incremental builds

Related Modules:
    - bengal.cache.build_cache.core: Main BuildCache class
    - bengal.rendering.renderer: Page rendering
    - plan/active/rfc-orchestrator-performance.md: Performance RFC
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.hashing import hash_str

if TYPE_CHECKING:
    pass


class RenderedOutputCacheMixin:
    """
    Mixin providing rendered output caching (Optimization #3).

    Requires these attributes on the host class:
        - rendered_output: dict[str, dict[str, Any]]
        - is_changed: Callable[[Path], bool]  (from FileTrackingMixin)
    """

    # Type hints for mixin attributes (provided by host class)
    rendered_output: dict[str, dict[str, Any]]

    def is_changed(self, file_path: Path) -> bool:
        """Check if file changed (provided by FileTrackingMixin)."""
        raise NotImplementedError("Must be provided by FileTrackingMixin")

    def store_rendered_output(
        self,
        file_path: Path,
        html: str,
        template: str,
        metadata: dict[str, Any],
        dependencies: list[str] | None = None,
    ) -> None:
        """
        Store fully rendered HTML output in cache.

        This allows skipping BOTH markdown parsing AND template rendering for
        pages where content, template, and metadata are unchanged. Expected
        to provide 20-40% faster incremental builds.

        Args:
            file_path: Path to source file
            html: Fully rendered HTML (post-template, ready to write)
            template: Template name used for rendering
            metadata: Page metadata (frontmatter)
            dependencies: List of template/partial paths this page depends on
        """
        # Hash metadata to detect changes
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hash_str(metadata_str)

        # Calculate size for cache management
        size_bytes = len(html.encode("utf-8"))

        # Store as dict (will be serialized to JSON)
        self.rendered_output[str(file_path)] = {
            "html": html,
            "template": template,
            "metadata_hash": metadata_hash,
            "dependencies": dependencies or [],
            "timestamp": datetime.now().isoformat(),
            "size_bytes": size_bytes,
        }

    def get_rendered_output(
        self, file_path: Path, template: str, metadata: dict[str, Any]
    ) -> str | None:
        """
        Get cached rendered HTML if still valid.

        Validates that:
        1. Content file hasn't changed (via file_fingerprints)
        2. Metadata hasn't changed (via metadata_hash)
        3. Template name matches
        4. Template files haven't changed (via dependencies)
        5. Config hasn't changed (caller should validate config_hash)

        Args:
            file_path: Path to source file
            template: Current template name
            metadata: Current page metadata

        Returns:
            Cached HTML string if valid, None if invalid or not found
        """
        key = str(file_path)

        # Check if cached
        if key not in self.rendered_output:
            return None

        cached = self.rendered_output[key]

        # Validate file hasn't changed (uses fast mtime+size first)
        if self.is_changed(file_path):
            return None

        # Validate metadata hasn't changed
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hash_str(metadata_str)
        if cached.get("metadata_hash") != metadata_hash:
            return None

        # Validate template name matches
        if cached.get("template") != template:
            return None

        # Validate dependencies haven't changed (templates, partials)
        for dep_path in cached.get("dependencies", []):
            dep = Path(dep_path)
            if dep.exists() and self.is_changed(dep):
                # A dependency changed - invalidate cache
                return None

        return cached.get("html")

    def invalidate_rendered_output(self, file_path: Path) -> None:
        """
        Remove cached rendered output for a file.

        Args:
            file_path: Path to file
        """
        self.rendered_output.pop(str(file_path), None)

    def get_rendered_output_stats(self) -> dict[str, Any]:
        """
        Get rendered output cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.rendered_output:
            return {"cached_pages": 0, "total_size_mb": 0, "avg_size_kb": 0}

        total_size = sum(c.get("size_bytes", 0) for c in self.rendered_output.values())
        return {
            "cached_pages": len(self.rendered_output),
            "total_size_mb": total_size / 1024 / 1024,
            "avg_size_kb": (total_size / len(self.rendered_output) / 1024)
            if self.rendered_output
            else 0,
        }
