# RFC: Bengal v2 Architecture - Protocol-First, Composition-Based Design

**Status**: Draft  
**Created**: 2026-01-17  
**Author**: Bengal Team  
**Confidence**: 85% 🟢  
**Category**: Core / Orchestration / Architecture

---

## Executive Summary

Bengal has evolved organically from a simple SSG into a feature-rich platform with incremental builds, versioning, autodoc, and more. This growth has introduced architectural debt: mixin-heavy god objects, inconsistent protocol adoption, dual-access config patterns, and scattered mutable state. This RFC proposes a v2 architecture based on **protocol-first design**, **composition over inheritance**, and **immutable-by-default models**—while preserving the solid foundations (model/orchestrator split, external packages, PageCore contract).

This is a **self-contained design document** with complete implementation details for each phase.

---

## Problem Statement

### Current State

Bengal's architecture has several structural challenges identified through code analysis.

**Evidence** (verified 2026-01-17):

| File | Issue | Metric |
|------|-------|--------|
| `bengal/core/site/core.py:77-85` | Site inherits from **7 mixins** | Inheritance depth |
| `bengal/core/site/properties.py` | Single mixin with **800 lines** | Code complexity |
| `bengal/core/site/core.py:155-228` | **25 mutable `_` fields** | State management |
| `bengal/protocols/core.py:1-377` | Well-designed protocols exist | Available infrastructure |
| `bengal/orchestration/incremental/` | **13 detector files** with bespoke logic | Maintenance burden |

### Pain Points

#### 1. Inconsistent Protocol Adoption

Protocols exist but adoption varies wildly by type:

| Type Annotation | Concrete | Protocol | Adoption Rate |
|-----------------|----------|----------|---------------|
| `Site` / `SiteLike` | 443 usages | 169 usages | 28% ✅ |
| `Page` / `PageLike` | 430 usages | 52 usages | 11% ⚠️ |
| `Section` / `SectionLike` | 176 usages | 4 usages | 2% ❌ |

**Impact**: Rigid APIs that can't accept proxies or test doubles, especially for `Section` operations.

#### 2. Mixin God Object

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

**Impact**: Hidden coupling (mixins assume `self.config`, `self._theme_obj` exist), impossible to understand without tracing 7 files, untestable in isolation.

#### 3. Dual Config Access Patterns

```python
# Both patterns exist throughout codebase:
config["title"]           # Flat access
config["site"]["title"]   # Nested access
# Which wins? Depends on flattening order.
```

**Impact**: Two config loaders (`ConfigLoader`, `ConfigDirectoryLoader`) with different flattening behaviors, runtime surprises, hard to reason about config precedence.

#### 4. Mutable State Proliferation

```python
# bengal/core/site/core.py:155-228 (25 mutable fields)
_regular_pages_cache: list[Page] | None
_generated_pages_cache: list[Page] | None
_page_path_map: dict[str, Page] | None
_theme_obj: Theme | None
_query_registry: Any
_registry: ContentRegistry | None
_current_build_state: BuildState | None
_paths: Any
_dev_menu_metadata: dict[str, Any] | None
_affected_tags: set[str]
_page_lookup_maps: dict[str, dict[str, Page]] | None
_last_build_stats: dict[str, Any] | None
_template_parser: Any
_asset_manifest_previous: Any
_bengal_theme_chain_cache: dict[str, Any] | None
# ... 10 more
```

**Impact**: Thread-safety concerns with Python 3.14t free-threading, hard to reason about state transitions, cache invalidation bugs.

#### 5. Incremental Build Detector Explosion

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

**Impact**: Each detector implements its own "what changed → what rebuilds" logic with no unified dependency model. 13 files totaling ~2,500 lines of bespoke detection code.

### Impact Summary

| Issue | Symptoms | Affected Areas |
|-------|----------|----------------|
| Protocol gap | Rigid APIs, especially for Section | Everywhere |
| Mixin architecture | Hidden coupling, untestable | `core/site/` |
| Config duality | Runtime surprises, two loaders | `config/`, consumers |
| Mutable state | Thread-safety, cache bugs | `core/site/`, builds |
| Detector explosion | Bespoke logic, hard to debug | `orchestration/incremental/` |

---

## Goals and Non-Goals

### Goals

1. **Protocol-first APIs** - Public functions accept protocols, not concrete types
2. **Composition over mixins** - Replace 7-mixin Site with focused services
3. **Canonical config structure** - One nested structure, typed accessor class
4. **Immutable core models** - Enforce frozen dataclasses, no `__setattr__` bypasses
5. **Declarative dependencies** - Operations declare their effects, not bespoke detectors
6. **Backward compatibility path** - Incremental migration, not big bang rewrite

### Non-Goals

1. **Rewrite from scratch** - Preserve working code, refactor incrementally
2. **Change public CLI** - `bengal build`, `bengal serve` stay the same
3. **Break existing sites** - Config migration with clear deprecation path
4. **Abandon mixins entirely** - Some composition patterns still useful

---

## Design Options

### Option A: Protocol Migration Only (Incremental)

**Approach**: Migrate function signatures from concrete types to existing protocols. No structural changes.

**Implementation**:

```python
# Before (current)
def register_functions(env: TemplateEnvironment, site: Site) -> None:
    baseurl = site.baseurl
    ...

# After (protocol)
from bengal.protocols import SiteLike

def register_functions(env: TemplateEnvironment, site: SiteLike) -> None:
    baseurl = site.baseurl  # Works! SiteLike defines .baseurl
    ...
```

**Migration Priority** (based on current adoption rates):

1. **Section → SectionLike**: 2% adoption, 176 usages to migrate
2. **Page → PageLike**: 11% adoption, ~380 usages to migrate  
3. **Site → SiteLike**: 28% adoption, ~270 usages to migrate

**Protocol Extensions Needed**:

```python
# bengal/protocols/core.py additions
class PageLike(Protocol):
    # Existing properties...
    
    # Add missing for full compatibility:
    @property
    def section(self) -> SectionLike | None: ...
    
    @property
    def output_path(self) -> Path: ...

class SectionLike(Protocol):
    # Existing properties...
    
    # Add missing:
    @property
    def subsections(self) -> list[SectionLike]: ...
    
    def get_pages(self, *, recursive: bool = False) -> list[PageLike]: ...
```

**Pros**:
- Low risk - function signatures only
- Fixes rigid APIs immediately
- Fully backward compatible
- ~600 signature changes

**Cons**:
- Doesn't address mixin complexity
- Doesn't fix config duality
- Doesn't address mutable state

**Estimated Effort**: 12-16 hours

---

### Option B: Service-Oriented Site (Composition Refactor)

**Approach**: Replace Site mixins with composed services. Site becomes a thin data container.

**Implementation**:

```python
# New architecture
@dataclass(frozen=True, slots=True)
class SiteConfig:
    """Immutable, validated configuration."""
    title: str
    baseurl: str
    output_dir: Path
    theme: str
    language: str = "en"

@dataclass
class Site:
    """Thin container - data only, no behavior."""
    config: SiteConfig
    content: ContentRegistry      # Pages, sections, assets
    root_path: Path
    
    # No mixins, no methods beyond property access

# Services do the work
class ThemeService:
    """Resolves themes - extracted from ThemeIntegrationMixin."""
    
    def __init__(self, site: SiteLike) -> None:
        self._site = site
        self._theme_obj: Theme | None = None  # Lazy-loaded
    
    def resolve(self) -> Theme:
        if self._theme_obj is None:
            self._theme_obj = self._load_theme()
        return self._theme_obj
    
    def _load_theme(self) -> Theme:
        theme_name = self._site.config.theme.name
        # Resolution logic extracted from mixin...

class ContentDiscoveryService:
    """Content discovery - extracted from ContentDiscoveryMixin."""
    
    def __init__(self, site: SiteLike) -> None:
        self._site = site
    
    def discover(self) -> ContentRegistry:
        """Discover all pages, sections, assets."""
        pages = self._discover_pages()
        sections = self._build_section_tree(pages)
        assets = self._discover_assets()
        return ContentRegistry(pages, sections, assets)

class QueryService:
    """Page/section queries - extracted from SectionRegistryMixin."""
    
    def __init__(self, registry: ContentRegistry) -> None:
        self._registry = registry
        self._path_index: dict[str, Page] = {}
        self._section_index: dict[str, Section] = {}
    
    def page_by_href(self, href: str) -> Page | None:
        return self._path_index.get(href)
    
    def section_by_path(self, path: str) -> Section | None:
        return self._section_index.get(path)

# Usage
site = Site.from_config(path)
theme_service = ThemeService(site)
query_service = QueryService(site.content)

theme = theme_service.resolve()
page = query_service.page_by_href("/docs/guide/")
```

**Mixin → Service Mapping**:

| Current Mixin | New Service | State Moved |
|---------------|-------------|-------------|
| `SitePropertiesMixin` | Delete (use `Config` accessor) | N/A |
| `PageCachesMixin` | `QueryService` | `_page_path_map`, etc. |
| `SiteFactoriesMixin` | `SiteFactory` class | N/A (stateless) |
| `ThemeIntegrationMixin` | `ThemeService` | `_theme_obj` |
| `ContentDiscoveryMixin` | `ContentDiscoveryService` | Discovery state |
| `DataLoadingMixin` | `DataService` | `data` dict |
| `SectionRegistryMixin` | `QueryService` | Registry caches |

**Pros**:
- Clear separation of concerns
- Each service is independently testable
- Eliminates hidden mixin coupling
- Enables dependency injection

**Cons**:
- Breaking change for `site.theme` direct access
- Significant refactoring effort
- More objects to wire together

**Estimated Effort**: 40-60 hours

---

### Option C: Canonical Config + Typed Accessor

**Approach**: Unify config to nested-only structure with typed accessor class.

**Implementation**:

```python
# bengal/config/defaults.py
DEFAULTS: dict[str, Any] = {
    "site": {
        "title": "Bengal Site",
        "baseurl": "",
        "description": "",
        "author": "",
        "language": "en",
    },
    "build": {
        "output_dir": "public",
        "content_dir": "content",
        "parallel": True,
        "incremental": None,
        "max_workers": None,
        "pretty_urls": True,
        "minify_html": True,
    },
    "dev": {
        "cache_templates": True,
        "live_reload": True,
        "port": 8000,
    },
    "theme": {
        "name": "default",
    },
    # No flat keys - everything nested
}

# bengal/config/accessor.py
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
    pretty_urls: bool
    minify_html: bool

@dataclass(frozen=True, slots=True)
class Config:
    """
    Typed configuration with IDE autocomplete.
    
    Access pattern (canonical):
        >>> cfg.site.title
        'My Site'
        >>> cfg.build.parallel
        True
    
    Dict access for dynamic keys:
        >>> cfg["theme"]["custom_option"]
        'value'
    """
    site: SiteSection
    build: BuildSection
    dev: DevSection
    theme: ThemeSection
    _raw: dict[str, Any] = field(repr=False)
    
    def __getitem__(self, key: str) -> Any:
        """Dict-style access for dynamic/custom sections."""
        return self._raw[key]
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create Config from loaded dict, applying defaults."""
        merged = deep_merge(DEFAULTS, data)
        return cls(
            site=SiteSection(**merged["site"]),
            build=BuildSection(**merged["build"]),
            dev=DevSection(**merged["dev"]),
            theme=ThemeSection(**merged["theme"]),
            _raw=merged,
        )

# bengal/config/loader.py
class UnifiedConfigLoader:
    """
    Single config loader for both single-file and directory configs.
    
    No flattening - preserves nested structure exactly.
    """
    
    def load(self, root_path: Path) -> Config:
        """Load config from bengal.toml or config/ directory."""
        if (root_path / "bengal.toml").exists():
            data = self._load_single_file(root_path / "bengal.toml")
        elif (root_path / "config").is_dir():
            data = self._load_directory(root_path / "config")
        else:
            data = {}
        
        return Config.from_dict(data)
    
    def _load_single_file(self, path: Path) -> dict[str, Any]:
        return tomllib.loads(path.read_text())
    
    def _load_directory(self, config_dir: Path) -> dict[str, Any]:
        """Load all YAML files from config/ and merge."""
        result: dict[str, Any] = {}
        for yaml_file in sorted(config_dir.glob("*.yaml")):
            section_name = yaml_file.stem  # site.yaml → "site"
            with yaml_file.open() as f:
                result[section_name] = yaml.safe_load(f)
        return result
```

**Migration Path**:

```python
# Deprecation shim for flat access
class ConfigCompat:
    """Temporary compatibility layer (remove in v1.0)."""
    
    def __getitem__(self, key: str) -> Any:
        # Flat keys redirect with warning
        if key in ("title", "baseurl", "author", "language"):
            warnings.warn(
                f"Flat config access config['{key}'] is deprecated. "
                f"Use config.site.{key} instead.",
                DeprecationWarning,
            )
            return getattr(self.site, key)
        # Nested access still works
        return self._raw[key]
```

**Pros**:
- IDE autocomplete for all config
- Type checking catches config typos
- Single loader, no flattening complexity
- Clear migration path

**Cons**:
- Breaking change for flat access patterns
- Requires updating all `config["title"]` usages

**Estimated Effort**: 20-30 hours

---

### Option D: Effect-Traced Incremental Builds

**Approach**: Replace 13 detector classes with declarative effect tracking.

**Core Concept**: Every operation that produces output declares:
1. What it produces (output paths)
2. What it depends on (input paths, config keys)
3. What it invalidates (cache keys)

**Implementation**:

```python
# bengal/build/effects.py
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet

@dataclass(frozen=True, slots=True)
class Effect:
    """
    Declarative effect of a build operation.
    
    Attributes:
        outputs: Files this operation produces
        depends_on: Files/keys this operation reads
        invalidates: Cache keys to clear if inputs change
    """
    outputs: frozenset[Path]
    depends_on: frozenset[Path | str]
    invalidates: frozenset[str]
    
    @classmethod
    def for_page(cls, page: PageLike, ctx: RenderContext) -> Effect:
        """Standard effect for rendering a page."""
        return cls(
            outputs=frozenset({ctx.output_path(page)}),
            depends_on=frozenset({
                page.source_path,
                ctx.layout_path(page),
                *ctx.included_templates(page),
                *page.frontmatter.get("resources", []),
            }),
            invalidates=frozenset({
                f"page:{page.href}",
                f"section:{page.section.href}" if page.section else "",
            }),
        )


class EffectTracer:
    """
    Unified dependency tracking replacing 13 detector classes.
    
    Records effects during build, enables precise incremental rebuilds.
    
    Thread Safety:
        Uses lock for effect recording during parallel builds.
    """
    
    def __init__(self) -> None:
        self._effects: list[Effect] = []
        self._lock = Lock()
        # Indexes for fast lookup
        self._by_output: dict[Path, Effect] = {}
        self._by_dependency: dict[Path | str, list[Effect]] = {}
    
    def record(self, effect: Effect) -> None:
        """Record an effect (thread-safe)."""
        with self._lock:
            self._effects.append(effect)
            for output in effect.outputs:
                self._by_output[output] = effect
            for dep in effect.depends_on:
                self._by_dependency.setdefault(dep, []).append(effect)
    
    def invalidated_by(self, changed: set[Path | str]) -> set[str]:
        """
        What cache keys are invalidated by these changes?
        
        Args:
            changed: Set of changed file paths or config keys
            
        Returns:
            Set of invalidated cache keys
        """
        result: set[str] = set()
        for path in changed:
            for effect in self._by_dependency.get(path, []):
                result |= effect.invalidates
        return result
    
    def outputs_needing_rebuild(self, changed: set[Path]) -> set[Path]:
        """
        Which outputs need rebuilding given changed inputs?
        
        Transitive: If A depends on B and B changed, A needs rebuild.
        """
        needs_rebuild: set[Path] = set()
        queue = list(changed)
        visited: set[Path | str] = set()
        
        while queue:
            item = queue.pop()
            if item in visited:
                continue
            visited.add(item)
            
            for effect in self._by_dependency.get(item, []):
                needs_rebuild |= effect.outputs
                # Transitive: outputs that depend on our outputs
                queue.extend(effect.outputs)
        
        return needs_rebuild
    
    def save(self, path: Path) -> None:
        """Persist effects for cross-build analysis."""
        data = [
            {
                "outputs": [str(p) for p in e.outputs],
                "depends_on": [str(d) for d in e.depends_on],
                "invalidates": list(e.invalidates),
            }
            for e in self._effects
        ]
        path.write_text(json.dumps(data, indent=2))
    
    @classmethod
    def load(cls, path: Path) -> EffectTracer:
        """Load effects from previous build."""
        tracer = cls()
        if path.exists():
            data = json.loads(path.read_text())
            for item in data:
                effect = Effect(
                    outputs=frozenset(Path(p) for p in item["outputs"]),
                    depends_on=frozenset(
                        Path(d) if "/" in d else d for d in item["depends_on"]
                    ),
                    invalidates=frozenset(item["invalidates"]),
                )
                tracer.record(effect)
        return tracer


# Context manager for automatic effect tracking
@contextmanager
def track_effects(tracer: EffectTracer):
    """
    Context manager that captures effects from render operations.
    
    Usage:
        with track_effects(tracer) as ctx:
            html = render_page(page, ctx)
        # Effect automatically recorded
    """
    ctx = EffectContext(tracer)
    yield ctx
    tracer.record(ctx.to_effect())


# Integration with rendering
def render_page_with_effects(
    page: PageLike,
    site: SiteLike,
    tracer: EffectTracer,
) -> str:
    """Render page and record its effect."""
    # Collect dependencies during render
    deps: set[Path | str] = {page.source_path}
    
    # Template dependencies
    layout = resolve_layout(page, site)
    deps.add(layout.path)
    deps.update(layout.includes)
    
    # Render
    html = render_template(layout, page=page, site=site)
    
    # Record effect
    tracer.record(Effect(
        outputs=frozenset({output_path(page, site)}),
        depends_on=frozenset(deps),
        invalidates=frozenset({f"page:{page.href}"}),
    ))
    
    return html
```

**Detector Replacement Mapping**:

| Current Detector | Effect-Based Replacement |
|------------------|-------------------------|
| `file_detector.py` | `Effect.depends_on` includes source file |
| `template_detector.py` | `Effect.depends_on` includes layout + includes |
| `cascade_tracker.py` | `Effect.depends_on` includes parent `_index.md` |
| `taxonomy_detector.py` | `Effect.invalidates` includes taxonomy keys |
| `data_detector.py` | `Effect.depends_on` includes `data/*.yaml` paths |
| `version_detector.py` | `Effect.depends_on` includes version file |
| `block_detector.py` | (Keep for content-hash optimization) |

**Pros**:
- Single unified dependency model
- Debuggable (inspect effect graph)
- Transitive dependencies automatic
- Thread-safe by design

**Cons**:
- Requires instrumenting all render paths
- Initial implementation complexity
- Migration period with both systems

**Estimated Effort**: 50-70 hours

---

## Recommended Approach

**Recommendation**: **Phased adoption of Options A → C → B → D**

Implement incrementally across multiple release cycles, ordered by risk/reward:

### Phase 1: Protocol Migration (Option A) — v0.2.x

Focus on the worst adoption gaps first.

**Deliverables**:
1. Extend `SectionLike` protocol with missing methods
2. Migrate 176 `Section` usages to `SectionLike` (2% → 80%+ adoption)
3. Migrate ~380 `Page` usages to `PageLike` (11% → 80%+ adoption)
4. Migrate ~270 `Site` usages to `SiteLike` (28% → 80%+ adoption)

**Implementation Order**:
1. **Week 1**: Protocol extensions in `bengal/protocols/core.py`
2. **Week 2**: Section protocol migration (lowest adoption, highest impact)
3. **Week 3**: Page protocol migration
4. **Week 4**: Site protocol migration + validation

**Success Metrics**:
- Protocol adoption ≥ 80% for all three types
- No new concrete type annotations in PRs

**Effort**: 12-16 hours

### Phase 2: Canonical Config (Option C) — v0.3.x

Unify config before touching Site structure.

**Deliverables**:
1. `Config` dataclass with typed sections
2. `UnifiedConfigLoader` replacing both loaders
3. Deprecation warnings for flat access
4. Migration guide for existing sites

**Implementation Order**:
1. **Week 1**: `Config` dataclass and section types
2. **Week 2**: `UnifiedConfigLoader` implementation
3. **Week 3**: Migrate consumers to `config.site.title` pattern
4. **Week 4**: Add deprecation warnings, documentation

**Success Metrics**:
- Zero flat config access in Bengal codebase
- Single config loader

**Effort**: 20-30 hours

### Phase 3: Service Extraction (Option B) — v0.4.x

Extract mixins into services incrementally.

**Implementation Order** (by risk):
1. **ThemeService** (clearest boundary, lowest coupling)
2. **DataService** (simple, self-contained)
3. **QueryService** (replaces registry + caches)
4. **ContentDiscoveryService** (most complex, last)

**Deliverables**:
- Site reduced to data container (~100 lines)
- 7 mixins → 4 focused services
- Dependency injection for testing

**Success Metrics**:
- Site class < 150 lines
- Each service independently testable
- No mixin inheritance in Site

**Effort**: 40-60 hours

### Phase 4: Effect-Traced Builds (Option D) — v0.5.x/v1.0

Replace detector explosion with effect system.

**Implementation Order**:
1. **Week 1-2**: `Effect` dataclass, `EffectTracer` core
2. **Week 3-4**: Instrument page rendering with effects
3. **Week 5-6**: Instrument asset processing, taxonomy
4. **Week 7-8**: Migration, deprecate old detectors

**Deliverables**:
- `Effect` dataclass for dependency tracking
- `EffectTracer` replaces 13 detector classes
- Effect persistence in `.bengal/effects.json`
- Build graph visualization tool

**Success Metrics**:
- All 13 detector files deprecated
- Incremental builds use effect graph only
- Build debugging via `bengal build --show-effects`

**Effort**: 50-70 hours

---

## Architecture Impact

| Subsystem | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|-----------|---------|---------|---------|---------|
| `bengal/core/` | Medium | Low | **High** | Low |
| `bengal/config/` | None | **High** | Low | None |
| `bengal/orchestration/` | Medium | Low | High | **High** |
| `bengal/rendering/` | Medium | Low | Low | Medium |
| `bengal/cache/` | Low | Low | Medium | **High** |
| `tests/` | Medium | Medium | **High** | **High** |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Protocol migration breaks duck-typed code | Medium | Medium | Run full test suite, type check before merge |
| Config migration breaks existing sites | Medium | High | Provide `bengal check-config` validation command |
| Service extraction introduces regressions | Medium | High | Incremental extraction with feature flags |
| Effect system adds runtime overhead | Low | Medium | Benchmark hot paths, optimize recording |
| Multi-release migration fatigues users | Low | Low | Clear versioning, detailed changelogs |

---

## Success Criteria

| Metric | Current | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|--------|---------|---------|---------|---------|---------|
| Section protocol adoption | 2% | 80% | 80% | 80% | 80% |
| Page protocol adoption | 11% | 80% | 80% | 80% | 80% |
| Site protocol adoption | 28% | 80% | 80% | 80% | 80% |
| Config loaders | 2 | 2 | 1 | 1 | 1 |
| Site mixin count | 7 | 7 | 7 | 0 | 0 |
| Mutable `_` fields in Site | 25 | 25 | 25 | 8 | 4 |
| Incremental detector files | 13 | 13 | 13 | 13 | 1 |

---

## Implementation Timeline

| Phase | Version | Quarter | Effort | Dependencies |
|-------|---------|---------|--------|--------------|
| Phase 1: Protocol Migration | v0.2.x | Q1 2026 | 12-16 hours | None |
| Phase 2: Canonical Config | v0.3.x | Q2 2026 | 20-30 hours | None |
| Phase 3: Service Extraction | v0.4.x | Q2-Q3 2026 | 40-60 hours | Phase 2 |
| Phase 4: Effect System | v0.5.x/v1.0 | Q3-Q4 2026 | 50-70 hours | Phase 3 |

**Total Estimated Effort**: 122-176 hours across 4 quarters

---

## Appendix: Current vs v2 Architecture Comparison

### Current Architecture

```
Site (god object with 7 mixins)
├── SitePropertiesMixin (800 lines of properties)
├── PageCachesMixin (page list caches)
├── SiteFactoriesMixin (factory methods)
├── ThemeIntegrationMixin (theme resolution)
├── ContentDiscoveryMixin (content discovery)
├── DataLoadingMixin (data/ loading)
├── SectionRegistryMixin (O(1) lookups)
└── 25 mutable _fields

Config Loading
├── ConfigLoader (flattens site.*, build.*)
├── ConfigDirectoryLoader (different flattening)
└── Dual access: config["title"] OR config["site"]["title"]

Incremental Builds
├── block_detector.py
├── cache_manager.py
├── cascade_tracker.py
├── data_detector.py
├── file_detector.py
├── taxonomy_detector.py
├── template_detector.py
├── version_detector.py
└── ... (13 files with bespoke logic)
```

### v2 Architecture

```
Site (data container only)
├── config: Config (immutable, typed sections)
├── content: ContentRegistry (pages, sections, assets)
└── root_path: Path

Services (composable, testable)
├── ThemeService (theme resolution)
├── DataService (data/ loading)
├── QueryService (page/section lookups)
└── ContentDiscoveryService (content discovery)

Config (canonical nested structure)
├── UnifiedConfigLoader (single loader)
└── Config dataclass: config.site.title (always nested)

EffectTracer (unified dependency tracking)
└── Effect(outputs, depends_on, invalidates)
```

### Key Differences

| Aspect | Current | v2 |
|--------|---------|-----|
| Site class | God object with 7 mixins | Data container only |
| Config access | `config["title"]` or `config["site"]["title"]` | `config.site.title` only |
| Config typing | `dict[str, Any]` | Typed dataclasses |
| Theme resolution | `site._theme_obj` mixin field | `ThemeService(site).resolve()` |
| Incremental tracking | 13 detector classes | Single `EffectTracer` |
| Type annotations | Mixed concrete/protocol | Protocols everywhere |
| Mutability | 25 `_` fields | 4 managed cache fields |
