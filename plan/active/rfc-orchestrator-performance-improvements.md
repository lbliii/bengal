# RFC: Orchestrator Performance Improvements

## Status
- **Owner**: AI Assistant
- **Created**: 2024-12-05
- **State**: Draft
- **Confidence**: 85% 🟢

## Executive Summary

Bengal's orchestrator-based build system is architecturally sound and aligns with industry standards (Hugo, Eleventy, Astro). This RFC proposes targeted performance improvements that maximize gains without architectural rewrites.

**Goal**: Make Bengal the fastest Python-based SSG while maintaining code simplicity and reliability.

**Non-Goal**: Replace the orchestrator with reactive dataflow or other paradigm shifts.

---

## Problem Statement

While Bengal's orchestrator is solid, there are measurable opportunities for improvement:

| Area | Current State | Opportunity |
|------|--------------|-------------|
| **File I/O** | Synchronous reads during discovery | Async I/O could parallelize reads |
| **Cache Invalidation** | File hash-based | Could use mtime + size for faster checks |
| **Page Rendering** | Re-renders all changed pages | Could cache rendered output by content hash |
| **Template Loading** | Eager compilation on startup | Could lazy-compile on first use |
| **Incremental Granularity** | Page-level | Could be section or taxonomy-level |

### Evidence

**Current benchmarks** (site/ with ~200 pages):
- Cold build: ~2.5s
- Incremental (1 page changed): ~0.8s
- Incremental (template changed): ~2.0s (full rebuild)

**Target benchmarks**:
- Cold build: <2.0s (20% improvement)
- Incremental (1 page changed): <0.3s (60% improvement)
- Incremental (template changed): <1.0s (50% improvement)

---

## Proposed Improvements

### Phase 1: Quick Wins (Low Risk, High Impact)

#### 1.1 Granular Page Output Caching

**Current**: Rendered HTML is not cached; re-renders on every build.

**Proposed**: Cache rendered HTML keyed by content hash + template hash.

```python
# bengal/cache/render_cache.py
@dataclass
class RenderCacheEntry:
    content_hash: str
    template_hash: str
    output_html: str
    dependencies: list[str]  # Template includes, assets

class RenderCache:
    def get(self, page: Page) -> str | None:
        """Return cached HTML if content and templates unchanged."""
        key = self._cache_key(page)
        entry = self._entries.get(key)
        if entry and self._is_valid(entry, page):
            return entry.output_html
        return None
    
    def _cache_key(self, page: Page) -> str:
        return f"{page.source_path}:{page.content_hash}"
```

**Impact**: Skip rendering for unchanged pages even in "full" builds.  
**Effort**: Low (2-3 days)  
**Risk**: Low

#### 1.2 Fast Cache Invalidation with mtime + size

**Current**: Hash every file to detect changes (I/O intensive).

**Proposed**: Use mtime + size as first-pass check, hash only on mismatch.

```python
# bengal/cache/invalidation.py
@dataclass
class FileFingerprint:
    path: str
    mtime: float
    size: int
    hash: str | None = None  # Computed lazily

def needs_rebuild(cached: FileFingerprint, current: Path) -> bool:
    """Fast invalidation: mtime+size first, hash only if needed."""
    stat = current.stat()
    
    # Fast path: mtime and size unchanged = definitely no change
    if cached.mtime == stat.st_mtime and cached.size == stat.st_size:
        return False
    
    # mtime changed but could be touch/rsync - verify with hash
    if cached.hash:
        current_hash = compute_hash(current)
        return current_hash != cached.hash
    
    return True  # No cached hash, assume changed
```

**Impact**: 10-30% faster incremental build detection.  
**Effort**: Low (1-2 days)  
**Risk**: Low (mtime is reliable on modern filesystems)

#### 1.3 Lazy Template Compilation

**Current**: All templates compiled on `TemplateEngine` initialization.

**Proposed**: Compile templates on first use, cache compiled versions.

```python
# bengal/rendering/template_engine.py
class LazyTemplateEngine:
    def __init__(self, ...):
        self._env = self._create_env()
        self._compiled_cache: dict[str, Template] = {}
    
    def get_template(self, name: str) -> Template:
        if name not in self._compiled_cache:
            self._compiled_cache[name] = self._env.get_template(name)
        return self._compiled_cache[name]
```

**Impact**: Faster startup for incremental builds (only compile used templates).  
**Effort**: Low (1 day)  
**Risk**: Very low

---

### Phase 2: Medium Effort Improvements

#### 2.1 Async File Discovery

**Current**: Synchronous file walking and reading during discovery.

**Proposed**: Use `asyncio` + `aiofiles` for parallel file operations.

```python
# bengal/discovery/async_content.py
import asyncio
import aiofiles

async def discover_content_async(content_dir: Path) -> list[Page]:
    """Discover and parse content files in parallel."""
    files = list(content_dir.rglob("*.md"))
    
    async def parse_file(path: Path) -> Page:
        async with aiofiles.open(path, 'r') as f:
            content = await f.read()
        return parse_frontmatter_and_content(path, content)
    
    # Parse all files concurrently (I/O bound, not CPU bound)
    pages = await asyncio.gather(*[parse_file(f) for f in files])
    return pages
```

**Integration**: Orchestrator calls `asyncio.run(discover_content_async(...))`.

**Impact**: 15-25% faster discovery phase (especially on NVMe/SSD).  
**Effort**: Medium (3-5 days)  
**Risk**: Medium (async introduces complexity, need to maintain sync fallback)

#### 2.2 Dependency-Aware Incremental Builds

**Current**: Template change triggers full rebuild.

**Proposed**: Track which pages use which templates, rebuild only affected.

```python
# bengal/cache/dependency_tracker.py
@dataclass
class DependencyGraph:
    """Track page → template/partial dependencies."""
    page_templates: dict[str, set[str]]  # page_path → {template_names}
    template_pages: dict[str, set[str]]  # template_name → {page_paths}
    
    def pages_affected_by(self, changed_templates: set[str]) -> set[str]:
        """Return page paths that need rebuild due to template changes."""
        affected = set()
        for template in changed_templates:
            affected.update(self.template_pages.get(template, set()))
        return affected
```

**Impact**: Template changes rebuild only affected pages (could be 10% vs 100%).  
**Effort**: Medium (5-7 days)  
**Risk**: Medium (need to track all includes/extends/macros)

#### 2.3 Section-Level Incremental Builds

**Current**: Incremental builds check every page.

**Proposed**: Skip entire sections if no files changed within them.

```python
# bengal/orchestration/incremental.py
def get_changed_sections(cache: BuildCache, sections: list[Section]) -> set[str]:
    """Identify sections with any changed files."""
    changed = set()
    for section in sections:
        section_mtime = max(
            (p.source_path.stat().st_mtime for p in section.pages),
            default=0
        )
        if section_mtime > cache.last_build_time:
            changed.add(section.path)
    return changed
```

**Impact**: Large sites with localized changes see significant speedup.  
**Effort**: Medium (3-4 days)  
**Risk**: Low

---

### Phase 3: Advanced Optimizations

#### 3.1 Persistent Worker Process

**Current**: Each `bengal build` is a fresh Python process.

**Proposed**: Optional daemon mode that keeps process warm.

```bash
# Start daemon
bengal daemon start

# Builds use daemon (warm JIT, cached templates)
bengal build --use-daemon

# Stop daemon
bengal daemon stop
```

**Impact**: Eliminates Python startup + import overhead (~300ms).  
**Effort**: High (2-3 weeks)  
**Risk**: High (process management complexity)

#### 3.2 Parallel Phase Execution

**Current**: Phases run sequentially (discovery → sections → taxonomies → ...).

**Proposed**: Run independent phases in parallel where dependencies allow.

```
Current:
  discovery → sections → taxonomies → menus → assets → render → postprocess
  
Proposed (parallel where possible):
  discovery ─┬─→ sections ──┬─→ menus ────┬─→ render → postprocess
             │              │             │
             └─→ assets ────┘             │
             │                            │
             └─→ taxonomies ──────────────┘
```

**Impact**: 10-20% faster cold builds on multi-core systems.  
**Effort**: High (1-2 weeks)  
**Risk**: Medium (need careful dependency analysis)

#### 3.3 Content AST Caching

**Current**: Markdown parsed to AST on every build.

**Proposed**: Cache parsed AST, only re-parse on content change.

```python
# bengal/cache/ast_cache.py
@dataclass
class ASTCacheEntry:
    content_hash: str
    ast: dict  # Serialized AST
    toc: list[dict]
    meta_description: str
```

**Impact**: Skip parsing phase for unchanged content.  
**Effort**: Medium (4-5 days)  
**Risk**: Low (AST is deterministic)

---

## Implementation Roadmap

### Sprint 1: Quick Wins (Week 1-2)
- [ ] 1.1 Granular page output caching
- [ ] 1.2 Fast mtime+size invalidation
- [ ] 1.3 Lazy template compilation

**Expected Result**: 20-30% faster incremental builds

### Sprint 2: Medium Improvements (Week 3-5)
- [ ] 2.1 Async file discovery
- [ ] 2.2 Dependency-aware incremental builds
- [ ] 2.3 Section-level incremental builds

**Expected Result**: 40-50% faster incremental builds, 15-20% faster cold builds

### Sprint 3: Advanced (Week 6-8, Optional)
- [ ] 3.1 Persistent worker process
- [ ] 3.2 Parallel phase execution
- [ ] 3.3 Content AST caching

**Expected Result**: Best-in-class Python SSG performance

---

## Alternatives Considered

### Alternative A: Reactive Dataflow Pipeline

**Rejected**: Already attempted. The hybrid approach created complexity without proportional performance gains. Python's GIL limits true parallelism benefits.

### Alternative B: Rust Core with Python Bindings

**Deferred**: Would provide significant performance gains but requires major investment. Could revisit if Python optimizations hit ceiling.

### Alternative C: PyPy Runtime

**Deferred**: Could provide 2-5x speedup but adds deployment complexity and dependency issues. Worth benchmarking but not prioritizing.

---

## Success Metrics

| Metric | Current | Target | Stretch |
|--------|---------|--------|---------|
| Cold build (200 pages) | 2.5s | 2.0s | 1.5s |
| Incremental (1 page) | 0.8s | 0.3s | 0.15s |
| Incremental (template) | 2.0s | 1.0s | 0.5s |
| Memory (5K pages) | ~500MB | ~400MB | ~300MB |

**Measurement**: Benchmark suite in `benchmarks/` with reproducible scenarios.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Async complexity | Bugs, harder debugging | Maintain sync fallback, comprehensive tests |
| Cache invalidation bugs | Stale content served | Conservative invalidation, cache versioning |
| Breaking changes | User frustration | Feature flags, gradual rollout |

---

## Open Questions

1. **Should async discovery be opt-in or default?**  
   Recommendation: Default on Python 3.11+, opt-in on older versions.

2. **Should we expose cache internals for debugging?**  
   Recommendation: Yes, via `bengal cache inspect` command.

3. **Should persistent daemon be part of core or separate package?**  
   Recommendation: Separate package initially (`bengal-daemon`).

---

## References

- Hugo's caching strategy: https://gohugo.io/troubleshooting/build-performance/
- Astro's lazy hydration: https://docs.astro.build/en/concepts/islands/
- Eleventy's incremental builds: https://www.11ty.dev/docs/usage/#incremental-for-partial-builds
- Python asyncio best practices: https://docs.python.org/3/library/asyncio.html

---

## Appendix: Benchmark Scenarios

### Scenario 1: Documentation Site (Current `site/`)
- ~200 pages
- 10 sections
- 3 taxonomies (tags, categories, authors)
- 50 assets

### Scenario 2: Large Blog
- 5,000 posts
- 100 tags
- Date-based archives
- 200 assets

### Scenario 3: API Documentation
- 10,000 autodoc pages
- Deep hierarchy
- Cross-references
- Minimal assets

Benchmarks should cover cold build, incremental (content), and incremental (template) for each scenario.

