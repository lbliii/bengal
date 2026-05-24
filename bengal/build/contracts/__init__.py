"""
Contracts for incremental build components.
"""

from __future__ import annotations

from bengal.build.contracts.dependency_index import (
    DependencyIndexEntry,
    DependencyReadIndex,
    build_dependency_read_index,
)
from bengal.build.contracts.keys import (
    CacheKey,
    asset_key,
    content_key,
    data_key,
    parse_key,
    template_key,
)
from bengal.build.contracts.protocol import ChangeDetector, DetectionContext
from bengal.build.contracts.results import (
    ChangeDetectionResult,
    RebuildReason,
    RebuildReasonCode,
)

__all__ = [
    "CacheKey",
    "ChangeDetectionResult",
    "ChangeDetector",
    "DependencyIndexEntry",
    "DependencyReadIndex",
    "DetectionContext",
    "RebuildReason",
    "RebuildReasonCode",
    "asset_key",
    "build_dependency_read_index",
    "content_key",
    "data_key",
    "parse_key",
    "template_key",
]
