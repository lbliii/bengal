"""
Immutable result types for change detection.

All detectors return ChangeDetectionResult. Results are merged
with .merge() to compose detector outputs.

This module is the CANONICAL home of the rebuild-reason vocabulary
(RebuildReasonCode / RebuildReason). The build-orchestration copy at
``bengal.orchestration.build.results`` re-exports these symbols, so the two
import paths resolve to the same objects (see #445).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bengal.build.contracts.keys import CacheKey


class RebuildReasonCode(Enum):
    """
    Why a page needs rebuilding.

    Values are STRINGS so they serialize cleanly into observability output and
    JSON sidecars (do not switch to ``auto()`` ints). The vocabulary is the
    union of the historic contracts-side and orchestration-side enums; where two
    names denoted the same concept they alias to a single value:

    - ``CASCADE`` and ``CASCADE_DEPENDENCY`` are aliases (value
      ``"cascade_dependency"``).
    """

    CONTENT_CHANGED = "content_changed"
    DATA_FILE_CHANGED = "data_file_changed"
    TEMPLATE_CHANGED = "template_changed"
    TAXONOMY_CASCADE = "taxonomy_cascade"
    ASSET_FINGERPRINT_CHANGED = "asset_fingerprint_changed"
    CONFIG_CHANGED = "config_changed"
    OUTPUT_MISSING = "output_missing"
    CROSS_VERSION_DEPENDENCY = "cross_version_dependency"
    NAV_CHANGED = "nav_changed"
    ADJACENT_NAV_CHANGED = "adjacent_nav_changed"
    FORCED = "forced"
    FULL_REBUILD = "full_rebuild"
    # Cascade-dependency rebuild. CASCADE is the original contracts-side
    # spelling; CASCADE_DEPENDENCY is the orchestration-side spelling. They
    # are intentional aliases so neither call-site breaks.
    CASCADE = "cascade_dependency"
    CASCADE_DEPENDENCY = "cascade_dependency"  # noqa: PIE796 (intentional alias of CASCADE)


class SkipReasonCode(Enum):
    """Why a page was skipped (not rebuilt)."""

    CACHE_HIT = "cache_hit"
    NO_CHANGES = "no_changes"
    SECTION_FILTERED = "section_filtered"


@dataclass(frozen=True, slots=True)
class RebuildReason:
    """
    Detailed reason for a page rebuild.

    ``details`` is the primary, structured payload (used by observability and
    the ``--explain`` CLI). ``trigger`` is a backward-compatible convenience
    field for the common single-path case (e.g. ``"data/team.yaml"``); older
    call-sites that read ``reason.trigger`` keep working unchanged.
    """

    code: RebuildReasonCode
    details: dict[str, Any] = field(default_factory=dict)
    trigger: str = ""  # Backward-compat: what triggered it (e.g. "data/team.yaml")

    def __str__(self) -> str:
        # Observability/JSON form: lead with the string code value.
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.code.value} ({detail_str})"
        if self.trigger:
            return f"{self.code.value}: {self.trigger}"
        return self.code.value


# Sentinel key used by ChangeDetectionResult.full_rebuild() to record its reason
# (a full rebuild has no single triggering page key).
_FULL_REBUILD_KEY = "<full_rebuild>"


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
        """
        Create result indicating a full rebuild is needed.

        The ``reason`` string is recorded under a sentinel key in
        ``rebuild_reasons`` (as the ``trigger`` of a FULL_REBUILD reason) so the
        cause is observable downstream instead of being silently discarded.
        """
        from bengal.build.contracts.keys import CacheKey  # local: NewType is str at runtime

        return cls(
            force_full_rebuild=True,
            rebuild_reasons={
                CacheKey(_FULL_REBUILD_KEY): RebuildReason(
                    code=RebuildReasonCode.FULL_REBUILD,
                    trigger=reason,
                )
            },
        )

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
