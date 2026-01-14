"""Incremental filter decision engine.

Consolidates the decision logic from phase_incremental_filter() into
a single testable class with explicit ordering and observability.

Uses Python 3.14 typing features (Self) and optimized dataclass patterns (slots).

Key Concepts:
- Single Responsibility: One class for incremental filter decisions
- Protocol-Based: Composable components (OutputChecker, ChangeDetector integration)
- Testable: Core logic testable without Site/Orchestrator
- Observable: Consolidates existing IncrementalDecision with structured decision log
- Additive: Gradual migration, not big-bang rewrite

Related Modules:
- bengal.orchestration.incremental.change_detector: ChangeDetector integration
- bengal.orchestration.build.results: IncrementalDecision, RebuildReasonCode
- bengal.orchestration.build.initialization: phase_incremental_filter wrapper

See Also:
- plan/rfc-rebuild-decision-hardening.md: RFC for this module

"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, Self

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.orchestration.incremental.change_detector import ChangeDetector
    from bengal.orchestration.build.results import IncrementalDecision


class FullRebuildTrigger(Enum):
    """Why a full rebuild was triggered.

    Each trigger is a distinct code path that can force full rebuild.
    Enables exhaustive testing and clear diagnostics.
    """

    INCREMENTAL_DISABLED = "incremental_disabled"
    OUTPUT_DIR_EMPTY = "output_dir_empty"
    OUTPUT_ASSETS_MISSING = "output_assets_missing"
    AUTODOC_OUTPUT_MISSING = "autodoc_output_missing"
    FINGERPRINT_CASCADE = "fingerprint_cascade"


class FilterDecisionType(Enum):
    """Type of filter decision."""

    FULL = "full"
    INCREMENTAL = "incremental"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class OutputPresenceResult:
    """Result of checking if build output exists."""

    is_present: bool
    reason: str | None = None
    checked_paths: tuple[Path, ...] = ()

    @classmethod
    def present(cls) -> Self:
        """Create a result indicating output is present."""
        return cls(is_present=True)

    @classmethod
    def missing(cls, reason: str, checked: list[Path]) -> Self:
        """Create a result indicating output is missing."""
        return cls(is_present=False, reason=reason, checked_paths=tuple(checked))


class OutputChecker(Protocol):
    """Contract for checking if build output exists."""

    def check(self, output_dir: Path) -> OutputPresenceResult:
        """Check if build output exists in the given directory."""
        ...


class DefaultOutputChecker:
    """Default implementation - checks for non-empty output dir and assets.

    Note: Does NOT check for root index.html specifically since not all
    sites have a home page. Instead, checks if output_dir has any content.
    """

    MIN_ASSET_FILES = 3

    def check(self, output_dir: Path) -> OutputPresenceResult:
        """Check if build output exists."""
        checked_paths = [output_dir]

        if not output_dir.exists():
            return OutputPresenceResult.missing("output_dir_not_exists", checked_paths)

        if not any(output_dir.iterdir()):
            return OutputPresenceResult.missing("output_dir_empty", checked_paths)

        assets_dir = output_dir / "assets"
        checked_paths.append(assets_dir)

        if not assets_dir.exists():
            return OutputPresenceResult.missing("assets_dir_not_exists", checked_paths)

        # Generator for memory efficiency in large directories
        asset_count = sum(1 for _ in assets_dir.iterdir())
        if asset_count < self.MIN_ASSET_FILES:
            return OutputPresenceResult.missing(
                f"assets_insufficient ({asset_count}/{self.MIN_ASSET_FILES})",
                checked_paths,
            )

        return OutputPresenceResult.present()


@dataclass(slots=True)
class FilterDecisionLog:
    """Complete audit trail of filter decision checks.

    Tracks every decision point in the filtering pipeline for
    observability and debugging.

    RFC: rfc-incremental-build-observability
    Added layer-specific trace fields for enhanced debugging.
    """

    # Mode checks
    incremental_enabled: bool = True

    # Output presence checks
    output_present: bool = True
    output_assets_count: int = 0
    output_presence_reason: str | None = None

    # Change detection
    pages_with_changes: int = 0
    assets_with_changes: int = 0
    pages_skipped: int = 0

    # Fingerprint cascade
    fingerprint_cascade_triggered: bool = False
    fingerprint_assets_changed: list[str] = field(default_factory=list)

    # Special checks
    autodoc_output_missing: bool = False
    special_pages_missing: bool = False
    taxonomy_regen_needed: bool = False

    # Final decision
    decision_type: FilterDecisionType = FilterDecisionType.INCREMENTAL
    full_rebuild_trigger: FullRebuildTrigger | None = None

    # ==========================================================================
    # Layer Trace Fields (RFC: rfc-incremental-build-observability)
    # ==========================================================================

    # Layer 1: Data files
    data_files_checked: int = 0
    data_files_changed: int = 0
    data_file_fingerprints_available: bool = True
    data_file_fallback_used: bool = False

    # Layer 2: autodoc
    autodoc_metadata_available: bool = True
    autodoc_fingerprint_fallback_used: bool = False
    autodoc_sources_total: int = 0
    autodoc_sources_stale: int = 0
    autodoc_stale_method: str = ""  # "metadata" | "fingerprint" | "all_stale"

    # Layer 3: Section optimization
    sections_total: int = 0
    sections_marked_changed: list[str] = field(default_factory=list)
    section_change_reasons: dict[str, str] = field(default_factory=dict)

    # Layer 4: Page filtering
    pages_in_changed_sections: int = 0
    pages_filtered_by_section: int = 0

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "incremental_enabled": self.incremental_enabled,
            "output_present": self.output_present,
            "output_assets_count": self.output_assets_count,
            "pages_with_changes": self.pages_with_changes,
            "assets_with_changes": self.assets_with_changes,
            "pages_skipped": self.pages_skipped,
            "fingerprint_cascade_triggered": self.fingerprint_cascade_triggered,
            "fingerprint_assets_changed": self.fingerprint_assets_changed,
            "autodoc_output_missing": self.autodoc_output_missing,
            "special_pages_missing": self.special_pages_missing,
            "taxonomy_regen_needed": self.taxonomy_regen_needed,
            "decision_type": self.decision_type.value,
            "full_rebuild_trigger": (
                self.full_rebuild_trigger.value if self.full_rebuild_trigger else None
            ),
            # Layer trace fields
            "layer_trace": {
                "data_files": {
                    "checked": self.data_files_checked,
                    "changed": self.data_files_changed,
                    "fingerprints_available": self.data_file_fingerprints_available,
                    "fallback_used": self.data_file_fallback_used,
                },
                "autodoc": {
                    "sources_total": self.autodoc_sources_total,
                    "sources_stale": self.autodoc_sources_stale,
                    "metadata_available": self.autodoc_metadata_available,
                    "fingerprint_fallback_used": self.autodoc_fingerprint_fallback_used,
                    "stale_method": self.autodoc_stale_method or None,
                },
                "sections": {
                    "total": self.sections_total,
                    "changed": self.sections_marked_changed,
                    "change_reasons": self.section_change_reasons or None,
                },
                "page_filtering": {
                    "in_changed_sections": self.pages_in_changed_sections,
                    "filtered_out": self.pages_filtered_by_section,
                },
            },
        }

    def to_trace_output(self) -> str:
        """Generate human-readable layer trace for --explain.

        RFC: rfc-incremental-build-observability

        Returns:
            Multi-line string with formatted decision trace
        """
        lines = [
            "",
            "═══════════════════════════════════════════════════════════════",
            "                    DECISION TRACE                              ",
            "═══════════════════════════════════════════════════════════════",
            "",
            f"Decision: {self.decision_type.name}",
        ]

        if self.full_rebuild_trigger:
            lines.append(f"  Trigger: {self.full_rebuild_trigger.value}")

        lines.extend(
            [
                "",
                "───────────────────────────────────────────────────────────────",
                "Layer 1: Data Files",
                "───────────────────────────────────────────────────────────────",
                f"  Checked:     {self.data_files_checked}",
                f"  Changed:     {self.data_files_changed}",
                f"  Fingerprints available: {'✓' if self.data_file_fingerprints_available else '✗'}",
            ]
        )
        if self.data_file_fallback_used:
            lines.append("  ⚠ Fallback used (fingerprints unavailable)")

        lines.extend(
            [
                "",
                "───────────────────────────────────────────────────────────────",
                "Layer 2: Autodoc",
                "───────────────────────────────────────────────────────────────",
                f"  Sources tracked: {self.autodoc_sources_total}",
                f"  Sources stale:   {self.autodoc_sources_stale}",
                f"  Metadata available: {'✓' if self.autodoc_metadata_available else '✗'}",
            ]
        )
        if self.autodoc_fingerprint_fallback_used:
            lines.append("  ⚠ Using fingerprint fallback (metadata unavailable)")
        if self.autodoc_stale_method:
            lines.append(f"  Detection method: {self.autodoc_stale_method}")

        lines.extend(
            [
                "",
                "───────────────────────────────────────────────────────────────",
                "Layer 3: Section Optimization",
                "───────────────────────────────────────────────────────────────",
                f"  Sections total:   {self.sections_total}",
                f"  Sections changed: {len(self.sections_marked_changed)}",
            ]
        )
        if self.sections_marked_changed:
            for section in self.sections_marked_changed[:5]:
                reason = self.section_change_reasons.get(section, "content_changed")
                lines.append(f"    • {section} ({reason})")
            if len(self.sections_marked_changed) > 5:
                lines.append(
                    f"    ... and {len(self.sections_marked_changed) - 5} more"
                )

        lines.extend(
            [
                "",
                "───────────────────────────────────────────────────────────────",
                "Layer 4: Page Filtering",
                "───────────────────────────────────────────────────────────────",
                f"  In changed sections: {self.pages_in_changed_sections}",
                f"  Filtered out:        {self.pages_filtered_by_section}",
                "",
                "═══════════════════════════════════════════════════════════════",
            ]
        )

        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class FilterDecision:
    """Final filter decision with full audit trail.

    Immutable result of the IncrementalFilterEngine.decide() method.
    Contains all information needed to proceed with the build.
    """

    pages_to_build: list[Page]
    assets_to_process: list[Asset]
    affected_tags: set[str]
    affected_sections: set[str]
    changed_page_paths: set[Path]
    decision_log: FilterDecisionLog

    @property
    def decision_type(self) -> FilterDecisionType:
        """Get the decision type (full/incremental/skip)."""
        return self.decision_log.decision_type

    @property
    def is_full_rebuild(self) -> bool:
        """Check if this is a full rebuild decision."""
        return self.decision_log.decision_type == FilterDecisionType.FULL

    @property
    def is_skip(self) -> bool:
        """Check if this is a skip decision (no changes)."""
        return self.decision_log.decision_type == FilterDecisionType.SKIP

    @property
    def full_rebuild_reason(self) -> str | None:
        """Get the human-readable reason for full rebuild."""
        if self.decision_log.full_rebuild_trigger:
            return self.decision_log.full_rebuild_trigger.value
        return None

    def to_legacy_decision(self) -> IncrementalDecision:
        """Convert to legacy format for backward compatibility.

        Bridges to existing IncrementalDecision for Phase 2 compatibility
        with orchestrator.stats and --explain CLI.
        """
        from bengal.orchestration.build.results import (
            IncrementalDecision,
            RebuildReasonCode,
        )

        decision = IncrementalDecision(
            pages_to_build=self.pages_to_build,
            pages_skipped_count=self.decision_log.pages_skipped,
        )

        # Reconstruct reasons for --explain
        if self.is_full_rebuild:
            trigger_map = {
                FullRebuildTrigger.INCREMENTAL_DISABLED: RebuildReasonCode.FULL_REBUILD,
                FullRebuildTrigger.OUTPUT_DIR_EMPTY: RebuildReasonCode.OUTPUT_MISSING,
                FullRebuildTrigger.OUTPUT_ASSETS_MISSING: RebuildReasonCode.OUTPUT_MISSING,
                FullRebuildTrigger.AUTODOC_OUTPUT_MISSING: RebuildReasonCode.OUTPUT_MISSING,
                FullRebuildTrigger.FINGERPRINT_CASCADE: RebuildReasonCode.ASSET_FINGERPRINT_CHANGED,
            }
            reason_code = trigger_map.get(
                self.decision_log.full_rebuild_trigger, RebuildReasonCode.FULL_REBUILD
            )
            for page in self.pages_to_build:
                decision.add_rebuild_reason(str(page.source_path), reason_code)

        # Track fingerprint changes
        if self.decision_log.fingerprint_cascade_triggered:
            decision.fingerprint_changes = True
            decision.asset_changes = self.decision_log.fingerprint_assets_changed

        return decision


class IncrementalFilterEngine:
    """Single source of truth for incremental filter decisions.

    Consolidates all filter logic from phase_incremental_filter() into
    one testable class with explicit ordering and observability.

    Note: This is distinct from RebuildDecisionEngine (block-level).

    Decision Pipeline (explicit ordering):
        1. Check incremental mode → may return full
        2. Detect changes → baseline incremental list + change_summary
        3. Check fingerprint cascade → may expand pages
        4. Check output presence → may force full (html/assets)
        5. Check autodoc output → may force full
        6. Check taxonomy and special pages → blocks skip when graph/search missing
        7. Check skip condition → may return skip

    Example:
        >>> engine = IncrementalFilterEngine(
        ...     cache=cache,
        ...     output_dir=site.output_dir,
        ...     change_detector=incremental.change_detector,
        ... )
        >>> decision = engine.decide(
        ...     pages=site.pages,
        ...     assets=site.assets,
        ...     incremental=True,
        ... )
        >>>
        >>> if decision.is_skip:
        ...     return None  # Early exit
        >>>
        >>> if decision.is_full_rebuild:
        ...     logger.info("full_rebuild", reason=decision.full_rebuild_reason)

    """

    def __init__(
        self,
        cache: BuildCache,
        output_dir: Path,
        change_detector: ChangeDetector | None = None,
        output_checker: OutputChecker | None = None,
        autodoc_checker: "AutodocOutputChecker | None" = None,
        special_pages_checker: "SpecialPagesChecker | None" = None,
    ) -> None:
        """Initialize the filter engine.

        Args:
            cache: BuildCache for change detection
            output_dir: Path to output directory
            change_detector: ChangeDetector instance (lazy if None)
            output_checker: Custom output checker (DefaultOutputChecker if None)
            autodoc_checker: Custom autodoc checker (DefaultAutodocChecker if None)
            special_pages_checker: Custom special pages checker (None = skip check)
        """
        self.cache = cache
        self.output_dir = output_dir
        self.change_detector = change_detector
        self.output_checker = output_checker or DefaultOutputChecker()
        self.autodoc_checker = autodoc_checker
        self.special_pages_checker = special_pages_checker

    def decide(
        self,
        pages: list[Page],
        assets: list[Asset],
        incremental: bool = True,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
        needs_taxonomy_regen: bool = False,
    ) -> FilterDecision:
        """Determine what needs to be built.

        Decision pipeline (explicit ordering):
        1. If not incremental → full rebuild
        2. Detect changes → baseline incremental list
        3. Check fingerprint cascade → may expand pages
        4. Check output presence → may force full
        5. Check autodoc output → may force full
        6. Check special pages → may prevent skip
        7. Check skip condition → may return skip

        All checks are logged to decision_log for observability.

        Args:
            pages: All pages in the site
            assets: All assets in the site
            incremental: Whether incremental mode is enabled
            forced_changed_sources: Paths to treat as changed (file watcher)
            nav_changed_sources: Paths with navigation-affecting changes
            needs_taxonomy_regen: Whether taxonomy pages need regeneration

        Returns:
            FilterDecision with pages/assets to build and decision_log
        """
        log = FilterDecisionLog()
        all_pages = list(pages)
        all_assets = list(assets)

        # Step 1: Check incremental mode
        log.incremental_enabled = incremental
        if not incremental:
            log.decision_type = FilterDecisionType.FULL
            log.full_rebuild_trigger = FullRebuildTrigger.INCREMENTAL_DISABLED
            return self._full_rebuild(all_pages, all_assets, log)

        # RFC: rfc-incremental-build-observability - Collect layer trace info

        # Layer 1: Data file stats (collected from cache)
        self._collect_data_file_trace(log)

        # Layer 2: Autodoc stats (collected from cache)
        self._collect_autodoc_trace(log)

        # Step 2: Detect changes (Layer 3 & 4 info collected here)
        (
            pages_to_build,
            assets_to_process,
            affected_tags,
            affected_sections,
            changed_paths,
        ) = self._detect_changes(
            all_pages, all_assets, forced_changed_sources, nav_changed_sources, log
        )
        log.pages_with_changes = len(pages_to_build)
        log.assets_with_changes = len(assets_to_process)
        log.pages_skipped = len(all_pages) - len(pages_to_build)

        # Step 3: Fingerprint cascade
        cascade_assets = [
            a
            for a in assets_to_process
            if a.source_path.suffix.lower() in {".css", ".js"}
        ]
        if cascade_assets:
            log.fingerprint_cascade_triggered = True
            log.fingerprint_assets_changed = [a.source_path.name for a in cascade_assets]
            if not pages_to_build:
                # Assets changed but no content changes - force all pages to rebuild
                pages_to_build = all_pages
                log.pages_skipped = 0

        # Step 4: Check output presence
        output_result = self.output_checker.check(self.output_dir)
        log.output_present = output_result.is_present
        log.output_presence_reason = output_result.reason
        if self.output_dir.exists():
            assets_dir = self.output_dir / "assets"
            if assets_dir.exists():
                log.output_assets_count = sum(1 for _ in assets_dir.iterdir())

        if not output_result.is_present and all_pages:
            log.decision_type = FilterDecisionType.FULL
            log.full_rebuild_trigger = FullRebuildTrigger.OUTPUT_DIR_EMPTY
            return self._full_rebuild(all_pages, all_assets, log)

        # Step 5: Check autodoc output
        if self.autodoc_checker:
            autodoc_missing = self.autodoc_checker.check(self.output_dir)
            log.autodoc_output_missing = autodoc_missing
            if autodoc_missing and all_pages:
                log.decision_type = FilterDecisionType.FULL
                log.full_rebuild_trigger = FullRebuildTrigger.AUTODOC_OUTPUT_MISSING
                return self._full_rebuild(all_pages, all_assets, log)

        # Step 6: Check special pages and taxonomy regen
        log.taxonomy_regen_needed = needs_taxonomy_regen
        if self.special_pages_checker:
            log.special_pages_missing = self.special_pages_checker.check(self.output_dir)

        # Step 7: Check skip condition
        can_skip = (
            not pages_to_build
            and not assets_to_process
            and not log.taxonomy_regen_needed
            and not log.special_pages_missing
        )
        if can_skip:
            log.decision_type = FilterDecisionType.SKIP
            return FilterDecision(
                pages_to_build=[],
                assets_to_process=[],
                affected_tags=set(),
                affected_sections=set(),
                changed_page_paths=set(),
                decision_log=log,
            )

        # Incremental build
        log.decision_type = FilterDecisionType.INCREMENTAL
        return FilterDecision(
            pages_to_build=pages_to_build,
            assets_to_process=assets_to_process,
            affected_tags=affected_tags,
            affected_sections=affected_sections,
            changed_page_paths=changed_paths,
            decision_log=log,
        )

    def _collect_data_file_trace(self, log: FilterDecisionLog) -> None:
        """Collect Layer 1 (Data Files) trace information.

        RFC: rfc-incremental-build-observability
        """
        # Check if cache has data file fingerprints
        try:
            fingerprints = getattr(self.cache, "file_fingerprints", None)
            if fingerprints is not None and isinstance(fingerprints, dict):
                # Count data files in fingerprints (rough estimate)
                data_file_count = sum(1 for p in fingerprints.keys() if "data/" in p)
                log.data_files_checked = data_file_count
                log.data_file_fingerprints_available = True
            else:
                log.data_file_fingerprints_available = False
                log.data_file_fallback_used = True
        except (TypeError, AttributeError):
            log.data_file_fingerprints_available = False
            log.data_file_fallback_used = True

    def _collect_autodoc_trace(self, log: FilterDecisionLog) -> None:
        """Collect Layer 2 (Autodoc) trace information.

        RFC: rfc-incremental-build-observability
        """
        # Check autodoc tracking state
        try:
            deps = getattr(self.cache, "autodoc_dependencies", None)
            if deps is not None and isinstance(deps, dict):
                log.autodoc_sources_total = len(deps)

                # Check metadata availability
                metadata = getattr(self.cache, "autodoc_source_metadata", None)
                if metadata is not None and isinstance(metadata, dict):
                    metadata_count = len(metadata)
                    log.autodoc_metadata_available = metadata_count > 0

                    # If we have dependencies but no metadata, fallback is used
                    if log.autodoc_sources_total > 0 and metadata_count == 0:
                        log.autodoc_fingerprint_fallback_used = True
                        # Determine stale method
                        fingerprints = getattr(self.cache, "file_fingerprints", None)
                        if fingerprints and isinstance(fingerprints, dict) and fingerprints:
                            log.autodoc_stale_method = "fingerprint"
                        else:
                            log.autodoc_stale_method = "all_stale"
                    elif metadata_count > 0:
                        log.autodoc_stale_method = "metadata"
                else:
                    log.autodoc_metadata_available = False
                    if log.autodoc_sources_total > 0:
                        log.autodoc_fingerprint_fallback_used = True
                        log.autodoc_stale_method = "all_stale"
        except (TypeError, AttributeError):
            # Cache doesn't support autodoc tracking
            pass

    def _detect_changes(
        self,
        all_pages: list[Page],
        all_assets: list[Asset],
        forced_changed: set[Path] | None,
        nav_changed: set[Path] | None,
        log: FilterDecisionLog | None = None,
    ) -> tuple[list[Page], list[Asset], set[str], set[str], set[Path]]:
        """Detect which pages/assets have changed.

        Delegates to ChangeDetector if available, otherwise uses
        simple cache-based detection.

        Args:
            all_pages: All pages in the site
            all_assets: All assets in the site
            forced_changed: Paths to treat as changed (file watcher)
            nav_changed: Paths with navigation-affecting changes
            log: FilterDecisionLog to populate with trace info

        Returns:
            Tuple of (pages_to_build, assets_to_process, affected_tags,
                     affected_sections, changed_paths)
        """
        # Delegate to ChangeDetector if available
        if self.change_detector:
            change_set = self.change_detector.detect_changes(
                phase="early",
                forced_changed_sources=forced_changed,
                nav_changed_sources=nav_changed,
            )

            # Compute affected tags and sections from pages
            affected_tags = self._compute_affected_tags(change_set.pages_to_build)
            affected_sections = self._compute_affected_sections(change_set.pages_to_build)

            # RFC: rfc-incremental-build-observability - Layer 3 & 4 trace
            if log is not None:
                self._collect_section_trace(log, all_pages, affected_sections)

            return (
                change_set.pages_to_build,
                change_set.assets_to_process,
                affected_tags,
                affected_sections,
                {p.source_path for p in change_set.pages_to_build},
            )

        # Fallback: simple cache-based detection
        return self._detect_changes_fallback(
            all_pages, all_assets, forced_changed, log
        )

    def _collect_section_trace(
        self,
        log: FilterDecisionLog,
        all_pages: list[Page],
        affected_sections: set[str],
    ) -> None:
        """Collect Layer 3 & 4 (Section/Page Filtering) trace information.

        RFC: rfc-incremental-build-observability
        """
        from bengal.core.section.utils import resolve_page_section_path

        # Layer 3: Section optimization stats
        unique_sections: set[str] = set()
        for page in all_pages:
            section_path = resolve_page_section_path(page)
            if section_path:
                unique_sections.add(section_path)

        log.sections_total = len(unique_sections)
        log.sections_marked_changed = list(affected_sections)

        # Infer change reasons based on affected sections
        for section in affected_sections:
            log.section_change_reasons[section] = "content_changed"

        # Layer 4: Page filtering stats
        pages_in_sections = 0
        for page in all_pages:
            section_path = resolve_page_section_path(page)
            if section_path and section_path in affected_sections:
                pages_in_sections += 1

        log.pages_in_changed_sections = pages_in_sections
        log.pages_filtered_by_section = len(all_pages) - pages_in_sections

    def _detect_changes_fallback(
        self,
        all_pages: list[Page],
        all_assets: list[Asset],
        forced_changed: set[Path] | None,
        log: FilterDecisionLog | None = None,
    ) -> tuple[list[Page], list[Asset], set[str], set[str], set[Path]]:
        """Fallback change detection using cache.is_changed()."""
        pages_to_build: list[Page] = []
        assets_to_process: list[Asset] = []
        affected_tags: set[str] = set()
        affected_sections: set[str] = set()
        changed_paths: set[Path] = set()
        forced = forced_changed or set()

        for page in all_pages:
            if page.source_path in forced or self.cache.is_changed(page.source_path):
                pages_to_build.append(page)
                changed_paths.add(page.source_path)

        for asset in all_assets:
            if asset.source_path in forced or self.cache.is_changed(asset.source_path):
                assets_to_process.append(asset)

        # Compute affected tags and sections
        affected_tags = self._compute_affected_tags(pages_to_build)
        affected_sections = self._compute_affected_sections(pages_to_build)

        # RFC: rfc-incremental-build-observability - Layer 3 & 4 trace
        if log is not None:
            self._collect_section_trace(log, all_pages, affected_sections)

        return (
            pages_to_build,
            assets_to_process,
            affected_tags,
            affected_sections,
            changed_paths,
        )

    def _compute_affected_tags(self, pages: list[Page]) -> set[str]:
        """Compute affected tags from changed pages."""
        affected: set[str] = set()
        for page in pages:
            if page.metadata.get("_generated"):
                continue
            if page.tags:
                for tag in page.tags:
                    if tag is not None:
                        affected.add(str(tag).lower().replace(" ", "-"))
        return affected

    def _compute_affected_sections(self, pages: list[Page]) -> set[str]:
        """Compute affected sections from changed pages."""
        from bengal.core.section.utils import resolve_page_section_path

        affected: set[str] = set()
        for page in pages:
            if page.metadata.get("_generated"):
                continue
            section_path = resolve_page_section_path(page)
            if section_path:
                affected.add(section_path)
        return affected

    def _full_rebuild(
        self,
        all_pages: list[Page],
        all_assets: list[Asset],
        log: FilterDecisionLog,
    ) -> FilterDecision:
        """Return a full rebuild decision."""
        log.pages_skipped = 0
        return FilterDecision(
            pages_to_build=all_pages,
            assets_to_process=all_assets,
            affected_tags=set(),
            affected_sections=set(),
            changed_page_paths={p.source_path for p in all_pages},
            decision_log=log,
        )


class AutodocOutputChecker(Protocol):
    """Contract for checking if autodoc output exists."""

    def check(self, output_dir: Path) -> bool:
        """Check if autodoc output is missing.

        Returns:
            True if autodoc output is missing and needs regeneration
        """
        ...


class SpecialPagesChecker(Protocol):
    """Contract for checking if special pages (graph, search) exist."""

    def check(self, output_dir: Path) -> bool:
        """Check if special pages are missing.

        Returns:
            True if any enabled special page is missing from output
        """
        ...


# =============================================================================
# Adapter classes for BuildOrchestrator integration
# =============================================================================


class OrchestratorAutodocChecker:
    """Autodoc checker that delegates to initialization.py helper.

    Used to adapt the existing _check_autodoc_output_missing() function
    to the AutodocOutputChecker protocol.
    """

    def __init__(self, orchestrator: "BuildOrchestrator", cache: "BuildCache") -> None:
        """Initialize with orchestrator and cache."""
        self._orchestrator = orchestrator
        self._cache = cache

    def check(self, output_dir: Path) -> bool:
        """Check if autodoc output is missing."""
        from bengal.orchestration.build.initialization import _check_autodoc_output_missing

        return _check_autodoc_output_missing(self._orchestrator, self._cache)


class OrchestratorSpecialPagesChecker:
    """Special pages checker that delegates to initialization.py helper.

    Used to adapt the existing _check_special_pages_missing() function
    to the SpecialPagesChecker protocol.
    """

    def __init__(self, orchestrator: "BuildOrchestrator") -> None:
        """Initialize with orchestrator."""
        self._orchestrator = orchestrator

    def check(self, output_dir: Path) -> bool:
        """Check if special pages are missing."""
        from bengal.orchestration.build.initialization import _check_special_pages_missing

        return _check_special_pages_missing(self._orchestrator)


if TYPE_CHECKING:
    from bengal.orchestration.build import BuildOrchestrator
