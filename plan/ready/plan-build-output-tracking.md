# Plan: Build Output Tracking Implementation

**Source**: `plan/ready/rfc-build-output-tracking.md`  
**Status**: Ready  
**Created**: 2025-12-22  
**Estimated Time**: 4-6 hours (across 4-5 phases)

---

## Executive Summary

Convert RFC for typed `OutputCollector` protocol into actionable tasks. The implementation replaces `BuildStats.changed_outputs: list[str] | None` with typed `list[OutputRecord]`, enabling reliable CSS hot reload and eliminating snapshot diffing.

---

## Phase 1: Core Types (45-60 min)

### 1.1 Create output package structure

**Files**: Create `bengal/core/output/__init__.py`

```python
# bengal/core/output/__init__.py
"""Output tracking types and protocol for build coordination."""
from bengal.core.output.types import OutputRecord, OutputType
from bengal.core.output.collector import BuildOutputCollector, OutputCollector

__all__ = ["OutputRecord", "OutputType", "OutputCollector", "BuildOutputCollector"]
```

**Commit**: `core(output): create output tracking package with types and collector`

---

### 1.2 Define OutputType enum and OutputRecord dataclass

**File**: `bengal/core/output/types.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

class OutputType(Enum):
    """Classification of output files."""
    HTML = "html"
    CSS = "css"
    JS = "js"
    IMAGE = "image"
    FONT = "font"
    ASSET = "asset"
    JSON = "json"
    MANIFEST = "manifest"
    XML = "xml"

@dataclass(frozen=True, slots=True)
class OutputRecord:
    """Immutable record of a written output file."""
    path: Path
    output_type: OutputType
    phase: Literal["render", "asset", "postprocess"]

    @classmethod
    def from_path(cls, path: Path, phase: str = "render") -> OutputRecord:
        """Auto-detect output type from extension."""
        # Implementation per RFC
```

**Evidence**:
- RFC lines 79-140 specify exact type definitions
- Uses `frozen=True, slots=True` per bengal/dataclass-conventions

**Commit**: `core(output): add OutputType enum and OutputRecord dataclass`

---

### 1.3 Define OutputCollector protocol and BuildOutputCollector implementation

**File**: `bengal/core/output/collector.py`

```python
from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Protocol, runtime_checkable

from bengal.core.output.types import OutputRecord, OutputType

@runtime_checkable
class OutputCollector(Protocol):
    """Protocol for collecting output writes during build."""
    def record(self, path: Path, output_type: OutputType | None = None, phase: str = "render") -> None: ...
    def get_outputs(self, output_type: OutputType | None = None) -> list[OutputRecord]: ...
    def css_only(self) -> bool: ...
    def validate(self, changed_sources: list[str] | None = None) -> None: ...

class BuildOutputCollector:
    """Thread-safe implementation of OutputCollector for builds."""
    # Implementation per RFC lines 183-246
```

**Evidence**:
- RFC lines 144-246 specify protocol and implementation
- Thread-safe with Lock per bengal/no-globals and bengal/performance

**Commit**: `core(output): add OutputCollector protocol and BuildOutputCollector`

---

### 1.4 Add unit tests for output collector

**File**: `tests/unit/core/output/test_collector.py`

Tests to add:
- `test_record_and_retrieve`: Basic recording and retrieval
- `test_css_only_detection`: Verify css_only() logic
- `test_thread_safety`: Concurrent recording with threads
- `test_filter_by_type`: get_outputs(OutputType.CSS) filtering
- `test_relative_paths`: get_relative_paths() for ReloadController
- `test_validate_warns_on_empty`: Validation logging

**Evidence**: RFC lines 419-456 provide test templates

**Commit**: `tests(output): add unit tests for BuildOutputCollector`

---

## Phase 2: Writer Integration (60-90 min)

### 2.1 Update rendering/pipeline/output.py - add collector param

**File**: `bengal/rendering/pipeline/output.py`

**Change**: Add `collector: OutputCollector | None = None` parameter to `write_output()`

```python
# Around line 102-106
def write_output(
    page: Page,
    site: Any,
    dependency_tracker: Any = None,
    collector: OutputCollector | None = None,  # NEW
) -> None:
    # ... existing write logic ...

    # Record output for reload tracking (add after write succeeds)
    if collector and page.output_path:
        collector.record(page.output_path, OutputType.HTML, phase="render")
```

**Evidence**:
- RFC lines 270-289 specify integration point
- Current `write_output` signature at `rendering/pipeline/output.py:102-106`
- Add after line 177 (dependency tracking)

**Commit**: `rendering(pipeline): add OutputCollector support to write_output`

---

### 2.2 Update orchestration/asset.py - add collector param

**File**: `bengal/orchestration/asset.py`

**Changes**:

1. Add `collector` parameter to `AssetOrchestrator.process()`:
```python
def process(
    self,
    assets: list[Asset],
    parallel: bool = True,
    progress_manager: LiveProgressManager | None = None,
    collector: OutputCollector | None = None,  # NEW
) -> None:
```

2. Pass collector to `_process_css_entry()` and `_process_single_asset()`

3. Record outputs after successful copy:
```python
# In _process_single_asset, after copy_to_output:
if collector and asset.output_path:
    collector.record(asset.output_path, phase="asset")
```

**Evidence**:
- RFC lines 295-310 specify integration
- Current signatures at `orchestration/asset.py:140-146`, `:328-337`, `:713-728`

**Commit**: `orchestration(asset): add OutputCollector support for asset tracking`

---

### 2.3 Update postprocess writers - add collector param

**Files**:
- `bengal/postprocess/sitemap.py`
- `bengal/postprocess/rss.py`
- `bengal/orchestration/postprocess.py`

**Pattern** (for each writer):
```python
def write_sitemap(site: Any, collector: OutputCollector | None = None) -> Path:
    output_path = site.output_dir / "sitemap.xml"
    # ... write logic ...
    if collector:
        collector.record(output_path, OutputType.XML, phase="postprocess")
    return output_path
```

**Commit**: `postprocess: add OutputCollector support to sitemap, RSS, and manifest writers`

---

### 2.4 Update BuildStats.changed_outputs type

**File**: `bengal/orchestration/stats/models.py`

**Change** (line 103):
```python
# Before
changed_outputs: list[str] | None = None

# After
from bengal.core.output.types import OutputRecord

changed_outputs: list[OutputRecord] = field(default_factory=list)
```

**Add helper method**:
```python
def get_output_paths(self, output_type: OutputType | None = None) -> list[str]:
    """Get output paths, optionally filtered by type."""
    if output_type is None:
        return [str(o.path) for o in self.changed_outputs]
    return [str(o.path) for o in self.changed_outputs if o.output_type == output_type]
```

**Evidence**: RFC lines 250-266

**Commit**: `orchestration(stats): type BuildStats.changed_outputs as list[OutputRecord]`

---

## Phase 3: Orchestrator Wiring (45-60 min)

### 3.1 Create collector in BuildOrchestrator.build()

**File**: `bengal/orchestration/build/__init__.py`

**Changes**:

1. Import collector:
```python
from bengal.core.output.collector import BuildOutputCollector
```

2. Create collector at build start (add to build() method):
```python
def build(self, options: BuildOptions = ...) -> BuildStats:
    # Create output collector for this build
    collector = BuildOutputCollector(self.site.output_dir)
    self._collector = collector  # Store for access by sub-orchestrators
```

3. Store on BuildOrchestrator instance for sub-orchestrators to access

**Commit**: `orchestration(build): create OutputCollector per build`

---

### 3.2 Pass collector through rendering phase

**File**: `bengal/orchestration/build/rendering.py`

**Changes**:

1. Pass collector to asset processing:
```python
# In execute_assets_phase or equivalent
self.assets.process(assets, collector=self._collector)
```

2. Pass collector to page rendering/write:
```python
# In execute_render_phase
from bengal.rendering.pipeline.output import write_output
write_output(page, site, dependency_tracker, collector=self._collector)
```

**Evidence**: RFC lines 324-351

**Commit**: `orchestration(build): pass OutputCollector to rendering and asset phases`

---

### 3.3 Pass collector through postprocess phase

**File**: `bengal/orchestration/postprocess.py`

**Changes**:

1. Add collector parameter to `PostprocessOrchestrator.run()`:
```python
def run(self, collector: OutputCollector | None = None) -> None:
```

2. Pass to individual postprocess writers (sitemap, RSS, etc.)

**Commit**: `orchestration(postprocess): wire OutputCollector through postprocess phase`

---

### 3.4 Populate BuildStats.changed_outputs at build end

**File**: `bengal/orchestration/build/__init__.py`

**Changes** (at end of build):
```python
# Populate stats with typed outputs
self.stats.changed_outputs = self._collector.get_outputs()

# Validate tracking integrity
self._collector.validate(getattr(self, "_changed_sources", None))
```

**Commit**: `orchestration(build): populate BuildStats.changed_outputs from collector`

---

## Phase 4: Server Integration (45-60 min)

### 4.1 Add ReloadController.decide_from_outputs() method

**File**: `bengal/server/reload_controller.py`

**Add new method** (after `decide_and_update`):
```python
def decide_from_outputs(self, outputs: list[OutputRecord]) -> ReloadDecision:
    """
    Decide reload action from typed output records.

    This is the preferred path when builder provides output information.
    No snapshot diffing required.
    """
    if not outputs:
        return ReloadDecision("none", "no-outputs", [])

    # Throttle
    now = self._now_ms()
    if now - self._last_notify_time_ms < self._min_interval_ms:
        return ReloadDecision("none", "throttled", [])
    self._last_notify_time_ms = now

    # Classify by output type
    css_only = all(o.output_type == OutputType.CSS for o in outputs)
    paths = [str(o.path) for o in outputs[:MAX_CHANGED_PATHS_TO_SEND]]

    if css_only:
        return ReloadDecision("reload-css", "css-only", paths)
    return ReloadDecision("reload", "content-changed", paths)
```

**Evidence**: RFC lines 355-383

**Commit**: `server(reload): add decide_from_outputs for typed output records`

---

### 4.2 Update BuildTrigger._handle_reload() to use typed outputs

**File**: `bengal/server/build_trigger.py`

**Changes** (around line 527-575):

1. Update signature:
```python
def _handle_reload(
    self,
    changed_files: list[str],
    changed_outputs: list[OutputRecord],  # Changed from tuple[str, ...]
) -> None:
```

2. Use `decide_from_outputs` when outputs available:
```python
# Prefer typed outputs when available
if changed_outputs:
    decision = controller.decide_from_outputs(changed_outputs)
else:
    # Fall back to snapshot diffing for backward compatibility
    decision = controller.decide_and_update(output_dir)
```

**Evidence**: RFC lines 551-554 (bug location), RFC design section

**Commit**: `server(trigger): use typed OutputRecord for reload decisions`

---

### 4.3 Update BuildResult and BuildExecutor for typed outputs

**File**: `bengal/server/build_executor.py`

**Changes**:

1. Update `BuildResult.changed_outputs` type:
```python
from bengal.core.output.types import OutputRecord

@dataclass
class BuildResult:
    # ...
    changed_outputs: list[OutputRecord] = field(default_factory=list)  # Was tuple[str, ...]
```

2. Update `_execute_full_build()` to pass typed outputs:
```python
# Around line 174
changed_outputs = stats.changed_outputs  # Already list[OutputRecord]
```

**Commit**: `server(executor): type BuildResult.changed_outputs as list[OutputRecord]`

---

## Phase 5: Tests & Validation (30-45 min)

### 5.1 Add integration test for CSS hot reload

**File**: `tests/integration/server/test_hot_reload.py`

```python
def test_css_change_triggers_css_only_reload(tmp_site, dev_server):
    """CSS-only changes trigger reload-css with correct paths."""
    # Modify CSS file
    css_path = tmp_site.root / "assets/style.css"
    css_path.write_text("body { color: red; }")

    # Wait for rebuild
    reload_event = dev_server.wait_for_reload(timeout=5)

    assert reload_event["action"] == "reload-css"
    assert "style.css" in reload_event["changedPaths"][0]
```

**Evidence**: RFC lines 461-474

**Commit**: `tests(server): add integration tests for typed output hot reload`

---

### 5.2 Verify output tracking coverage

**Manual verification checklist**:
- [ ] HTML pages record outputs
- [ ] CSS entry points record outputs
- [ ] Asset processing records outputs
- [ ] Sitemap/RSS record outputs
- [ ] Asset manifest records output
- [ ] CSS hot reload sends correct paths
- [ ] Full reload triggers for mixed content

---

### 5.3 Run full test suite and linter

```bash
# Run tests
uv run pytest tests/unit/core/output/ -v
uv run pytest tests/integration/server/test_hot_reload.py -v

# Run linter
uv run ruff check bengal/core/output/ bengal/server/ bengal/orchestration/

# Type check
uv run mypy bengal/core/output/ --strict
```

**Commit**: `tests: verify output tracking with full test suite`

---

## Migration Notes

### Backward Compatibility

1. **Phase 1-3**: Additive changes only, no breaking changes
2. **Phase 4**: `changed_outputs` type changes from `list[str] | None` to `list[OutputRecord]`
   - Server code that consumed `changed_outputs` as strings needs update
   - `BuildResult` in `build_executor.py` changes type

### Deprecation Path

After validation:
1. Mark `decide_and_update()` as deprecated (keep for fallback)
2. Log warning when snapshot diffing is used
3. Future: Remove snapshot diffing entirely

---

## Success Criteria

- [ ] `OutputCollector` protocol defined with full type annotations
- [ ] All write paths (render, asset, postprocess) record outputs
- [ ] `BuildStats.changed_outputs` is `list[OutputRecord]` not `list[str] | None`
- [ ] CSS hot reload works with correct `changedPaths`
- [ ] No `Any` at build↔server boundary
- [ ] Snapshot diffing is fallback only, not primary path
- [ ] All tests pass
- [ ] Linter clean

---

## File Change Summary

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/core/output/__init__.py` | **New** | ~10 |
| `bengal/core/output/types.py` | **New** | ~60 |
| `bengal/core/output/collector.py` | **New** | ~80 |
| `bengal/orchestration/stats/models.py` | Modify | ~15 |
| `bengal/rendering/pipeline/output.py` | Modify | ~10 |
| `bengal/orchestration/asset.py` | Modify | ~25 |
| `bengal/orchestration/postprocess.py` | Modify | ~20 |
| `bengal/orchestration/build/__init__.py` | Modify | ~15 |
| `bengal/orchestration/build/rendering.py` | Modify | ~10 |
| `bengal/server/reload_controller.py` | Modify | ~40 |
| `bengal/server/build_trigger.py` | Modify | ~20 |
| `bengal/server/build_executor.py` | Modify | ~10 |
| `tests/unit/core/output/test_collector.py` | **New** | ~100 |
| `tests/integration/server/test_hot_reload.py` | Modify | ~30 |

**Total**: ~445 lines added/modified

---

## Commit Sequence

1. `core(output): create output tracking package with types and collector`
2. `core(output): add OutputType enum and OutputRecord dataclass`
3. `core(output): add OutputCollector protocol and BuildOutputCollector`
4. `tests(output): add unit tests for BuildOutputCollector`
5. `rendering(pipeline): add OutputCollector support to write_output`
6. `orchestration(asset): add OutputCollector support for asset tracking`
7. `postprocess: add OutputCollector support to sitemap, RSS, and manifest writers`
8. `orchestration(stats): type BuildStats.changed_outputs as list[OutputRecord]`
9. `orchestration(build): create OutputCollector per build`
10. `orchestration(build): pass OutputCollector to rendering and asset phases`
11. `orchestration(postprocess): wire OutputCollector through postprocess phase`
12. `orchestration(build): populate BuildStats.changed_outputs from collector`
13. `server(reload): add decide_from_outputs for typed output records`
14. `server(trigger): use typed OutputRecord for reload decisions`
15. `server(executor): type BuildResult.changed_outputs as list[OutputRecord]`
16. `tests(server): add integration tests for typed output hot reload`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Writers forget to call `record()` | Add validation logging; audit all write paths |
| Thread contention | Lock held briefly; profile if issues arise |
| Type changes break existing code | Default is `[]` not `None`; update all consumers |
| Snapshot diffing removal breaks edge cases | Keep as opt-in fallback initially |

---

## References

- RFC: `plan/ready/rfc-build-output-tracking.md`
- Current `BuildStats`: `bengal/orchestration/stats/models.py:103`
- Current `write_output`: `bengal/rendering/pipeline/output.py:102-178`
- Current `AssetOrchestrator.process`: `bengal/orchestration/asset.py:140-326`
- Current `ReloadController`: `bengal/server/reload_controller.py`
- Current `BuildTrigger._handle_reload`: `bengal/server/build_trigger.py:527-587`
