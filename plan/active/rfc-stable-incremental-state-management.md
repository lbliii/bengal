# RFC: Stable State Management for Incremental Builds

**Title**: Stable State Management for Incremental Builds  
**Author**: AI + Human Reviewer  
**Date**: 2025-10-26  
**Status**: Draft  
**Confidence**: 91% 🟢

---

## Executive Summary

Bengal's incremental build system suffers from **object identity fragmentation** where Section objects are recreated on every build, breaking references from PageProxy objects. This causes pages to lose section relationships during live server rebuilds, resulting in wrong URLs (`/page/` instead of `/section/page/`), missing cascaded metadata, and broken navigation.

**Recommended Solution**: Path-based references with lazy lookup (Option B) balances reliability, performance, and implementation complexity. Provides stable references that survive object recreation while maintaining Bengal's fast build times (256 pps).

---

## Problem Statement

### Current State

Bengal uses three systems for state management:

1. **Live Object Graph** (`bengal/core/site.py:764-799`)
   - `Site.pages` (list of Page/PageProxy objects)
   - `Site.sections` (list of Section objects)
   - Pages reference sections via `page._section: Section`

2. **Build Cache** (`bengal/cache/build_cache.py:20-82`)
   - Stores: file hashes, dependencies, parsed content
   - **Does NOT store**: object references (by design)
   - Persisted as JSON (`.bengal-cache.json`)

3. **Discovery Cache** (`bengal/cache/page_discovery_cache.py:84-163`)
   - Stores: page metadata (title, date, tags, section **path**)
   - Enables PageProxy lazy loading
   - Persisted as JSON (`.bengal/page_metadata.json`)

**Evidence**: Discovery cache stores section as `section: str | None` (line 43), not as object reference.

### Pain Points

**Problem 1: Object Identityis Unstable**

```python
# Build 1
section_a = Section("getting-started", path=Path("content/getting-started"))
page._section = section_a  # Reference to 0x1234

# Dev server rebuilds (user edits _index.md)
site.reset_ephemeral_state()  # Clears site.sections
site.sections = []

# Build 2  
section_a = Section("getting-started", path=Path("content/getting-started"))  
# NEW object at 0x5678!
```

**Evidence**: `bengal/core/site.py:779-782`
```python
# Content to be rediscovered
self.pages = []
self.sections = []
self.assets = []
```

**Problem 2: PageProxy References Become Stale**

When incremental builds use PageDiscoveryCache:

1. `_discover_with_cache()` calls `_discover_full()` internally (`bengal/discovery/content_discovery.py:258`)
2. Creates **new Section objects** with new memory addresses
3. PageProxy objects created from cache still reference **old Section objects** from previous build
4. Result: `proxy._section` points to deleted section → wrong URL generation

**Evidence**: `bengal/discovery/content_discovery.py:288-290`
```python
# Copy section and site relationships
proxy._section = page._section  # This is the OLD section!
proxy._site = page._site
```

**Problem 3: Cascade Application Fails**

Cascade engine relies on `page._section` to traverse hierarchy (`bengal/core/cascade_engine.py:21-52`). When sections are recreated:
- Old section hierarchy is orphaned
- New sections don't have cascade applied to proxies
- Pages lose `type: doc` and other cascaded values

### User Impact

**Live Server (Dev Workflow)**:
- ❌ Wrong URLs: `/writer-quickstart/` instead of `/getting-started/writer-quickstart/`
- ❌ Missing sidebars: Pages lose `type: doc` cascade
- ❌ Broken navigation: Links point to wrong URLs
- ❌ Manual fix required: Restart server to rebuild clean state

**Affected Users**: Content writers, theme developers, core contributors

**Frequency**: Every time `_index.md` or directory structure changes during live server

**Current Workaround**: Restart dev server for full rebuild (defeats purpose of incremental builds)

---

## Goals & Non-Goals

### Goals

1. **Stability**: Page-section relationships survive object recreation
2. **Performance**: Maintain 256 pps build rate (15-50x incremental speedup)
3. **Reliability**: No stale references, ever
4. **Ergonomics**: Zero user-facing changes, transparent fix
5. **Live Server**: Support create/modify/delete operations without restart

### Non-Goals

- Complete architectural rewrite (preserve existing codebase structure)
- Remove PageProxy system (it's a good optimization)
- Change user-facing APIs or configuration
- Support distributed/concurrent builds (out of scope)

---

## Architecture Impact

### Affected Subsystems

**Core** (`bengal/core/`): HIGH impact
- Modules: `page/__init__.py`, `page/metadata.py`, `page/proxy.py`, `section.py`, `site.py`
- Changes: Path-based lookups, section registry
- Lines affected: ~300

**Orchestration** (`bengal/orchestration/`): MEDIUM impact  
- Modules: `content.py`, `build.py`
- Changes: Section setup order, cascade timing
- Lines affected: ~50

**Discovery** (`bengal/discovery/`): MEDIUM impact
- Modules: `content_discovery.py`
- Changes: Section reuse logic
- Lines affected: ~100

**Cache** (`bengal/cache/`): LOW impact
- Modules: No changes (already stores paths, not objects)
- Changes: None

**Server** (`bengal/server/`): LOW impact
- Modules: `build_handler.py`
- Changes: Validation of fix works correctly
- Lines affected: ~20 (tests)

---

## Design Options

### Option A: Preserve Section Objects in Incremental Builds

**Description**: Don't clear `site.sections` in `reset_ephemeral_state()` when `incremental=True`.

```python
def reset_ephemeral_state(self, preserve_structure: bool = False) -> None:
    """Clear ephemeral state, optionally preserving section structure."""
    self.pages = []

    if not preserve_structure:
        self.sections = []
    else:
        # Keep section objects, but clear their page lists
        for section in self.sections:
            section.pages = []
            self._clear_section_recursive(section)
```

**Pros**:
- ✅ Minimal code changes (~50 lines)
- ✅ Zero performance impact
- ✅ Object identity preserved
- ✅ Fast to implement (1-2 days)

**Cons**:
- ❌ **Doesn't handle deleted/moved sections** (stale sections persist)
- ❌ **Doesn't handle new sections properly** (need merge logic)
- ❌ Requires complex reconciliation when structure changes
- ❌ Still brittle: what if section metadata changes?

**Complexity**: Simple  
**Evidence**: Similar pattern in `bengal/orchestration/section.py:50-78` (selective finalization)

**Verdict**: ❌ **Not Recommended** - Trades one brittleness for another

---

### Option B: Path-Based References with Lazy Lookup (RECOMMENDED)

**Description**: Replace direct object references with path-based lookups through a section registry.

```python
# Page stores path, not object
@dataclass
class Page:
    _section_path: Path | None = None  # Store path instead of object

    @property
    def _section(self) -> Section | None:
        """Lazy lookup via site registry."""
        if not self._section_path or not self._site:
            return None
        return self._site.get_section_by_path(self._section_path)

# Site maintains fast lookup registry
class Site:
    _section_registry: dict[Path, Section] = {}  # O(1) lookup

    def get_section_by_path(self, path: Path) -> Section | None:
        return self._section_registry.get(path)

    def register_sections(self) -> None:
        """Build section registry after discovery."""
        self._section_registry = {s.path: s for s in self.sections}
```

**Pros**:
- ✅ **Stable references** survive object recreation
- ✅ **Handles all changes**: create/delete/move sections
- ✅ **O(1) lookup performance** via dict registry
- ✅ **Clean separation**: paths are immutable, objects are ephemeral
- ✅ **Cache-friendly**: paths already stored in PageDiscoveryCache
- ✅ **Transparent**: no user-facing changes

**Cons**:
- ❌ Larger refactor (~300 lines across 6 files)
- ❌ Small lookup overhead (dict access per property call)
- ❌ Requires careful migration (existing code uses `_section` directly)

**Complexity**: Moderate  
**Implementation Time**: 3-5 days  
**Performance Impact**: <1% (dict lookup is ~10ns, negligible)

**Evidence**: Similar pattern already exists:
- `bengal/cache/page_discovery_cache.py:43` stores `section: str | None`
- `bengal/core/page/metadata.py:175-184` uses path-based fallback URL

**Verdict**: ✅ **RECOMMENDED** - Best long-term solution

---

### Option C: Immutable Value Objects + Functional Updates

**Description**: Make Page/Section immutable value objects, use functional updates instead of mutation.

```python
from dataclasses import dataclass, replace

@dataclass(frozen=True)  # Immutable
class Page:
    source_path: Path
    title: str
    _section_path: Path | None

    def with_section(self, section_path: Path) -> Page:
        """Return new Page with updated section."""
        return replace(self, _section_path=section_path)

# Updates create new objects
new_pages = [page.with_section(new_section.path) for page in old_pages]
site = replace(site, pages=new_pages, sections=new_sections)
```

**Pros**:
- ✅ **No stale references possible** (immutability prevents it)
- ✅ **Easier to reason about** (pure functions, no side effects)
- ✅ **Thread-safe by design** (immutable = safe to share)
- ✅ **Future-proof** for distributed builds

**Cons**:
- ❌ **Major architectural rewrite** (~2000+ lines)
- ❌ **Breaking change** for plugins/extensions
- ❌ **Memory overhead** (copying objects instead of mutating)
- ❌ **Performance impact** (~5-10% slower due to copying)
- ❌ **Implementation time**: 3-4 weeks

**Complexity**: Complex  
**Evidence**: Against Bengal's design principle of "fast and practical" (`architecture/design-principles.md`)

**Verdict**: ❌ **Not Recommended** - Too invasive for the benefit

---

## Recommended Solution: Option B (Path-Based References)

### Detailed Design

#### API Changes

**Page Model** (`bengal/core/page/__init__.py`):
```python
@dataclass
class Page:
    # CRITICAL: Remove _section as dataclass field to prevent bypassing setter
    # BEFORE (delete this):
    # _section: Section | None = field(default=None, repr=False)

    # AFTER: Add path storage field
    _section_path: Path | None = field(default=None, repr=False)
    _site: Site | None = field(default=None, repr=False)

    # Track missing section warnings to avoid log spam
    _missing_section_warnings: dict[str, int] = field(
        default_factory=dict, repr=False, init=False
    )

    @property
    def _section(self) -> Section | None:
        """Get section via path lookup (lazy, stable reference)."""
        if not self._section_path or not self._site:
            return None
        return self._site.get_section_by_path(self._section_path)

    @_section.setter
    def _section(self, section: Section | None) -> None:
        """
        Set section (stores path, not object).

        This setter is called by all code that assigns page._section = ...
        including helpers, content discovery, and cascade application.
        """
        self._section_path = section.path if section else None
```

**PageProxy** (`bengal/core/page/proxy.py`):
```python
class PageProxy:
    def __init__(self, source_path: Path, metadata: Any, loader: callable):
        self._source_path = source_path
        self._metadata = metadata
        self._loader = loader
        self._section_path: Path | None = None  # Store path, not object
        self._site: Any | None = None

    @property
    def _section(self) -> Section | None:
        """Lazy section lookup (matches Page interface)."""
        if self._lazy_loaded:
            # If loaded, delegate to real page
            return self._loaded_page._section

        # Otherwise, lookup via path
        if not self._section_path or not self._site:
            return None
        return self._site.get_section_by_path(self._section_path)

    @_section.setter
    def _section(self, section: Section | None) -> None:
        """Set section path."""
        self._section_path = section.path if section else None

    def _ensure_loaded(self) -> None:
        """Load full page on demand."""
        if self._lazy_loaded:
            return

        # Load full page
        self._loaded_page = self._loader(self._source_path)

        # CRITICAL: Transfer path, not object reference
        self._loaded_page._section_path = self._section_path
        self._loaded_page._site = self._site

        self._lazy_loaded = True
```

**Site Registry** (`bengal/core/site.py`):
```python
@dataclass
class Site:
    # Add registry
    _section_registry: dict[Path, Section] = field(default_factory=dict, repr=False)

    def _normalize_section_path(self, path: Path) -> Path:
        """
        Normalize section path for registry key.

        - Relative to content/ directory
        - Resolve symlinks
        - Lowercase on case-insensitive filesystems (macOS/Windows)
        """
        try:
            # Make relative to content root
            rel_path = path.relative_to(self.root_path / "content")
        except ValueError:
            rel_path = path

        # Resolve symlinks
        try:
            rel_path = rel_path.resolve()
        except (OSError, RuntimeError):
            pass  # Keep original if resolution fails

        # Normalize case on case-insensitive systems
        import platform
        if platform.system() in ("Darwin", "Windows"):
            rel_path = Path(str(rel_path).lower())

        return rel_path

    def get_section_by_path(self, path: Path) -> Section | None:
        """O(1) section lookup by normalized path."""
        normalized = self._normalize_section_path(path)
        return self._section_registry.get(normalized)

    def register_sections(self) -> None:
        """
        Build section registry (called after content discovery).

        Thread-safety: Built once per build, then treated as read-only
        during parallel rendering. Safe for concurrent reads.
        """
        start_time = time.time()
        self._section_registry.clear()
        self._register_section_recursive(self.sections)

        elapsed_ms = (time.time() - start_time) * 1000
        logger.debug(
            "section_registry_built",
            count=len(self._section_registry),
            elapsed_ms=f"{elapsed_ms:.2f}"
        )

    def _register_section_recursive(self, sections: list[Section]) -> None:
        """Recursively register sections and subsections."""
        for section in sections:
            normalized = self._normalize_section_path(section.path)
            self._section_registry[normalized] = section
            if section.subsections:
                self._register_section_recursive(section.subsections)
```

**Content Discovery** (`bengal/discovery/content_discovery.py:288-290`):
```python
# BEFORE
proxy._section = page._section  # Stores object
proxy._site = page._site

# AFTER  
proxy._section = page._section  # Now stores path via setter
proxy._site = page._site

def _cache_is_valid(self, page: Page, cached: PageProxy) -> bool:
    """Check if cached page is still valid."""
    # ... existing checks ...

    # UPDATED: Compare section paths (normalized), not object identity
    cached_section_path = cached._section_path
    current_section_path = page._section.path if page._section else None

    if cached_section_path != current_section_path:
        return False  # Section changed

    return True
```

**Content Orchestrator** (`bengal/orchestration/content.py:172-203`):
```python
def discover_and_setup(self):
    """
    Discover content and set up relationships.

    BUILD ORDERING INVARIANT (critical for correctness):
    1. discover_content()       → Creates Page/Section objects
    2. register_sections()      → Builds path→section registry
    3. setup_page_references()  → Sets page._section (stores paths via setter)
    4. apply_cascades()         → Traverses via page._section (lookups via registry)
    5. generate_urls()          → Uses section hierarchy for URL paths

    If structure mutates later (rare), call register_sections() again.
    """
    # ... discovery ...

    # CRITICAL: Register sections BEFORE setting up references
    self.site.register_sections()  # NEW - Must come before setup_page_references

    # Now set up page references (paths will resolve correctly)
    self._setup_page_references()
    self._apply_cascades()
```

#### Data Flow

**Build 1 (Initial)**:
1. Content discovery creates Section objects
2. `site.register_sections()` builds path→section registry
3. `page._section = section` → stores `section.path` internally
4. `page._section` property → looks up via registry → returns current section

**Build 2 (Incremental, _index.md modified)**:
1. `site.reset_ephemeral_state()` → clears sections, pages, registry
2. Content discovery creates **new** Section objects (different memory addresses)
3. `site.register_sections()` rebuilds registry with **new** sections
4. PageProxy from cache has stored `_section_path`
5. `proxy._section` property → looks up via **new** registry → returns **new** section ✅
6. URLs generated correctly from current section hierarchy ✅

#### Error Handling

**Missing Section** (deleted/moved):
```python
@property
def _section(self) -> Section | None:
    if not self._section_path or not self._site:
        return None

    section = self._site.get_section_by_path(self._section_path)
    if section is None:
        # Counter-gated warnings to avoid noisy dev-server logs
        path_key = str(self._section_path)
        count = self._missing_section_warnings.get(path_key, 0)

        if count < 3:
            # Warn for first 3 occurrences per path
            logger.warning(
                "section_not_found",
                page=str(self.source_path),
                section_path=path_key,
                suggestion="Section may have been deleted or moved",
                warning_count=count + 1
            )
            self._missing_section_warnings[path_key] = count + 1
        elif count == 3:
            # Summary message on 4th occurrence
            logger.warning(
                "section_not_found_repeated",
                page=str(self.source_path),
                section_path=path_key,
                note="Further warnings suppressed"
            )
            self._missing_section_warnings[path_key] = count + 1
        # After 4th occurrence, silently fail

    return section
```

**URL Generation Fallback** (already exists):
- Uses `_fallback_url()` when section is None
- Based on page slug: `f"/{self.slug}/"`

#### Configuration

**Feature Flag** (for safe rollout):
```yaml
# bengal.toml or config/build.yaml
build:
  stable_section_references: true  # Default: true (new behavior)
```

**Rollback Plan**:
- If critical issues discovered post-release, users can set `stable_section_references: false`
- Falls back to direct object references (pre-fix behavior)
- Should be temporary - flag removed after 2-3 releases of stability

**Default**: Enabled (new behavior) - Users should not need to change this

#### Testing Strategy

**Unit Tests**:
```python
# tests/unit/test_page_section_references.py

def test_section_reference_survives_recreation():
    """Section references remain valid after object recreation."""
    site = Site.from_config(tmp_path)
    section1 = Section("docs", path=Path("content/docs"))
    site.sections = [section1]
    site.register_sections()

    page = Page(source_path=Path("content/docs/guide.md"))
    page._site = site
    page._section = section1

    # Simulate rebuild - create new section object
    section2 = Section("docs", path=Path("content/docs"))
    site.sections = [section2]
    site.register_sections()

    # Reference should resolve to new section
    assert page._section is section2  # NEW object
    assert page._section.name == "docs"

def test_page_url_stable_across_rebuilds():
    """Page URLs remain correct after section recreation."""
    # Similar test verifying URL generation

def test_proxy_url_without_forcing_load():
    """PageProxy.url correct after rebuild without loading full content."""
    # Create proxy from cache
    proxy = PageProxy(
        source_path=Path("content/docs/guide.md"),
        metadata=cached_metadata,
        loader=load_page
    )
    proxy._site = site
    proxy._section_path = Path("content/docs")

    # Rebuild sections
    site.sections = [new_section]
    site.register_sections()

    # URL should be correct WITHOUT triggering full load
    assert proxy.url == "/docs/guide/"
    assert not proxy._lazy_loaded  # Verify no load occurred

def test_section_rename_treated_as_delete_create():
    """Section rename/move results in fallback URL or correct new URL."""
    page = Page(source_path=Path("content/old/guide.md"))
    page._site = site
    page._section_path = Path("content/old")  # Old path

    # Section renamed: old deleted, new created
    new_section = Section("new", path=Path("content/new"))
    site.sections = [new_section]
    site.register_sections()

    # page._section returns None (old path not in registry)
    assert page._section is None

    # URL falls back to slug-based
    assert page.url == "/guide/"  # Fallback behavior

def test_registry_lookup_performance():
    """Section registry lookup performance < 1µs for 10K sections."""
    import time

    # Create 10K sections
    sections = [
        Section(f"section-{i}", path=Path(f"content/s{i}"))
        for i in range(10_000)
    ]
    site.sections = sections
    site.register_sections()

    # Measure lookup time
    path = Path("content/s5000")
    start = time.perf_counter()
    for _ in range(1000):
        _ = site.get_section_by_path(path)
    elapsed = (time.perf_counter() - start) / 1000

    assert elapsed < 1e-6  # < 1µs per lookup

def test_path_normalization_cross_platform():
    """Path normalization handles case-insensitive filesystems."""
    # macOS/Windows: case-insensitive
    # Linux: case-sensitive
    section = Section("Docs", path=Path("content/Docs"))
    site.sections = [section]
    site.register_sections()

    # Lookup with different case
    result = site.get_section_by_path(Path("content/docs"))

    import platform
    if platform.system() in ("Darwin", "Windows"):
        assert result is section  # Case-insensitive match
    else:
        assert result is None  # Case-sensitive no match
```

**Integration Tests**:
```python
# tests/integration/test_incremental_section_stability.py

def test_live_server_section_changes():
    """Live server maintains correct URLs when _index.md changes."""
    # Simulate dev server workflow
    # 1. Build
    # 2. Modify _index.md (change cascade)
    # 3. Rebuild (incremental)
    # 4. Verify URLs and cascade still correct

def test_dev_server_index_edit_preserves_cascades():
    """Editing _index.md preserves cascades and URLs for all descendant pages."""
    site = build_site(tmp_path)

    # Verify initial state
    page = site.get_page("content/docs/guide.md")
    assert page.type == "doc"  # From cascade
    assert page.url == "/docs/guide/"

    # Edit _index.md (change cascade)
    index_path = tmp_path / "content/docs/_index.md"
    index_path.write_text("---\ncascade:\n  type: tutorial\n---\n")

    # Incremental rebuild
    site.build(incremental=True)

    # Verify cascade updated
    page = site.get_page("content/docs/guide.md")
    assert page.type == "tutorial"  # Updated cascade
    assert page.url == "/docs/guide/"  # URL still correct

def test_large_site_registry_memory_bounded():
    """10K sections: registry memory growth bounded, rebuild stable."""
    # Create 10K sections with 10 pages each
    # Measure memory before/after registry build
    # Assert < 50MB for registry
    # Verify all page URLs correct
```

**Performance Tests**:
```python
# tests/performance/benchmark_section_lookup.py

def test_section_lookup_performance():
    """Section lookups remain O(1) with registry."""
    # Covered in unit tests above

def test_full_build_performance_regression():
    """Full build performance within 1% of baseline (256 → 253+ pps)."""
    import time

    # Build 1000-page site
    start = time.time()
    site.build(parallel=True)
    elapsed = time.time() - start

    pages_per_sec = 1000 / elapsed

    # Baseline: 256 pps (3.90s for 1000 pages)
    # Target: 253+ pps (< 1% regression)
    assert pages_per_sec >= 253, f"Performance regression: {pages_per_sec} pps"

def test_incremental_build_speedup_maintained():
    """Incremental builds maintain 15-50x speedup."""
    # Full build
    start = time.time()
    site.build(parallel=True, incremental=False)
    full_time = time.time() - start

    # Modify 1 file
    (tmp_path / "content/page1.md").touch()

    # Incremental rebuild
    start = time.time()
    site.build(parallel=True, incremental=True)
    inc_time = time.time() - start

    speedup = full_time / inc_time
    assert speedup >= 15, f"Incremental speedup too low: {speedup}x"
```

---

## Tradeoffs & Risks

### Tradeoffs

**Tradeoff 1: Indirection vs Simplicity**
- **Lose**: Direct object access (`page._section` is now a property call + dict lookup)
- **Gain**: Stability (references never stale), resilience (handles structure changes)
- **Impact**: Minimal performance cost (<1%), major reliability improvement

**Tradeoff 2: Migration Effort vs Long-Term Benefit**
- **Lose**: 3-5 days implementation time, ~300 lines changed
- **Gain**: Eliminates entire class of bugs, improves dev server UX
- **Impact**: One-time cost for permanent fix

### Risks

**Risk 1: Breaking Existing Code**
- **Likelihood**: Medium
- **Impact**: High (if plugins/tests access `_section` directly)
- **Mitigation**:
  - Property interface maintains backward compatibility
  - Comprehensive test suite
  - Gradual rollout with feature flag

**Risk 2: Performance Regression**
- **Likelihood**: Low
- **Impact**: Medium (user-facing build times)
- **Mitigation**:
  - Benchmark before/after
  - Dict lookup is O(1) and fast (~10ns)
  - Expected <1% slowdown (negligible)

**Risk 3: Incomplete Migration**
- **Likelihood**: Medium
- **Impact**: Medium (some code paths still broken)
- **Mitigation**:
  - Systematic grep for `_section` usage
  - Update all assignment sites
  - Integration tests covering all code paths

---

## Performance & Compatibility

### Performance Impact

**Lookup Overhead**:
- Dict access: ~10-50ns per lookup
- Property call: ~20ns overhead
- **Total**: ~30-70ns per `page._section` access
- **Baseline**: Page rendering is ~4ms (4,000,000ns)
- **Impact**: 0.001-0.002% per page

**Measured Impact** (estimated):
- Full build (1000 pages): 3.90s → 3.91s (+0.25%)
- Incremental build: 0.5s → 0.5s (no change, sections not recreated)

**Confidence**: 90% 🟢 (similar patterns exist, dict lookups are fast)

### Compatibility

**Breaking Changes**: None (property interface maintains existing API)

**Migration Path**:
1. Add path storage fields alongside object references
2. Implement property wrappers
3. Update assignment sites to use properties
4. Run full test suite
5. Remove direct object references

**Deprecation Timeline**: N/A (internal change, no user-facing API)

---

## Implementation Phases

### Phase 1: Foundation (Day 1-2)

**Deliverables**:
- Add `_section_path` field to Page
- Add `_section` property with lazy lookup
- Add `get_section_by_path()` to Site
- Add section registry
- Unit tests for lookup mechanism

**Success Criteria**:
- All tests pass with property-based access
- Registry builds correctly
- Lookups are O(1)

### Phase 2: Migration (Day 3-4)

**Critical Migration Steps**:

1. **Remove dataclass field** (`bengal/core/page/__init__.py`):
   ```python
   # DELETE THIS LINE:
   # _section: Section | None = field(default=None, repr=False)
   ```
   This prevents bypassing the property setter.

2. **Audit all assignment sites**:
   ```bash
   # Find all places that assign _section
   rg "\\._section\s*=" bengal/
   ```
   Common locations:
   - `bengal/orchestration/content.py` - `_setup_page_references()`
   - `bengal/utils/page_initializer.py` - Page creation helpers
   - `bengal/discovery/content_discovery.py` - Proxy creation
   - Any cascade application code

3. **Update helpers** - All code using `page._section = ...` will automatically use property setter (no changes needed), but verify behavior.

4. **Update cache comparisons** (`bengal/discovery/content_discovery.py`):
   - Change from object identity checks to path comparisons
   - Use normalized paths

5. **Update proxy transfer** (`bengal/core/page/proxy.py`):
   - Transfer `_section_path` in `_ensure_loaded()`, not object

**Deliverables**:
- ContentOrchestrator calls `register_sections()`
- PageProxy uses path storage
- All assignment sites verified
- Cache comparison uses paths
- Integration tests

**Success Criteria**:
- No direct `_section` field exists as dataclass field
- All assignment sites use property (automatic via setter)
- Live server test passes
- Incremental builds maintain correct URLs

### Phase 3: Validation & Polish (Day 5)

**Deliverables**:
- Performance benchmarks (microbenchmark + full build)
- Error handling for missing sections (counter-gated warnings)
- Path normalization (cross-platform)
- Thread-safety verification
- Registry metrics logging
- Plugin author documentation
- Final integration tests

**Microbenchmark Targets**:
- Section registry build: < 10ms for 10K sections
- Section lookup: < 1µs per call
- Full build: 253+ pages/sec (< 1% regression)
- Incremental build: 15-50x speedup maintained

**Documentation Updates**:
- `architecture/object-model.md` - Document path-based references
- `CONTRIBUTING.md` - Note for plugin authors (see below)

**Success Criteria**:
- Performance within 1% of baseline (validated with benchmarks)
- All edge cases handled (missing sections, renames, case-insensitive FS)
- Dev server works flawlessly
- Logs show registry metrics at debug level
- Plugin contract documented

---

## Plugin Author Documentation

**Contract for `page._section`** (add to `CONTRIBUTING.md`):

```markdown
### Working with Page-Section References

As of Bengal v0.2.0, `page._section` uses **path-based lazy lookup** for stability across rebuilds.

**What this means for plugin authors**:

✅ **DO**:
- Access `page._section` as normal - it behaves like a property
- Assign `page._section = section` - setter stores path automatically
- Use `page._section.name`, `page._section.path`, etc. - all work transparently

❌ **DON'T**:
- Store `Page` or `Section` objects across builds (object identity not stable)
- Compare sections with `is` - use `section.path == other.path` instead
- Persist object references in caches - store paths as strings

**Example (plugin code)**:
```python
# ✅ GOOD: Works with path-based references
def get_section_pages(site, section_path: str) -> list[Page]:
    section = site.get_section_by_path(Path(section_path))
    return section.pages if section else []

# ❌ BAD: Assumes object identity is stable
cached_section = page._section  # Don't store this across builds
# Later...
if page._section is cached_section:  # This will fail!
    ...

# ✅ GOOD: Compare by path
cached_path = page._section.path
# Later...
if page._section and page._section.path == cached_path:
    ...
```

**Performance**: Section lookups are O(1) via dict registry (< 1µs per call).
```

---

## Open Questions

- [x] **Q1**: Should we add section registry to BuildCache for persistence?
  - **Resolution**: No, registry is cheap to rebuild (< 10ms for 10K sections)

- [x] **Q2**: How to handle section renames/moves?
  - **Resolution**: Treat as delete+create. Old path not in registry → `_section` returns `None` → URL fallback kicks in (slug-based)

- [x] **Q3**: Should we add caching to section lookups?
  - **Resolution**: No, dict lookup already O(1) and fast (<1µs)

- [x] **Q4**: Path normalization strategy?
  - **Resolution**: Relative to content/, lowercased on case-insensitive FS, symlinks resolved

- [x] **Q5**: Thread-safety for parallel rendering?
  - **Resolution**: Registry built once per build, then read-only. Safe for concurrent reads.

- [x] **Q6**: How to avoid noisy logs for missing sections?
  - **Resolution**: Counter-gated warnings (first 3, then summary, then silent)

---

## Success Metrics

**Reliability**:
- ✅ Zero stale reference bugs in dev server
- ✅ URLs remain correct after any file change

**Performance**:
- ✅ Build time within 1% of current (256 pps → 253+ pps)
- ✅ Incremental speedup maintained (15-50x)

**Ergonomics**:
- ✅ Dev server "just works" for create/modify/delete
- ✅ No user-facing changes or configuration needed

---

## Alternatives Considered

See Design Options section for full analysis of:
- Option A: Preserve Section Objects (rejected - trades one brittleness for another)
- Option C: Immutable Value Objects (rejected - too invasive)

---

## References

**Evidence Sources**:
- `bengal/core/site.py:764-799` - reset_ephemeral_state()
- `bengal/core/page/__init__.py:100-102` - _section reference
- `bengal/core/page/proxy.py:38-56` - PageProxy lifecycle
- `bengal/discovery/content_discovery.py:238-320` - cache discovery
- `bengal/cache/page_discovery_cache.py:36-47` - metadata storage
- `architecture/performance.md:1-129` - performance baselines

**Related Issues**:
- User report: "URLs wrong after modifying _index.md"
- User report: "Pages lose sidebar after creating new files"

---

## Confidence Scoring

**Formula**: Evidence(40) + Consistency(30) + Recency(15) + Tests(15)

- **Evidence** (39/40): Extensive code analysis, clear root cause, ChatGPT validation
- **Consistency** (28/30): Similar patterns exist (URL fallback, cache paths), proven approach, cross-platform considerations added
- **Recency** (14/15): Code reviewed Oct 2025, recent codebase state
- **Tests** (10/15): Comprehensive test plan added, specific test cases defined

**Total**: 91/100 = **91% 🟢 HIGH**

**Gate**: RFC requires ≥85% → **PASS**

**Improvements Made**:
- ✅ Added path normalization for cross-platform consistency
- ✅ Specified build ordering invariant
- ✅ Added thread-safety guarantees
- ✅ Counter-gated warnings to reduce log noise
- ✅ Explicit migration checklist with critical steps
- ✅ Plugin author documentation and contract
- ✅ Performance microbenchmark targets defined
- ✅ Feature flag for safe rollout

---

## Next Steps

**Before Implementation**:
- [ ] Review RFC with Bengal maintainers
- [ ] Validate performance estimates with prototype
- [ ] Create detailed migration checklist

**Implementation** (run `::plan`):
- [ ] Break down into atomic tasks
- [ ] Assign priority and dependencies
- [ ] Draft commit messages

**Validation** (run `::validate`):
- [ ] Verify implementation meets gates
- [ ] Confirm test coverage
- [ ] Measure actual performance impact

---

**Status**: Draft (ready for review)  
**Recommended Next Command**: `::plan` (convert RFC to implementation tasks)
