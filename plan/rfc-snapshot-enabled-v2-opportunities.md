# RFC: Snapshot-Enabled v2 Opportunities

**Status**: Draft  
**Created**: 2026-01-18  
**Author**: AI Assistant  
**Depends On**: `rfc-bengal-snapshot-engine.md` (implemented)  
**Confidence**: 82% 🟡 (performance claims need benchmarking)  
**Category**: Architecture / Performance / Incremental Builds

---

## Executive Summary

With the Snapshot Engine (v2 architecture) now in place, Bengal has established a **clear phase boundary** between mutation and read-only operations. This unlocks a series of architectural improvements that were previously difficult or impossible:

| Opportunity | Impact | Effort |
|-------------|--------|--------|
| Effect-Traced Incremental Builds | -13 detector classes, unified deps | 50-70 hours |
| Incremental Snapshot Updates | O(changed) vs O(all) rebuilds | 15-20 hours |
| Speculative Rendering | Near-instant HMR | 20-30 hours |
| Service Extraction | -7 mixins, testable services | 40-60 hours |
| Template Dependency Snapshots | Instant template→page mapping | 10-15 hours |
| Config Snapshot | Typed, frozen config | 20-30 hours |

**Key Insight**: The snapshot boundary transforms Bengal's architecture from "shared mutable state with careful locking" to "pure functions over immutable data"—enabling true free-threading parallelism and dramatically simpler code.

---

## Goals

1. **Leverage the snapshot boundary** — Exploit the mutation/read-only phase split for architectural improvements
2. **Reduce complexity** — Delete redundant detector classes, mixins, and wrapper patterns
3. **Improve incremental build performance** — Single-file changes should rebuild in <100ms
4. **Enable free-threading parallelism** — All render-phase operations must be lock-free
5. **Improve testability** — Services accept frozen snapshots → deterministic, easy to mock

## Non-Goals

1. **Plugin system** — Third-party extensibility is out of scope (separate RFC)
2. **AST-level incremental parsing** — We reparse entire files; block-level diffing is optimization-only
3. **Distributed builds** — Multi-machine parallelism not addressed here
4. **Breaking API changes** — Template APIs (`page.title`, `site.pages`) must remain stable
5. **Config schema redesign** — `ConfigSnapshot` types existing keys; new config options are separate RFC
6. **Dev server rewrite** — Speculative rendering improves HMR within current server architecture

---

## Background: What Snapshots Enable

The Snapshot Engine creates a clear architectural boundary:

```
┌──────────────────────────────┐       ┌──────────────────────────────┐
│     MUTATION PHASE           │       │     READ-ONLY PHASE          │
│     (Phases 1-5)             │──────▶│     (Phases 6-21)            │
│                              │       │                              │
│  • Mutable Site/Page/Section │       │  • Frozen SiteSnapshot       │
│  • add_page(), add_subsec()  │       │  • Pure render functions     │
│  • Locks for thread safety   │       │  • Zero lock contention      │
│  • @cached_property races    │       │  • Pre-computed everything   │
└──────────────────────────────┘       └──────────────────────────────┘
                                 ▲
                                 │
                          snapshot()
                          ONE TIME
                          O(n) pages
```

This phase boundary provides:

1. **Thread-safety by construction** — Frozen dataclasses cannot race
2. **Pure functions** — `render(PageSnapshot) → HTML` with no side effects
3. **Explicit dependencies** — Effects declare inputs/outputs
4. **Trivial caching** — Immutable data is safely cacheable forever
5. **Testable architecture** — Snapshot in → deterministic output

---

## Opportunity 1: Effect-Traced Incremental Builds

### Problem

Bengal currently has **13 detector classes** in `bengal/orchestration/incremental/`:

```
bengal/orchestration/incremental/
├── block_detector.py      # Block-level change detection
├── cache_manager.py       # Cache coordination
├── cascade_tracker.py     # Cascade dependency tracking
├── cleanup.py             # Orphan cleanup
├── data_detector.py       # data/ file changes
├── file_detector.py       # Page/asset file changes
├── orchestrator.py        # Build coordination
├── rebuild_decision.py    # Rebuild logic
├── rebuild_filter.py      # Filter changed pages
├── taxonomy_detector.py   # Taxonomy changes
├── template_detector.py   # Template changes
├── version_detector.py    # Version file changes
└── __init__.py
```

Each implements its own "what changed → what rebuilds" logic with **~4,000 lines** of bespoke detection code.

### Solution: Declarative Effects

With snapshots, every render operation becomes a pure function that can declare its effects:

```python
@dataclass(frozen=True, slots=True)
class Effect:
    """
    Declarative effect of a build operation.

    Replaces 13 detector classes with one unified model.
    """
    outputs: frozenset[Path]           # Files this operation produces
    depends_on: frozenset[Path | str]  # Files/keys this operation reads
    invalidates: frozenset[str]        # Cache keys to clear if inputs change


class EffectTracer:
    """
    Unified dependency tracking.

    Thread-safe because it only reads frozen SiteSnapshot.
    """

    def record(self, effect: Effect) -> None:
        """Record an effect during rendering."""
        ...

    def invalidated_by(self, changed: set[Path]) -> set[str]:
        """What cache keys are invalidated by these changes?"""
        ...

    def outputs_needing_rebuild(self, changed: set[Path]) -> set[Path]:
        """Which outputs need rebuilding? (transitive)"""
        ...


# Usage: Effects are pure functions of immutable data
def render_page_with_effects(
    page: PageSnapshot,
    snapshot: SiteSnapshot,
    tracer: EffectTracer,
) -> str:
    """Render page and record its effect."""
    # Collect dependencies (all from frozen snapshot)
    deps = {
        page.source_path,
        Path(page.template_name),
        *get_template_includes(page.template_name),
    }

    # Render (pure function)
    html = render_template(page.template_name, page=page, site=snapshot)

    # Record effect
    tracer.record(Effect(
        outputs=frozenset({page.output_path}),
        depends_on=frozenset(deps),
        invalidates=frozenset({f"page:{page.href}"}),
    ))

    return html
```

### Why Snapshots Enable This

| Without Snapshots | With Snapshots |
|-------------------|----------------|
| Detectors track mutable state | Effects track frozen snapshot |
| Complex locking for thread safety | Lock-free (immutable data) |
| Race conditions between detect/render | Pure functions, deterministic |
| 13 files with bespoke logic | 1 unified `EffectTracer` |

### Detector Replacement Mapping

| Current Detector | Effect-Based Replacement |
|------------------|-------------------------|
| `file_detector.py` | `Effect.depends_on` includes source file |
| `template_detector.py` | `Effect.depends_on` includes layout + includes |
| `cascade_tracker.py` | `Effect.depends_on` includes parent `_index.md` |
| `taxonomy_detector.py` | `Effect.invalidates` includes taxonomy keys |
| `data_detector.py` | `Effect.depends_on` includes `data/*.yaml` paths |
| `version_detector.py` | `Effect.depends_on` includes version file |
| `block_detector.py` | Integrated as a specialized content-hash optimizer |

### block_detector.py Integration

While 12 detectors are fully replaced by the declarative Effect model, `block_detector.py` performs specialized content-aware diffing (e.g., ignoring frontmatter changes for content-only rebuilds). It will be refactored into a **BlockDiffService** used by the `EffectTracer` to determine if a dependency change actually necessitates a re-render.

### Design Alternatives

#### Option A: Full Effect System (Recommended)

Replace all detectors with unified `EffectTracer` as described above.

| Pros | Cons |
|------|------|
| Single unified model | Larger upfront effort (50-70 hours) |
| Transitive deps automatic | Must migrate all detection logic |
| Debug tooling (`--show-effects`) | Risk of regression during migration |
| Scales to new content types | Learning curve for contributors |

#### Option B: Gradual Detector Consolidation

Keep detector pattern but consolidate into fewer files with shared infrastructure.

```python
# Instead of 13 separate detectors, 3 consolidated:
# - ContentDetector (pages, data, versions)
# - StructureDetector (sections, taxonomies, cascades)  
# - AssetDetector (templates, static assets)
```

| Pros | Cons |
|------|------|
| Lower risk (incremental) | Still ~3 detectors with separate logic |
| Preserves working code | No transitive dep tracking |
| Easier to review | No debug visualization |
| ~30 hours effort | Technical debt remains |

#### Option C: Hybrid (Effect Tracking + Detectors as Adapters)

Introduce `Effect` type but keep detectors as adapters that produce effects.

```python
class FileDetector:
    def detect(self, changed: set[Path]) -> list[Effect]:
        """Adapter: existing logic → Effect output."""
        ...
```

| Pros | Cons |
|------|------|
| Incremental migration path | More code during transition |
| Validates Effect model early | Two mental models temporarily |
| ~40 hours effort | Must eventually delete adapters |

**Recommendation**: Option A (Full Effect System) for long-term simplicity, but Option C is viable if risk tolerance is low.

### Impact

- **-13 detector files** → 1 `EffectTracer`
- **-~4,000 lines** of bespoke detection logic
- **Debuggable**: `bengal build --show-effects` visualizes dependency graph
- **Transitive deps**: If A depends on B and B changed, A rebuilds automatically

### Estimated Effort: 50-70 hours (Option A) / 30 hours (Option B) / 40 hours (Option C)

---

## Opportunity 2: Incremental Snapshot Updates

### Problem

Current snapshot creation is O(n) for all pages:

```python
def create_site_snapshot(site: Site) -> SiteSnapshot:
    """O(n) where n = total pages + sections."""
    for page in site.pages:  # ALL pages
        page_cache[id(page)] = _snapshot_page_initial(page, site)
    ...
```

For a 1000-page site: ~50ms per build (acceptable but wasteful for single-file changes).

### Solution: Structural Sharing

Frozen dataclasses enable **structural sharing**—unchanged portions reference the same objects:

```python
def update_snapshot(
    old: SiteSnapshot,
    changed_paths: set[Path],
) -> SiteSnapshot:
    """
    Incrementally update snapshot for changed files.

    O(changed) instead of O(all).

    Args:
        old: Previous build's snapshot
        changed_paths: Files that changed since last build

    Returns:
        New snapshot with structural sharing for unchanged data
    """
    # Identify affected pages
    affected_pages = {
        page for page in old.pages
        if page.source_path in changed_paths
    }

    # Identify affected sections (pages' parents)
    affected_sections = {
        page.section for page in affected_pages
        if page.section is not None
    }

    # Reuse unchanged pages (same tuple reference)
    new_pages = tuple(
        _re_snapshot_page(page) if page in affected_pages else page
        for page in old.pages
    )

    # Reuse unchanged sections
    new_sections = _update_section_tree(
        old.root_section,
        affected_sections,
        {p.source_path: p for p in new_pages},
    )

    return SiteSnapshot(
        pages=new_pages,
        sections=new_sections,
        # Config/menus unchanged → reuse reference
        config=old.config,
        menus=old.menus,
        ...
    )
```

### Why Snapshots Enable This

| Without Snapshots | With Snapshots |
|-------------------|----------------|
| Mutable objects → can't reuse safely | Frozen → safe to share references |
| Must deep-copy to avoid mutation | Structural sharing is free |
| O(n) always | O(changed) for incremental |

### Performance Impact

> **Note**: Performance figures are estimates. Baseline measurements needed before implementation.

| Scenario | Current (est.) | With Structural Sharing |
|----------|----------------|-------------------------|
| Full build (1000 pages) | ~50ms | ~50ms (same) |
| 1 file changed | ~50ms | **<1ms** |
| 10 files changed | ~50ms | **~5ms** |
| Section index changed | ~50ms | **~10ms** (section + children) |

**Validation Required**:
```bash
# Measure current snapshot creation time
bengal build --profile 2>&1 | grep -i snapshot
```

### Estimated Effort: 15-20 hours

---

## Opportunity 3: Speculative Rendering

### Problem

Dev server HMR latency includes:

```
File change detected
    → Determine what changed (~10ms)
    → Compute affected pages (~20ms)
    → Re-parse affected (~50ms)
    → Re-render affected (~100ms)
    → Write to disk (~20ms)
    → Signal browser (~5ms)
────────────────────────────────
Total: ~200ms minimum
```

### Solution: Start Work Before Analysis Completes

With `content_hash` on every `PageSnapshot`, we can speculate:

```python
async def speculative_hmr(
    file_change: Path,
    snapshot: SiteSnapshot,
) -> None:
    """
    Start rendering speculatively while computing exact rebuild set.

    Uses content_hash to validate speculation after the fact.
    """
    # ... implementation logic ...
```

#### Shadow Mode Validation

To avoid wasting CPU on poor predictions, we will first implement a **Shadow Mode** for `predict_affected()`. In this mode:
1. Both prediction and exact computation run.
2. Accuracy is logged (`[PREDICT] Accuracy: 94% (Hit: index.md, Miss: sidebar.html)`).
3. Speculative rendering only activates when prediction confidence (historical accuracy) > 85%.


def predict_affected(file_path: Path, snapshot: SiteSnapshot) -> set[PageSnapshot]:
    """
    Fast heuristic prediction of affected pages.

    Accuracy: ~90% (based on file type and location)
    Speed: <1ms (vs ~30ms for exact computation)
    """
    if file_path.suffix == ".md":
        # Content file → likely just this page
        return {p for p in snapshot.pages if p.source_path == file_path}

    elif file_path.suffix in (".html", ".jinja"):
        # Template → all pages using this template
        template_name = file_path.name
        return set(snapshot.template_groups.get(template_name, ()))

    elif file_path.suffix in (".css", ".js"):
        # Asset → all pages (fingerprints change)
        return set(snapshot.pages)

    else:
        # Unknown → conservative (all pages)
        return set(snapshot.pages)
```

### Why Snapshots Enable This

| Without Snapshots | With Snapshots |
|-------------------|----------------|
| Must wait for mutation phase | Snapshot already has all data |
| content_hash computed on demand | content_hash pre-computed |
| template_groups computed per-access | template_groups pre-indexed |

### Performance Impact

> **Note**: Performance figures are estimates. Baseline HMR latency measurements needed.

| Scenario | Current (est.) | With Speculation |
|----------|----------------|------------------|
| Single MD file change | ~200ms | **~80ms** |
| Template change | ~500ms | **~200ms** |
| CSS change | ~1000ms | **~400ms** |

**Key**: Speculation overlaps computation with rendering, hiding latency.

**Validation Required**:
```bash
# Measure current HMR latency
bengal serve --debug  # Observe file-change-to-reload timestamps
```

### Estimated Effort: 20-30 hours

---

## Opportunity 4: Service Extraction

### Problem

`Site` is a god object with 7 mixins:

```python
# bengal/core/site/core.py:77-85
@dataclass
class Site(
    SitePropertiesMixin,      # 800 lines of property accessors
    PageCachesMixin,          # Cached page lists
    SiteFactoriesMixin,       # Factory methods
    ThemeIntegrationMixin,    # Theme resolution
    ContentDiscoveryMixin,    # Content discovery
    DataLoadingMixin,         # data/ loading
    SectionRegistryMixin,     # O(1) lookups
):
```

And **36 mutable `_` fields** across mixins for caching/state.

### Solution: Services Over Frozen Snapshot

With snapshots, services become pure functions over immutable data:

```python
# Before: Service needs to handle mutable Site state
class ThemeService:
    def __init__(self, site: Site) -> None:
        self._site = site
        self._theme_obj: Theme | None = None  # Mutable cache
        self._lock = Lock()  # Thread safety

    def resolve(self) -> Theme:
        with self._lock:  # Required for thread safety
            if self._theme_obj is None:
                self._theme_obj = self._load_theme()
            return self._theme_obj


# After: Service is pure function over frozen snapshot
class ThemeService:
    def __init__(self, snapshot: SiteSnapshot) -> None:
        self._snapshot = snapshot  # Frozen, thread-safe

    def resolve(self) -> Theme:
        # Theme resolved at snapshot time, just return it
        return self._snapshot.theme

    # Or for lazy resolution:
    @cached_property  # Safe because snapshot is frozen
    def theme(self) -> Theme:
        return self._load_theme(self._snapshot.config.theme)
```

### Why Snapshots Enable This

| Without Snapshots | With Snapshots |
|-------------------|----------------|
| Services manage mutable state | Services read frozen data |
| Complex locking for thread safety | Lock-free (immutable input) |
| Hard to test (stateful) | Easy to test (pure functions) |
| Hidden coupling via `self._site` | Explicit `snapshot` parameter |

### Service Extraction Plan

| Current Mixin | New Service | Snapshot Impact |
|---------------|-------------|-----------------|
| `SitePropertiesMixin` | **Delete** | All properties in `SiteSnapshot` |
| `PageCachesMixin` | **Delete** | `SiteSnapshot.pages` pre-sorted |
| `SiteFactoriesMixin` | `SiteFactory` | Stateless, no change |
| `ThemeIntegrationMixin` | `ThemeService(snapshot)` | Theme in snapshot |
| `ContentDiscoveryMixin` | `ContentService` | Runs before snapshot |
| `DataLoadingMixin` | `DataService(snapshot)` | Data in snapshot |
| `SectionRegistryMixin` | `QueryService(snapshot)` | Indexes in snapshot |

### Design Alternatives

#### Option A: Full Service Extraction (Recommended)

Extract all mixins to standalone services that operate on `SiteSnapshot`.

| Pros | Cons |
|------|------|
| Clean separation of concerns | Large migration (40-60 hours) |
| Easy to test each service | Must update all call sites |
| Explicit dependencies | Temporary parallel code paths |
| Zero-mixin Site class | |

#### Option B: Mixin Thinning

Keep mixins but move computation to snapshot; mixins become thin wrappers.

```python
class SitePropertiesMixin:
    """Thin wrapper - delegates to snapshot."""
    @property
    def title(self) -> str:
        return self._snapshot.config.site.title  # Delegate
```

| Pros | Cons |
|------|------|
| Lower migration risk | Mixins still exist (complexity) |
| Incremental refactor | Two indirection layers |
| ~25 hours effort | Not the final architecture |

#### Option C: Facade Pattern

Keep `Site` but make it a facade over services; services use snapshots internally.

```python
class Site:
    """Facade - coordinates services."""
    def __init__(self, ...) -> None:
        self._theme_service = ThemeService()
        self._query_service = QueryService()

    @property
    def theme(self) -> Theme:
        return self._theme_service.resolve(self._snapshot)
```

| Pros | Cons |
|------|------|
| API compatibility preserved | More indirection |
| Services testable independently | Site still complex |
| ~35 hours effort | Facade can grow over time |

**Recommendation**: Option A for new codebases; Option C if API stability is paramount.

### Impact

- **Site class**: 7 mixins → 0 mixins (~100 lines)
- **Mutable fields**: 36 → 4 (build phase only)
- **Thread safety**: Structural (frozen) vs manual (locks)
- **Testability**: Services accept `SiteSnapshot` → easy mocking

### Estimated Effort: 40-60 hours (Option A) / 25 hours (Option B) / 35 hours (Option C)

---

## Opportunity 5: Template Dependency Snapshots

### Problem

When a template changes, we need to know which pages use it. Currently computed at query time.

### Solution: Pre-compute at Snapshot Time

```python
@dataclass(frozen=True, slots=True)
class TemplateSnapshot:
    """
    Pre-analyzed template with dependency graph.

    Created during snapshot phase via static template analysis.
    """
    path: Path
    name: str

    # Template relationships (pre-resolved)
    extends: TemplateSnapshot | None       # {% extends "base.html" %}
    includes: tuple[TemplateSnapshot, ...] # {% include "partial.html" %}

    # Block definitions
    blocks: tuple[str, ...]                # {% block content %}

    # Macros
    macros_defined: tuple[str, ...]        # {% macro name() %}
    macros_used: tuple[str, ...]           # {{ macros.name() }}

    # Incremental build support
    content_hash: str

    # Reverse index (pages using this template)
    dependents: tuple[PageSnapshot, ...]


@dataclass(frozen=True, slots=True)
class SiteSnapshot:
    # ... existing fields ...

    # Template snapshots with dependency graph
    templates: MappingProxyType[str, TemplateSnapshot]
    template_dependency_graph: MappingProxyType[str, frozenset[str]]
```

### Usage for Incremental Builds

```python
def pages_affected_by_template_change(
    template_path: Path,
    snapshot: SiteSnapshot,
) -> set[PageSnapshot]:
    """
    Instantly determine which pages need rebuild.

    O(1) lookup instead of O(pages) scan.
    """
    template = snapshot.templates.get(template_path.name)
    if template is None:
        return set()

    # Direct dependents
    affected = set(template.dependents)

    # Transitive: templates that extend/include this one
    for other_name in snapshot.template_dependency_graph.get(template.name, ()):
        other = snapshot.templates.get(other_name)
        if other:
            affected.update(other.dependents)

    return affected
```

### Impact

- **Template change detection**: O(1) vs O(pages)
- **Transitive deps**: Automatic (pre-computed graph)
- **Debug support**: `bengal templates --deps` shows graph

### Estimated Effort: 10-15 hours

---

## Opportunity 6: Config Snapshot

### Problem

Config has dual access patterns:

```python
# Both patterns exist throughout codebase:
config["title"]           # Flat access (sometimes)
config["site"]["title"]   # Nested access (sometimes)
# Which wins? Depends on loader.
```

Two config loaders (`ConfigLoader`, `ConfigDirectoryLoader`) with different flattening behaviors.

### Solution: Frozen Config at Load Time

Apply the snapshot pattern to config:

```python
@dataclass(frozen=True, slots=True)
class SiteSection:
    """Typed accessor for site.* config."""
    title: str
    baseurl: str
    description: str
    author: str
    language: str


@dataclass(frozen=True, slots=True)
class BuildSection:
    """Typed accessor for build.* config."""
    output_dir: str
    content_dir: str
    parallel: bool
    incremental: bool | None
    max_workers: int | None


@dataclass(frozen=True, slots=True)
class ConfigSnapshot:
    """
    Frozen, typed configuration.

    Created once at load time, used throughout build.
    Same pattern as SiteSnapshot.
    """
    site: SiteSection
    build: BuildSection
    theme: ThemeSection
    dev: DevSection

    # Raw access for custom/dynamic keys
    _raw: MappingProxyType[str, Any]

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for custom sections."""
        return self._raw[key]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfigSnapshot:
        """Create frozen config from loaded dict."""
        merged = deep_merge(DEFAULTS, data)
        return cls(
            site=SiteSection(**merged["site"]),
            build=BuildSection(**merged["build"]),
            theme=ThemeSection(**merged["theme"]),
            dev=DevSection(**merged["dev"]),
            _raw=MappingProxyType(merged),
        )
```

### Integration with SiteSnapshot

```python
@dataclass(frozen=True, slots=True)
class SiteSnapshot:
    # Config is now frozen ConfigSnapshot
    config: ConfigSnapshot

    # Shortcut for common access
    @property
    def params(self) -> MappingProxyType[str, Any]:
        return self.config._raw.get("params", MappingProxyType({}))
```

### Why Snapshots Enable This

The snapshot pattern established for Site/Page/Section provides the template:
1. Load mutable data
2. Validate and merge
3. Freeze into typed dataclass
4. Use frozen version throughout

### Impact

- **Single config loader**: Consolidation of `loader.py`, `directory_loader.py`, and `unified_loader.py` into a single `ConfigSnapshot` pipeline.
- **Type safety**: IDE autocomplete for `config.site.title`.
- **No dual access**: Always `config.site.title` (nested).
- **Thread-safe**: Frozen = safe for parallel builds (aligns with `rfc-free-threading-hardening.md`).

### Estimated Effort: 20-30 hours

---

## Implementation Roadmap

### Phase 0: Baseline Benchmarking (Pre-requisite)

Before any optimization, we must establish a ground truth.

| Task | Description | Effort |
|------|-------------|--------|
| Baseline Creation | Run `scripts/benchmark_snapshot.py` on 100/1000/5000 page sites | 4 hours |
| HMR Latency Profile | Profile current dev server reload times | 4 hours |

### Phase 1: Foundation (Weeks 1-2)

| Task | Depends On | Effort |
|------|------------|--------|
| Template Dependency Snapshots | Snapshots (done) | 10-15 hours |
| Config Snapshot | Snapshots (done) | 20-30 hours |

**Rationale**: These are independent and provide immediate value for other phases.

### Phase 2: Incremental Optimization (Weeks 3-4)

| Task | Depends On | Effort |
|------|------------|--------|
| Incremental Snapshot Updates | Phase 1 | 15-20 hours |
| Speculative Rendering | Incremental Snapshots | 20-30 hours |

**Rationale**: Builds on Phase 1 foundations for performance wins.

### Phase 3: Architecture Cleanup (Weeks 5-8)

| Task | Depends On | Effort |
|------|------------|--------|
| Effect-Traced Builds | Template Snapshots | 50-70 hours |
| Service Extraction | Config Snapshot | 40-60 hours |

**Rationale**: Major refactors that benefit from earlier phases.

### Timeline

```
Week 1-2:   ████████ Template Deps + Config Snapshot
Week 3-4:   ████████ Incremental Snapshots + Speculation
Week 5-6:   ████████████████ Effect-Traced Builds
Week 7-8:   ████████████████ Service Extraction
            ────────────────────────────────────────
Total:      155-225 hours over 8 weeks (~20-28 hours/week)
```

> **Note**: 155-225 hours over 8 weeks requires ~20-28 hours/week of focused development.
> At 50% allocation, this extends to 16 weeks. Plan accordingly.

---

## Success Criteria

| Metric | Current | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|---------|---------------|---------------|---------------|
| Incremental detector files | 13 | 13 | 13 | **1** |
| Site mixin count | 7 | 7 | 7 | **0** |
| Config loaders | 2 | **1** | 1 | 1 |
| Single-file HMR latency | ~200ms | ~150ms | **~80ms** | ~80ms |
| Incremental snapshot time | ~50ms | ~50ms | **<5ms** | <5ms |
| Template→page lookup | O(n) | **O(1)** | O(1) | O(1) |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Speculation wastes CPU on wrong guesses | Medium | Low | Limit speculation to high-confidence predictions |
| Structural sharing adds memory overhead | Low | Low | Measure; Python's GC handles well |
| Effect system adds runtime overhead | Low | Medium | Benchmark hot paths; effects are O(1) recording |
| Service extraction breaks integrations | Medium | High | Feature flags, incremental extraction |
| Template analysis misses dynamic includes | Medium | Medium | Fall back to conservative "all pages" for dynamic |

---

## Validation Plan

Before Phase 2 implementation, establish performance baselines:

### Required Benchmarks

| Metric | Command | Baseline Needed For |
|--------|---------|---------------------|
| Snapshot creation time | `bengal build --profile` | Opportunity 2 |
| HMR latency (MD change) | Dev server + stopwatch | Opportunity 3 |
| HMR latency (template change) | Dev server + stopwatch | Opportunity 3 |
| Template→page lookup time | Custom benchmark | Opportunity 5 |

### Benchmark Script

```python
# scripts/benchmark_snapshot.py
import time
from pathlib import Path
from bengal.core.site import Site
from bengal.snapshots.builder import create_site_snapshot

def benchmark_snapshot_creation(site_path: Path, iterations: int = 5) -> None:
    """Measure snapshot creation time."""
    site = Site.from_config(site_path)
    site.discover_content()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        snapshot = create_site_snapshot(site)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    print(f"Snapshot creation: {sum(times)/len(times):.1f}ms avg ({len(snapshot.pages)} pages)")

if __name__ == "__main__":
    benchmark_snapshot_creation(Path("."))
```

### Acceptance Criteria

| Opportunity | Metric | Target | Validation |
|-------------|--------|--------|------------|
| Incremental Snapshots | 1-file change rebuild | <5ms | Benchmark before/after |
| Speculative Rendering | HMR latency | <100ms | Dev server measurement |
| Template Deps | Template→page lookup | <1ms | Benchmark |

---

## Open Questions

1. **Block detector fate**: **Resolved**. Refactor into `BlockDiffService` used by `EffectTracer`.
2. **Free-threading RFC interaction**: **Resolved**. `SiteSnapshot` and `ConfigSnapshot` are key components for the GIL-free architecture proposed in `rfc-free-threading-hardening.md`. Frozen snapshots eliminate 90% of the render-phase lock requirements.
3. **Speculation accuracy**: **Resolved**. Implement a **Shadow Mode** in Phase 2 to validate accuracy before full enablement.
4. **Config loader consolidation scope**: **Resolved**. All 3 files (`loader.py`, `directory_loader.py`, `unified_loader.py`) will be merged into the new `UnifiedConfigLoader` pipeline.

---

## Related Documents

- `plan/rfc-bengal-snapshot-engine.md` — Foundation (implemented)
- `plan/rfc-bengal-v2-architecture.md` — Broader v2 vision
- `plan/rfc-free-threading-hardening.md` — Thread safety patterns
- `plan/rfc-global-build-state-dependencies.md` — Incremental build gaps

---

## Appendix: Evidence Commands

```bash
# Count incremental detector files
ls -1 bengal/orchestration/incremental/*.py | wc -l
# Verified: 13 ✓

# Count lines in incremental detectors
wc -l bengal/orchestration/incremental/*.py | tail -1
# Verified: 4039 total ✓

# Count Site mixins
grep "class.*Mixin" bengal/core/site/*.py | wc -l
# Verified: 7 ✓

# Count mutable _ fields across Site mixins
grep "^    _\w\+:" bengal/core/site/*.py | wc -l
# Verified: 36 ✓

# Verify snapshot is frozen
grep -c "@dataclass(frozen=True" bengal/snapshots/types.py
# Verified: 5 ✓

# Template groups already in snapshot
grep "template_groups" bengal/snapshots/types.py
# Verified: Present in SiteSnapshot (line 160) ✓

# Count config loaders
ls bengal/config/*loader*.py
# Verified: loader.py, directory_loader.py, unified_loader.py (3 files, 2 patterns) ✓
```

---

## Changelog

- 2026-01-18: Revised after RFC evaluation
  - Added Goals/Non-Goals section
  - Added design alternatives for Opportunities 1 and 4 (highest effort)
  - Fixed evidence: ~4,000 lines (not ~2,500), 36 mutable fields (not ~25)
  - Added performance validation notes (figures are estimates)
  - Updated appendix with verified evidence commands
  - Added timeline realism note (20-28 hours/week required)
  - Confidence adjusted to 82% 🟡 pending benchmark validation
- 2026-01-18: Initial draft
