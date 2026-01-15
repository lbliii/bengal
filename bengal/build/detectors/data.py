"""
Data file change detection.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.results import ChangeDetectionResult, RebuildReason, RebuildReasonCode
from bengal.build.detectors.base import (
    data_key_for_path,
    normalize_source_path,
    page_key_for_path,
    page_key_for_page,
)
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.build.contracts.protocol import DetectionContext

logger = get_logger(__name__)

DATA_FILE_EXTENSIONS = frozenset({".yaml", ".yml", ".json", ".toml"})


class DataChangeDetector:
    """Detect data file changes and affected pages."""

    def detect(self, ctx: "DetectionContext") -> ChangeDetectionResult:
        data_dir = ctx.site.root_path / "data"
        if not data_dir.exists():
            return ChangeDetectionResult.empty()

        changed_data_files: list[Path] = []
        for data_file in data_dir.rglob("*"):
            if not data_file.is_file():
                continue
            if data_file.suffix not in DATA_FILE_EXTENSIONS:
                continue
            data_key = data_key_for_path(ctx.site.root_path, data_file)
            if data_key in ctx.forced_changed or ctx.cache.is_changed(data_file):
                changed_data_files.append(data_file)

        if not changed_data_files:
            return ChangeDetectionResult.empty()

        data_files_changed: set[CacheKey] = {
            data_key_for_path(ctx.site.root_path, data_file) for data_file in changed_data_files
        }

        pages_to_rebuild: set[CacheKey] = set()
        rebuild_reasons: dict[CacheKey, RebuildReason] = {}

        for data_file in changed_data_files:
            dep_key = Path(f"data:{data_file}")
            affected_pages = ctx.cache.get_affected_pages(dep_key)
            for page_path_str in affected_pages:
                page_path = normalize_source_path(ctx.site.root_path, page_path_str)
                page_key = page_key_for_path(ctx.site.root_path, page_path)
                pages_to_rebuild.add(page_key)

        if not pages_to_rebuild:
            for page in ctx.site.pages:
                if page.metadata.get("_generated"):
                    continue
                pages_to_rebuild.add(page_key_for_page(ctx.site.root_path, page))

        trigger = str(changed_data_files[0].relative_to(ctx.site.root_path))
        for page_key in pages_to_rebuild:
            rebuild_reasons.setdefault(
                page_key,
                RebuildReason(RebuildReasonCode.DATA_FILE_CHANGED, trigger=trigger),
            )

        return ChangeDetectionResult(
            pages_to_rebuild=frozenset(pages_to_rebuild),
            rebuild_reasons=rebuild_reasons,
            data_files_changed=frozenset(data_files_changed),
        )
