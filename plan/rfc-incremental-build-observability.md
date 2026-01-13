# RFC: Incremental Build Observability

## Status: Phase 1 + Phase 2 Implemented
## Created: 2026-01-13
## Updated: 2026-01-13
## Origin: Debugging session for stale CSS fingerprints bug

---

## Summary

**Problem**: Incremental build decisions are opaque—no visibility into WHY pages are included/excluded from `pages_to_build`, making debugging cache issues extremely difficult.

**Solution**: Add structured logging, "explain mode", and rebuild reason tracking to the incremental filter.

**Priority**: High (this class of bug took 1+ hour to diagnose due to lack of observability)

**Scope**: Phase 1 (~100 LOC), Phase 2 (~80 LOC), Phase 3 (deferred indefinitely)

---

## Problem Statement

### The Observability Gap

The `phase_incremental_filter()` function determines which pages to rebuild, but provides no insight into its decisions:

```python
# Current: Silent decision-making
pages_to_build, assets_to_process, change_summary = (
    orchestrator.incremental.find_work_early(...)
)
# At this point, we have no idea WHY index.md is/isn't in pages_to_build
```

### Why This Matters (Evidence from Debugging)

During the stale CSS fingerprint bug investigation:

1. **Symptom**: Home page had old CSS fingerprint
2. **Hypothesis**: Rendered cache not invalidating
3. **Reality**: Page wasn't in `pages_to_build` at all (never hit cache logic)
4. **Diagnosis method**: Manual monkey-patching of `should_bypass()` 

**Time to root cause**: ~45 minutes  
**Time with observability**: ~5 minutes (check "rebuild reasons" log)

### Specific Gaps

| Gap | Impact | Example |
|-----|--------|---------|
| No "rebuild reason" per page | Can't see WHY a page is included | "content_changed" vs "asset_fingerprint_changed" |
| No "skip reason" per page | Can't see WHY a page is excluded | "cache_hit" vs "no_changes" |
| Silent incremental decisions | Have to read code to understand behavior | `find_work_early()` internals |
| No "dry run" mode | Can't preview what WOULD rebuild | `bengal build --dry-run --explain` |

### Existing Logging (What We Have)

The `ChangeDetector` already emits some structured logs:

```python
# change_detector.py:198-246
logger.info("cascade_dependencies_detected", additional_pages=cascade_count, reason="...")
logger.info("cross_version_dependencies_detected", additional_pages=xver_count, reason="...")
logger.info("navigation_dependencies_detected", additional_pages=nav_count, reason="...")
```

**Gap**: These logs tell us WHAT triggered additional rebuilds, but not the **per-page breakdown** or **summary statistics**.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Log verbosity | INFO for summary, DEBUG for per-page | Summary is always useful; details add noise |
| Skip reason tracking | Only when `verbose=True` | Avoid O(n) overhead for large sites |
| Storage | In-memory only (not persisted) | Diagnostic tool, not build artifact |
| Integration | Additive (alongside existing logs) | Don't break existing structured logging |
| Reason representation | Enum + dataclass | Type safety, exhaustive handling |

---

## Proposed Solutions

### Phase 1: Rebuild Reason Tracking (Implement Now)

Add structured data about WHY each page is in `pages_to_build`.

**File**: `bengal/orchestration/build/results.py`

```python
from enum import Enum

class RebuildReasonCode(Enum):
    """Why a page is being rebuilt.
    
    Enables exhaustive handling and better IDE support.
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


@dataclass
class RebuildReason:
    """Tracks why a page is being rebuilt.
    
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


class SkipReasonCode(Enum):
    """Why a page was skipped (not rebuilt)."""
    CACHE_HIT = "cache_hit"
    NO_CHANGES = "no_changes"
    SECTION_FILTERED = "section_filtered"


@dataclass  
class IncrementalDecision:
    """Complete picture of incremental build decisions.
    
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
    skip_reasons: dict[str, SkipReasonCode] = field(default_factory=dict)  # Only when verbose
    asset_changes: list[str] = field(default_factory=list)
    fingerprint_changes: bool = False
    
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
```

**Usage in `phase_incremental_filter`**:

```python
def phase_incremental_filter(..., verbose: bool = False) -> FilterResult | None:
    decision = IncrementalDecision(
        pages_to_build=[],
        pages_skipped_count=0,
    )
    
    # ... existing logic ...
    
    # When CSS/JS changes detected
    if fingerprint_assets_changed:
        decision.fingerprint_changes = True
        decision.asset_changes = [a.source_path.name for a in fingerprint_assets]
        pages_to_build = list(orchestrator.site.pages)
        
        for page in pages_to_build:
            decision.rebuild_reasons[str(page.source_path)] = RebuildReason(
                code=RebuildReasonCode.ASSET_FINGERPRINT_CHANGED,
                details={"assets": decision.asset_changes},
            )
    
    # Track skip reasons only when verbose (avoid O(n) overhead)
    if verbose:
        all_pages = set(orchestrator.site.pages)
        skipped = all_pages - set(pages_to_build)
        for page in skipped:
            decision.skip_reasons[str(page.source_path)] = SkipReasonCode.NO_CHANGES
    
    decision.pages_to_build = pages_to_build
    decision.pages_skipped_count = len(orchestrator.site.pages) - len(pages_to_build)
    
    # Always log summary (INFO), details only when verbose (DEBUG)
    decision.log_summary(orchestrator.logger)
    if verbose:
        decision.log_details(orchestrator.logger)
    
    return FilterResult(...)
```

**Logging output**:

```
INFO: incremental_decision pages_to_build=15 pages_skipped=42 fingerprint_changes=True asset_changes=['style.css']

DEBUG: rebuild_reason page=content/index.md reason=asset_fingerprint_changed details={'assets': ['style.css']}
DEBUG: rebuild_reason page=content/docs/intro.md reason=asset_fingerprint_changed details={'assets': ['style.css']}
```

**LOC**: ~100 lines

---

### Phase 2: Explain Mode CLI (User Request)

Add `--explain` flag for user-facing diagnostics.

**CLI Specification**:

| Flag | Behavior |
|------|----------|
| `--explain` | Show detailed rebuild decision breakdown |
| `--dry-run` | Don't write output files, show what WOULD happen |
| `--dry-run --explain` | Combined: preview + detailed breakdown |
| `--explain --json` | Output as JSON (for tooling integration) |

**Implementation**: `bengal/cli/commands/build.py`

```python
@click.option("--explain", is_flag=True, help="Show detailed rebuild decisions")
@click.option("--dry-run", is_flag=True, help="Preview build without writing files")
def build_command(explain: bool, dry_run: bool, ...):
    # Pass explain flag through to orchestrator
    result = orchestrator.build(
        explain=explain,
        dry_run=dry_run,
    )
    
    if explain:
        _print_explain_output(result.incremental_decision)
```

**Output format**:

```bash
$ bengal build --dry-run --explain

📊 Incremental Build Preview

Would rebuild 15 pages (57 skipped):

  REBUILD (15 pages):
  ┌─────────────────────────────────────────────────────────────┐
  │ Reason                      │ Count │ Pages                 │
  ├─────────────────────────────────────────────────────────────┤
  │ asset_fingerprint_changed   │    12 │ index.md, docs/...    │
  │ content_changed             │     2 │ blog/post.md, ...     │
  │ cascade_dependency          │     1 │ docs/api.md           │
  └─────────────────────────────────────────────────────────────┘

  ASSETS:
    • style.css      → CHANGED (fingerprint: 8daed388 → d860120c)
    • main.js        → unchanged

  SKIP (57 pages): no_changes

Run without --dry-run to execute build.
```

**JSON output** (for tooling):

```bash
$ bengal build --dry-run --explain --json
```

```json
{
  "pages_to_build": 15,
  "pages_skipped": 57,
  "fingerprint_changes": true,
  "asset_changes": ["style.css"],
  "rebuild_reasons": {
    "content/index.md": {"code": "asset_fingerprint_changed", "details": {"assets": ["style.css"]}},
    ...
  },
  "dry_run": true
}
```

**LOC**: ~80 lines

---

### Phase 3: Asset Dependency Graph (Deferred Indefinitely)

Track which pages depend on which assets for smarter selective rebuilds.

**Status**: ⛔ **Deferred indefinitely**

**Rationale**:
- Requires template parsing to extract `{{ asset_url("style.css") }}` calls
- Templates include other templates (transitive dependency tracking)
- Estimated ~400 LOC, high complexity
- Current "rebuild all on asset change" is correct, just not optimal
- Optimize only if asset-only changes become a measured bottleneck

**Future Consideration**: If implemented, benefits include:
- Only rebuild pages that actually use changed assets
- Warnings: "Page X references asset Y which doesn't exist"
- Asset tree-shaking potential

---

## Implementation Priority

| Phase | Priority | LOC | Complexity | Value | Status |
|-------|----------|-----|------------|-------|--------|
| 1. Rebuild Reasons | 🟢 High | ~100 | Low | Immediate debugging help | **✅ Implemented** |
| 2. Explain Mode | 🟡 Medium | ~150 | Low | User-facing diagnostics | **✅ Implemented** |
| 3. Asset Dependencies | ⛔ Deferred | ~400 | High | Smarter rebuilds | Not planned |

---

## Implementation Checklist

### Phase 1

- [x] Add `RebuildReasonCode` enum to `bengal/orchestration/build/results.py`
- [x] Add `SkipReasonCode` enum
- [x] Add `RebuildReason` dataclass
- [x] Add `IncrementalDecision` dataclass with `log_summary()` and `log_details()`
- [x] Update `phase_incremental_filter()` to create and populate `IncrementalDecision`
- [x] Track rebuild reasons for each code path:
  - [x] Content changes (from `ChangeDetector`)
  - [x] Template changes
  - [x] Asset fingerprint changes
  - [x] Cascade dependencies
  - [x] Nav changes
  - [x] Cross-version dependencies
  - [x] Forced rebuilds
  - [x] Output missing (new reason added)
  - [x] Full rebuild
- [x] Add `verbose` guard for skip_reasons population
- [x] Add INFO log for summary, DEBUG for details
- [x] Add unit tests for `RebuildReason` and `IncrementalDecision`

### Phase 2

- [x] Add `--explain` flag to `bengal build` command
- [x] Add `--dry-run` flag
- [x] Add `--explain-json` output option for `--explain`
- [x] Implement `_print_explain_output()` formatter with table format
- [x] Implement `_print_explain_json()` for machine-readable output
- [x] Update orchestrator to support `dry_run` mode (skips rendering phases)
- [x] Add `explain`, `dry_run`, `explain_json` options to BuildOptions
- [x] Add integration tests for explain output (8 tests)

---

## Error Message Improvements

### Render Pipeline Guard

Add warning when PageProxy reaches render without loading:

```python
def process_page(self, page: Page) -> None:
    # Validate we're not accidentally rendering a PageProxy
    if isinstance(page, PageProxy) and not page._lazy_loaded:
        logger.warning(
            "rendering_unloaded_proxy",
            page=str(page.source_path),
            hint="PageProxy passed to render pipeline without loading. "
                 "Check incremental filter - this page may need to be in pages_to_build."
        )
```

### PageProxy Setter Warning

```python
class PageProxy:
    @links.setter
    def links(self, value: list[str]) -> None:
        if not self._lazy_loaded:
            logger.warning(
                "page_proxy_setter_before_load",
                property="links",
                page=str(self.source_path),
                hint="Setting property on PageProxy before _ensure_loaded() was called.",
            )
        self._ensure_loaded()
        if self._full_page:
            self._full_page.links = value
```

---

## Relationship to Other RFCs

| RFC | Relationship |
|-----|--------------|
| `rfc-global-build-state-dependencies.md` | Observability AFTER the fact (cache validation); this RFC is DURING incremental decisions |
| `rfc-asset-resolution-observability.md` | Asset resolution path logging; this RFC covers build decision logging |

**Potential Integration**: Both this RFC and `rfc-asset-resolution-observability` need observability infrastructure. Consider shared module at `bengal/orchestration/observability.py` for stats/reason tracking patterns.

---

## Success Criteria

1. **Debugging time reduction**: Next cache-related bug should take <15 minutes to diagnose
2. **Structured logs**: Can grep for `incremental_decision` to see rebuild summary
3. **Per-page visibility**: Can grep for `rebuild_reason` to see why specific pages rebuilt
4. **Explain mode** (Phase 2): User can run `bengal build --explain` to understand decisions
5. **Error context**: Errors include hints about likely causes (PageProxy warnings)

---

## Test Plan

### Unit Tests

```python
# tests/unit/orchestration/test_incremental_decision.py

def test_rebuild_reason_str_with_details():
    reason = RebuildReason(
        code=RebuildReasonCode.ASSET_FINGERPRINT_CHANGED,
        details={"assets": ["style.css"]},
    )
    assert str(reason) == "asset_fingerprint_changed (assets=['style.css'])"


def test_rebuild_reason_str_no_details():
    reason = RebuildReason(code=RebuildReasonCode.CONTENT_CHANGED)
    assert str(reason) == "content_changed"


def test_incremental_decision_log_summary(caplog):
    decision = IncrementalDecision(
        pages_to_build=[mock_page],
        pages_skipped_count=10,
        fingerprint_changes=True,
        asset_changes=["style.css"],
    )
    decision.log_summary(logger)
    assert "incremental_decision" in caplog.text
    assert "pages_to_build=1" in caplog.text


def test_skip_reasons_only_populated_when_verbose():
    """Skip reasons should only be tracked when verbose=True."""
    # ... test that skip_reasons is empty when verbose=False
```

### Integration Tests

```python
# tests/integration/test_incremental_observability.py

def test_rebuild_reasons_logged_on_css_change(tmp_project, caplog):
    """CSS change should log asset_fingerprint_changed reason."""
    build_site(tmp_project)
    modify_css(tmp_project)
    
    with caplog.at_level("INFO"):
        build_site(tmp_project, incremental=True)
    
    assert "incremental_decision" in caplog.text
    assert "fingerprint_changes=True" in caplog.text


def test_explain_mode_output(tmp_project, capsys):
    """--explain flag should produce human-readable output."""
    result = run_cli(["build", "--dry-run", "--explain"], cwd=tmp_project)
    assert "REBUILD" in result.stdout
    assert "SKIP" in result.stdout
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-13 | Phase 1 high priority | Direct result of 45-minute debugging session |
| 2026-01-13 | INFO for summary, DEBUG for details | Summary is always useful; per-page is verbose |
| 2026-01-13 | Skip reasons only when verbose | Avoid O(n) overhead for large sites |
| 2026-01-13 | Use enums for reason codes | Type safety, exhaustive handling, IDE support |
| 2026-01-13 | Phase 3 deferred indefinitely | High effort (~400 LOC), low incremental value |
| 2026-01-13 | Additive integration with ChangeDetector | Don't break existing structured logging |
| 2026-01-13 | Phase 1 implemented | Added RebuildReasonCode, SkipReasonCode enums; IncrementalDecision dataclass; updated phase_incremental_filter(); 17 unit tests |
| 2026-01-13 | Added OUTPUT_MISSING reason | Handle warm CI builds where output cleaned but cache present |
| 2026-01-13 | Phase 2 implemented | Added --explain, --dry-run, --explain-json CLI flags; _print_explain_output() and _print_explain_json() formatters; dry_run mode in orchestrator; 8 integration tests |

---

## Appendix: Existing Log Events

For reference, these are the existing structured log events in the incremental system:

```python
# change_detector.py
logger.debug("section_level_filtering", total_sections=..., changed_sections=...)
logger.info("cascade_dependencies_detected", additional_pages=..., reason="...")
logger.info("cross_version_dependencies_detected", additional_pages=..., reason="...")
logger.info("navigation_dependencies_detected", additional_pages=..., reason="...")

# initialization.py (phase_incremental_filter)
logger.info("fingerprint_assets_changed_forcing_page_rebuild", assets_changed=..., pages_to_rebuild=...)
```

Phase 1 adds:
```python
logger.info("incremental_decision", pages_to_build=..., pages_skipped=..., fingerprint_changes=..., asset_changes=...)
logger.debug("rebuild_reason", page=..., reason=..., details=...)
```
