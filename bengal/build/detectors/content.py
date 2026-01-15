"""
Content and asset change detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.results import ChangeDetectionResult, RebuildReason, RebuildReasonCode
from bengal.build.detectors.base import (
    asset_key_for_asset,
    page_key_for_page,
)
from bengal.core.section import resolve_page_section_path
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.build.contracts.protocol import DetectionContext

logger = get_logger(__name__)


class ContentChangeDetector:
    """Detect changes in content pages and assets."""

    def detect(self, ctx: "DetectionContext") -> ChangeDetectionResult:
        pages_to_rebuild: set[CacheKey] = set()
        assets_to_process: set[CacheKey] = set()
        rebuild_reasons: dict[CacheKey, RebuildReason] = {}
        content_files_changed: set[CacheKey] = set()
        affected_tags: set[str] = set()
        affected_sections: set[CacheKey] = set()

        forced_changed = ctx.forced_changed
        nav_changed = ctx.nav_changed

        for page in ctx.site.pages:
            if page.metadata.get("_generated"):
                continue

            page_key = page_key_for_page(ctx.site.root_path, page)

            reason: RebuildReason | None = None
            if page_key in forced_changed:
                reason = RebuildReason(RebuildReasonCode.FORCED, trigger=str(page.source_path))
            elif page_key in nav_changed:
                reason = RebuildReason(
                    RebuildReasonCode.ADJACENT_NAV_CHANGED,
                    trigger=str(page.source_path),
                )
            elif ctx.cache.is_changed(page.source_path):
                reason = RebuildReason(
                    RebuildReasonCode.CONTENT_CHANGED,
                    trigger=str(page.source_path),
                )

            if reason:
                pages_to_rebuild.add(page_key)
                content_files_changed.add(page_key)
                rebuild_reasons.setdefault(page_key, reason)

                if page.tags:
                    affected_tags.update(
                        str(tag).lower().replace(" ", "-")
                        for tag in page.tags
                        if tag is not None
                    )

                section_path = resolve_page_section_path(page)
                if section_path:
                    affected_sections.add(CacheKey(str(section_path)))

        for asset in ctx.site.assets:
            asset_key = asset_key_for_asset(ctx.site.root_path, asset)
            if asset_key in forced_changed or asset_key in nav_changed:
                assets_to_process.add(asset_key)
            elif ctx.cache.is_changed(asset.source_path):
                assets_to_process.add(asset_key)

        if not pages_to_rebuild and not assets_to_process:
            return ChangeDetectionResult.empty()

        return ChangeDetectionResult(
            pages_to_rebuild=frozenset(pages_to_rebuild),
            rebuild_reasons=rebuild_reasons,
            assets_to_process=frozenset(assets_to_process),
            content_files_changed=frozenset(content_files_changed),
            affected_tags=frozenset(affected_tags),
            affected_sections=frozenset(affected_sections),
        )
