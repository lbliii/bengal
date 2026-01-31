"""
Immutable result types for change detection.

All detectors return ChangeDetectionResult. Results are merged
with .merge() to compose detector outputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.build.contracts.keys import CacheKey


class RebuildReasonCode(Enum):
    """Why a page needs rebuilding."""

    CONTENT_CHANGED = auto()
    DATA_FILE_CHANGED = auto()
    TEMPLATE_CHANGED = auto()
    TAXONOMY_CASCADE = auto()
    CASCADE = auto()
    ASSET_FINGERPRINT_CHANGED = auto()
    CONFIG_CHANGED = auto()
    OUTPUT_MISSING = auto()
    CROSS_VERSION_DEPENDENCY = auto()
    ADJACENT_NAV_CHANGED = auto()
    FORCED = auto()
    FULL_REBUILD = auto()


@dataclass(frozen=True, slots=True)
class RebuildReason:
    """Detailed reason for page rebuild."""

    code: RebuildReasonCode
    trigger: str = ""  # What triggered it (e.g., "data/team.yaml")

    def __str__(self) -> str:
        if self.trigger:
            return f"{self.code.name}: {self.trigger}"
        return self.code.name


@dataclass(frozen=True, slots=True)
class ChangeDetectionResult:
    """
    Immutable result of change detection.

    Produced by each detector, merged to accumulate changes.

    Thread Safety:
        Frozen dataclass - inherently thread-safe.
        Can be safely passed between threads without copying.
    """

    # Pages that need rebuilding (canonical keys)
    pages_to_rebuild: frozenset[CacheKey] = field(default_factory=frozenset)

    # Why each page needs rebuilding (for logging/debugging)
    rebuild_reasons: Mapping[CacheKey, RebuildReason] = field(default_factory=dict)

    # Assets that need processing
    assets_to_process: frozenset[CacheKey] = field(default_factory=frozenset)

    # What changed (for downstream detectors)
    content_files_changed: frozenset[CacheKey] = field(default_factory=frozenset)
    data_files_changed: frozenset[CacheKey] = field(default_factory=frozenset)
    templates_changed: frozenset[CacheKey] = field(default_factory=frozenset)

    # Affected taxonomies (for taxonomy detector)
    affected_tags: frozenset[str] = field(default_factory=frozenset)
    affected_sections: frozenset[CacheKey] = field(default_factory=frozenset)

    # Global flags
    config_changed: bool = False
    force_full_rebuild: bool = False

    @classmethod
    def empty(cls) -> ChangeDetectionResult:
        """Create empty result."""
        return cls()

    @classmethod
    def full_rebuild(cls, reason: str = "forced") -> ChangeDetectionResult:
        """Create result indicating full rebuild needed."""
        return cls(force_full_rebuild=True)

    def merge(self, other: ChangeDetectionResult) -> ChangeDetectionResult:
        """
        Merge two results (immutable - returns new instance).

        Used to compose results from multiple detectors.
        """
        return ChangeDetectionResult(
            pages_to_rebuild=self.pages_to_rebuild | other.pages_to_rebuild,
            rebuild_reasons={**self.rebuild_reasons, **other.rebuild_reasons},
            assets_to_process=self.assets_to_process | other.assets_to_process,
            content_files_changed=self.content_files_changed | other.content_files_changed,
            data_files_changed=self.data_files_changed | other.data_files_changed,
            templates_changed=self.templates_changed | other.templates_changed,
            affected_tags=self.affected_tags | other.affected_tags,
            affected_sections=self.affected_sections | other.affected_sections,
            config_changed=self.config_changed or other.config_changed,
            force_full_rebuild=self.force_full_rebuild or other.force_full_rebuild,
        )

    def with_pages(
        self,
        pages: frozenset[CacheKey],
        reason: RebuildReason,
    ) -> ChangeDetectionResult:
        """Add pages with reason (returns new instance)."""
        new_reasons = {**self.rebuild_reasons}
        for page in pages:
            if page not in new_reasons:  # Don't overwrite existing reason
                new_reasons[page] = reason
        return ChangeDetectionResult(
            pages_to_rebuild=self.pages_to_rebuild | pages,
            rebuild_reasons=new_reasons,
            assets_to_process=self.assets_to_process,
            content_files_changed=self.content_files_changed,
            data_files_changed=self.data_files_changed,
            templates_changed=self.templates_changed,
            affected_tags=self.affected_tags,
            affected_sections=self.affected_sections,
            config_changed=self.config_changed,
            force_full_rebuild=self.force_full_rebuild,
        )

    @property
    def needs_rebuild(self) -> bool:
        """Check if any pages need rebuilding."""
        return bool(self.pages_to_rebuild) or self.force_full_rebuild

    def summary(self) -> str:
        """Human-readable summary."""
        parts: list[str] = []
        if self.force_full_rebuild:
            parts.append("FULL REBUILD")
        if self.pages_to_rebuild:
            parts.append(f"{len(self.pages_to_rebuild)} pages")
        if self.assets_to_process:
            parts.append(f"{len(self.assets_to_process)} assets")
        if self.data_files_changed:
            parts.append(f"{len(self.data_files_changed)} data files")
        if self.templates_changed:
            parts.append(f"{len(self.templates_changed)} templates")
        return ", ".join(parts) or "no changes"
