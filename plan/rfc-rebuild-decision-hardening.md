# RFC: Incremental Filter Consolidation

## Status: Approved
## Created: 2026-01-14
## Updated: 2026-01-14
## Origin: Debugging session for flaky incremental build tests

---

## Summary

**Problem**: The incremental rebuild decision logic in `phase_incremental_filter()` spans ~250 lines with 5+ decision points, mixing concerns (output presence, config changes, content detection, fingerprint cascade). This structure makes isolated testing difficult, debugging time-consuming, and future enhancements risky.

**Solution**: Extract rebuild decision logic into a dedicated `IncrementalFilterEngine` class with explicit contracts, protocol-based composition, and consolidated observability. Adopt a **Bridge Adapter** pattern to maintain backward compatibility with the existing `IncrementalDecision` infrastructure while enabling sub-second decision diagnostics via Python 3.14 optimized data structures.

**Priority**: High (incremental/warm builds are a core Bengal value proposition)

**Scope**: ~350 LOC refactor + ~150 LOC tests

---

## Strategic Context

### Why This Matters

**Reliable warm builds are a core Bengal value proposition.** Users expect:
- **Sub-second rebuilds** when editing content (leveraging Python 3.14 performance).
- **Predictable behavior** (same inputs → same rebuild decisions).
- **Clear diagnostics** when something forces a full rebuild via `--explain`.
- **Confidence** that incremental mode won't miss changes.

**Current state**: The incremental logic works but is fragile:
- Two bugs were found in one debugging session (both now fixed)
- 60+ minutes to diagnose each issue
- No unit tests for decision logic in isolation
- Adding new decision criteria (e.g., data file changes) is risky

**Investment thesis**: Hardening this subsystem now prevents:
- User-facing bugs that erode trust in incremental mode
- Slow debugging cycles when issues arise
- Hesitation to add new incremental optimizations

### Bugs Found & Fixed (Evidence of Fragility)

This RFC originated from a debugging session that uncovered two bugs. Both have been resolved, but the experience highlights the need for better structure:

| Bug | Status | Fix Location |
|-----|--------|--------------|
| `output_html_missing` assumed root index.html | ✅ Fixed | `initialization.py:688-692` - Now checks for empty dir, not index.html |
| Stale `_change_detector` reference | ✅ Fixed | `orchestrator.py:105-107` - Resets detector on cache reinit |

**Evidence of Bug 1 fix** (`initialization.py:688-692`):
```python
# Note: We don't check for root index.html specifically since not all sites
# have a home page. Instead, check if output_dir has any content at all.
output_html_missing = (
    not output_dir.exists() or len(list(output_dir.iterdir())) == 0
)
```

**Evidence of Bug 2 fix** (`orchestrator.py:105-107`):
```python
# Reset change detector so it picks up the new cache
# (fixes stale reference bug where detector kept old cache)
self._change_detector = None
```

### Current Observability

The codebase already has observability infrastructure for incremental decisions:

- `IncrementalDecision` dataclass tracks rebuild reasons per page
- `RebuildReasonCode` enum provides structured reason codes
- `_track_reasons_from_change_summary()` helper records change context
- Structured logging throughout `phase_incremental_filter()`

### Existing Rebuild Decision Infrastructure

Note: `bengal/orchestration/incremental/rebuild_decision.py` already exists and contains `RebuildDecisionEngine` for **block-level template decisions** (different scope):

```python
# EXISTING: Block-level rebuild decisions (template changes)
class RebuildDecisionEngine:
    """Makes smart rebuild decisions based on block-level changes."""
    def decide(self, template_name: str, template_path: Path) -> RebuildDecision:
        ...
```

This RFC proposes a **different component** for **incremental filter decisions** (full build vs. incremental vs. skip).

---

## Problem Statement

### Why Consolidation Still Has Value

Even with bugs fixed, `phase_incremental_filter()` has structural issues:

1. **Mixed concerns**: Output presence, config changes, change detection, fingerprint cascade, taxonomy regeneration, special pages - all in one function
2. **250+ lines**: Difficult to reason about as a unit
3. **Multiple exit paths**: 5+ ways to return (early exits for various conditions)
4. **Implicit ordering**: Decision checks must happen in specific order, not enforced by structure
5. **Testing requires full orchestrator**: Can't unit test decision logic in isolation

### Current Code Structure

```python
def phase_incremental_filter(...) -> FilterResult | None:
    # 1. Initialize (lines 571-581)
    pages_to_build = orchestrator.site.pages
    decision = IncrementalDecision(...)
    
    if incremental:
        # 2. Find changes (lines 585-598)
        pages_to_build, assets_to_process, change_summary = ...
        
        # 3. Fingerprint cascade (lines 600-631)
        if fingerprint_assets_changed:
            pages_to_build = list(orchestrator.site.pages)
        
        # 4. Track affected sections/tags (lines 634-651)
        for page in pages_to_build:
            ...
        
        # 5. Cache statistics (lines 653-676)
        orchestrator.stats.cache_hits = ...
        
        # 6. Check taxonomy regen needed (line 679)
        needs_taxonomy_regen = bool(cache.get_all_tags())
        
        # 7. Output presence check (lines 681-732)
        if output_html_missing or output_assets_missing or autodoc_output_missing:
            pages_to_build = list(orchestrator.site.pages)
        
        # 8. Skip check (lines 733-746)
        elif not pages_to_build and not assets_to_process:
            return None
        
        # 9. Special pages check (lines 747-753)
        elif special_pages_missing:
            ...
        
        # 10. Update decision tracker (lines 755-...)
        ...
    
    return FilterResult(...)
```

**Issues**:
- Each "check" can override previous decisions
- Order matters but isn't enforced
- Unit testing requires mocking entire `BuildOrchestrator`

---

## Proposed Solution: IncrementalFilterEngine

### Design Goals

1. **Single Responsibility**: One class for incremental filter decisions
2. **Protocol-Based**: Composable components (OutputChecker, ChangeDetector integration)
3. **Testable**: Core logic testable without Site/Orchestrator
4. **Observable**: Consolidates existing `IncrementalDecision` with structured decision log
5. **Additive**: Gradual migration, not big-bang rewrite

### Naming Rationale

- **NOT** `RebuildDecisionMaker` - avoids confusion with existing `RebuildDecisionEngine` (block-level)
- **`IncrementalFilterEngine`** - clearly scoped to incremental filtering phase
- **`FilterDecision`** - distinct from existing `RebuildDecision` (block-level)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  phase_incremental_filter()                  │
│  (thin wrapper - orchestrates engine + stats + logging)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   IncrementalFilterEngine                    │
│                                                              │
│  Inputs:                                                     │
│    - pages: list[Page]                                       │
│    - assets: list[Asset]                                     │
│    - cache: BuildCache                                       │
│    - output_dir: Path                                        │
│    - change_detector: ChangeDetector                         │
│                                                              │
│  Decision Pipeline (explicit ordering, parity with current flow): │
│    1. _check_incremental_mode() → may return full                 │
│    2. _detect_changes() → baseline incremental list + change_summary│
│    3. _check_fingerprint_cascade() → may expand pages             │
│    4. _check_output_presence() → may force full (html/assets)     │
│    5. _check_autodoc_output() → may force full                    │
│    6. _check_taxonomy_and_special_pages() → blocks skip when graph/search missing; allows postprocess-only regen │
│    7. _check_skip_condition() → may return skip                   │
│                                                              │
│  Output:                                                     │
│    FilterDecision (pages, assets, decision_log, stats)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      FilterDecision                          │
│                                                              │
│  - pages_to_build: list[Page]                               │
│  - assets_to_process: list[Asset]                           │
│  - affected_tags: set[str]                                  │
│  - affected_sections: set[str]                              │
│  - decision_log: FilterDecisionLog                          │
│  - decision_type: "full" | "incremental" | "skip"           │
│  - full_rebuild_reason: FullRebuildTrigger | None           │
└─────────────────────────────────────────────────────────────┘
```

### Parity Requirements (must retain current safeguards)

- Preserve all existing skip/full decision gates from `phase_incremental_filter()`:
  - Output/html/assets missing → force full rebuild when any content exists.
  - Autodoc output missing → force full rebuild.
  - Special pages (graph/search) missing → continue to postprocess, not skip.
  - Taxonomy regen flag prevents skip when tag pages need regeneration.
- Maintain per-page observability: keep rebuild/skip reasons and change_summary mapping (`IncrementalDecision`) available to `--explain` and logs; bridge or embed into `FilterDecisionLog`.
- Keep stats parity: update cache_hits/cache_misses/time_saved in the wrapper or engine.
- Config change trigger: either feed config_changed into the engine to emit `FullRebuildTrigger.CONFIG_CHANGED` or drop the trigger to avoid dead code.

### Relationship to Existing Components

```
                    ┌─────────────────────────────┐
                    │     BuildOrchestrator       │
                    └─────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
┌───────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│ IncrementalFilter │ │  ChangeDetector │ │ RebuildDecisionEngine│
│    Engine         │ │                 │ │   (block-level)      │
│  (THIS RFC)       │ │  (existing)     │ │   (existing)         │
└───────────────────┘ └─────────────────┘ └─────────────────────────┘
        │                     │                     │
        │                     │                     │
        ▼                     ▼                     ▼
   FilterDecision        ChangeSet           RebuildDecision
   (full/incr/skip)    (pages/assets)      (blocks/pages)
```

### Bridge Strategy: IncrementalDecision Parity

To ensure no loss of signal in `--explain`, `FilterDecision` will include a bridge method to populate the legacy `IncrementalDecision` object used by the orchestrator stats:

```python
def to_legacy_decision(self) -> IncrementalDecision:
    """Bridge to existing IncrementalDecision for backward compatibility."""
    from bengal.orchestration.build.results import IncrementalDecision, RebuildReasonCode
    
    decision = IncrementalDecision(
        pages_to_build=self.pages_to_build,
        pages_skipped_count=self.decision_log.pages_skipped,
    )
    # Map engine decision_log to legacy RebuildReasonCodes
    if self.is_full_rebuild:
        reason_map = {
            FullRebuildTrigger.OUTPUT_DIR_EMPTY: RebuildReasonCode.OUTPUT_MISSING,
            FullRebuildTrigger.CONFIG_CHANGED: RebuildReasonCode.FULL_REBUILD,
            # ...
        }
        for page in self.pages_to_build:
            decision.add_rebuild_reason(
                str(page.source_path), 
                reason_map.get(self.decision_log.full_rebuild_trigger, RebuildReasonCode.FULL_REBUILD)
            )
    return decision
```

### Implementation (Python 3.14)

**File**: `bengal/orchestration/incremental/filter_engine.py` (new file)

```python
"""Incremental filter decision engine.

Consolidates the decision logic from phase_incremental_filter() into
a single testable class with explicit ordering and observability.

Uses Python 3.14 typing features (Self) and optimized dataclass patterns (slots).
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
    CONFIG_CHANGED = "config_changed"
    AUTODOC_OUTPUT_MISSING = "autodoc_output_missing"


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
    checked_paths: list[Path] = field(default_factory=list)
    
    @classmethod
    def present(cls) -> Self:
        return cls(is_present=True)
    
    @classmethod
    def missing(cls, reason: str, checked: list[Path]) -> Self:
        return cls(is_present=False, reason=reason, checked_paths=checked)


class OutputChecker(Protocol):
    """Contract for checking if build output exists."""
    def check(self, output_dir: Path) -> OutputPresenceResult:
        ...


class DefaultOutputChecker:
    """Default implementation - checks for non-empty output dir and assets.
    
    Note: Does NOT check for root index.html specifically.
    """
    
    MIN_ASSET_FILES = 3
    
    def check(self, output_dir: Path) -> OutputPresenceResult:
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
    """Complete audit trail of filter decision checks."""
    incremental_enabled: bool = True
    output_present: bool = True
    output_assets_count: int = 0
    config_changed: bool = False
    
    pages_with_changes: int = 0
    assets_with_changes: int = 0
    pages_skipped: int = 0
    
    fingerprint_cascade_triggered: bool = False
    fingerprint_assets_changed: list[str] = field(default_factory=list)
    
    autodoc_output_missing: bool = False
    special_pages_missing: bool = False
    taxonomy_regen_needed: bool = False
    
    decision_type: FilterDecisionType = FilterDecisionType.INCREMENTAL
    full_rebuild_trigger: FullRebuildTrigger | None = None
    
    def to_dict(self) -> dict:
        return {
            "incremental_enabled": self.incremental_enabled,
            "output_present": self.output_present,
            "decision_type": self.decision_type.value,
            "full_rebuild_trigger": (
                self.full_rebuild_trigger.value if self.full_rebuild_trigger else None
            ),
        }


@dataclass(frozen=True, slots=True)
class FilterDecision:
    """Final filter decision with full audit trail."""
    pages_to_build: list[Page]
    assets_to_process: list[Asset]
    affected_tags: set[str]
    affected_sections: set[str]
    changed_page_paths: set[Path]
    decision_log: FilterDecisionLog
    
    @property
    def decision_type(self) -> FilterDecisionType:
        return self.decision_log.decision_type
    
    @property
    def is_full_rebuild(self) -> bool:
        return self.decision_log.decision_type == FilterDecisionType.FULL
    
    @property
    def is_skip(self) -> bool:
        return self.decision_log.decision_type == FilterDecisionType.SKIP
    
    @property
    def full_rebuild_reason(self) -> str | None:
        if self.decision_log.full_rebuild_trigger:
            return self.decision_log.full_rebuild_trigger.value
        return None

    def to_legacy_decision(self) -> IncrementalDecision:
        """Convert to legacy format for Phase 2 compatibility."""
        from bengal.orchestration.build.results import IncrementalDecision, RebuildReasonCode, RebuildReason
        
        decision = IncrementalDecision(
            pages_to_build=self.pages_to_build,
            pages_skipped_count=self.decision_log.pages_skipped,
        )
        
        # Reconstruct reasons for --explain
        if self.is_full_rebuild:
            trigger_map = {
                FullRebuildTrigger.INCREMENTAL_DISABLED: RebuildReasonCode.FULL_REBUILD,
                FullRebuildTrigger.OUTPUT_DIR_EMPTY: RebuildReasonCode.OUTPUT_MISSING,
                FullRebuildTrigger.CONFIG_CHANGED: RebuildReasonCode.FULL_REBUILD,
                FullRebuildTrigger.AUTODOC_OUTPUT_MISSING: RebuildReasonCode.OUTPUT_MISSING,
            }
            reason_code = trigger_map.get(self.decision_log.full_rebuild_trigger, RebuildReasonCode.FULL_REBUILD)
            for page in self.pages_to_build:
                decision.add_rebuild_reason(str(page.source_path), reason_code)
        
        return decision


class IncrementalFilterEngine:
    """
    Single source of truth for incremental filter decisions.
    
    Consolidates all filter logic from phase_incremental_filter() into
    one testable class with explicit ordering and observability.
    
    Note: This is distinct from RebuildDecisionEngine (block-level).
    
    Example:
        engine = IncrementalFilterEngine(
            cache=cache,
            output_dir=site.output_dir,
            change_detector=incremental.change_detector,
        )
        decision = engine.decide(
            pages=site.pages,
            assets=site.assets,
            incremental=True,
        )
        
        if decision.is_skip:
            return None  # Early exit
        
        if decision.is_full_rebuild:
            logger.info("full_rebuild", reason=decision.full_rebuild_reason)
    """
    
    def __init__(
        self,
        cache: BuildCache,
        output_dir: Path,
        change_detector: ChangeDetector | None = None,
        output_checker: OutputChecker | None = None,
    ):
        self.cache = cache
        self.output_dir = output_dir
        self.change_detector = change_detector
        self.output_checker = output_checker or DefaultOutputChecker()
    
    def decide(
        self,
        pages: list[Page],
        assets: list[Asset],
        incremental: bool = True,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
    ) -> FilterDecision:
        """
        Determine what needs to be built.
        
        Decision pipeline (explicit ordering):
        1. If not incremental → full rebuild
        2. Detect changes → baseline incremental list
        3. Check fingerprint cascade → may expand pages
        4. Check output presence → may force full
        5. Check autodoc output → may force full
        6. Check skip condition → may return skip
        
        All checks are logged to decision_log for observability.
        
        Args:
            pages: All pages in the site
            assets: All assets in the site  
            incremental: Whether incremental mode is enabled
            forced_changed_sources: Paths to treat as changed (file watcher)
            nav_changed_sources: Paths with navigation-affecting changes
            
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
        
        # Step 2: Detect changes
        pages_to_build, assets_to_process, affected_tags, affected_sections, changed_paths = (
            self._detect_changes(all_pages, all_assets, forced_changed_sources, nav_changed_sources)
        )
        log.pages_with_changes = len(pages_to_build)
        log.assets_with_changes = len(assets_to_process)
        
        # Step 3: Fingerprint cascade
        cascade_assets = [a for a in assets_to_process if a.source_path.suffix.lower() in {".css", ".js"}]
        if cascade_assets:
            log.fingerprint_cascade_triggered = True
            log.fingerprint_assets_changed = [a.source_path.name for a in cascade_assets]
            if not pages_to_build:
                pages_to_build = all_pages
        
        # Step 4: Check output presence
        log.output_presence_checked = True
        output_result = self.output_checker.check(self.output_dir)
        log.output_present = output_result.is_present
        if self.output_dir.exists():
            assets_dir = self.output_dir / "assets"
            if assets_dir.exists():
                log.output_assets_count = len(list(assets_dir.iterdir()))
        
        if not output_result.is_present:
            log.decision_type = FilterDecisionType.FULL
            log.full_rebuild_trigger = FullRebuildTrigger.OUTPUT_DIR_EMPTY
            return self._full_rebuild(all_pages, all_assets, log)
        
        # Step 5: Check skip condition
        if not pages_to_build and not assets_to_process:
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
    
    def _detect_changes(
        self,
        all_pages: list[Page],
        all_assets: list[Asset],
        forced_changed: set[Path] | None,
        nav_changed: set[Path] | None,
    ) -> tuple[list[Page], list[Asset], set[str], set[str], set[Path]]:
        """Detect which pages/assets have changed."""
        # Delegate to ChangeDetector if available
        if self.change_detector:
            change_set = self.change_detector.detect_changes(
                phase="early",
                forced_changed_sources=forced_changed,
                nav_changed_sources=nav_changed,
            )
            return (
                change_set.pages_to_build,
                change_set.assets_to_process,
                change_set.affected_tags,
                change_set.affected_sections or set(),
                {p.source_path for p in change_set.pages_to_build},
            )
        
        # Fallback: simple cache-based detection
        pages_to_build = []
        assets_to_process = []
        affected_tags: set[str] = set()
        affected_sections: set[str] = set()
        changed_paths: set[Path] = set()
        
        for page in all_pages:
            if (forced_changed and page.source_path in forced_changed) or \
               self.cache.is_changed(page.source_path):
                pages_to_build.append(page)
                changed_paths.add(page.source_path)
                if page.tags:
                    affected_tags.update(str(t).lower().replace(" ", "-") for t in page.tags if t)
        
        for asset in all_assets:
            if (forced_changed and asset.source_path in forced_changed) or \
               self.cache.is_changed(asset.source_path):
                assets_to_process.append(asset)
        
        return pages_to_build, assets_to_process, affected_tags, affected_sections, changed_paths
    
    def _full_rebuild(
        self,
        all_pages: list[Page],
        all_assets: list[Asset],
        log: FilterDecisionLog,
    ) -> FilterDecision:
        """Return a full rebuild decision."""
        return FilterDecision(
            pages_to_build=all_pages,
            assets_to_process=all_assets,
            affected_tags=set(),
            affected_sections=set(),
            changed_page_paths={p.source_path for p in all_pages},
            decision_log=log,
        )
```

### Implementation Notes (parity)

- Keep `IncrementalDecision` wired until `FilterDecisionLog` exposes per-page rebuild/skip reasons and change_summary to avoid regressions in `--explain` and logging.
- Wrapper (phase_incremental_filter) must continue to update stats (`cache_hits`, `cache_misses`, `time_saved_ms`) and emit the same incremental summary logs.
- Engine should accept a `config_changed: bool` input; if true, set `FullRebuildTrigger.CONFIG_CHANGED`, otherwise remove that trigger from the enum to avoid dead code.
- Output checks must mirror current behavior: force full rebuild when html or assets missing (assets <3), force full on autodoc output missing, and bypass skip when special pages are missing (allow postprocess regeneration).
- Taxonomy regen flag prevents skip even when no page/asset changes were detected.

---

## Migration Plan (Enhanced)

### Phase 1: Engine Construction & Shadow Run (Non-Breaking)

1. Create `bengal/orchestration/incremental/filter_engine.py`.
2. Implement `IncrementalFilterEngine` with 100% logic parity to `initialization.py`.
3. Add comprehensive unit tests (target: 95%+ coverage).
4. **Shadow Run**: In `phase_incremental_filter()`, run the engine but do NOT use its output for the build yet. Compare its `FilterDecision` with the legacy result and log any discrepancies.
5. Add "Regress-to-Bug" tests for `Bug 1` and `Bug 2`.

**LOC**: ~350 new lines  
**Risk**: Low (parallel execution)  
**Effort**: ~4 hours

### Phase 2: Bridge & Swap

1. Update `FilterDecision` to implement `to_legacy_decision()`.
2. Update `phase_incremental_filter()` to delegate to the engine.
3. Bridge the result to `IncrementalDecision` to populate `orchestrator.stats`.
4. Run full test suite + manual warm build testing.
5. Validate parity for stats/logging/--explain outputs.
6. Keep old code path behind `BENGAL_LEGACY_FILTER=1` for one cycle.

**LOC**: ~100 lines changed  
**Risk**: Medium (behavior parity required)  
**Effort**: ~2 hours

### Phase 3: Observability & Cleanup

1. Add `--explain` support directly to `FilterDecisionLog`.
2. Add JSON export for `FilterDecisionLog` for external debugging tools.
3. Remove legacy code path and the bridge adapter.
4. Consolidate `IncrementalDecision` dataclass entirely into `FilterDecisionLog`.

**LOC**: ~150 lines changed  
**Risk**: Low  
**Effort**: ~2 hours

---

## Test Plan

### Unit Tests (Phase 1)

- **Regress-to-Bug B1**: Mock `output_dir` as non-empty but without `index.html`. Verify `FilterDecision` is **INCREMENTAL**, not FULL.
- **Regress-to-Bug B2**: Simulate cache reinitialization. Verify `IncrementalFilterEngine` picks up the new cache and doesn't hold stale state.
- **Parity cases**:
  - Autodoc output missing forces full rebuild.
  - Assets/html missing forces full rebuild.
  - Special pages missing prevents skip.
  - Taxonomy regen flag blocks skip.

### Success Criteria (Measurable)

1. **Zero Discrepancy**: Shadow run (Phase 1) reports 0 differences across standard benchmarks.
2. **Sub-second Decision**: Decision overhead < 2ms on sites with 5,000+ pages.
3. **Traceability**: `--explain` identifies the exact `FullRebuildTrigger` for every full build.
4. **No regressions**: All existing 800+ tests in `/tests` pass.

### Should Have (Performance & DX)

7. **Performance parity**: No measurable overhead from extraction
   - Benchmark: <1ms for decision logic on 1000-page site

8. **Clear naming**: No confusion with existing RebuildDecisionEngine
   - `IncrementalFilterEngine` (this) vs `RebuildDecisionEngine` (block-level)

9. **Extensible**: Easy to add new decision criteria
   - Protocol-based composition
   - Adding a new check = adding a method + test

---

## Future Enhancements (Enabled by This Architecture)

Once `IncrementalFilterEngine` is in place, these improvements become straightforward:

| Enhancement | Description | Effort with Engine |
|-------------|-------------|--------------------|
| **Data file cascade** | Rebuild pages when `data/*.yaml` changes | Add `_check_data_files()` + test |
| **Shortcode cascade** | Rebuild pages using changed shortcodes | Add `_check_shortcode_deps()` + test |
| **Selective taxonomy regen** | Only rebuild affected tag pages | Refine `affected_tags` logic |
| **Decision explain CLI** | `bengal build --explain` shows why each page rebuilds | Serialize `FilterDecisionLog` |
| **Incremental dashboard** | Real-time view of what's rebuilding and why | Emit decision_log to dashboard |
| **Warm build benchmarks** | CI benchmarks for incremental performance | Use decision_log metrics |

Without this architecture, each enhancement requires:
- Understanding 250+ lines of interleaved logic
- Risk of breaking existing decision paths
- Manual testing to verify no regressions

---

## Relationship to Other RFCs & Components

| Component/RFC | Relationship |
|---------------|--------------|
| `RebuildDecisionEngine` (existing) | **Distinct scope**: That handles block-level template decisions; this handles incremental filter decisions |
| `ChangeDetector` (existing) | **Integrates**: FilterEngine delegates change detection to ChangeDetector |
| `IncrementalDecision` (existing) | **Consolidates**: FilterDecisionLog incorporates IncrementalDecision fields |
| `rfc-incremental-build-observability` | **Complementary**: That RFC adds logging; this RFC extracts logic to make logging meaningful |
| `rfc-cache-invalidation-architecture` | **Complementary**: CacheCoordinator handles cache layer; this RFC handles filter decision |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-14 | Create RFC after debugging session | Two bugs found due to scattered decision logic |
| 2026-01-14 | Extract to dedicated class | Single responsibility, testable in isolation |
| 2026-01-14 | Protocol for OutputChecker | Explicit contract, easy to mock in tests |
| 2026-01-14 | Rename to `IncrementalFilterEngine` | Avoid collision with existing `RebuildDecisionEngine` |
| 2026-01-14 | Approve for implementation | Incremental builds are core value prop; hardening is strategic investment |

---

## Appendix: Original Bugs (Historical)

### Bug 1: output_html_missing Check (FIXED)

**Before** (hidden assumption):
```python
output_html_missing = not (output_dir / "index.html").exists()
```

**After** (current implementation):
```python
# Note: We don't check for root index.html specifically since not all sites
# have a home page. Instead, check if output_dir has any content at all.
output_html_missing = (
    not output_dir.exists() or len(list(output_dir.iterdir())) == 0
)
```

**Location**: `initialization.py:688-692`

### Bug 2: Stale Reference (FIXED)

**Before** (implicit lifecycle):
```python
def initialize(self, enabled: bool) -> tuple[BuildCache, ...]:
    self.cache = BuildCache.load(...)  # Cache replaced
    # _change_detector still has old cache!
```

**After** (current implementation):
```python
def initialize(self, enabled: bool) -> tuple[BuildCache, ...]:
    self.cache, self.tracker = self._cache_manager.initialize(enabled)
    # Reset change detector so it picks up the new cache
    # (fixes stale reference bug where detector kept old cache)
    self._change_detector = None
    return self.cache, self.tracker
```

**Location**: `orchestrator.py:105-107`
