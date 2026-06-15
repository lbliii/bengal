"""
Result dataclasses for build orchestration phases.

Provides typed dataclasses for better type safety, readability, and IDE support.

All dataclasses support convenient access patterns:
- Tuple unpacking via __iter__() methods
- Dict-like access for ChangeSummary (to_dict(), items(), get(), __getitem__())

Note:
    The rebuild-reason vocabulary (``RebuildReasonCode`` / ``RebuildReason``) and
    ``SkipReasonCode`` are CANONICALLY defined in
    ``bengal.build.contracts.results`` and re-exported here so the two import
    paths resolve to the same objects (see #445). Do not redefine them.

See Also:
- plan/active/rfc-dataclass-improvements.md - Design rationale
- plan/rfc-incremental-build-observability.md - Incremental decision tracking

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

# Canonical rebuild/skip vocabulary lives in the contracts package. Re-export so
# that bengal.orchestration.build.results.RebuildReasonCode IS
# bengal.build.contracts.results.RebuildReasonCode (identity, not a copy).
from bengal.build.contracts.results import (
    RebuildReason,
    RebuildReasonCode,
    SkipReasonCode,
)

if TYPE_CHECKING:
    from collections.abc import ItemsView
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.core.asset import Asset
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.content import ContentOrchestrator
    from bengal.protocols.core import PageLike, SectionLike
    from bengal.utils.observability.logger import BengalLogger

__all__ = [
    "ChangeSummary",
    "ConfigCheckResult",
    "DiscoveryPhaseInput",
    "DiscoveryPhaseOutput",
    "FilterResult",
    "IncrementalDecision",
    "RebuildReason",
    "RebuildReasonCode",
    "SkipReasonCode",
]


@dataclass
class DiscoveryPhaseInput:
    """
    Input for the discovery phase.

    Contains everything needed to run content and asset discovery
    without coupling to BuildOrchestrator.

    Attributes:
        site: Site instance to populate
        cache: Optional BuildCache for incremental builds
        incremental: Whether this is an incremental build
        build_context: Optional BuildContext for content caching
        content_orchestrator: Optional ContentOrchestrator to reuse (avoids creating duplicate)
    """

    site: Site
    cache: BuildCache | None
    incremental: bool
    build_context: BuildContext | None
    content_orchestrator: ContentOrchestrator | None = None


@dataclass
class DiscoveryPhaseOutput:
    """
    Output from the discovery phase.

    Contains the discovered pages, sections, and assets.
    Cached content lives in build_context; discovery populates it.

    Attributes:
        pages: Discovered content pages
        sections: Discovered sections
        assets: Discovered assets
        content_ms: Time spent on content discovery (ms)
        assets_ms: Time spent on asset discovery (ms)
    """

    pages: list[PageLike]
    sections: list[SectionLike]
    assets: list[Asset]
    content_ms: float = 0.0
    assets_ms: float = 0.0


@dataclass
class IncrementalDecision:
    """
    Complete picture of incremental build decisions.

    Provides observability into the incremental filter's decision-making
    for debugging and the --explain CLI flag.

    Attributes:
        pages_to_build: Pages that will be rebuilt
        pages_skipped_count: Number of pages skipped (avoid storing full list)
        rebuild_reasons: Why each page is being rebuilt (keyed by source_path str)
        skip_reasons: Why pages were skipped (only populated when verbose=True)
        asset_changes: Which assets triggered rebuilds
        fingerprint_changes: Whether CSS/JS fingerprints changed

    """

    pages_to_build: list[PageLike]
    pages_skipped_count: int
    rebuild_reasons: dict[str, RebuildReason] = field(default_factory=dict)
    skip_reasons: dict[str, SkipReasonCode] = field(default_factory=dict)
    asset_changes: list[str] = field(default_factory=list)
    fingerprint_changes: bool = False

    def add_rebuild_reason(
        self,
        page_path: str,
        code: RebuildReasonCode,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add a rebuild reason for a page (will not overwrite existing)."""
        if page_path not in self.rebuild_reasons:
            self.rebuild_reasons[page_path] = RebuildReason(code=code, details=details or {})

    def log_summary(self, logger: BengalLogger) -> None:
        """Emit INFO-level summary log."""
        logger.info(
            "incremental_decision",
            pages_to_build=len(self.pages_to_build),
            pages_skipped=self.pages_skipped_count,
            fingerprint_changes=self.fingerprint_changes,
            asset_changes=self.asset_changes if self.asset_changes else None,
        )

    def log_details(self, logger: BengalLogger) -> None:
        """Emit DEBUG-level per-page breakdown."""
        for page_path, reason in self.rebuild_reasons.items():
            logger.debug(
                "rebuild_reason",
                page=page_path,
                reason=reason.code.value,
                details=reason.details if reason.details else None,
            )

    def get_reason_summary(self) -> dict[str, int]:
        """Get count of pages by rebuild reason code."""
        summary: dict[str, int] = {}
        for reason in self.rebuild_reasons.values():
            key = reason.code.value
            summary[key] = summary.get(key, 0) + 1
        return summary


@dataclass
class ConfigCheckResult:
    """
    Result of configuration check phase.

    Determines whether incremental builds are still valid after
    checking for configuration changes.

    Attributes:
        incremental: Whether incremental build should proceed (False if config changed)
        config_changed: Whether configuration file was modified

    """

    incremental: bool
    config_changed: bool

    def __iter__(self):
        """Allow tuple unpacking."""
        yield self.incremental
        yield self.config_changed


@dataclass
class FilterResult:
    """
    Result of incremental filtering phase.

    Contains the work items and change information determined during
    Phase 5: Incremental Filtering.

    Attributes:
        pages_to_build: Pages that need rendering (changed or dependent)
        assets_to_process: Assets that need processing
        affected_tags: Tags that have changed (triggers taxonomy rebuild)
        changed_page_paths: Source paths of changed pages
        affected_sections: Sections with changes (None if all sections affected)

    """

    pages_to_build: list[PageLike]
    assets_to_process: list[Asset]
    affected_tags: set[str]
    changed_page_paths: set[Path]
    affected_sections: set[str] | None

    def __iter__(self):
        """Allow tuple unpacking."""
        yield self.pages_to_build
        yield self.assets_to_process
        yield self.affected_tags
        yield self.changed_page_paths
        yield self.affected_sections


@dataclass
class ChangeSummary:
    """
    Summary of changes detected during incremental build.

    Used for verbose logging and debugging. Contains lists of paths
    that changed, organized by change type.

    Attributes:
        modified_content: Source paths of modified content files
        modified_assets: Paths of modified asset files
        modified_templates: Paths of modified template files
        taxonomy_changes: Tag slugs that have taxonomy changes
        extra_changes: Additional dynamic change types (e.g., "Cascade changes", "Navigation changes")

    """

    modified_content: list[Path] = field(default_factory=list)
    modified_assets: list[Path] = field(default_factory=list)
    modified_templates: list[Path] = field(default_factory=list)
    taxonomy_changes: list[str] = field(default_factory=list)
    extra_changes: dict[str, list[Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, list[Any]]:
        """
        Convert to dict format.

        Returns dict with string keys matching the original format.
        """
        result: dict[str, list[Any]] = {}
        if self.modified_content:
            result["Modified content"] = self.modified_content
        if self.modified_assets:
            result["Modified assets"] = self.modified_assets
        if self.modified_templates:
            result["Modified templates"] = self.modified_templates
        if self.taxonomy_changes:
            result["Taxonomy changes"] = self.taxonomy_changes
        # Merge extra_changes
        result.update(self.extra_changes)
        return result

    def items(self) -> ItemsView[str, list[Any]]:
        """Allow dict-like iteration."""
        return self.to_dict().items()

    def get(self, key: str, default: list[Any] | None = None) -> list[Any]:
        """Allow dict-like get()."""
        result = self.to_dict().get(key, default)
        return result if result is not None else []

    def __getitem__(self, key: str) -> list[Any]:
        """Allow dict-like indexing."""
        result = self.to_dict()
        if key not in result:
            # Return empty list for missing keys to match original dict behavior
            return []
        return result[key]

    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator."""
        return key in self.to_dict()
