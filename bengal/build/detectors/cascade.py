"""
Frontmatter cascade and navigation dependency detection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.results import ChangeDetectionResult, RebuildReason, RebuildReasonCode
from bengal.build.detectors.base import key_to_path, page_key_for_page
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.hashing import hash_str

if TYPE_CHECKING:
    from bengal.build.contracts.protocol import DetectionContext
    from bengal.core.page import Page

logger = get_logger(__name__)


class SectionCascadeDetector:
    """Detect pages affected by frontmatter cascade changes in section indices."""

    def detect(self, ctx: "DetectionContext") -> ChangeDetectionResult:
        pages_to_rebuild: set[CacheKey] = set()
        rebuild_reasons: dict[CacheKey, RebuildReason] = {}

        # We only need to check pages that are already marked for rebuild
        # because those are the only ones that could trigger a cascade.
        for page_key in ctx.previous.pages_to_rebuild:
            page_path = key_to_path(ctx.site.root_path, page_key)
            
            # Optimization: Only section indices can trigger cascades
            if page_path.stem not in ("_index", "index"):
                continue

            page = ctx.site.page_by_source_path.get(page_path)
            if not page or "cascade" not in page.metadata:
                continue

            # Optimization: Check if cascade metadata actually changed
            if self._cascade_unchanged(ctx, page, page_path):
                continue

            affected_pages = self._find_cascade_affected_pages(ctx, page)
            for affected_path in affected_pages:
                key = page_key_for_page(ctx.site.root_path, ctx.site.page_by_source_path[affected_path])
                if key not in ctx.previous.pages_to_rebuild:
                    pages_to_rebuild.add(key)
                    rebuild_reasons[key] = RebuildReason(
                        RebuildReasonCode.CASCADE,
                        trigger=str(page_path),
                    )

        if not pages_to_rebuild:
            return ChangeDetectionResult.empty()

        return ChangeDetectionResult(
            pages_to_rebuild=frozenset(pages_to_rebuild),
            rebuild_reasons=rebuild_reasons,
        )

    def _cascade_unchanged(self, ctx: "DetectionContext", page: Page, path: Path) -> bool:
        """Check if cascade metadata is unchanged from cached version."""
        try:
            current_cascade = page.metadata.get("cascade", {})
            current_hash = hash_str(
                json.dumps(current_cascade, sort_keys=True, default=str)
            )

            # Get cached metadata from parsed_content cache
            cached = ctx.cache.parsed_content.get(str(path))
            if not isinstance(cached, dict):
                return False

            cached_cascade_hash = cached.get("cascade_metadata_hash")
            if cached_cascade_hash is not None:
                return cached_cascade_hash == current_hash

            # Fallback: Compare full metadata hash
            cached_full_hash = cached.get("metadata_hash")
            if cached_full_hash is not None:
                current_full_hash = hash_str(
                    json.dumps(page.metadata or {}, sort_keys=True, default=str)
                )
                return cached_full_hash == current_full_hash

            return False
        except Exception:
            return False

    def _find_cascade_affected_pages(self, ctx: "DetectionContext", index_page: Page) -> set[Path]:
        """Find all pages affected by a cascade change."""
        affected: set[Path] = set()
        
        # Determine if root-level or section-level
        is_root_level = True
        target_section = None
        for section in ctx.site.sections:
            if section.index_page == index_page:
                target_section = section
                is_root_level = False
                break
            if any(p == index_page for p in section.pages):
                is_root_level = False
                # If it's in a section but not the index page, it shouldn't trigger cascade
                # (though stem check above handles this too)
                break

        if is_root_level:
            for page in ctx.site.pages:
                if not page.metadata.get("_generated"):
                    affected.add(page.source_path)
        elif target_section:
            for page in target_section.regular_pages_recursive:
                if not page.metadata.get("_generated"):
                    affected.add(page.source_path)

        # Remove the index page itself
        affected.discard(index_page.source_path)
        return affected


class NavigationDependencyDetector:
    """Detect pages affected by prev/next navigation changes."""

    def detect(self, ctx: "DetectionContext") -> ChangeDetectionResult:
        pages_to_rebuild: set[CacheKey] = set()
        rebuild_reasons: dict[CacheKey, RebuildReason] = {}

        for page_key in ctx.previous.pages_to_rebuild:
            page_path = key_to_path(ctx.site.root_path, page_key)
            page = ctx.site.page_by_source_path.get(page_path)
            if not page or page.metadata.get("_generated"):
                continue

            # Check neighbors
            for neighbor_attr in ("prev", "next"):
                neighbor = getattr(page, neighbor_attr, None)
                if neighbor and not neighbor.metadata.get("_generated"):
                    key = page_key_for_page(ctx.site.root_path, neighbor)
                    if key not in ctx.previous.pages_to_rebuild:
                        pages_to_rebuild.add(key)
                        rebuild_reasons[key] = RebuildReason(
                            RebuildReasonCode.ADJACENT_NAV_CHANGED,
                            trigger=str(page_path),
                        )

        if not pages_to_rebuild:
            return ChangeDetectionResult.empty()

        return ChangeDetectionResult(
            pages_to_rebuild=frozenset(pages_to_rebuild),
            rebuild_reasons=rebuild_reasons,
        )
