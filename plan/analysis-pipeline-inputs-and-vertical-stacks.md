# Deep Dive: Pipeline Inputs, Vertical Stacks Alignment, and Incremental/Hot Reload

**Status**: Analysis  
**Created**: 2026-02-14  
**Purpose**: Understand Bengal's build pipeline, align with b-stack vertical stacks philosophy, and improve incremental/hot reload control.

---

## 1. The Vertical Stacks Design Philosophy

### What "Vertical Stacks" Means in b-stack

From `site/content/docs/about/ecosystem.md` and `README.md`:

> **A structured reactive stack — every layer written in pure Python for 3.14t free-threading.**

The b-stack ecosystem is a **layered vertical stack**:

```
┌─────────────────────────────────────────────────────────────────┐
│ Content Layer     │ Patitas (Markdown), Rosettes (Highlighting) │
├───────────────────┼───────────────────────────────────────────┤
│ Rendering Layer   │ Kida (Templates)                            │
├───────────────────┼───────────────────────────────────────────┤
│ Application Layer │ Chirp (Web Framework)                       │
├───────────────────┼───────────────────────────────────────────┤
│ Transport Layer   │ Pounce (ASGI Server)                       │
├───────────────────┼───────────────────────────────────────────┤
│ Orchestration     │ Bengal (SSG), Purr (Content Runtime)       │
└─────────────────────────────────────────────────────────────────┘
```

**Key principles implied by this stack:**

1. **Layered composition** — Each layer consumes the layer below; no horizontal coupling
2. **Pure Python, free-threading ready** — No GIL assumptions, thread-safe by design
3. **Reactive** — Changes flow down; outputs flow up
4. **Single responsibility per layer** — Bengal orchestrates; Patitas parses; Kida renders
5. **Explicit boundaries** — Protocols and contracts at layer boundaries

### How Bengal Fits

Bengal sits in **Orchestration** — it coordinates Patitas, Kida, Rosettes, and Chirp. It should:

- **Consume** from content/rendering layers (not implement them)
- **Produce** a build artifact (static output)
- **React** to input changes (incremental, hot reload)
- **Expose** a clear input/output contract

---

## 2. Complete Input Map: What Drives a Build

### 2.1 Entry Points and Their Inputs

| Entry Point | Location | Primary Inputs |
|-------------|----------|----------------|
| **CLI `bengal build`** | `cli/commands/build.py` | `BuildOptions` from `resolve_build_options(config, CLI flags)` |
| **CLI `bengal serve`** | `server/dev_server.py` | Same, plus `watch`, `open_browser`, `version_scope` |
| **Dev server hot reload** | `server/build_trigger.py` | `changed_paths`, `event_types` → converted to `BuildOptions` |
| **Process-isolated build** | `server/build_executor.py` | `BuildRequest` (serializable) → `BuildOptions` |
| **Warm build (same process)** | `server/build_trigger.py` | `BuildOptions` directly |

### 2.2 BuildOptions — The Canonical Input (Mostly)

**Location**: `bengal/orchestration/build/options.py`

```python
@dataclass
class BuildOptions:
    # Build behavior
    force_sequential: bool = False
    incremental: bool | None = None  # None = auto-detect from cache
    verbose: bool = False
    quiet: bool = False
    memory_optimized: bool = False

    # Output behavior
    strict: bool = False
    full_output: bool = False

    # Explain mode
    explain: bool = False
    dry_run: bool = False
    explain_json: bool = False

    # Profiling
    profile: BuildProfile | None = None
    profile_templates: bool = False

    # Incremental hints (from dev server / file watcher)
    changed_sources: set[Path] = field(default_factory=set)
    nav_changed_sources: set[Path] = field(default_factory=set)
    structural_changed: bool = False

    # Phase streaming
    on_phase_start: PhaseStartCallback | None = None
    on_phase_complete: PhaseCompleteCallback | None = None
```

**Gap**: `BuildOptions` is the intended single source of build configuration, but many inputs are **not** in BuildOptions — they come from:

- `Site` (config, paths, theme)
- `BuildCache` (fingerprints, provenance)
- `BuildContext` (accumulated during build)
- Environment (`BENGAL_BUILD_EXECUTOR`, `_version_scope` in config)

### 2.3 BuildRequest — Serializable Subset (Process-Isolated Builds)

**Location**: `bengal/server/build_executor.py`

```python
@dataclass(frozen=True)
class BuildRequest:
    site_root: str
    changed_paths: tuple[str, ...]
    incremental: bool = True
    profile: str = "WRITER"
    nav_changed_paths: tuple[str, ...]
    structural_changed: bool = False
    force_sequential: bool = False
    version_scope: str | None = None
```

**Gap**: `BuildRequest` is a **subset** of `BuildOptions`. When using process isolation, `explain`, `dry_run`, `profile_templates`, `memory_optimized`, and phase callbacks are **lost** — the subprocess builds with defaults.

### 2.4 Inputs That Flow Through (Not in BuildOptions)

| Input | Source | Consumed By |
|-------|--------|-------------|
| `Site.config` | `Site.from_config()` or existing Site | All phases |
| `Site.root_path`, `Site.output_dir` | Config / paths | All phases |
| `Site.dev_mode` | Set by dev server | Font skip, fingerprinting |
| `BuildCache` | `IncrementalOrchestrator.initialize()` | Provenance filter, discovery |
| `GeneratedPageCache` | Created in build | Taxonomy phase, cache save |
| `SnapshotCache` | Created in build | Snapshot save/load |
| `early_ctx` (BuildContext) | Created in build | Discovery, rendering, health |
| `output_collector` | Created in build | Assets, render, postprocess → stats.changed_outputs |

### 2.5 The Input Flow Diagram (Current State)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BUILD INPUT FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  WatcherRunner          CLI                    BuildExecutor (subprocess)    │
│       │                   │                              │                  │
│       │ changed_paths     │ resolve_build_options()       │ BuildRequest     │
│       │ event_types       │ BuildOptions                  │                  │
│       ▼                   ▼                              ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ BuildTrigger._detect_nav_changes()                                   │    │
│  │ BuildTrigger._needs_full_rebuild()                                   │    │
│  │ → BuildOptions(changed_sources, nav_changed_sources, structural_*)   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                       │                                      │
│                                       ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ BuildOrchestrator.build(options)                                     │    │
│  │                                                                      │    │
│  │ Extracts from options: incremental, force_sequential, profile,       │    │
│  │ changed_sources, nav_changed_sources, structural_changed,            │    │
│  │ memory_optimized, quiet, verbose, explain, dry_run, ...              │    │
│  │                                                                      │    │
│  │ BUT ALSO reads: site.config, site._cache, site._last_build_options   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                       │                                      │
│                                       ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ phase_incremental_filter_provenance()                                │    │
│  │   Inputs: orchestrator, cache, options.changed_sources,              │    │
│  │           options.nav_changed_sources, options.structural_changed    │    │
│  │   Outputs: FilterResult(pages_to_build, assets_to_process, ...)       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                       │                                      │
│                                       ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ phase_render()                                                       │    │
│  │   Receives: options.*, early_ctx, output_collector                    │    │
│  │   Passes to RenderOrchestrator: changed_sources (for priority sort)  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Hot Reload and Incremental Flow

### 3.1 Hot Reload Pipeline

```
WatcherRunner (watchfiles)
    │
    │ on_file_change(changed_paths, event_types)
    ▼
BuildTrigger.trigger_build()
    │
    ├─ _needs_full_rebuild()      → created/deleted/moved → full
    ├─ _detect_nav_changes()      → frontmatter with nav keys → nav_changed_sources
    ├─ run_pre_build_hooks()
    ├─ site.prepare_for_rebuild() → reset caches, cascade snapshot
    │
    ├─ [Warm build] site.build(options)  OR  [Cold] BuildExecutor.submit(BuildRequest)
    │
    ├─ run_post_build_hooks()
    └─ controller.decide_and_update() → ReloadDecision
            │
            ▼
       LiveReload.send_event() → Browser
```

### 3.2 Reload Decision Inputs

**Location**: `bengal/server/reload_controller.py`

| Input | Source | Purpose |
|-------|--------|---------|
| `changed_outputs` | `BuildStats.changed_outputs` (from `BuildOutputCollector`) | What files were written |
| `OutputSnapshot` (baseline) | Previous build's output state | Diff to detect real changes |
| Content hashes (optional) | `bengal:content-hash` meta tags | Avoid false positives from aggregate-only changes |

**ReloadDecision**: `action` ∈ {`none`, `reload-css`, `reload`}

- **reload-css**: All changed outputs are CSS → inject new CSS, no full refresh
- **reload**: Any HTML/JS/other → full page reload
- **none**: No meaningful changes (throttled or hash match)

### 3.3 Where changed_outputs Comes From

`BuildOutputCollector` is created in `BuildOrchestrator.build()` and passed to:

1. `phase_assets()` — records asset writes
2. `phase_render()` → `BuildContext.output_collector` → `RenderingPipeline` / `WriteBehindCollector` records HTML
3. `phase_postprocess()` — records sitemap, RSS, etc.

After build: `stats.changed_outputs = output_collector.get_outputs()`

**Gap**: The collector is passed through many layers. Not all write paths go through it — some phases may write without recording. Audit needed.

---

## 4. Vertical Stacks Alignment Gaps

### 4.1 Horizontal Coupling (Anti-Stack)

| Issue | Evidence | Stack Violation |
|-------|----------|-----------------|
| BuildOrchestrator owns 8 orchestrators | `build/__init__.py:133-140` | Orchestration layer doing composition at init time |
| Phase functions take full orchestrator | `phase_*(orchestrator, ...)` | Phases reach into any orchestrator field |
| BuildContext accumulates unrelated state | `build_context.py` | Single bag for render, incremental, I/O, progress |
| Site has 25+ mutable `_` fields | `core/site/core.py` | Mutable shared state across layers |

### 4.2 Input Opacity

| Issue | Impact |
|-------|--------|
| BuildOptions incomplete | Can't reconstruct "why did this build run?" from options alone |
| BuildRequest ≠ BuildOptions | Subprocess builds lose explain, dry_run, callbacks |
| changed_sources flows 5 layers deep | Hard to trace; used for priority sort only in render |
| No BuildInputSummary type | No single serializable record of "all inputs to this build" |

### 4.3 Reactive Flow Gaps

| Expected (Reactive Stack) | Actual |
|--------------------------|--------|
| Change → Detect → Filter → Render | ✅ Mostly (provenance filter) |
| Clear dependency graph | ❌ 13 detectors, bespoke logic (RFC: incremental-build-contracts) |
| Outputs declared per phase | ⚠️ Collector exists but coverage unclear |
| Hot reload uses typed outputs | ✅ OutputRecord, ReloadDecision |

### 4.4 Layer Boundary Violations

| Layer | Should | Actually |
|-------|--------|----------|
| Build | Orchestrate only | Creates BuildContext, loads asset manifest, configures directive cache |
| Render | Render pages | Also: block cache warm, write-behind, dependency tracking |
| Discovery | Return content | Mutates Site, caches in BuildContext for validators |

---

## 5. Recommendations for Pipeline Control and Input Clarity

### 5.1 Introduce BuildInput (Single Source of Truth)

**Goal**: One frozen dataclass that captures every input to a build.

```python
@dataclass(frozen=True)
class BuildInput:
    """Complete, serializable record of all inputs to a build."""
    options: BuildOptions
    site_root: Path
    config_hash: str  # For cache invalidation
    # Optional hints (from watcher)
    changed_sources: frozenset[Path]
    nav_changed_sources: frozenset[Path]
    structural_changed: bool
    event_types: frozenset[str]
```

- `BuildRequest` becomes a serialization of `BuildInput` (or vice versa)
- `BuildInput` can be logged, stored, and replayed for debugging
- Enables "explain" mode: show exactly what triggered this build

### 5.2 PhaseInput / PhaseOutput Contracts

**Goal**: Phases receive only what they need; return what they produce.

```python
@dataclass
class DiscoveryPhaseInput:
    site: Site
    cache: BuildCache
    incremental: bool
    build_context: BuildContext | None  # For content caching

@dataclass
class DiscoveryPhaseOutput:
    pages: list[Page]
    sections: list[Section]
    assets: list[Asset]
    cached_content: dict[Path, str]  # For validators
```

- Phases no longer take `orchestrator: BuildOrchestrator`
- BuildOrchestrator becomes a thin coordinator: create PhaseInput, call phase, apply PhaseOutput

### 5.3 Output Tracking Audit

**Goal**: Every write during a build is recorded.

- Audit: `phase_assets`, `phase_render`, `phase_postprocess`, font copy, autodoc
- Ensure `BuildOutputCollector.record()` is called for each
- Add `OutputCollector` to protocols so phases receive it explicitly

### 5.4 Hot Reload: Typed Reload Hints

**Goal**: Build can declare "this change only affects CSS" for smarter reload.

- Today: ReloadController infers from output types only
- Enhancement: Build could pass `reload_hint: Literal["css-only", "full", "none"]` when it knows (e.g., only assets changed)
- Reduces false full reloads when only CSS changed

### 5.5 Vertical Stack Refactor (Longer Term)

Per `rfc-bengal-v2-architecture.md` and `rfc-bengal-snapshot-engine.md`:

1. **Snapshot-first rendering** — Immutable snapshot after discovery; render from snapshot only
2. **Protocol-first phases** — Phases accept protocols (SiteLike, PageLike), not concrete types
3. **Composition over god object** — BuildOrchestrator delegates to focused coordinators (DiscoveryCoordinator, RenderCoordinator, CacheCoordinator)
4. **Declarative dependencies** — Replace 13 detectors with effect declarations per operation

---

## 6. Summary: Inputs Checklist

| Input | In BuildOptions? | In BuildRequest? | Flows to |
|-------|------------------|------------------|----------|
| incremental | ✅ | ✅ | Provenance filter, all phases |
| force_sequential | ✅ | ✅ | Render, assets, postprocess |
| changed_sources | ✅ | ✅ (as changed_paths) | Provenance, RenderOrchestrator (priority) |
| nav_changed_sources | ✅ | ✅ | Provenance filter |
| structural_changed | ✅ | ✅ | Provenance filter |
| profile | ✅ | ✅ | BuildContext, health |
| memory_optimized | ✅ | ❌ | phase_render (streaming vs standard) |
| explain / dry_run | ✅ | ❌ | Build early-exit, explain output |
| profile_templates | ✅ | ❌ | BuildContext |
| on_phase_start/complete | ✅ | ❌ | Build loop |
| version_scope | ❌ (in config) | ✅ | Taxonomy filtering |
| output_collector | ❌ (created in build) | ❌ | Assets, render, postprocess |
| early_ctx / BuildContext | ❌ (created in build) | ❌ | Discovery, render, health |

---

## 7. Implementation Status

Implemented per `plan/pipeline_inputs_vertical_stacks_0c2ce8e7.plan.md`:

| Phase | Status | Notes |
|-------|--------|-------|
| **1. BuildInput** | ✅ Done | `bengal/orchestration/build/inputs.py` — `BuildInput` with `from_options()`, `from_build_request()`, `to_build_request()` |
| **2. Output tracking** | ✅ Done | fonts.css recorded; SpecialPages, Redirects, SocialCards, XRefIndex record to collector |
| **3. Discovery PhaseInput** | ✅ Done | `DiscoveryPhaseInput`, `DiscoveryPhaseOutput` in `results.py`; `run_discovery_phase()` in `initialization.py` |
| **4. Reload hint** | ✅ Done | `BuildStats.reload_hint`; computed after postprocess; used in `ReloadController.decide_from_outputs()` |
| **5. RFC** | ✅ Done | `plan/rfc-pipeline-input-output-contracts.md` |

### BuildInput Fields

- `options`, `site_root`, `config_hash`, `changed_sources`, `nav_changed_sources`, `structural_changed`, `event_types`

### PhaseInput/PhaseOutput Contracts

- `DiscoveryPhaseInput`: site, cache, incremental, build_context
- `DiscoveryPhaseOutput`: pages, sections, assets

---

## 8. Next Steps (Prioritized)

1. ~~**BuildInput dataclass**~~ — Done
2. ~~**Output tracking audit**~~ — Done
3. ~~**PhaseInput extraction (discovery)**~~ — Done
4. ~~**Reload hint from build**~~ — Done
5. ~~**RFC: Pipeline Input/Output Contracts**~~ — Done
6. **PhaseInput for remaining phases** — Assets, render, postprocess, finalization (future)
