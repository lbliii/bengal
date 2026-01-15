"""
Autodoc change detection.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.results import ChangeDetectionResult, RebuildReason, RebuildReasonCode
from bengal.build.detectors.base import normalize_source_path, page_key_for_path
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.build.contracts.protocol import DetectionContext

logger = get_logger(__name__)


class AutodocChangeDetector:
    """Detect autodoc source changes and affected pages."""

    def detect(self, ctx: "DetectionContext") -> ChangeDetectionResult:
        autodoc_pages = self._find_autodoc_changes(ctx)
        if not autodoc_pages:
            return ChangeDetectionResult.empty()

        pages_to_rebuild: set[CacheKey] = set()
        rebuild_reasons: dict[CacheKey, RebuildReason] = {}

        for page_path_str in autodoc_pages:
            page_path = normalize_source_path(ctx.site.root_path, page_path_str)
            page_key = page_key_for_path(ctx.site.root_path, page_path)
            pages_to_rebuild.add(page_key)
            rebuild_reasons.setdefault(
                page_key,
                RebuildReason(
                    RebuildReasonCode.CONTENT_CHANGED,
                    trigger="autodoc_source_changed",
                ),
            )

        return ChangeDetectionResult(
            pages_to_rebuild=frozenset(pages_to_rebuild),
            rebuild_reasons=rebuild_reasons,
        )

    def _find_autodoc_changes(self, ctx: "DetectionContext") -> set[str]:
        autodoc_pages_to_rebuild: set[str] = set()

        if not hasattr(ctx.cache, "autodoc_dependencies") or not hasattr(
            ctx.cache, "get_autodoc_source_files"
        ):
            return autodoc_pages_to_rebuild

        try:
            def _is_external_autodoc_source(path: Path) -> bool:
                parts = path.parts
                return (
                    "site-packages" in parts
                    or "dist-packages" in parts
                    or ".venv" in parts
                    or ".tox" in parts
                )

            source_files = ctx.cache.get_autodoc_source_files()
            if source_files:
                for source_file in source_files:
                    source_path = Path(source_file)
                    if _is_external_autodoc_source(source_path):
                        continue
                    if ctx.cache.is_changed(source_path):
                        affected_pages = ctx.cache.get_affected_autodoc_pages(source_path)
                        if affected_pages:
                            autodoc_pages_to_rebuild.update(affected_pages)

            if hasattr(ctx.cache, "get_stale_autodoc_sources"):
                stale_sources = ctx.cache.get_stale_autodoc_sources(ctx.site.root_path)
                if stale_sources:
                    for source_key in stale_sources:
                        affected_pages = ctx.cache.get_affected_autodoc_pages(source_key)
                        if affected_pages:
                            autodoc_pages_to_rebuild.update(affected_pages)

                    logger.info(
                        "autodoc_self_validation_detected_stale",
                        stale_count=len(stale_sources),
                        affected_pages=len(autodoc_pages_to_rebuild),
                    )

            if autodoc_pages_to_rebuild and hasattr(ctx.cache, "is_doc_content_changed"):
                page_to_source = {}
                for src_key, pages in ctx.cache.autodoc_dependencies.items():
                    for page_path in pages:
                        page_to_source[page_path] = src_key

                filtered_pages: set[str] = set()
                skipped_count = 0

                for page_path_str in autodoc_pages_to_rebuild:
                    source_key = page_to_source.get(page_path_str)
                    page = ctx.site.page_by_source_path.get(Path(page_path_str))
                    doc_hash = page.metadata.get("doc_content_hash") if page else None

                    if source_key and doc_hash:
                        if ctx.cache.is_doc_content_changed(source_key, page_path_str, doc_hash):
                            filtered_pages.add(page_path_str)
                        else:
                            skipped_count += 1
                    else:
                        filtered_pages.add(page_path_str)

                if skipped_count > 0:
                    logger.debug(
                        "autodoc_skipping_unchanged_content",
                        skipped=skipped_count,
                        remaining=len(filtered_pages),
                    )
                autodoc_pages_to_rebuild = filtered_pages

            if autodoc_pages_to_rebuild:
                logger.info(
                    "autodoc_selective_rebuild",
                    affected_pages=len(autodoc_pages_to_rebuild),
                    reason="source_files_changed",
                )
        except (TypeError, AttributeError):
            pass

        return autodoc_pages_to_rebuild
