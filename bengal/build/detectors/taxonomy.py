"""
Taxonomy cascade detection.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.results import ChangeDetectionResult, RebuildReason, RebuildReasonCode
from bengal.build.detectors.base import (
    key_to_path,
    normalize_source_path,
    page_key_for_page,
)
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.build.contracts.protocol import DetectionContext

logger = get_logger(__name__)


class TaxonomyCascadeDetector:
    """Detect tag/section cascades from changed pages."""

    def detect(self, ctx: "DetectionContext") -> ChangeDetectionResult:
        affected_tags: set[str] = set()
        affected_sections: set[Path] = set()
        pages_to_rebuild: set[CacheKey] = set()
        rebuild_reasons: dict[CacheKey, RebuildReason] = {}

        for page_key in ctx.previous.content_files_changed:
            page_path = key_to_path(ctx.site.root_path, page_key)
            page = self._get_page_by_path(ctx, page_path)
            if not page:
                continue

            old_tags = ctx.cache.get_previous_tags(page.source_path)
            new_tags = set(page.tags) if page.tags else set()

            changed_tags = (new_tags - old_tags) | (old_tags - new_tags)
            for tag in changed_tags:
                if tag is not None:
                    affected_tags.add(str(tag).lower().replace(" ", "-"))

            if hasattr(page, "section") and page.section:
                affected_sections.add(page.section)

        if affected_tags:
            for page in ctx.site.generated_pages:
                if page.metadata.get("type") in ("tag", "tag-index"):
                    tag_slug = page.metadata.get("_tag_slug")
                    if (tag_slug and tag_slug in affected_tags) or page.metadata.get("type") == "tag-index":
                        key = page_key_for_page(ctx.site.root_path, page)
                        pages_to_rebuild.add(key)
                        rebuild_reasons.setdefault(
                            key,
                            RebuildReason(
                                RebuildReasonCode.TAXONOMY_CASCADE,
                                trigger=f"tag:{tag_slug or 'index'}",
                            ),
                        )

        if affected_sections:
            for page in ctx.site.pages:
                if page.metadata.get("_generated") and page.metadata.get("type") == "archive":
                    page_section = page.metadata.get("_section")
                    if page_section and page_section in affected_sections:
                        key = page_key_for_page(ctx.site.root_path, page)
                        pages_to_rebuild.add(key)
                        rebuild_reasons.setdefault(
                            key,
                            RebuildReason(
                                RebuildReasonCode.TAXONOMY_CASCADE,
                                trigger=str(page_section),
                            ),
                        )

        # Metadata cascades (member page updates → term pages)
        if ctx.tracker:
            pages_to_rebuild.update(self._metadata_cascades(ctx, rebuild_reasons))

        if not pages_to_rebuild:
            return ChangeDetectionResult.empty()

        return ChangeDetectionResult(
            pages_to_rebuild=frozenset(pages_to_rebuild),
            rebuild_reasons=rebuild_reasons,
            affected_tags=frozenset(affected_tags),
        )

    def _metadata_cascades(
        self,
        ctx: "DetectionContext",
        rebuild_reasons: dict[CacheKey, RebuildReason],
    ) -> set[CacheKey]:
        if not ctx.tracker:
            return set()

        pages_to_rebuild: set[CacheKey] = set()
        term_pages_to_add: set[str] = set()

        for page_key in ctx.previous.pages_to_rebuild:
            page_path = key_to_path(ctx.site.root_path, page_key)
            page = self._get_page_by_path(ctx, page_path)
            if not page or not page.tags:
                continue

            try:
                term_keys = ctx.tracker.get_term_pages_for_member(page.source_path)
                term_keys_set = set(term_keys) if term_keys else set()
            except TypeError:
                term_keys_set = set()

            term_pages_to_add.update(term_keys_set)

        for term_key in term_pages_to_add:
            term_page = self._find_term_page_by_key(ctx, term_key)
            if term_page:
                key = page_key_for_page(ctx.site.root_path, term_page)
                pages_to_rebuild.add(key)
                rebuild_reasons.setdefault(
                    key,
                    RebuildReason(RebuildReasonCode.TAXONOMY_CASCADE, trigger=str(term_key)),
                )

        return pages_to_rebuild

    def _get_page_by_path(self, ctx: "DetectionContext", path: Path) -> Any | None:
        return ctx.site.page_by_source_path.get(path)

    def _find_term_page_by_key(self, ctx: "DetectionContext", term_key: str) -> Any | None:
        # Term keys look like "_generated/tags/tag:python"
        for page in ctx.site.generated_pages:
            if page.metadata.get("_generated") and page.metadata.get("type") in ("tag", "tag-index"):
                if page.metadata.get("_term_key") == term_key:
                    return page

        # Fallback: match against source path for generated term pages
        for page in ctx.site.generated_pages:
            if page.metadata.get("_generated") and term_key in str(page.source_path):
                return page
        return None
