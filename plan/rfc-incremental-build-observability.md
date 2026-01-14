# RFC: Incremental Build Observability & Debugging

## Status: Draft
## Created: 2026-01-14
## Origin: Debugging session that took 60+ minutes to trace 5 interconnected bugs

---

## Summary

**Problem**: Debugging incremental build issues is extremely difficult due to:
- Silent failures with conservative fallbacks that "work" but poorly
- Multiple caching layers without unified observability
- Tests that don't catch real-world failure modes (cross-process, subsection changes)
- No structured decision tracing to understand why builds happen

**Solution**: Implement a comprehensive observability system with:
1. `--trace-incremental` CLI flag for decision tracing
2. Invariant-based tests that verify correctness properties
3. Structured decision logging at each layer
4. Fail-fast mode for development

**Priority**: High (incremental builds are core Bengal value proposition)

**Scope**: ~400 LOC implementation + ~200 LOC tests

---

## Evidence: The Debugging Odyssey

A simple "hello world" text change triggered a full rebuild. Diagnosing this required:

| Issue | Time to Find | Root Cause | Why Hard |
|-------|--------------|------------|----------|
| Data file fingerprints not saved | 20 min | `_update_data_file_fingerprints()` never called | No log when fallback triggered |
| Python 3.12 vs 3.14 | 10 min | `compression.zstd` import failed silently | Empty cache returned, no error |
| Autodoc metadata empty | 15 min | Fingerprint fallback not implemented | "Cache migration" message misleading |
| Section optimization too strict | 20 min | Didn't check subsections recursively | No trace of section filtering |
| Subsection path matching | 10 min | Identity check vs path containment | No log showing which pages filtered |

**Total**: 75+ minutes to trace what should have been obvious with proper observability.

---

## Problem Analysis

### 1. Silent Failures Mask Root Causes

Current behavior when cache loading fails:

```python
# In BuildCache.load()
try:
    return cls._load_compressed(cache_path)
except Exception:
    return cls()  # Silent empty cache - no warning!
```

When autodoc metadata is missing:

```python
# In get_stale_autodoc_sources()
if not self.autodoc_source_metadata and self.autodoc_dependencies:
    return set(self.autodoc_dependencies.keys())  # "Works" but rebuilds everything
```

**Result**: The system "works" but users see full rebuilds with no explanation.

### 2. Multiple Caching Layers Without Unified View

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Incremental Build Decision Pipeline               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Layer 1: Data Files        Layer 2: Autodoc         Layer 3: Sections
│  ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  │ Fingerprints    │  →    │ Source Metadata │  →    │ Section Opt     │
│  │ (file_tracking) │       │ (autodoc_track) │       │ (rebuild_filter)│
│  └─────────────────┘       └─────────────────┘       └─────────────────┘
│         │                         │                         │
│         ↓                         ↓                         ↓
│    [3 changes]              [empty → all]           [docs marked]
│                                                            │
│                                                            ↓
│                                                   Layer 4: Page Filter
│                                                   ┌─────────────────┐
│                                                   │ file_detector   │
│                                                   │ (pages_to_scan) │
│                                                   └─────────────────┘
│                                                            │
│                                                            ↓
│                                                      [0 pages!?]
│                                                                      │
│  ❌ No single place to see: "Why did we decide to rebuild X pages?" │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. Tests Test Implementation, Not Invariants

Current tests:
```python
def test_save_and_load(self, tmp_path):
    cache = BuildCache()
    cache.update_file(some_file)
    cache.save(cache_path)
    loaded = BuildCache.load(cache_path)
    assert loaded.file_fingerprints  # Passes in-process, fails cross-process!
```

Missing tests:
- Cross-process cache round-trip
- Subsection changes detected
- Autodoc with missing metadata uses fingerprints
- Page filtering includes subsection pages

---

## Proposed Solution

### 1. Decision Trace System (`--trace-incremental`)

Add a structured trace that captures every decision point:

```python
@dataclass
class IncrementalDecisionTrace:
    """Full trace of incremental build decision for debugging."""
    
    # Timestamps for performance analysis
    trace_started: float
    trace_completed: float
    
    # Layer 1: Data files
    data_files_checked: int = 0
    data_files_changed: list[str] = field(default_factory=list)
    data_file_fingerprints_available: bool = False
    data_file_fallback_used: bool = False
    
    # Layer 2: Autodoc
    autodoc_metadata_available: bool = False
    autodoc_fingerprint_fallback_used: bool = False
    autodoc_sources_total: int = 0
    autodoc_sources_stale: list[str] = field(default_factory=list)
    autodoc_stale_reason: str = ""  # "metadata" | "fingerprint" | "missing"
    
    # Layer 3: Section optimization
    sections_total: int = 0
    sections_checked: int = 0
    sections_marked_changed: list[str] = field(default_factory=list)
    section_change_reasons: dict[str, str] = field(default_factory=dict)
    # e.g., {"docs": "subsection_fingerprint_stale:about/glossary.md"}
    
    # Layer 4: Page filtering
    pages_total: int = 0
    pages_in_changed_sections: int = 0
    pages_with_stale_fingerprints: int = 0
    pages_filtered_by_section: int = 0
    pages_filtered_reasons: dict[str, str] = field(default_factory=dict)
    
    # Layer 5: Final decision
    pages_to_rebuild: int = 0
    pages_skipped: int = 0
    assets_to_process: int = 0
    decision_type: Literal["full", "incremental", "skip"] = "incremental"
    full_rebuild_reason: str | None = None
    
    def to_diagnostic(self) -> str:
        """Generate human-readable diagnostic output."""
        lines = [
            "═══════════════════════════════════════════════════════════════",
            "                  INCREMENTAL BUILD TRACE                       ",
            "═══════════════════════════════════════════════════════════════",
            "",
            f"Final Decision: {self.decision_type.upper()}",
            f"  Pages to rebuild: {self.pages_to_rebuild}",
            f"  Pages skipped:    {self.pages_skipped}",
            "",
            "─────────────────────────────────────────────────────────────────",
            "Layer 1: Data Files",
            "─────────────────────────────────────────────────────────────────",
            f"  Checked: {self.data_files_checked}",
            f"  Changed: {len(self.data_files_changed)}",
            f"  Fingerprints available: {self.data_file_fingerprints_available}",
            f"  Fallback used: {self.data_file_fallback_used}",
        ]
        if self.data_files_changed:
            lines.append("  Changed files:")
            for f in self.data_files_changed[:5]:
                lines.append(f"    - {f}")
            if len(self.data_files_changed) > 5:
                lines.append(f"    ... and {len(self.data_files_changed) - 5} more")
        
        lines.extend([
            "",
            "─────────────────────────────────────────────────────────────────",
            "Layer 2: Autodoc",
            "─────────────────────────────────────────────────────────────────",
            f"  Metadata available: {self.autodoc_metadata_available}",
            f"  Fingerprint fallback used: {self.autodoc_fingerprint_fallback_used}",
            f"  Sources total: {self.autodoc_sources_total}",
            f"  Sources stale: {len(self.autodoc_sources_stale)}",
        ])
        if self.autodoc_stale_reason:
            lines.append(f"  Stale reason: {self.autodoc_stale_reason}")
        
        lines.extend([
            "",
            "─────────────────────────────────────────────────────────────────",
            "Layer 3: Section Optimization",
            "─────────────────────────────────────────────────────────────────",
            f"  Sections total: {self.sections_total}",
            f"  Sections changed: {len(self.sections_marked_changed)}",
        ])
        if self.sections_marked_changed:
            lines.append("  Changed sections:")
            for s in self.sections_marked_changed:
                reason = self.section_change_reasons.get(s, "unknown")
                lines.append(f"    - {s} ({reason})")
        
        lines.extend([
            "",
            "─────────────────────────────────────────────────────────────────",
            "Layer 4: Page Filtering",
            "─────────────────────────────────────────────────────────────────",
            f"  Pages total: {self.pages_total}",
            f"  In changed sections: {self.pages_in_changed_sections}",
            f"  With stale fingerprints: {self.pages_with_stale_fingerprints}",
            f"  Filtered by section: {self.pages_filtered_by_section}",
            "",
            "═══════════════════════════════════════════════════════════════",
        ])
        
        return "\n".join(lines)
```

**CLI Integration**:

```bash
$ bengal build --trace-incremental

═══════════════════════════════════════════════════════════════
                  INCREMENTAL BUILD TRACE                       
═══════════════════════════════════════════════════════════════

Final Decision: INCREMENTAL
  Pages to rebuild: 3
  Pages skipped:    1060

─────────────────────────────────────────────────────────────────
Layer 1: Data Files
─────────────────────────────────────────────────────────────────
  Checked: 3
  Changed: 0
  Fingerprints available: True
  Fallback used: False

─────────────────────────────────────────────────────────────────
Layer 2: Autodoc
─────────────────────────────────────────────────────────────────
  Metadata available: False
  Fingerprint fallback used: True    ← Would have been "all stale" before fix
  Sources total: 448
  Sources stale: 0

─────────────────────────────────────────────────────────────────
Layer 3: Section Optimization
─────────────────────────────────────────────────────────────────
  Sections total: 5
  Sections changed: 1
  Changed sections:
    - docs (subsection_fingerprint_stale:about/glossary.md)

─────────────────────────────────────────────────────────────────
Layer 4: Page Filtering
─────────────────────────────────────────────────────────────────
  Pages total: 1063
  In changed sections: 35
  With stale fingerprints: 3
  Filtered by section: 1028

═══════════════════════════════════════════════════════════════
```

### 2. Invariant-Based Tests

Add tests that verify correctness properties, not implementation details:

```python
# tests/integration/test_incremental_invariants.py

class TestIncrementalInvariants:
    """Tests that verify incremental build correctness invariants."""
    
    def test_unchanged_file_never_rebuilt(self, warm_site: WarmBuildTestSite):
        """INVARIANT: Unchanged files must never be rebuilt."""
        # Build once to warm cache
        first_stats = warm_site.build()
        first_pages = {p.source_path for p in first_stats.pages_built}
        
        # Build again with no changes
        second_stats = warm_site.build()
        second_pages = {p.source_path for p in second_stats.pages_to_build}
        
        # INVARIANT: No overlap
        assert second_pages == set(), (
            f"Unchanged files were rebuilt: {second_pages & first_pages}"
        )
    
    def test_changed_file_always_rebuilt(self, warm_site: WarmBuildTestSite):
        """INVARIANT: Changed files must always be rebuilt."""
        warm_site.build()
        
        # Modify a file
        test_file = warm_site.content / "test.md"
        test_file.write_text(test_file.read_text() + "\n<!-- changed -->")
        
        stats = warm_site.build()
        rebuilt_paths = {p.source_path for p in stats.pages_to_build}
        
        # INVARIANT: Changed file must be rebuilt
        assert test_file in rebuilt_paths, (
            f"Changed file {test_file} was not rebuilt"
        )
    
    def test_subsection_change_marks_parent_section(
        self, warm_site_with_sections: WarmBuildTestSite
    ):
        """INVARIANT: Subsection changes must mark parent section as changed."""
        warm_site_with_sections.build()
        
        # Modify file in subsection
        subsection_file = warm_site_with_sections.content / "docs/about/glossary.md"
        subsection_file.write_text(subsection_file.read_text() + "\n<!-- changed -->")
        
        # Get changed sections (internal API for testing)
        cache = BuildCache.load(warm_site_with_sections.cache_path)
        filter = RebuildFilter(warm_site_with_sections.site, cache)
        changed_sections = filter.get_changed_sections()
        
        # INVARIANT: Parent section "docs" must be in changed_sections
        docs_changed = any("docs" in str(s.path) for s in changed_sections)
        assert docs_changed, (
            f"Parent section 'docs' not marked changed. "
            f"Changed sections: {[str(s.path) for s in changed_sections]}"
        )
    
    def test_cross_process_cache_consistency(self, tmp_path: Path):
        """INVARIANT: Cache saved in one process must load correctly in another."""
        cache_path = tmp_path / "cache.json"
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")
        
        # Save cache in subprocess
        save_script = f'''
import sys
sys.path.insert(0, "{Path(__file__).parent.parent.parent}")
from pathlib import Path
from bengal.cache.build_cache import BuildCache

cache = BuildCache()
cache.update_file(Path("{test_file}"))
cache.save(Path("{cache_path}"))
print(f"Saved {{len(cache.file_fingerprints)}} fingerprints")
'''
        result = subprocess.run(
            [sys.executable, "-c", save_script],
            capture_output=True,
            text=True,
        )
        assert "Saved 1 fingerprints" in result.stdout
        
        # Load in current process
        loaded = BuildCache.load(cache_path)
        
        # INVARIANT: Fingerprints must survive cross-process round-trip
        assert str(test_file) in loaded.file_fingerprints, (
            f"Fingerprint lost in cross-process round-trip. "
            f"Available: {list(loaded.file_fingerprints.keys())}"
        )
    
    def test_autodoc_with_missing_metadata_uses_fingerprints(
        self, warm_site_with_autodoc: WarmBuildTestSite
    ):
        """INVARIANT: Missing autodoc metadata must fallback to fingerprints."""
        warm_site_with_autodoc.build()
        
        # Simulate missing metadata (old cache format)
        cache = BuildCache.load(warm_site_with_autodoc.cache_path)
        cache.autodoc_source_metadata = {}  # Clear metadata
        cache.save(warm_site_with_autodoc.cache_path)
        
        # Build again
        stats = warm_site_with_autodoc.build()
        
        # INVARIANT: Should NOT rebuild all autodoc (fingerprints should work)
        autodoc_rebuilt = sum(
            1 for p in stats.pages_to_build if p.metadata.get("is_autodoc")
        )
        assert autodoc_rebuilt == 0, (
            f"Autodoc pages unnecessarily rebuilt: {autodoc_rebuilt}. "
            f"Fingerprint fallback should have prevented this."
        )
```

### 3. Structured Decision Logging

Replace ad-hoc logging with structured decision events:

```python
# bengal/orchestration/incremental/decision_logger.py

from enum import Enum
from typing import Any

class DecisionEvent(Enum):
    """Incremental build decision events."""
    
    # Layer 1: Data files
    DATA_FILE_CHECK_START = "data_file_check_start"
    DATA_FILE_CHANGED = "data_file_changed"
    DATA_FILE_FINGERPRINT_MISSING = "data_file_fingerprint_missing"
    DATA_FILE_FALLBACK_TRIGGERED = "data_file_fallback_triggered"
    
    # Layer 2: Autodoc
    AUTODOC_CHECK_START = "autodoc_check_start"
    AUTODOC_METADATA_MISSING = "autodoc_metadata_missing"
    AUTODOC_FINGERPRINT_FALLBACK = "autodoc_fingerprint_fallback"
    AUTODOC_SOURCE_STALE = "autodoc_source_stale"
    AUTODOC_ALL_STALE_FALLBACK = "autodoc_all_stale_fallback"
    
    # Layer 3: Sections
    SECTION_CHECK_START = "section_check_start"
    SECTION_MARKED_CHANGED = "section_marked_changed"
    SECTION_SKIPPED = "section_skipped"
    SUBSECTION_STALE_DETECTED = "subsection_stale_detected"
    
    # Layer 4: Page filtering
    PAGE_FILTER_START = "page_filter_start"
    PAGE_INCLUDED = "page_included"
    PAGE_EXCLUDED_BY_SECTION = "page_excluded_by_section"
    PAGE_STALE_FINGERPRINT = "page_stale_fingerprint"
    
    # Final
    DECISION_COMPLETE = "decision_complete"


def log_decision(
    event: DecisionEvent,
    *,
    decision: str | None = None,
    reason: str | None = None,
    impact: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Log an incremental build decision event.
    
    Args:
        event: The decision event type
        decision: What was decided (e.g., "include", "exclude", "rebuild_all")
        reason: Why this decision was made
        impact: Effect of this decision (e.g., "3 pages added to rebuild")
        context: Additional context (file paths, counts, etc.)
    """
    logger.debug(
        event.value,
        decision=decision,
        reason=reason,
        impact=impact,
        **(context or {}),
    )
```

**Usage in code**:

```python
# Before (hard to trace):
logger.debug("autodoc_cache_migration", msg="No source metadata found...")

# After (structured and traceable):
log_decision(
    DecisionEvent.AUTODOC_METADATA_MISSING,
    decision="use_fingerprint_fallback",
    reason="autodoc_source_metadata empty but fingerprints available",
    impact=f"{len(self.autodoc_dependencies)} sources to check via fingerprints",
    context={"source_count": len(self.autodoc_dependencies)},
)
```

### 4. Fail-Fast Mode for Development

Add an environment variable or flag to surface errors instead of silent fallbacks:

```python
# bengal/config/environment.py

import os

def is_development_mode() -> bool:
    """Check if running in development mode (fail-fast)."""
    return os.environ.get("BENGAL_DEV_MODE", "").lower() in ("1", "true", "yes")


# Usage in autodoc_tracking.py
if not self.autodoc_source_metadata and self.autodoc_dependencies:
    if is_development_mode():
        raise IncrementalCacheError(
            "Autodoc source metadata empty but dependencies present.\n"
            "This will cause full autodoc rebuilds on every incremental build.\n"
            "Fix: Ensure autodoc metadata is saved via add_autodoc_dependency().\n"
            "Workaround: Run `bengal cache clear` to reset cache."
        )
    
    # Production: use fingerprint fallback
    if has_fingerprints:
        log_decision(
            DecisionEvent.AUTODOC_FINGERPRINT_FALLBACK,
            decision="use_fingerprints",
            reason="metadata_missing_fingerprints_available",
            impact="incremental detection via fingerprints",
        )
        return self._check_via_fingerprints()
    else:
        log_decision(
            DecisionEvent.AUTODOC_ALL_STALE_FALLBACK,
            decision="mark_all_stale",
            reason="metadata_missing_no_fingerprints",
            impact=f"full autodoc rebuild ({len(self.autodoc_dependencies)} sources)",
        )
        return set(self.autodoc_dependencies.keys())
```

---

## Implementation Plan

### Phase 1: Foundation (2 days)

1. **Add `IncrementalDecisionTrace` dataclass** with all fields
2. **Wire trace collection** through existing decision points
3. **Add `--trace-incremental` CLI flag** to output trace
4. **Add Python version warning** in CLI entry point ✅ (already done)

### Phase 2: Tests (1 day)

1. **Add invariant tests** in `tests/integration/test_incremental_invariants.py`
2. **Add subsection detection test**
3. **Add cross-process cache test** ✅ (already done)
4. **Add autodoc fallback test**

### Phase 3: Structured Logging (1 day)

1. **Add `DecisionEvent` enum**
2. **Add `log_decision()` helper**
3. **Replace ad-hoc logging** in key decision points
4. **Add development mode flag**

### Phase 4: Documentation (0.5 day)

1. **Document caching layers** in architecture doc
2. **Add troubleshooting guide** for incremental build issues
3. **Document `--trace-incremental` flag**

---

## Success Criteria

1. **Debugging time < 10 minutes** for incremental build issues (vs 60+ today)
2. **`--trace-incremental` identifies root cause** in single command
3. **Invariant tests catch regressions** before release
4. **No silent failures** in development mode
5. **Clear documentation** for troubleshooting

---

## Appendix: Bugs That Would Have Been Caught

| Bug | Would Be Caught By |
|-----|-------------------|
| Data file fingerprints not saved | Invariant test: unchanged file rebuilt |
| Python version mismatch | CLI warning (implemented) |
| Autodoc metadata empty | Trace: "Fingerprint fallback used: True" |
| Section optimization skipped subsections | Invariant test: subsection change marks parent |
| Subsection path matching broken | Invariant test: changed file always rebuilt |

---

## Related

- `plan/rfc-rebuild-decision-hardening.md` - Prior RFC on incremental filter consolidation
- `bengal/orchestration/incremental/filter_engine.py` - Current decision logic
- `tests/integration/test_incremental_cache_stability.py` - Existing tests

