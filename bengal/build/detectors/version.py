"""
Version-related change detection.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.results import ChangeDetectionResult, RebuildReason, RebuildReasonCode
from bengal.build.detectors.base import key_to_path, page_key_for_path
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.build.contracts.protocol import DetectionContext

logger = get_logger(__name__)


class VersionChangeDetector:
    """Detect cross-version dependency cascades."""

    def detect(self, ctx: "DetectionContext") -> ChangeDetectionResult:
        if not getattr(ctx.site, "versioning_enabled", False):
            return ChangeDetectionResult.empty()
        if not ctx.tracker or not hasattr(ctx.tracker, "get_cross_version_dependents"):
            return ChangeDetectionResult.empty()

        pages_to_rebuild: set[CacheKey] = set()
        rebuild_reasons: dict[CacheKey, RebuildReason] = {}

        for changed_key in ctx.previous.pages_to_rebuild:
            changed_path = key_to_path(ctx.site.root_path, changed_key)
            page = ctx.site.page_by_source_path.get(changed_path)
            if not page:
                continue

            version = getattr(page, "version", None) or page.metadata.get("version")
            if not version:
                continue

            path_str = str(changed_path)
            content_prefix = str(ctx.site.root_path / "content") + "/"
            if path_str.startswith(content_prefix):
                path_str = path_str[len(content_prefix) :]

            version_config = getattr(ctx.site, "version_config", None)
            if version_config:
                for section in getattr(version_config, "sections", []):
                    section_prefix = f"{section}/{version}/"
                    if path_str.startswith(section_prefix):
                        path_str = section + "/" + path_str[len(section_prefix) :]
                        break

            if path_str.endswith(".md"):
                path_str = path_str[:-3]

            if path_str.endswith("/_index"):
                path_str = path_str[:-7]
            elif path_str.endswith("/index"):
                path_str = path_str[:-6]

            dependents = ctx.tracker.get_cross_version_dependents(
                changed_version=version,
                changed_path=path_str,
            )

            for dependent_path in dependents:
                dependent_key = page_key_for_path(ctx.site.root_path, dependent_path)
                pages_to_rebuild.add(dependent_key)
                rebuild_reasons.setdefault(
                    dependent_key,
                    RebuildReason(
                        RebuildReasonCode.CROSS_VERSION_DEPENDENCY,
                        trigger=path_str,
                    ),
                )

        if not pages_to_rebuild:
            return ChangeDetectionResult.empty()

        return ChangeDetectionResult(
            pages_to_rebuild=frozenset(pages_to_rebuild),
            rebuild_reasons=rebuild_reasons,
        )
