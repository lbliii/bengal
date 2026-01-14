# RFC: Incremental Build Dependency Gaps

## Status: Draft
## Created: 2026-01-13
## Updated: 2026-01-13

---

## Summary

**Problem**: Warm build testing (RFC `rfc-warm-build-test-expansion.md`) revealed three dependency tracking gaps that cause stale content during incremental builds.

**Gaps Discovered**:
1. **Data file changes** don't trigger page rebuilds
2. **Taxonomy listing pages** don't update when member post metadata changes
3. **Sitemap** doesn't include new pages during incremental builds

**Solution**: Extend `DependencyTracker` to capture implicit dependencies from data files, taxonomy relationships, and global output files.

---

## Problem Statement

Bengal's incremental build system optimizes rebuilds by tracking explicit dependencies (content files → output pages). However, several implicit dependencies aren't tracked:

### Gap 1: Data File Dependencies

**Scenario**:
```yaml
# data/team.yaml
- name: Alice
  role: Engineer
```

```jinja
{# templates/team.html #}
{% for member in site.data.team %}
  <p>{{ member.name }} - {{ member.role }}</p>
{% endfor %}
```

**Current Behavior**:
1. Full build renders team page with Alice
2. Edit `data/team.yaml` to change role to "Senior Engineer"
3. Run incremental build
4. **Result**: Team page still shows "Engineer" ❌

**Root Cause**: `find_work_early()` in `phase_incremental_filter` checks content file mtime, not data file access during rendering.

### Gap 2: Taxonomy Metadata Propagation

**Scenario**:
```markdown
---
title: My Python Post
tags: [python]
---
```

**Current Behavior**:
1. Full build creates `/tags/python/` listing with "My Python Post"
2. Edit post title to "Advanced Python Techniques"
3. Run incremental build
4. **Result**: `/tags/python/` still shows old title "My Python Post" ❌

**Root Cause**: Taxonomy term pages are generated from collected page metadata. When a member page changes, the incremental filter correctly rebuilds `post.md` but doesn't mark `/tags/python/` as stale since its "source" (`tags/python/_index.md` or virtual) didn't change.

### Gap 3: Sitemap Incremental Updates

**Scenario**:
1. Full build with 10 pages → sitemap.xml has 10 URLs
2. Add `content/new-page.md`
3. Run incremental build
4. **Result**: sitemap.xml still has 10 URLs ❌

**Root Cause**: Sitemap generation in post-processing uses `site.pages`, but the sitemap output isn't triggered for regeneration when new pages are discovered.

---

## Current Architecture

### How Incremental Builds Work

```
phase_discovery()
    └─► Discover all content files
    
phase_incremental_filter()
    └─► find_work_early()
        └─► Check mtime/hash of .md files
        └─► pages_to_build = changed content files
        
phase_assets()
    └─► Process changed CSS/JS/images
    └─► Update asset-manifest.json
    └─► (Gap: doesn't notify pages of data file changes)
    
phase_rendering()
    └─► Render only pages_to_build
    └─► (Gap: taxonomy pages not in pages_to_build)
    
phase_post_processing()
    └─► Generate sitemap, RSS, llm-full.txt
    └─► (Gap: uses cached page list, not fresh discovery)
```

### Existing Dependency Tracking

`DependencyTracker` in `bengal/core/dependencies.py` tracks:

| Dependency Type | Tracked? | Notes |
|-----------------|----------|-------|
| Content file → Page | ✅ | `content_hash` comparison |
| Template → Page | ✅ | Template mtime triggers rebuild |
| Partial → Page | ✅ | Partial include detection |
| Asset → Page | ✅ | `rfc-global-build-state-dependencies` |
| **Data file → Page** | ❌ | Not tracked |
| **Taxonomy term → Member pages** | ❌ | Not tracked |
| **Page discovery → Sitemap** | ❌ | Not tracked |

---

## Proposed Solution

### Phase 1: Data File Dependency Tracking

**Goal**: When `data/team.yaml` changes, rebuild pages that access `site.data.team`.

**Implementation**:

1. **Track data file access during rendering**:

```python
# bengal/core/dependencies.py
class DependencyTracker:
    def __init__(self):
        self._content_deps: dict[str, set[Path]] = {}
        self._template_deps: dict[str, set[Path]] = {}
        self._data_deps: dict[str, set[Path]] = {}  # NEW
    
    def record_data_access(self, page_path: str, data_file: Path) -> None:
        """Record that a page accessed a data file during rendering."""
        if page_path not in self._data_deps:
            self._data_deps[page_path] = set()
        self._data_deps[page_path].add(data_file)
    
    def get_pages_using_data_file(self, data_file: Path) -> set[str]:
        """Find all pages that depend on a data file."""
        return {
            page for page, deps in self._data_deps.items()
            if data_file in deps
        }
```

2. **Instrument data access in Site**:

```python
# bengal/core/site.py
class Site:
    @property
    def data(self) -> DataProxy:
        """Returns proxy that tracks data file access."""
        return DataProxy(self._data, self._dependency_tracker, self._current_page)
    
class DataProxy:
    """Proxy for site.data that records access for dependency tracking."""
    
    def __getattr__(self, name: str) -> Any:
        data_file = self._data_dir / f"{name}.yaml"
        if self._tracker and self._current_page:
            self._tracker.record_data_access(self._current_page, data_file)
        return self._data.get(name)
```

3. **Include data-dependent pages in incremental filter**:

```python
# bengal/build/incremental.py
def find_work_early(site: Site, cache: BuildCache) -> list[Page]:
    pages_to_build = []
    
    # Existing: content changes
    for page in site.pages:
        if content_changed(page, cache):
            pages_to_build.append(page)
    
    # NEW: data file changes
    for data_file in site.data_dir.glob("*.yaml"):
        if data_file_changed(data_file, cache):
            dependent_pages = site.dependency_tracker.get_pages_using_data_file(data_file)
            pages_to_build.extend(site.get_pages(dependent_pages))
    
    return pages_to_build
```

**Challenge**: Data access happens during rendering, but we need to know dependencies BEFORE rendering to decide what to rebuild.

**Solution**: Use cached dependencies from previous build:

```python
def find_work_early(site: Site, cache: BuildCache) -> list[Page]:
    # Load dependency graph from previous build
    prev_deps = cache.load_dependencies()
    
    # Check data file mtimes
    changed_data_files = [
        f for f in site.data_dir.glob("*.yaml")
        if cache.data_mtime(f) != f.stat().st_mtime
    ]
    
    # Find pages that used changed data files (from previous build)
    for data_file in changed_data_files:
        pages_to_build.extend(prev_deps.get_pages_using_data_file(data_file))
```

---

### Phase 2: Taxonomy Metadata Propagation

**Goal**: When post metadata changes, rebuild taxonomy term pages that list that post.

**Implementation**:

1. **Track taxonomy term → member page relationships**:

```python
# bengal/core/dependencies.py
class DependencyTracker:
    def __init__(self):
        # ... existing ...
        self._taxonomy_deps: dict[str, set[str]] = {}  # term_path -> {member_paths}
    
    def record_taxonomy_membership(self, term_path: str, member_path: str) -> None:
        """Record that a taxonomy term page lists a member page."""
        if term_path not in self._taxonomy_deps:
            self._taxonomy_deps[term_path] = set()
        self._taxonomy_deps[term_path].add(member_path)
    
    def get_taxonomy_terms_for_page(self, page_path: str) -> set[str]:
        """Find all taxonomy term pages that list this page."""
        return {
            term for term, members in self._taxonomy_deps.items()
            if page_path in members
        }
```

2. **Cascade rebuilds to taxonomy pages**:

```python
# bengal/build/incremental.py
def find_work_early(site: Site, cache: BuildCache) -> list[Page]:
    pages_to_build = []
    
    # Existing: content changes
    changed_pages = [p for p in site.pages if content_changed(p, cache)]
    pages_to_build.extend(changed_pages)
    
    # NEW: cascade to taxonomy pages
    prev_deps = cache.load_dependencies()
    for page in changed_pages:
        affected_terms = prev_deps.get_taxonomy_terms_for_page(page.source_path)
        for term_path in affected_terms:
            term_page = site.get_page(term_path)
            if term_page and term_page not in pages_to_build:
                pages_to_build.append(term_page)
    
    return pages_to_build
```

3. **Optimization: Metadata-only changes**

Full page content changes already trigger taxonomy rebuilds via the cascade. But what about metadata-only changes?

```python
def metadata_changed(page: Page, cache: BuildCache) -> bool:
    """Check if page frontmatter changed (title, tags, date, etc.)."""
    prev_meta = cache.get_metadata_hash(page.source_path)
    curr_meta = hash_frontmatter(page.frontmatter)
    return prev_meta != curr_meta
```

---

### Phase 3: Sitemap Incremental Updates

**Goal**: Sitemap includes new pages discovered during incremental builds.

**Implementation**:

1. **Detect page count changes**:

```python
# bengal/build/post_processing.py
def should_regenerate_sitemap(site: Site, cache: BuildCache) -> bool:
    """Check if sitemap needs regeneration."""
    prev_page_count = cache.get("sitemap_page_count", 0)
    curr_page_count = len(site.pages)
    
    # New pages added
    if curr_page_count > prev_page_count:
        return True
    
    # Pages deleted (handled by full rebuild, but check anyway)
    if curr_page_count < prev_page_count:
        return True
    
    # URL changes (slug, permalink)
    prev_urls = set(cache.get("sitemap_urls", []))
    curr_urls = {p.permalink for p in site.pages}
    if prev_urls != curr_urls:
        return True
    
    return False
```

2. **Trigger sitemap regeneration in post-processing**:

```python
# bengal/build/phases.py
def phase_post_processing(site: Site, state: BuildState, cache: BuildCache):
    # Existing sitemap generation
    if site.config.build.generate_sitemap:
        if state.is_full_build or should_regenerate_sitemap(site, cache):
            generate_sitemap(site)
            cache.set("sitemap_page_count", len(site.pages))
            cache.set("sitemap_urls", [p.permalink for p in site.pages])
```

3. **Alternative: Always regenerate on incremental**

Sitemap generation is fast (~10ms for 1000 pages). Consider always regenerating:

```python
if site.config.build.generate_sitemap:
    # Sitemap is cheap - always regenerate for correctness
    generate_sitemap(site)
```

---

## Implementation Plan

### Phase 1: Data File Dependencies (3 days)

| Task | Effort | Priority |
|------|--------|----------|
| Add `_data_deps` to DependencyTracker | 0.5 day | P1 |
| Create `DataProxy` with access tracking | 1 day | P1 |
| Update `find_work_early()` for data changes | 1 day | P1 |
| Add tests for data file warm builds | 0.5 day | P1 |

### Phase 2: Taxonomy Metadata Propagation (2 days)

| Task | Effort | Priority |
|------|--------|----------|
| Add `_taxonomy_deps` to DependencyTracker | 0.5 day | P1 |
| Record taxonomy membership during taxonomy generation | 0.5 day | P1 |
| Cascade metadata changes to term pages | 0.5 day | P1 |
| Add tests for taxonomy warm builds | 0.5 day | P1 |

### Phase 3: Sitemap Incremental Updates (1 day)

| Task | Effort | Priority |
|------|--------|----------|
| Add `should_regenerate_sitemap()` | 0.5 day | P2 |
| Update post-processing phase | 0.25 day | P2 |
| Add tests for sitemap warm builds | 0.25 day | P2 |

### Total Effort: 6 days

---

## Success Criteria

### Functional Requirements

- [ ] Data file change triggers rebuild of pages using that data
- [ ] Post metadata change triggers rebuild of taxonomy term pages
- [ ] New pages appear in sitemap after incremental build
- [ ] Deleted pages removed from sitemap after full rebuild

### Performance Requirements

- [ ] Dependency tracking adds < 5% overhead to full builds
- [ ] Incremental builds remain faster than full builds for targeted changes
- [ ] Memory overhead for dependency graph < 10MB for 10K page sites

### Test Coverage

- [ ] Tests from `rfc-warm-build-test-expansion.md` pass without workarounds
- [ ] Specifically: `test_data_file_change_rebuilds_dependent_pages` uses incremental
- [ ] Specifically: `test_taxonomy_term_page_title_change` uses incremental
- [ ] Specifically: `test_sitemap_updated_on_page_add` uses incremental

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular dependencies in data files | Medium | Detect cycles, warn user |
| Over-invalidation (rebuild too much) | Low | Start conservative, optimize later |
| Dependency graph too large | Low | Prune stale entries, use weak refs |
| Breaking change to cache format | Medium | Version cache, invalidate on upgrade |

---

## Alternatives Considered

### Alternative 1: Always Full Rebuild for Data/Taxonomy

**Approach**: Detect data file or taxonomy-related content changes → trigger full rebuild.

**Pros**: Simple, no dependency tracking needed
**Cons**: Defeats purpose of incremental builds for common workflows

**Decision**: Rejected - dependency tracking is worth the complexity.

### Alternative 2: Hash-Based Invalidation Only

**Approach**: Hash all inputs (content + data + templates), rebuild if hash changes.

**Pros**: Simpler mental model
**Cons**: Doesn't tell us WHICH pages need rebuilding

**Decision**: Rejected - too coarse-grained for large sites.

### Alternative 3: Lazy Regeneration

**Approach**: Don't rebuild taxonomy pages incrementally; regenerate on next full build.

**Pros**: No dependency tracking needed
**Cons**: Stale content visible to users until manual full rebuild

**Decision**: Rejected - user experience is poor.

---

## Related Work

- `rfc-global-build-state-dependencies.md` - Asset fingerprint tracking (Phase 1 complete)
- `rfc-warm-build-test-expansion.md` - Test coverage that discovered these gaps
- `rfc-incremental-build-observability.md` - Logging for debugging incremental issues

---

## Open Questions

1. **Should we track nested data file access?** (e.g., `site.data.config.feature.enabled`)
   - Proposal: Track at file level, not key level (simpler, sufficient)

2. **How to handle taxonomy changes in cascade frontmatter?**
   - When `_index.md` cascade sets `tags: [featured]`, all children inherit
   - Proposal: Track cascade inheritance as dependency

3. **Should sitemap regeneration be configurable?**
   - Option A: Always regenerate (simple, correct)
   - Option B: User config `build.incremental_sitemap = true`
   - Proposal: Option A (sitemap is cheap)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-13 | RFC created | Warm build testing revealed gaps |
| 2026-01-13 | Phase 1-3 scoped | Prioritize data files (most common), then taxonomy, then sitemap |
| TBD | Phase 1 approved | Data file dependencies most impactful |
| TBD | Phase 2 approved | Taxonomy propagation common workflow |
| TBD | Phase 3 approved | Sitemap correctness important for SEO |
