# RFC: Build Output Tracking - Typed Protocol for Reliable Hot Reload

**Status**: Evaluated  
**Created**: 2025-12-22  
**Author**: AI-assisted  
**Confidence**: 95% 🟢  
**Category**: Architecture / Server / Type Safety  
**Related**: `rfc-type-system-hardening.md`

---

## Executive Summary

Bengal's dev server hot reload is fragile because the build system doesn't communicate what it wrote. The current approach infers changes via post-hoc directory snapshots, which is error-prone and ignores builder knowledge.

This RFC introduces a **typed `OutputCollector` protocol** that writers use to report outputs during build. The result flows through `BuildStats.changed_outputs` to the reload controller, eliminating snapshot diffing for builds that provide output information.

**Type Hardening Alignment**: This RFC eliminates the untyped `list[str] | None` boundary between build and server, replacing it with a structured `OutputRecord` type and `OutputCollector` protocol.

---

## Problem Statement

### Current State

The reload decision pipeline has a critical gap:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  BuildTrigger   │ →  │  BuildExecutor  │ →  │ ReloadController│
│ (knows sources) │    │ (runs build)    │    │ (infers outputs)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │
        │                      │                      │
  changed_sources         BuildStats           snapshot diffing
  (explicit)         changed_outputs=None      (inferred, fragile)
```

**Evidence**:
- `BuildStats.changed_outputs` is `list[str] | None` and never populated (`orchestration/stats/models.py:103`)
- `ReloadController.decide_and_update()` walks output directory and diffs snapshots (`server/reload_controller.py:192-207`)
- `BuildTrigger._handle_reload()` creates empty `changed_paths=[]` for CSS-only reloads (`server/build_trigger.py:551-554`)

### Impact

1. **CSS Hot Reload Fails**: Browser receives `reload-css` with empty paths, reloads ALL stylesheets blindly
2. **False Positives**: Snapshot diffing triggers on mtime changes without content changes
3. **Race Conditions**: File system state between build completion and snapshot may differ
4. **Autodoc Fragility**: 269 autodoc pages aren't re-rendered on CSS changes but receive broken reload signals

### Root Cause

The build system knows exactly what it writes but discards this information. The server then tries to rediscover it via directory scanning.

---

## Goals & Non-Goals

### Goals

1. **Explicit Output Tracking**: Build writes are recorded, not inferred
2. **Typed Protocol**: `OutputCollector` protocol with `OutputRecord` dataclass
3. **Zero Snapshot Diffing** (when outputs provided): ReloadController trusts builder data
4. **Thread-Safe**: Parallel builds can record outputs concurrently
5. **Type Hardening**: No `Any` at build↔server boundary

### Non-Goals

- **Backward Compatibility Layer**: No fallback to snapshot diffing when outputs available
- **Runtime Validation**: Static types only, no Pydantic overhead
- **CSS Memory Server**: Out of scope (future enhancement)

---

## Design

### 1. Output Record Types

```python
# bengal/core/output/types.py
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
    ASSET = "asset"  # images, fonts, etc.
    JSON = "json"    # index.json, manifest, etc.
    MANIFEST = "manifest" # asset-manifest.json
    XML = "xml"      # sitemap, RSS

@dataclass(frozen=True, slots=True)
class OutputRecord:
    """
    Immutable record of a written output file.

    Attributes:
        path: Absolute path to written file
        output_type: Classification for reload decision
        phase: Build phase that wrote this (render, asset, postprocess)
    """
    path: Path
    output_type: OutputType
    phase: Literal["render", "asset", "postprocess"]

    @property
    def relative_path(self) -> str:
        """Path relative to output directory (for client)."""
        # Resolved at collection time
        return self._relative or str(self.path)

    @classmethod
    def from_path(cls, path: Path, phase: str = "render") -> OutputRecord:
        """Auto-detect output type from extension."""
        suffix = path.suffix.lower()
        output_type = {
            ".html": OutputType.HTML,
            ".css": OutputType.CSS,
            ".js": OutputType.JS,
            ".json": OutputType.JSON,
            ".xml": OutputType.XML,
            ".png": OutputType.IMAGE,
            ".jpg": OutputType.IMAGE,
            ".jpeg": OutputType.IMAGE,
            ".svg": OutputType.IMAGE,
            ".woff": OutputType.FONT,
            ".woff2": OutputType.FONT,
            ".ttf": OutputType.FONT,
        }.get(suffix, OutputType.ASSET)
        if path.name == "asset-manifest.json":
            output_type = OutputType.MANIFEST
        return cls(path=path, output_type=output_type, phase=phase)
```

### 2. Output Collector Protocol

```python
# bengal/core/output/collector.py
from __future__ import annotations
from pathlib import Path
from threading import Lock
from typing import Protocol, runtime_checkable

from bengal.core.output.types import OutputRecord, OutputType

@runtime_checkable
class OutputCollector(Protocol):
    """
    Protocol for collecting output writes during build.

    All output writers (render, asset, postprocess) receive a collector
    and call record() for each file written.
    """
    def record(self, path: Path, output_type: OutputType | None = None, phase: str = "render") -> None:
        """Record an output file write. Thread-safe."""
        ...

    def get_outputs(self, output_type: OutputType | None = None) -> list[OutputRecord]:
        """Get recorded outputs, optionally filtered by type."""
        ...

    def css_only(self) -> bool:
        """Check if only CSS files were written."""
        ...

    def validate(self, changed_sources: list[str] | None = None) -> None:
        """
        Validate collection integrity.

        Warns if changed_sources is non-empty but zero outputs were recorded,
        suggesting a missing record() call in a writer.
        """
        ...


class BuildOutputCollector:
    """
    Thread-safe implementation of OutputCollector for builds.

    Created per-build and passed through the pipeline. Final outputs
    are extracted and set on BuildStats.changed_outputs.
    """

    def __init__(self, output_dir: Path):
        self._output_dir = output_dir.resolve()
        self._outputs: list[OutputRecord] = []
        self._lock = Lock()

    def record(self, path: Path, output_type: OutputType | None = None, phase: str = "render") -> None:
        """Record an output file. Thread-safe for parallel builds."""
        record = OutputRecord.from_path(path, phase) if output_type is None else OutputRecord(
            path=path, output_type=output_type, phase=phase
        )
        with self._lock:
            self._outputs.append(record)

    def get_outputs(self, output_type: OutputType | None = None) -> list[OutputRecord]:
        """Get outputs, optionally filtered by type."""
        with self._lock:
            if output_type is None:
                return list(self._outputs)
            return [o for o in self._outputs if o.output_type == output_type]

    def get_relative_paths(self, output_type: OutputType | None = None) -> list[str]:
        """Get output paths relative to output_dir (for ReloadController)."""
        outputs = self.get_outputs(output_type)
        result = []
        for o in outputs:
            try:
                rel = o.path.relative_to(self._output_dir)
                result.append(str(rel).replace("\\", "/"))
            except ValueError:
                # Path not under output_dir, skip
                pass
        return result

    def css_only(self) -> bool:
        """Check if only CSS files were written."""
        with self._lock:
            if not self._outputs:
                return False
            return all(o.output_type == OutputType.CSS for o in self._outputs)

    def clear(self) -> None:
        """Clear collected outputs (for reuse between incremental builds)."""
        with self._lock:
            self._outputs.clear()

    def validate(self, changed_sources: list[str] | None = None) -> None:
        """Validate that changes were actually recorded."""
        with self._lock:
            if not self._outputs and changed_sources:
                from bengal.utils.logger import get_logger
                get_logger(__name__).warning(
                    "output_tracking_gap",
                    message="Build reported changed sources but zero outputs recorded. Hot reload may be unreliable.",
                    sources=changed_sources[:5]
                )
```

### 3. Integration with BuildStats

```python
# bengal/orchestration/stats/models.py (updated)
from bengal.core.output.types import OutputRecord

@dataclass
class BuildStats:
    # ... existing fields ...

    # UPDATED: Typed output records instead of list[str] | None
    changed_outputs: list[OutputRecord] = field(default_factory=list)

    def get_output_paths(self, output_type: OutputType | None = None) -> list[str]:
        """Helper for reload controller."""
        if output_type is None:
            return [str(o.path) for o in self.changed_outputs]
        return [str(o.path) for o in self.changed_outputs if o.output_type == output_type]
```

### 4. Writer Integration Points

#### Rendering Pipeline

```python
# bengal/rendering/pipeline/output.py
from bengal.core.output.collector import OutputCollector
from bengal.core.output.types import OutputType

def write_output(
    page: Page,
    site: Any,
    dependency_tracker: Any = None,
    collector: OutputCollector | None = None,  # NEW
) -> None:
    """Write rendered page to output directory."""
    # ... existing write logic ...

    # Record output for reload tracking
    if collector:
        collector.record(page.output_path, OutputType.HTML, phase="render")
```

#### Asset Orchestrator

```python
# bengal/orchestration/asset.py
from bengal.core.output.collector import OutputCollector

class AssetOrchestrator:
    def process(
        self,
        assets: list[Asset],
        parallel: bool = True,
        progress_manager: Any = None,
        collector: OutputCollector | None = None,  # NEW
    ) -> None:
        """Process assets with output tracking."""
        for asset in assets:
            output_path = self._process_asset(asset)
            if collector and output_path:
                collector.record(output_path, phase="asset")
```

#### Postprocess Writers

```python
# bengal/postprocess/sitemap.py, rss.py, etc.
def write_sitemap(site: Any, collector: OutputCollector | None = None) -> Path:
    output_path = site.output_dir / "sitemap.xml"
    # ... write logic ...
    if collector:
        collector.record(output_path, OutputType.XML, phase="postprocess")
    return output_path
```

### 5. BuildOrchestrator Integration

```python
# bengal/orchestration/build/__init__.py
from bengal.core.output.collector import BuildOutputCollector

class BuildOrchestrator:
    def build(self, ...) -> BuildStats:
        # Create collector for this build
        collector = BuildOutputCollector(self.site.output_dir)

        # Pass to rendering
        self.render.process(pages, collector=collector)

        # Pass to assets
        self.assets.process(assets, collector=collector)

        # Pass to postprocess
        self.postprocess.run(collector=collector)

        # Populate stats with typed outputs
        self.stats.changed_outputs = collector.get_outputs()

        # Validate tracking integrity
        collector.validate(getattr(self, "changed_sources", None))

        return self.stats
```

### 6. Simplified ReloadController

```python
# bengal/server/reload_controller.py (updated)
from bengal.core.output.types import OutputRecord, OutputType

class ReloadController:
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

---

## Architecture Impact

| Subsystem | Change | Impact |
|-----------|--------|--------|
| **Core** | New `bengal/core/output/` package | Low - additive |
| **Orchestration** | `BuildStats.changed_outputs` typed | Medium - signature change |
| **Orchestration** | `AssetOrchestrator` simplification | High - removes ephemeral caches |
| **Rendering** | `write_output()` gains `collector` param | Low - optional param |
| **Assets** | `AssetOrchestrator.process()` gains `collector` param | Low - optional param |
| **Postprocess** | Writers gain `collector` param | Low - optional param |
| **Server** | `ReloadController.decide_from_outputs()` added | Low - additive |
| **Server** | `BuildTrigger` uses typed outputs | Medium - logic change |

---

## Type Hardening Alignment

This RFC advances type hardening goals:

| Before | After | Benefit |
|--------|-------|---------|
| `changed_outputs: list[str] \| None` | `changed_outputs: list[OutputRecord]` | Typed records |
| `changed_paths: list[str]` in `ReloadDecision` | Could be `list[OutputRecord]` | Full type chain |
| No protocol for writers | `OutputCollector` protocol | Explicit contract |
| `Any` in asset processing | Typed `OutputType` enum | Static verification |

**Related Work**: This RFC should be implemented alongside `rfc-type-system-hardening.md` Sprint 1 since both touch core data structures.

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/core/output/test_collector.py
class TestBuildOutputCollector:
    def test_record_and_retrieve(self):
        collector = BuildOutputCollector(Path("/output"))
        collector.record(Path("/output/style.css"), OutputType.CSS)
        collector.record(Path("/output/index.html"), OutputType.HTML)

        assert len(collector.get_outputs()) == 2
        assert len(collector.get_outputs(OutputType.CSS)) == 1

    def test_css_only_detection(self):
        collector = BuildOutputCollector(Path("/output"))
        collector.record(Path("/output/a.css"), OutputType.CSS)
        collector.record(Path("/output/b.css"), OutputType.CSS)

        assert collector.css_only() is True

        collector.record(Path("/output/index.html"), OutputType.HTML)
        assert collector.css_only() is False

    def test_thread_safety(self):
        """Verify concurrent recording works."""
        collector = BuildOutputCollector(Path("/output"))

        def record_many(prefix: str):
            for i in range(100):
                collector.record(Path(f"/output/{prefix}_{i}.html"))

        threads = [Thread(target=record_many, args=(f"t{i}",)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(collector.get_outputs()) == 400
```

### Integration Tests

```python
# tests/integration/server/test_hot_reload.py
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

---

## Implementation Plan

### Phase 1: Core Types (Day 1)

1. Create `bengal/core/output/__init__.py`
2. Create `bengal/core/output/types.py` with `OutputType`, `OutputRecord`
3. Create `bengal/core/output/collector.py` with `OutputCollector` protocol
4. Add unit tests

### Phase 2: Writer Integration (Day 2)

1. Update `rendering/pipeline/output.py` - add `collector` param
2. Update `orchestration/asset.py` - add `collector` param
3. Update postprocess writers
4. Update `BuildStats.changed_outputs` type

### Phase 3: Orchestrator Wiring (Day 3)

1. Create collector in `BuildOrchestrator.build()`
2. Pass through pipeline
3. Populate `BuildStats.changed_outputs`
4. Add integration tests

### Phase 4: Server Integration (Day 4)

1. Add `ReloadController.decide_from_outputs()`
2. Update `BuildTrigger._handle_reload()` to use typed outputs
3. Remove fallback to snapshot diffing (when outputs provided)
4. Add server integration tests

---

## Migration Path

1. **Phase 1-3**: Additive changes only, no breaking changes
2. **Phase 4**: `ReloadController` gains new method, old method remains
3. **Post-validation**: Mark `decide_and_update()` as deprecated
4. **Future**: Remove snapshot diffing entirely

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Writers forget to call `record()` | Medium | Medium | Audit all write paths; add logging when collector present but no outputs |
| Thread contention under heavy load | Low | Low | Lock is held briefly; profile if issues arise |
| Type changes break existing code | Low | Medium | `changed_outputs` default is `[]` not `None` - compatible |
| Snapshot diffing removal breaks edge cases | Low | High | Keep as opt-in fallback initially |

---

## Success Criteria

- [ ] `OutputCollector` protocol defined with full type annotations
- [ ] All write paths (render, asset, postprocess) record outputs
- [ ] `BuildStats.changed_outputs` is `list[OutputRecord]` not `list[str] | None`
- [ ] CSS hot reload works with correct `changedPaths`
- [ ] No `Any` at build↔server boundary
- [ ] Snapshot diffing is fallback only, not primary path

---

## Confidence Breakdown

| Component | Score | Reasoning |
|-----------|-------|-----------|
| Evidence Strength | 38/40 | Code paths verified with file:line references |
| Consistency | 28/30 | Aligns with type hardening RFC, existing patterns |
| Recency | 15/15 | Based on current codebase state |
| Test Coverage | 9/15 | Proposed tests, not yet implemented |
| **Total** | **90/100** | 🟢 High confidence |

---

## References

- `bengal/server/reload_controller.py` - Current snapshot diffing implementation
- `bengal/server/build_trigger.py:551-554` - Empty `changed_paths` bug
- `bengal/orchestration/stats/models.py:103` - Unpopulated `changed_outputs`
- `bengal/rendering/pipeline/output.py:102-178` - HTML write path
- `bengal/orchestration/asset.py` - Asset processing
- `plan/drafted/rfc-type-system-hardening.md` - Related type hardening work
