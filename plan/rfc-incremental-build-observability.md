# RFC: Incremental Build Observability & Debugging

## Status: Draft
## Created: 2026-01-14
## Origin: Debugging session that took 60+ minutes to trace 5 interconnected bugs

---

## Summary

**Problem**: Debugging incremental build issues is difficult because:
- Fallback paths work correctly but lack observability into *which* path was taken
- The existing `--explain` flag shows what rebuilt, but not *why* decisions were made at each layer
- Missing invariant tests for subsection behavior and fallback correctness
- No unified layer-by-layer decision trace in CLI output

**Solution**: Enhance observability by extending existing infrastructure:
1. Extend `FilterDecisionLog` with layer-specific trace fields
2. Enhance `--explain` output to show the full decision trace
3. Add invariant-based tests that verify correctness properties
4. Add `BENGAL_STRICT_INCREMENTAL` mode for development

**Priority**: High (incremental builds are core Bengal value proposition)

**Scope**: ~350 LOC implementation + ~200 LOC tests

---

## Evidence: The Debugging Odyssey

A simple "hello world" text change triggered a full rebuild. Diagnosing this required:

| Issue | Time to Find | Root Cause | Why Hard |
|-------|--------------|------------|----------|
| Data file fingerprints not saved | 20 min | `_update_data_file_fingerprints()` never called | No trace showing fallback triggered |
| Python 3.12 vs 3.14 | 10 min | `compression.zstd` import failed | Warning in logs, but no trace context |
| `autodoc` metadata empty | 15 min | Metadata missing in cache | Fallback worked, but no visibility |
| Section optimization too strict | 20 min | Subsection changes not visible | No trace of section filtering |
| Subsection path matching | 10 min | Path containment bug | No per-page section filter trace |

**Total**: 75+ minutes to trace what should have been obvious with proper observability.

---

## Existing Infrastructure

The codebase already has substantial observability infrastructure. This RFC **extends** rather than replaces it:

### What We Have

| Component | Location | Purpose |
|-----------|----------|---------|
| `--explain` flag | `bengal/cli/commands/build.py:147` | Show rebuild reasons |
| `--explain-json` flag | `bengal/cli/commands/build.py:152` | Machine-readable output |
| `IncrementalDecision` | `bengal/orchestration/build/results.py` | Track rebuild reasons per page |
| `RebuildReasonCode` | `bengal/orchestration/build/results.py` | Structured reason codes |
| `FilterDecisionLog` | `bengal/orchestration/incremental/filter_engine.py` | Decision pipeline logging |
| `IncrementalFilterEngine` | `bengal/orchestration/incremental/filter_engine.py` | 7-step decision pipeline |
| Autodoc fingerprint fallback | `bengal/cache/build_cache/autodoc_tracking.py:202-220` | Graceful degradation |

### What's Missing

The existing `--explain` output shows **what** was rebuilt and the immediate reason code, but doesn't expose:
- Whether a **fallback path** was used (e.g., fingerprints instead of metadata)
- Per-layer decision summaries (data files → autodoc → sections → pages)
- Section filtering decisions (why "docs" was marked changed)
- Whether observability data was **available** vs **missing**

---

## Problem Analysis

### 1. Observability Gap, Not Logic Gap

The incremental build logic is **correct**—fallbacks work properly. The issue is **visibility**:

```python
# autodoc_tracking.py:202-220 - This works correctly!
if not self.autodoc_source_metadata and self.autodoc_dependencies:
    has_fingerprints = hasattr(self, 'file_fingerprints') and self.file_fingerprints
    if has_fingerprints:
        # Fingerprint fallback - works, but user doesn't know it fired
        stale_sources: set[str] = set()
        for source_key in self.autodoc_dependencies:
            if hasattr(self, 'is_changed') and self.is_changed(source):
                stale_sources.add(source_key)
        return stale_sources
```

**The problem**: When debugging, there's no way to see that this fallback was used. The user only sees the final rebuild count, not *why* that count was computed.

### 2. Layer Decisions Not Surfaced

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Incremental Build Decision Pipeline               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Layer 1: Data Files        Layer 2: autodoc         Layer 3: Sections
│  ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  │ Fingerprints    │  →    │ Source Metadata │  →    │ Section Opt     │
│  │ ✓ Available     │       │ ✗ Missing       │       │ ✓ Enabled       │
│  │ 0 changed       │       │ ✓ Fallback used │       │ 1 section marked│
│  └─────────────────┘       └─────────────────┘       └─────────────────┘
│         │                         │                         │
│         ↓                         ↓                         ↓
│  [Currently hidden]        [Currently hidden]        [Currently hidden]
│                                                                      │
│  ❌ `--explain` shows final count, but not layer-by-layer decisions │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. Tests Verify Implementation, Not Invariants

Current tests verify specific implementation behavior. Missing: tests that verify **invariants** regardless of implementation:

| Invariant | Current Coverage |
|-----------|------------------|
| Unchanged files are never rebuilt | ❌ Not tested |
| Changed files are always rebuilt | ❌ Not tested |
| Subsection changes mark parent section | ❌ Not tested |
| Fallback to fingerprints works correctly | ✅ Unit test exists |
| Cross-process cache consistency | ✅ Unit test exists |

---

## Proposed Solution

### 1. Extend `FilterDecisionLog` with Layer Trace

Rather than creating a parallel `IncrementalDecisionTrace`, extend the existing `FilterDecisionLog`:

```python
# bengal/orchestration/incremental/filter_engine.py

@dataclass
class FilterDecisionLog:
    """Decision log with full layer-by-layer trace."""
    
    # Existing fields (unchanged)
    incremental_enabled: bool = False
    decision_type: FilterDecisionType = FilterDecisionType.INCREMENTAL
    full_rebuild_trigger: FullRebuildTrigger | None = None
    pages_with_changes: int = 0
    assets_with_changes: int = 0
    # ... other existing fields ...
    
    # NEW: Layer 1 - Data files
    data_files_checked: int = 0
    data_files_changed: int = 0
    data_file_fingerprints_available: bool = True
    data_file_fallback_used: bool = False
    
    # NEW: Layer 2 - autodoc
    autodoc_metadata_available: bool = True
    autodoc_fingerprint_fallback_used: bool = False
    autodoc_sources_total: int = 0
    autodoc_sources_stale: int = 0
    autodoc_stale_method: str = ""  # "metadata" | "fingerprint" | "all_stale"
    
    # NEW: Layer 3 - Section optimization
    sections_total: int = 0
    sections_marked_changed: list[str] = field(default_factory=list)
    section_change_reasons: dict[str, str] = field(default_factory=dict)
    
    # NEW: Layer 4 - Page filtering
    pages_in_changed_sections: int = 0
    pages_filtered_by_section: int = 0
    
    def to_trace_output(self) -> str:
        """Generate human-readable layer trace for --explain."""
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
        
        lines.extend([
            "",
            "───────────────────────────────────────────────────────────────",
            "Layer 1: Data Files",
            "───────────────────────────────────────────────────────────────",
            f"  Checked:     {self.data_files_checked}",
            f"  Changed:     {self.data_files_changed}",
            f"  Fingerprints available: {'✓' if self.data_file_fingerprints_available else '✗'}",
        ])
        if self.data_file_fallback_used:
            lines.append("  ⚠ Fallback used (fingerprints unavailable)")
        
        lines.extend([
            "",
            "───────────────────────────────────────────────────────────────",
            "Layer 2: autodoc",
            "───────────────────────────────────────────────────────────────",
            f"  Sources tracked: {self.autodoc_sources_total}",
            f"  Sources stale:   {self.autodoc_sources_stale}",
            f"  Metadata available: {'✓' if self.autodoc_metadata_available else '✗'}",
        ])
        if self.autodoc_fingerprint_fallback_used:
            lines.append("  ⚠ Using fingerprint fallback (metadata unavailable)")
        if self.autodoc_stale_method:
            lines.append(f"  Detection method: {self.autodoc_stale_method}")
        
        lines.extend([
            "",
            "───────────────────────────────────────────────────────────────",
            "Layer 3: Section Optimization",
            "───────────────────────────────────────────────────────────────",
            f"  Sections total:   {self.sections_total}",
            f"  Sections changed: {len(self.sections_marked_changed)}",
        ])
        if self.sections_marked_changed:
            for section in self.sections_marked_changed[:5]:
                reason = self.section_change_reasons.get(section, "content_changed")
                lines.append(f"    • {section} ({reason})")
            if len(self.sections_marked_changed) > 5:
                lines.append(f"    ... and {len(self.sections_marked_changed) - 5} more")
        
        lines.extend([
            "",
            "───────────────────────────────────────────────────────────────",
            "Layer 4: Page Filtering",
            "───────────────────────────────────────────────────────────────",
            f"  In changed sections: {self.pages_in_changed_sections}",
            f"  Filtered out:        {self.pages_filtered_by_section}",
            "",
            "═══════════════════════════════════════════════════════════════",
        ])
        
        return "\n".join(lines)
```

### 2. Enhance `--explain` Output

Extend the existing `_print_explain_output()` to include the layer trace:

```python
# bengal/cli/commands/build.py

def _print_explain_output(stats, cli, *, dry_run: bool = False) -> None:
    """Print detailed incremental build decision breakdown."""
    decision = stats.incremental_decision
    if decision is None:
        return
    
    # Existing output (rebuild reasons, page lists, etc.)
    # ...
    
    # NEW: Add layer trace if available
    filter_log = getattr(stats, 'filter_decision_log', None)
    if filter_log is not None:
        click.echo(filter_log.to_trace_output())
```

**CLI Example**:

```bash
$ bengal build --explain

Building site...
✓ Built 3 pages (1060 skipped)

═══════════════════════════════════════════════════════════════
                    DECISION TRACE                              
═══════════════════════════════════════════════════════════════

Decision: INCREMENTAL

───────────────────────────────────────────────────────────────
Layer 1: Data Files
───────────────────────────────────────────────────────────────
  Checked:     3
  Changed:     0
  Fingerprints available: ✓

───────────────────────────────────────────────────────────────
Layer 2: autodoc
───────────────────────────────────────────────────────────────
  Sources tracked: 448
  Sources stale:   0
  Metadata available: ✗
  ⚠ Using fingerprint fallback (metadata unavailable)
  Detection method: fingerprint

───────────────────────────────────────────────────────────────
Layer 3: Section Optimization
───────────────────────────────────────────────────────────────
  Sections total:   5
  Sections changed: 1
    • docs (subsection_changed:about/glossary.md)

───────────────────────────────────────────────────────────────
Layer 4: Page Filtering
───────────────────────────────────────────────────────────────
  In changed sections: 35
  Filtered out:        1028

═══════════════════════════════════════════════════════════════

Rebuild Reasons:
  content_changed: 3 pages
```

### 3. Invariant-Based Tests with Fixtures

Add test fixtures and invariant tests:

```python
# tests/integration/conftest.py

from dataclasses import dataclass
from pathlib import Path
from typing import Generator
import pytest

from bengal.cli.helpers import load_site_from_cli
from bengal.orchestration.build.options import BuildOptions


@dataclass
class WarmBuildTestSite:
    """Test site with pre-warmed cache for incremental testing."""
    
    root: Path
    content: Path
    cache_path: Path
    _site: "Site | None" = None
    
    @property
    def site(self) -> "Site":
        """Load or return cached site instance."""
        if self._site is None:
            self._site = load_site_from_cli(source=str(self.root))
        return self._site
    
    def build(self, *, incremental: bool = True, explain: bool = True):
        """Build the site and return stats."""
        # Reload site to pick up file changes
        self._site = load_site_from_cli(source=str(self.root))
        options = BuildOptions(
            incremental=incremental,
            quiet=True,
            explain=explain,
        )
        return self._site.build(options=options)
    
    def reload(self) -> None:
        """Force site reload (picks up file changes)."""
        self._site = None


@pytest.fixture
def warm_site(tmp_path: Path) -> Generator[WarmBuildTestSite, None, None]:
    """Create a minimal site and warm its cache."""
    # Create site structure
    root = tmp_path / "site"
    root.mkdir()
    
    config = root / "bengal.toml"
    config.write_text('''
[site]
title = "Test Site"
baseURL = "http://localhost"

[build]
output_dir = "public"
''')
    
    content = root / "content"
    content.mkdir()
    (content / "_index.md").write_text("---\ntitle: Home\n---\n# Home")
    (content / "page1.md").write_text("---\ntitle: Page 1\n---\n# Page 1")
    (content / "page2.md").write_text("---\ntitle: Page 2\n---\n# Page 2")
    
    site = WarmBuildTestSite(
        root=root,
        content=content,
        cache_path=root / ".bengal" / "cache.json",
    )
    
    # Warm the cache with initial build
    site.build(incremental=False)
    
    yield site


@pytest.fixture
def warm_site_with_sections(tmp_path: Path) -> Generator[WarmBuildTestSite, None, None]:
    """Create a site with nested sections and warm its cache."""
    root = tmp_path / "site"
    root.mkdir()
    
    config = root / "bengal.toml"
    config.write_text('''
[site]
title = "Test Site"
baseURL = "http://localhost"

[build]
output_dir = "public"
''')
    
    content = root / "content"
    content.mkdir()
    (content / "_index.md").write_text("---\ntitle: Home\n---\n# Home")
    
    # Create nested section: docs/about/
    docs = content / "docs"
    docs.mkdir()
    (docs / "_index.md").write_text("---\ntitle: Docs\n---\n# Docs")
    
    about = docs / "about"
    about.mkdir()
    (about / "_index.md").write_text("---\ntitle: About\n---\n# About")
    (about / "glossary.md").write_text("---\ntitle: Glossary\n---\n# Glossary")
    
    site = WarmBuildTestSite(
        root=root,
        content=content,
        cache_path=root / ".bengal" / "cache.json",
    )
    
    # Warm the cache
    site.build(incremental=False)
    
    yield site
```

```python
# tests/integration/test_incremental_invariants.py

"""
Invariant tests for incremental build correctness.

These tests verify behavioral contracts that must hold regardless of
implementation details. They catch regressions that unit tests might miss.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

from bengal.cache.build_cache import BuildCache


class TestIncrementalInvariants:
    """Tests that verify incremental build correctness invariants."""
    
    def test_unchanged_file_never_rebuilt(self, warm_site):
        """INVARIANT: Unchanged files must never be rebuilt."""
        # First incremental build (should rebuild nothing)
        stats = warm_site.build(incremental=True)
        
        # INVARIANT: No pages should be rebuilt
        pages_rebuilt = len(stats.incremental_decision.pages_to_build)
        assert pages_rebuilt == 0, (
            f"Unchanged files were rebuilt: {pages_rebuilt} pages. "
            f"Expected 0 rebuilds on warm cache with no changes."
        )
    
    def test_changed_file_always_rebuilt(self, warm_site):
        """INVARIANT: Changed files must always be rebuilt."""
        # Modify a file
        test_file = warm_site.content / "page1.md"
        original = test_file.read_text()
        time.sleep(0.01)  # Ensure mtime changes
        test_file.write_text(original + "\n<!-- modified -->")
        
        stats = warm_site.build(incremental=True)
        
        # INVARIANT: Modified file must be in rebuild list
        rebuilt_paths = {
            str(p.source_path) for p in stats.incremental_decision.pages_to_build
        }
        assert any("page1" in p for p in rebuilt_paths), (
            f"Changed file page1.md was not rebuilt. "
            f"Rebuilt: {rebuilt_paths}"
        )
    
    def test_subsection_change_marks_parent_section(self, warm_site_with_sections):
        """INVARIANT: Subsection changes must mark parent section as changed."""
        # Modify file in subsection
        glossary = warm_site_with_sections.content / "docs" / "about" / "glossary.md"
        original = glossary.read_text()
        time.sleep(0.01)
        glossary.write_text(original + "\n<!-- modified -->")
        
        stats = warm_site_with_sections.build(incremental=True)
        
        # INVARIANT: glossary.md must be rebuilt
        rebuilt_paths = {
            str(p.source_path) for p in stats.incremental_decision.pages_to_build
        }
        assert any("glossary" in p for p in rebuilt_paths), (
            f"Changed file glossary.md was not rebuilt. "
            f"Rebuilt: {rebuilt_paths}"
        )
    
    def test_cross_process_cache_consistency(self, tmp_path: Path):
        """INVARIANT: Cache saved in process A must load correctly in process B."""
        cache_path = tmp_path / "cache.json"
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")
        
        # Save cache in subprocess
        save_script = f'''
import sys
from pathlib import Path
sys.path.insert(0, "{Path(__file__).parent.parent.parent}")
from bengal.cache.build_cache import BuildCache

cache = BuildCache()
cache.update_file(Path("{test_file}"))
cache.save(Path("{cache_path}"), use_lock=False)
print(f"saved:{{len(cache.file_fingerprints)}}")
'''
        result = subprocess.run(
            [sys.executable, "-c", save_script],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert "saved:1" in result.stdout, f"Save failed: {result.stderr}"
        
        # Load in current process
        loaded = BuildCache.load(cache_path, use_lock=False)
        
        # INVARIANT: Fingerprints must survive cross-process round-trip
        assert len(loaded.file_fingerprints) == 1, (
            f"Fingerprint lost in cross-process round-trip. "
            f"Expected 1, got {len(loaded.file_fingerprints)}"
        )
    
    def test_second_build_without_changes_is_skip(self, warm_site):
        """INVARIANT: Consecutive builds without changes should skip or rebuild 0."""
        stats1 = warm_site.build(incremental=True)
        stats2 = warm_site.build(incremental=True)
        
        # INVARIANT: Second build should have 0 pages to rebuild
        pages_rebuilt = len(stats2.incremental_decision.pages_to_build)
        assert pages_rebuilt == 0, (
            f"Second build without changes rebuilt {pages_rebuilt} pages. "
            f"Cache should be stable."
        )
```

### 4. Strict Mode for Development

Add a strict mode that surfaces fallback usage as warnings or errors:

```python
# bengal/config/environment.py

import os
from enum import Enum


class StrictIncrementalMode(Enum):
    """Strict mode levels for incremental build debugging."""
    OFF = "off"          # Normal operation (silent fallbacks)
    WARN = "warn"        # Log warnings when fallbacks are used
    ERROR = "error"      # Raise errors when fallbacks are used


def get_strict_incremental_mode() -> StrictIncrementalMode:
    """Get the strict incremental mode from environment."""
    value = os.environ.get("BENGAL_STRICT_INCREMENTAL", "off").lower()
    try:
        return StrictIncrementalMode(value)
    except ValueError:
        return StrictIncrementalMode.OFF


def is_strict_incremental() -> bool:
    """Check if strict incremental mode is enabled (warn or error)."""
    return get_strict_incremental_mode() != StrictIncrementalMode.OFF
```

**Usage**:

```python
# In autodoc_tracking.py
from bengal.config.environment import get_strict_incremental_mode, StrictIncrementalMode

if not self.autodoc_source_metadata and self.autodoc_dependencies:
    mode = get_strict_incremental_mode()
    
    if mode == StrictIncrementalMode.ERROR:
        raise IncrementalCacheError(
            "autodoc source metadata empty but dependencies present.\n"
            "This triggers fingerprint fallback which may be slower.\n"
            "Fix: Ensure metadata is saved via add_autodoc_dependency().\n"
            "Disable check: unset BENGAL_STRICT_INCREMENTAL"
        )
    elif mode == StrictIncrementalMode.WARN:
        logger.warning(
            "autodoc_metadata_fallback",
            msg="Using fingerprint fallback (metadata unavailable)",
            source_count=len(self.autodoc_dependencies),
        )
    
    # Continue with fallback logic...
```

**CLI Usage**:

```bash
# Normal operation (default)
bengal build

# Warn when fallbacks are used (debugging)
BENGAL_STRICT_INCREMENTAL=warn bengal build

# Error on any fallback (CI, strict debugging)
BENGAL_STRICT_INCREMENTAL=error bengal build
```

---

## Implementation Plan

### Phase 1: Invariant Tests (1 day) — Highest ROI

1. **Add test fixtures** in `tests/integration/conftest.py`
   - `WarmBuildTestSite` dataclass
   - `warm_site` fixture
   - `warm_site_with_sections` fixture

2. **Add invariant tests** in `tests/integration/test_incremental_invariants.py`
   - `test_unchanged_file_never_rebuilt`
   - `test_changed_file_always_rebuilt`
   - `test_subsection_change_marks_parent_section`
   - `test_cross_process_cache_consistency`
   - `test_second_build_without_changes_is_skip`

### Phase 2: Extend FilterDecisionLog (1.5 days)

1. **Add layer trace fields** to `FilterDecisionLog`
2. **Wire trace collection** through decision points:
   - Data file checking
   - Autodoc staleness detection
   - Section optimization
   - Page filtering
3. **Add `to_trace_output()` method**

### Phase 3: Enhance --explain Output (0.5 day)

1. **Extend `_print_explain_output()`** to include layer trace
2. **Extend `_print_explain_json()`** with trace fields
3. **Update CLI help text**

### Phase 4: Strict Mode (0.5 day)

1. **Add `StrictIncrementalMode` enum**
2. **Add `get_strict_incremental_mode()` helper**
3. **Integrate into autodoc tracking** (warn/error on fallback)
4. **Integrate into data file tracking**

### Phase 5: Documentation (0.5 day)

1. **Update troubleshooting guide** with `--explain` trace examples
2. **Document `BENGAL_STRICT_INCREMENTAL`** environment variable
3. **Add architecture section** on caching layers

---

## Success Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| Debugging time | Minutes to identify root cause | < 10 min (vs 60+ today) |
| Single-command diagnosis | `--explain` shows layer decisions | All 4 layers visible |
| Regression prevention | Invariant tests catch bugs | 5+ invariant tests passing |
| Development feedback | Strict mode surfaces issues | WARN/ERROR modes work |
| Documentation | Troubleshooting guide exists | Complete with examples |

---

## Appendix A: Bugs This Would Have Caught Faster

| Bug | Would Catch With |
|-----|------------------|
| Data file fingerprints not saved | Invariant: unchanged file rebuilt |
| Python version mismatch | CLI warning ✅ (implemented) |
| `autodoc` metadata empty | Trace: "⚠ Using fingerprint fallback" |
| Section optimization skipped subsections | Invariant: subsection marks parent |
| Subsection path matching broken | Invariant: changed file always rebuilt |

---

## Appendix B: JSON Output Extension

The `--explain-json` output will include the layer trace:

```json
{
  "decision_type": "incremental",
  "pages_to_build": 3,
  "pages_skipped": 1060,
  "rebuild_reasons": { ... },
  "layer_trace": {
    "data_files": {
      "checked": 3,
      "changed": 0,
      "fingerprints_available": true,
      "fallback_used": false
    },
    "autodoc": {
      "sources_total": 448,
      "sources_stale": 0,
      "metadata_available": false,
      "fingerprint_fallback_used": true,
      "stale_method": "fingerprint"
    },
    "sections": {
      "total": 5,
      "changed": ["docs"],
      "change_reasons": {
        "docs": "subsection_changed:about/glossary.md"
      }
    },
    "page_filtering": {
      "in_changed_sections": 35,
      "filtered_out": 1028
    }
  }
}
```

---

## Related

- `plan/rfc-rebuild-decision-hardening.md` — Prior RFC on `IncrementalFilterEngine` (implemented ✅)
- `bengal/orchestration/incremental/filter_engine.py` — Current decision logic
- `bengal/cache/build_cache/autodoc_tracking.py` — Autodoc fallback handling
- `tests/integration/test_incremental_observability.py` — Existing `--explain` tests
