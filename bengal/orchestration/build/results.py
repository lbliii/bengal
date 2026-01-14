"""
Result dataclasses for build orchestration phases.

Provides typed dataclasses for better type safety, readability, and IDE support.

All dataclasses support convenient access patterns:
- Tuple unpacking via __iter__() methods
- Dict-like access for ChangeSummary (to_dict(), items(), get(), __getitem__())

See Also:
- plan/active/rfc-dataclass-improvements.md - Design rationale
- plan/rfc-incremental-build-observability.md - Incremental decision tracking

"""

from __future__ import annotations

from collections.abc import ItemsView
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.utils.observability.logger import Logger


class RebuildReasonCode(Enum):
    """
    Why a page is being rebuilt.

    Enables exhaustive handling and better IDE support for understanding
    incremental build decisions.
    """

    CONTENT_CHANGED = "content_changed"
    TEMPLATE_CHANGED = "template_changed"
    ASSET_FINGERPRINT_CHANGED = "asset_fingerprint_changed"
    CASCADE_DEPENDENCY = "cascade_dependency"
    NAV_CHANGED = "nav_changed"
    CROSS_VERSION_DEPENDENCY = "cross_version_dependency"
    ADJACENT_NAV_CHANGED = "adjacent_nav_changed"
    FORCED = "forced"
    FULL_REBUILD = "full_rebuild"
    OUTPUT_MISSING = "output_missing"


class SkipReasonCode(Enum):
    """Why a page was skipped (not rebuilt)."""

    CACHE_HIT = "cache_hit"
    NO_CHANGES = "no_changes"
    SECTION_FILTERED = "section_filtered"


@dataclass
class RebuildReason:
    """
    Tracks why a page is being rebuilt.

    Note: page_path is the dict key in IncrementalDecision.rebuild_reasons,
    not stored here to avoid redundancy.
    """

    code: RebuildReasonCode
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.code.value} ({detail_str})"
        return self.code.value


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

    pages_to_build: list[Page]
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
            self.rebuild_reasons[page_path] = RebuildReason(
                code=code, details=details or {}
            )

    def log_summary(self, logger: Logger) -> None:
        """Emit INFO-level summary log."""
        logger.info(
            "incremental_decision",
            pages_to_build=len(self.pages_to_build),
            pages_skipped=self.pages_skipped_count,
            fingerprint_changes=self.fingerprint_changes,
            asset_changes=self.asset_changes if self.asset_changes else None,
        )

    def log_details(self, logger: Logger) -> None:
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

    def __iter__(self) -> tuple[bool, bool]:
        """Allow tuple unpacking."""
        return (self.incremental, self.config_changed)


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

    pages_to_build: list[Page]
    assets_to_process: list[Asset]
    affected_tags: set[str]
    changed_page_paths: set[Path]
    affected_sections: set[str] | None

    def __iter__(
        self,
    ) -> tuple[list[Page], list[Asset], set[str], set[Path], set[str] | None]:
        """Allow tuple unpacking."""
        return (
            self.pages_to_build,
            self.assets_to_process,
            self.affected_tags,
            self.changed_page_paths,
            self.affected_sections,
        )


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
