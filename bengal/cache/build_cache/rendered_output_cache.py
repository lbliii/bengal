"""
Rendered output caching mixin for BuildCache.

Provides methods for caching fully rendered HTML output to skip both markdown
parsing AND template rendering. Optimization #3 from the cache RFC.

Key Concepts:
- Caches final HTML (post-template, ready to write)
- Validates against content, metadata, template, dependencies, AND asset manifest
- Expected 20-40% faster incremental builds

Related Modules:
- bengal.cache.build_cache.core: Main BuildCache class
- bengal.rendering.renderer: Page rendering
- plan/active/rfc-orchestrator-performance.md: Performance RFC

"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.hashing import hash_str
from bengal.utils.primitives.sentinel import MISSING

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


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

    def _compute_metadata_hash(self, metadata: dict[str, Any]) -> str:
        """Compute stable hash of metadata, with special handling for autodoc."""
        if not metadata:
            return hash_str("{}")

        # Create a copy to avoid mutating the original
        clean_metadata = metadata.copy()

        # Handle autodoc elements specially: they are large objects whose string
        # representation may be unstable or contain transient attributes (like hrefs
        # that depend on prefix derivation).
        # Instead of hashing the whole DocElement, we use the pre-computed doc_content_hash.
        is_autodoc = clean_metadata.get("is_autodoc", False)
        doc_hash = clean_metadata.get("doc_content_hash")

        if is_autodoc and doc_hash:
            # If we have a doc content hash, it is the single source of truth for
            # whether the documentation content changed. We can remove the heavy
            # autodoc_element from the metadata hash.
            clean_metadata.pop("autodoc_element", None)
            # Ensure doc_content_hash stays in the dict

        # Also remove other transient or large metadata that shouldn't affect the hash
        clean_metadata.pop("_site", None)
        clean_metadata.pop("_section", None)

        metadata_str = json.dumps(clean_metadata, sort_keys=True, default=str)
        return hash_str(metadata_str)

    def store_rendered_output(
        self,
        file_path: Path,
        html: str,
        template: str,
        metadata: dict[str, Any],
        dependencies: list[str] | None = None,
        output_dir: Path | None = None,
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
            output_dir: Output directory for locating asset manifest
        """
        # Hash metadata to detect changes
        metadata_hash = self._compute_metadata_hash(metadata)

        # Calculate size for cache management
        size_bytes = len(html.encode("utf-8"))

        # Capture asset manifest mtime for invalidation when assets change
        # This ensures cached HTML is invalidated when CSS/JS fingerprints change
        asset_manifest_mtime: float | None = None
        if output_dir:
            manifest_path = output_dir / "asset-manifest.json"
            try:
                asset_manifest_mtime = manifest_path.stat().st_mtime
            except (FileNotFoundError, OSError):
                pass

        # Store as dict (will be serialized to JSON)
        self.rendered_output[str(file_path)] = {
            "html": html,
            "template": template,
            "metadata_hash": metadata_hash,
            "dependencies": dependencies or [],
            "timestamp": datetime.now(UTC).isoformat(),
            "size_bytes": size_bytes,
            "asset_manifest_mtime": asset_manifest_mtime,
        }

    def get_rendered_output(
        self,
        file_path: Path,
        template: str,
        metadata: dict[str, Any],
        output_dir: Path | None = None,
    ) -> str | Any:
        """
        Get cached rendered HTML if still valid.

        Validates that:
        1. Content file hasn't changed (via file_fingerprints)
        2. Metadata hasn't changed (via metadata_hash)
        3. Template name matches
        4. Template files haven't changed (via dependencies)
        5. Asset manifest hasn't changed (via mtime) - prevents stale fingerprints
        6. Config hasn't changed (caller should validate config_hash)

        Args:
            file_path: Path to source file
            template: Current template name
            metadata: Current page metadata
            output_dir: Output directory for locating asset manifest

        Returns:
            Cached HTML string if valid, MISSING if invalid or not found
        """
        key = str(file_path)

        # Check if cached
        cached = self.rendered_output.get(key, MISSING)
        if cached is MISSING:
            return MISSING

        # Validate file hasn't changed (uses fast mtime+size first)
        # RFC: Autodoc Incremental Caching Enhancement
        # For autodoc pages, the "source file" is a virtual path that doesn't exist on disk.
        # Instead of checking if the virtual file changed (which it always "does"),
        # we rely on the metadata_hash which now contains the doc_content_hash.
        is_autodoc = metadata.get("is_autodoc", False)
        if not is_autodoc and self.is_changed(file_path):
            return MISSING

        # Validate metadata hasn't changed
        metadata_hash = self._compute_metadata_hash(metadata)
        if cached.get("metadata_hash") != metadata_hash:
            return MISSING

        # Validate template name matches
        if cached.get("template") != template:
            return MISSING

        # Validate dependencies haven't changed (templates, partials)
        for dep_path in cached.get("dependencies", []):
            dep = Path(dep_path)
            if dep.exists() and self.is_changed(dep):
                # A dependency changed - invalidate cache
                return MISSING

        # Validate asset manifest hasn't changed (prevents stale asset fingerprints)
        # This is critical: cached HTML contains fingerprinted asset URLs like
        # style.abc123.css - if assets are reprocessed, fingerprints change
        cached_manifest_mtime = cached.get("asset_manifest_mtime")
        if output_dir and cached_manifest_mtime is not None:
            manifest_path = output_dir / "asset-manifest.json"
            try:
                current_mtime = manifest_path.stat().st_mtime
                if current_mtime != cached_manifest_mtime:
                    logger.debug(
                        "rendered_cache_invalidated_asset_manifest",
                        page=key,
                        cached_mtime=cached_manifest_mtime,
                        current_mtime=current_mtime,
                    )
                    return MISSING
            except (FileNotFoundError, OSError):
                # Manifest doesn't exist - invalidate to be safe
                return MISSING

        return cached.get("html")

    def invalidate_rendered_output(self, file_path: Path) -> bool:
        """
        Remove cached rendered output for a file.

        Args:
            file_path: Path to file

        Returns:
            True if cache entry was removed, False if not present
        """
        key = str(file_path)
        if key in self.rendered_output:
            del self.rendered_output[key]
            return True
        return False

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
