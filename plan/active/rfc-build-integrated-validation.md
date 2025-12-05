# RFC: Build-Integrated Validation Architecture

**Status**: Implemented
**Created**: 2025-12-05
**Author**: AI Pair
**Depends On**: `rfc-lazy-build-artifacts.md` (implemented)
**Related**: `bengal/health/`, `bengal/orchestration/`

---

## Summary

Eliminate redundant disk I/O in health checks by integrating validation into the build pipeline. Currently, validators re-read source files after the build completes, adding 4-8 seconds to builds. This RFC proposes validating content during the build phase when files are already in memory.

**Expected Impact**: 95%+ reduction in health check time (4.6s → <200ms)

---

## Problem Statement

### Current Architecture (Redundant I/O)

```
BUILD PHASE                          HEALTH CHECK PHASE
───────────                          ──────────────────
1. Read 773 files from disk          1. Read 773 files AGAIN from disk 🐌
2. Parse markdown                    2. Parse directive patterns AGAIN
3. Render HTML                       3. Scan for issues
4. Write output                      4. Build knowledge graph

Total: 3.1s                          Total: 4.6s (mostly disk I/O!)
```

### Evidence

From actual build output (773 pages):
```
✓ Rendering 3102ms (773 pages)
✓ Health check 7949ms              ← 2.5x longer than rendering!

🐌 Slowest: Directives: 4637ms     ← Re-reads every source file!
```

The `DirectiveValidator` calls `page.source_path.read_text()` for every page:

```python
# bengal/health/validators/directives/analysis.py:68
content = page.source_path.read_text(encoding="utf-8")  # 773 disk reads!
```

### Why This Happens

1. **PageProxy lazy loading**: After build, many pages are `PageProxy` objects with content unloaded
2. **Validators designed for standalone use**: They don't assume build context is available
3. **No shared content cache**: Each validator independently reads files it needs

---

## Proposed Solution

### Architecture: Build-Time Validation with Tiered Execution

```
┌─────────────────────────────────────────────────────────────┐
│                      BUILD PHASE                             │
│                                                              │
│  ┌─────────┐    ┌─────────────┐    ┌──────────┐             │
│  │  Read   │ →  │   Parse +   │ →  │  Render  │             │
│  │  File   │    │  Validate   │    │   HTML   │             │
│  └─────────┘    └─────────────┘    └──────────┘             │
│       ↓               ↓                  ↓                   │
│  raw_content    directive_data      link_index              │
│                                                              │
│              ┌─────────────────────────────┐                │
│              │      BuildContext           │                │
│              │  - page_contents (dict)     │                │
│              │  - directive_analysis       │                │
│              │  - link_index               │                │
│              │  - knowledge_graph (lazy)   │                │
│              └─────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   HEALTH CHECK PHASE                         │
│                                                              │
│  TIER 1 (build): Syntax, links, directives    → <100ms     │
│  TIER 2 (full):  + Knowledge graph            → ~500ms     │
│  TIER 3 (ci):    + External link checking     → ~30s       │
└─────────────────────────────────────────────────────────────┘
```

### Key Changes

#### 1. Store Raw Content in BuildContext

```python
# bengal/utils/build_context.py
from threading import Lock

@dataclass
class BuildContext:
    site: Site

    # Content cache - populated during discovery, shared by validators
    _page_contents: dict[str, str] = field(default_factory=dict)
    _cache_lock: Lock = field(default_factory=Lock, repr=False)

    def cache_content(self, source_path: Path, content: str) -> None:
        """Cache raw content during discovery phase (thread-safe)."""
        with self._cache_lock:
            self._page_contents[str(source_path)] = content

    def get_content(self, source_path: Path) -> str | None:
        """Get cached content without disk I/O."""
        with self._cache_lock:
            return self._page_contents.get(str(source_path))

    @cached_property
    def directive_analysis(self) -> dict[str, DirectiveData]:
        """Analyze all directives once using cached content."""
        analyzer = DirectiveAnalyzer()
        # Note: analyze_from_cache needs to handle the lock or copy data
        return analyzer.analyze_from_cache(self._page_contents)
```

#### 2. Cache Content During Discovery

```python
# bengal/discovery/content_discovery.py
class ContentDiscovery:
    def __init__(self, ..., build_context: BuildContext | None = None):
        self.build_context = build_context
        # ...

    def _parse_content_file(self, file_path: Path) -> tuple:
        # Existing file read logic using utils.file_io
        file_content = read_text_file(file_path, ...)

        # Cache for validators (single read, shared by all)
        if self.build_context:
            self.build_context.cache_content(file_path, file_content)

        # Existing parsing logic...
        try:
            post = frontmatter.loads(file_content)
            # ...
```

#### 3. Validators Use BuildContext

```python
# bengal/health/validators/directives/__init__.py
class DirectiveValidator(BaseValidator):
    def validate(self, site: Site, build_context: BuildContext | None) -> list[CheckResult]:
        if build_context:
            # Use pre-analyzed data (no disk I/O)
            return self._validate_from_context(build_context.directive_analysis)
        else:
            # Fallback for standalone health check
            return self._validate_from_disk(site)
```

#### 4. Tiered Validation Config

```yaml
# bengal.toml
[health_check]
# Tier 1: Always run (fast, <100ms)
build_validators = ["syntax", "directives", "internal_links"]

# Tier 2: Run with --full flag (~500ms)
full_validators = ["connectivity", "performance", "navigation"]

# Tier 3: Run with --ci flag or in CI environment (~30s)
ci_validators = ["external_links", "accessibility"]
```

---

## Implementation Plan

### Phase 1: Content Caching (Quick Win)

**Files**: `bengal/utils/build_context.py`, `bengal/discovery/content_discovery.py`

1. Add `_page_contents` dict to `BuildContext`
2. Cache content during page discovery
3. Add `get_content()` method for validators

**Effort**: 1 hour
**Impact**: Enables Phase 2

### Phase 2: Directive Validator Migration

**Files**: `bengal/health/validators/directives/analysis.py`

1. Add `analyze_from_cache()` method to `DirectiveAnalyzer`
2. Update `DirectiveValidator` to use `build_context`
3. Keep disk-based fallback for standalone use

**Effort**: 2 hours
**Impact**: 4.6s → ~50ms for directive validation

### Phase 3: Link Validator Migration

**Files**: `bengal/health/validators/links.py`, `bengal/rendering/link_validator.py`

1. Build link index during render phase (already happening!)
2. Store in `BuildContext.link_index`
3. Validators check against index (O(1) lookup)

**Effort**: 1 hour
**Impact**: Already fast, but cleaner architecture

### Phase 4: Tiered Validation

**Files**: `bengal/health/health_check.py`, `bengal/config/defaults.py`

1. Add tier configuration
2. Filter validators by tier in `run()`
3. Add `--full` and `--ci` flags to CLI

**Effort**: 2 hours
**Impact**: Fast builds by default, thorough when needed

### Phase 5: Knowledge Graph Optimization

**Files**: `bengal/health/validators/connectivity.py`, `bengal/analysis/knowledge_graph.py`

1. Build graph incrementally during link extraction
2. Store in `BuildContext.knowledge_graph` (already done!)
3. Ensure all validators use shared instance

**Effort**: 1 hour
**Impact**: Eliminates duplicate graph builds

---

## Performance Expectations

### Before (Current)

| Validator | Time | Reason |
|-----------|------|--------|
| Directives | 4637ms | Re-reads 773 files |
| Connectivity | ~2000ms | Builds knowledge graph |
| Links | 20ms | Already optimized |
| Output | 50ms | Scans output dir |
| **Total** | **~7000ms** | |

### After (Proposed)

| Validator | Time | Reason |
|-----------|------|--------|
| Directives | <50ms | Uses cached content |
| Connectivity | <100ms | Uses shared graph |
| Links | 20ms | Already optimized |
| Output | 50ms | Scans output dir |
| **Total** | **<200ms** | **35x faster** |

---

## Alternatives Considered

### 1. Store raw_content on Page Object

```python
@dataclass
class Page:
    raw_content: str  # Original markdown
    content: str      # Rendered HTML
```

**Rejected**: Doubles memory usage for content. BuildContext cache can be cleared after validation.

### 2. Async Background Validation

```python
# Build completes immediately, validation in background
async def validate_in_background(site: Site):
    await asyncio.sleep(0)  # Yield to event loop
    return run_validators(site)
```

**Rejected**: Delays feedback, complex error handling. Better to make validation fast.

### 3. Skip Validation by Default (Hugo-like)

```yaml
[health_check]
enabled = false  # Opt-in only
```

**Rejected**: Misses real issues. Better to make it fast than skip it.

### 4. File Hash Caching Only

```python
# Cache validation results by file hash
if cached_hash == current_hash:
    return cached_results
```

**Partial adoption**: Good for incremental builds, but still requires disk reads on first build. Combined with content caching for best results.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Memory pressure from content cache | High memory on large sites | Clear cache after validation phase |
| Thread safety in parallel discovery | Race conditions in cache | Use `Lock` for `cache_content` operations |
| Breaking standalone health check | Users can't run `bengal health` alone | Keep disk-based fallback |
| Coupling validation to build | Harder to test validators | Validators work with or without context |
| Config complexity | Users confused by tiers | Sensible defaults, clear docs |

---

## Success Criteria

- [ ] Health check time < 200ms for 773-page site
- [ ] No disk reads during validation (when build_context available)
- [ ] Standalone `bengal health` still works (fallback mode)
- [ ] Tier 1 validators run by default
- [ ] Memory usage doesn't increase significantly
- [ ] All existing tests pass

---

## Testing Plan

### Unit Tests

1. `test_build_context_caches_content` - Content stored and retrieved
2. `test_directive_validator_uses_cache` - No disk I/O when context available
3. `test_directive_validator_fallback` - Disk I/O when no context
4. `test_tier_filtering` - Only configured validators run

### Integration Tests

1. Full build with validation - timing assertions
2. Incremental build - cache reuse
3. Standalone health check - fallback works

### Performance Tests

1. Benchmark: 773-page site, health check < 200ms
2. Memory: Peak memory doesn't exceed baseline + 50MB

---

## Related Files

- `bengal/utils/build_context.py` - BuildContext with lazy artifacts
- `bengal/health/health_check.py` - Health check orchestrator
- `bengal/health/validators/directives/` - Directive validator (main target)
- `bengal/discovery/content_discovery.py` - Page discovery
- `plan/implemented/rfc-lazy-build-artifacts.md` - BuildContext foundation
- `plan/implemented/rfc-parallel-validators.md` - Parallel execution

---

## Questions for Review

1. Should we clear the content cache immediately after validation, or keep it for dev server reloads?
2. Should tier 1 validators be hardcoded or configurable?
3. Should we add a `--quick` flag that skips all validation (for rapid iteration)?
