# RFC: Incremental Build Dependency Gaps

## Status: Infrastructure Complete, Integration Pending 🟡
## Created: 2026-01-13
## Updated: 2026-01-30
## Implemented: Partial (see Implementation Status below)

---

## Summary

**Problem**: Warm build testing (RFC `rfc-warm-build-test-expansion.md`) revealed three dependency tracking gaps that cause stale content during incremental builds.

**Gaps Discovered**:
1. **Data file changes** don't trigger page rebuilds
2. **Taxonomy listing pages** don't update when member post metadata changes
3. **Sitemap** doesn't include new pages during incremental builds

**Solution**: Extend existing `DependencyTracker` infrastructure to capture implicit dependencies from data files and taxonomy relationships. Use "always regenerate" for sitemap (fast, correct).

**Estimated Effort**: 4 days (revised from 6 days by leveraging existing infrastructure)

---

## Implementation Status (2026-01-30)

### ✅ Infrastructure Complete

The following tracking and invalidation methods were implemented:

| Component | Location | Status |
|-----------|----------|--------|
| `track_data_file()` | `bengal/build/tracking/tracker.py` | ✅ Implemented |
| `get_pages_using_data_file()` | `bengal/build/tracking/tracker.py` | ✅ Implemented |
| `_record_reverse_taxonomy()` | `bengal/build/tracking/tracker.py` | ✅ Implemented |
| `get_term_pages_for_member()` | `bengal/build/tracking/tracker.py` | ✅ Implemented |
| `invalidate_for_data_file()` | `bengal/orchestration/build/coordinator.py` | ✅ Implemented |
| `invalidate_for_template()` | `bengal/orchestration/build/coordinator.py` | ✅ Implemented |
| `invalidate_taxonomy_cascade()` | `bengal/orchestration/build/coordinator.py` | ✅ Implemented |

### ❌ Integration Pending

**Critical Gap**: The invalidation methods are **never called** during incremental builds.

The `ProvenanceFilter.filter()` in `phase_incremental_filter_provenance` does NOT:
- Check data file changes → should call `invalidate_for_data_file()`
- Check template file changes → should call `invalidate_for_template()`
- Propagate taxonomy member metadata changes → should call `invalidate_taxonomy_cascade()`

### Test Evidence

| Gap | Test | Status |
|-----|------|--------|
| Gap 1: Data files | `test_data_file_change_triggers_incremental_rebuild` | ❌ FAILED |
| Gap 2: Taxonomy | `test_taxonomy_term_page_updates_on_member_title_change` | ❌ FAILED |
| Gap 2: Taxonomy | `test_taxonomy_term_page_updates_on_member_date_change` | ❌ FAILED |
| Gap 3: Sitemap | `test_sitemap_includes_new_pages_on_incremental_build` | ✅ PASSED |

### Remaining Work (~1-2 days)

1. Integrate data file change detection into `phase_incremental_filter_provenance`
2. Integrate taxonomy cascade into `phase_incremental_filter_provenance`
3. Consider adding template change detection (related gap discovered during testing)

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

**Root Cause**: `find_work_early()` in `phase_incremental_filter` checks content file mtime, not data file changes. Data files are loaded once at startup (`DataLoadingMixin._load_data_directory()`), so changes aren't detected.

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

**Root Cause**: `DependencyTracker.track_taxonomy()` records page → tag relationships (forward direction), but not tag → page relationships (reverse direction). When a member page changes, the incremental filter correctly rebuilds the post but doesn't mark `/tags/python/` as stale.

### Gap 3: Sitemap Incremental Updates

**Scenario**:
1. Full build with 10 pages → sitemap.xml has 10 URLs
2. Add `content/new-page.md`
3. Run incremental build
4. **Result**: sitemap.xml still has 10 URLs ❌

**Root Cause**: `SitemapGenerator.generate()` reads `site.pages` at generation time, but post-processing phase isn't triggered during incremental builds when only new pages are added (no existing content changed).

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
    └─► (Gap: doesn't check data file mtimes)
    
phase_rendering()
    └─► Render only pages_to_build
    └─► (Gap: taxonomy pages not in pages_to_build)
    
phase_post_processing()
    └─► Generate sitemap, RSS, llm-full.txt
    └─► (Gap: not always triggered on incremental)
```

### Existing Dependency Tracking Infrastructure

`DependencyTracker` in `bengal/cache/dependency_tracker.py` already tracks multiple dependency types:

| Dependency Type | Tracked? | Method | Notes |
|-----------------|----------|--------|-------|
| Content file → Page | ✅ | `cache.is_changed()` | Content hash comparison |
| Template → Page | ✅ | `track_template()` | Template mtime triggers rebuild |
| Partial → Page | ✅ | `track_partial()` | Partial include detection |
| Asset → Page | ✅ | `track_asset()` | Per `rfc-global-build-state-dependencies` |
| Config → Page | ✅ | `track_config()` | Config hash triggers full rebuild |
| Taxonomy (forward) | ✅ | `track_taxonomy()` | Page → tags mapping |
| Cross-version links | ✅ | `track_cross_version_link()` | Version link dependencies |
| **Data file → Page** | ❌ | — | Not tracked |
| **Taxonomy (reverse)** | ❌ | — | Tags → pages not tracked |
| **Page discovery → Sitemap** | ❌ | — | Not tracked |

**Key Insight**: The existing `dependencies` and `reverse_dependencies` dicts in `DependencyTracker` can be extended for data file tracking without adding parallel data structures.

---

## Proposed Solution

### Phase 1: Data File Dependency Tracking (Simplified)

**Goal**: When `data/team.yaml` changes, rebuild pages that accessed `site.data.team`.

**Approach**: Use mtime-based invalidation with cached dependency sets. This is simpler than runtime access proxying and matches the existing "load once at startup" pattern.

**Implementation**:

1. **Extend DependencyTracker with data file methods**:

```python
# bengal/cache/dependency_tracker.py
class DependencyTracker:
    # Existing infrastructure (reuse these)
    # self.dependencies: dict[Path, set[Path]] = {}
    # self.reverse_dependencies: dict[Path, set[Path]] = {}
    
    def track_data_file(self, page_path: Path, data_file: Path) -> None:
        """Record that a page depends on a data file."""
        # Use existing dependency infrastructure with data: prefix
        dep_key = Path(f"data:{data_file}")
        self.cache.add_dependency(page_path, dep_key)
        self._update_dependency_file_once(data_file)
    
    def get_pages_using_data_file(self, data_file: Path) -> set[Path]:
        """Find all pages that depend on a data file."""
        dep_key = f"data:{data_file}"
        return {
            Path(page) for page, deps in self.cache.dependencies.items()
            if dep_key in deps
        }
```

2. **Record data usage during template rendering**:

```python
# bengal/rendering/template_functions/data.py
def get_data(path: str, root_path: Any, tracker: DependencyTracker | None = None,
             current_page: Path | None = None) -> Any:
    """Load data from JSON or YAML file, tracking dependency."""
    file_path = Path(root_path) / path
    
    # Track dependency if tracker available
    if tracker and current_page:
        tracker.track_data_file(current_page, file_path)
    
    return load_data_file(file_path, on_error="return_empty", caller="template")
```

3. **Check data file changes in find_work_early()**:

```python
# bengal/orchestration/incremental/orchestrator.py
def find_work_early(self, ...) -> tuple[list[Page], list[Asset], ChangeSummary]:
    pages_to_build = []
    
    # Existing: content changes
    for page in self._site.pages:
        if self._change_detector.content_changed(page):
            pages_to_build.append(page)
    
    # NEW: data file changes
    data_dir = self._site.root_path / "data"
    if data_dir.exists():
        for data_file in data_dir.rglob("*"):
            if data_file.suffix in (".yaml", ".yml", ".json", ".toml"):
                if self.cache.is_changed(data_file):
                    # Find pages that used this data file in previous build
                    dependent_pages = self.tracker.get_pages_using_data_file(data_file)
                    for page_path in dependent_pages:
                        page = self._site.get_page_by_source(page_path)
                        if page and page not in pages_to_build:
                            pages_to_build.append(page)
                            self._change_summary.data_file_triggered.append(page_path)
    
    return pages_to_build, assets_to_process, self._change_summary
```

**Alternative Considered**: Runtime `DataProxy` with `__getattr__` tracking. Rejected because:
- Adds proxy overhead on every `site.data` access
- Requires thread-local `_current_page` tracking
- Data files are loaded once at startup, making mtime-based detection sufficient

---

### Phase 2: Taxonomy Metadata Propagation (Extend Existing)

**Goal**: When post metadata changes, rebuild taxonomy term pages that list that post.

**Approach**: Extend existing `track_taxonomy()` to record the reverse relationship (term → member pages).

**Implementation**:

1. **Add reverse taxonomy tracking to existing method**:

```python
# bengal/cache/dependency_tracker.py
class DependencyTracker:
    def track_taxonomy(self, page_path: Path, tags: set[str]) -> None:
        """Record taxonomy (tags/categories) dependencies (both directions)."""
        for tag in tags:
            if tag is None:
                continue
            tag_key = f"tag:{str(tag).lower().replace(' ', '-')}"
            
            # Existing: forward mapping (tag → pages that have this tag)
            self.cache.add_taxonomy_dependency(tag_key, page_path)
            
            # NEW: reverse mapping (page → term pages that list it)
            term_page_path = f"_generated/tags/{tag_key}/index.html"
            self._record_reverse_taxonomy(page_path, term_page_path)
    
    def _record_reverse_taxonomy(self, member_path: Path, term_path: str) -> None:
        """Record that a term page depends on a member page's metadata."""
        # When member changes, term page needs rebuild
        with self.lock:
            if term_path not in self.reverse_dependencies:
                self.reverse_dependencies[term_path] = set()
            self.reverse_dependencies[term_path].add(str(member_path))
    
    def get_term_pages_for_member(self, member_path: Path) -> set[str]:
        """Find all taxonomy term pages that list this member page."""
        return {
            term for term, members in self.reverse_dependencies.items()
            if str(member_path) in members and term.startswith("_generated/tags/")
        }
```

2. **Cascade rebuilds to taxonomy pages**:

```python
# bengal/orchestration/incremental/orchestrator.py
def find_work_early(self, ...) -> tuple[list[Page], list[Asset], ChangeSummary]:
    pages_to_build = []
    
    # Existing: content changes
    changed_pages = [p for p in self._site.pages if self._change_detector.content_changed(p)]
    pages_to_build.extend(changed_pages)
    
    # NEW: cascade to taxonomy term pages
    for page in changed_pages:
        affected_terms = self.tracker.get_term_pages_for_member(page.source_path)
        for term_path in affected_terms:
            term_page = self._get_or_create_term_page(term_path)
            if term_page and term_page not in pages_to_build:
                pages_to_build.append(term_page)
                self._change_summary.taxonomy_cascade.append(term_path)
    
    return pages_to_build, assets_to_process, self._change_summary
```

3. **Detect metadata-only changes**:

```python
# bengal/orchestration/incremental/change_detector.py
def metadata_changed(self, page: Page) -> bool:
    """Check if page frontmatter changed (title, tags, date, etc.)."""
    prev_hash = self.cache.get_metadata_hash(page.source_path)
    if prev_hash is None:
        return True  # New page
    
    curr_hash = self._hash_frontmatter(page.metadata)
    return prev_hash != curr_hash

def _hash_frontmatter(self, metadata: dict) -> str:
    """Hash frontmatter fields that affect taxonomy listings."""
    # Only hash fields that appear in taxonomy term pages
    relevant = {
        "title": metadata.get("title"),
        "date": str(metadata.get("date", "")),
        "summary": metadata.get("summary"),
        "tags": sorted(metadata.get("tags", [])),
    }
    return hashlib.sha256(json.dumps(relevant, sort_keys=True).encode()).hexdigest()[:16]
```

---

### Phase 3: Sitemap Incremental Updates (Simplified)

**Goal**: Sitemap includes new pages discovered during incremental builds.

**Approach**: Always regenerate sitemap during incremental builds. Sitemap generation is fast (~10ms for 1000 pages), so the complexity of conditional regeneration isn't worth the minimal savings.

**Implementation**:

```python
# bengal/orchestration/build/finalization.py
def phase_post_processing(
    orchestrator: BuildOrchestrator,
    cache: BuildCache,
    incremental: bool,
) -> None:
    """Run post-processing tasks."""
    site = orchestrator.site
    
    # Sitemap: always regenerate for correctness (fast: ~10ms for 1K pages)
    if site.config.build.generate_sitemap:
        SitemapGenerator(site).generate()
    
    # RSS: regenerate if any pages changed or new pages added
    if site.config.build.generate_rss:
        if not incremental or orchestrator.has_content_changes():
            RSSGenerator(site).generate()
    
    # llm-full.txt: regenerate if any content changed
    if site.config.build.generate_llm_txt:
        if not incremental or orchestrator.has_content_changes():
            LLMFullGenerator(site).generate()
```

**Alternative Considered**: Conditional regeneration with page count/URL tracking. Rejected because:
- Adds complexity for ~10ms savings
- Edge cases (URL changes, page visibility changes) make conditional logic fragile
- "Always correct" is better than "usually correct but sometimes stale"

---

## Implementation Plan

### Phase 0: Test Infrastructure (0.5 day)

| Task | Effort | Priority |
|------|--------|----------|
| Identify test cases from `rfc-warm-build-test-expansion.md` that validate each gap | 0.25 day | P0 |
| Create test skeleton with `@pytest.mark.xfail` for gaps | 0.25 day | P0 |

**Test Mapping**:
| Gap | Test File | Test Name |
|-----|-----------|-----------|
| Data files | `test_warm_build_data_files.py` | `test_data_file_change_rebuilds_dependent_pages` |
| Taxonomy | `test_warm_build_taxonomy.py` | `test_taxonomy_term_page_updates_on_member_title_change` |
| Sitemap | `test_warm_build_output_formats.py` | `test_sitemap_includes_new_pages_incremental` |

### Phase 1: Data File Dependencies (2 days)

| Task | Effort | Priority |
|------|--------|----------|
| Add `track_data_file()` to DependencyTracker | 0.25 day | P1 |
| Add `get_pages_using_data_file()` query method | 0.25 day | P1 |
| Update `get_data()` template function with tracking | 0.5 day | P1 |
| Update `find_work_early()` for data file changes | 0.5 day | P1 |
| Add data file mtime to cache fingerprints | 0.25 day | P1 |
| Tests pass: `test_data_file_change_rebuilds_dependent_pages` | 0.25 day | P1 |

### Phase 2: Taxonomy Metadata Propagation (1.5 days)

| Task | Effort | Priority |
|------|--------|----------|
| Extend `track_taxonomy()` with reverse mapping | 0.25 day | P1 |
| Add `get_term_pages_for_member()` query method | 0.25 day | P1 |
| Add metadata hash tracking to cache | 0.25 day | P1 |
| Cascade metadata changes in `find_work_early()` | 0.5 day | P1 |
| Tests pass: `test_taxonomy_term_page_updates_on_member_title_change` | 0.25 day | P1 |

### Phase 3: Sitemap Always-Regenerate (0.5 day)

| Task | Effort | Priority |
|------|--------|----------|
| Update `phase_post_processing()` to always run sitemap | 0.25 day | P2 |
| Tests pass: `test_sitemap_includes_new_pages_incremental` | 0.25 day | P2 |

### Total Effort: 4.5 days

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
- [ ] Sitemap regeneration < 50ms for 1K pages

### Test Coverage

- [ ] All xfail tests from Phase 0 pass after implementation
- [ ] Tests from `rfc-warm-build-test-expansion.md` pass without workarounds
- [ ] Integration tests cover: data change → rebuild, metadata change → taxonomy rebuild, new page → sitemap

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Circular dependencies in data files | Medium | Low | Detect cycles during tracking, warn user, skip circular refs |
| Over-invalidation (rebuild too much) | Low | Medium | Start conservative; optimize with finer-grained tracking in v2 |
| Cache format breaking change | Medium | Medium | Increment cache version, force full rebuild on upgrade |
| Template data access not instrumented | High | Low | Audit all data access paths; add observability logging |
| Performance regression from tracking | Medium | Low | Benchmark before/after; use lazy tracking if needed |

---

## Alternatives Considered

### Alternative 1: Runtime DataProxy with Access Tracking

**Approach**: Wrap `site.data` in a proxy that records attribute access during rendering.

**Pros**: Fine-grained tracking at key level (e.g., `site.data.team.members[0].name`)
**Cons**: 
- Proxy overhead on every access
- Thread-local state for `_current_page`
- Complex implementation for marginal benefit

**Decision**: Rejected - mtime-based file-level tracking is sufficient for real-world usage patterns.

### Alternative 2: Always Full Rebuild for Data/Taxonomy

**Approach**: Detect data file or taxonomy-related content changes → trigger full rebuild.

**Pros**: Simple, no dependency tracking needed
**Cons**: Defeats purpose of incremental builds for common workflows

**Decision**: Rejected - dependency tracking is worth the complexity.

### Alternative 3: Hash-Based Invalidation Only

**Approach**: Hash all inputs (content + data + templates), rebuild if hash changes.

**Pros**: Simpler mental model
**Cons**: Doesn't tell us WHICH pages need rebuilding

**Decision**: Rejected - too coarse-grained for large sites.

### Alternative 4: Conditional Sitemap Regeneration

**Approach**: Track page count/URLs, only regenerate sitemap when changed.

**Pros**: Saves ~10ms per build
**Cons**: Adds complexity, edge cases (URL changes, visibility changes)

**Decision**: Rejected - "always correct" beats "usually correct".

---

## Related Work

- `rfc-global-build-state-dependencies.md` - Asset fingerprint tracking (implemented)
- `rfc-warm-build-test-expansion.md` - Test coverage that discovered these gaps
- `rfc-incremental-build-observability.md` - Logging for debugging incremental issues

---

## Decisions Made

| Item | Decision | Rationale |
|------|----------|-----------|
| Data file granularity | File-level, not key-level | Simpler; data files typically change atomically |
| Sitemap regeneration | Always regenerate | Fast (~10ms); correctness over optimization |
| Leverage existing infra | Reuse `DependencyTracker` structures | Less code; proven patterns |
| Cascade frontmatter | Track cascade inheritance as dependency | Ensures children rebuild when cascade changes |

---

## Open Questions

1. ~~**Should we track nested data file access?**~~ **Resolved**: Track at file level, not key level. Simpler and sufficient for real-world usage.

2. ~~**How to handle taxonomy changes in cascade frontmatter?**~~ **Resolved**: Track cascade sources (parent `_index.md` files) as provenance inputs. When any cascade source changes, child page provenance hash changes, triggering rebuild. Implemented in `ProvenanceFilter._get_cascade_sources()` and `_compute_provenance()`.

3. ~~**Should sitemap regeneration be configurable?**~~ **Resolved**: No. Always regenerate. It's fast and correctness matters for SEO.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-13 | RFC created | Warm build testing revealed gaps |
| 2026-01-13 | Phase 1-3 scoped | Prioritize data files (most common), then taxonomy, then sitemap |
| 2026-01-14 | Simplified Phase 1 | Mtime-based tracking instead of runtime proxy |
| 2026-01-14 | Simplified Phase 3 | Always-regenerate instead of conditional |
| 2026-01-14 | Added Phase 0 | Test-first approach with xfail markers |
| 2026-01-14 | Effort revised to 4.5 days | Leveraging existing DependencyTracker infrastructure |
| TBD | Phase 0 approved | Test infrastructure first |
| TBD | Phase 1 approved | Data file dependencies most impactful |
| TBD | Phase 2 approved | Taxonomy propagation common workflow |
| TBD | Phase 3 approved | Sitemap correctness important for SEO |
| 2026-01-30 | Status changed to "Infrastructure Complete, Integration Pending" | Re-evaluation found infrastructure exists but invalidation methods are never called during incremental builds. Tests still failing for Gaps 1 & 2. Gap 3 (sitemap) works. |
| 2026-01-30 | Cascade frontmatter tracking implemented | Added `_get_cascade_sources()` to ProvenanceFilter. Parent `_index.md` files now included in page provenance hash. Includes safety guards against infinite loops from circular references or mock objects. |

---

## Appendix: Code References

### Existing Infrastructure to Leverage

| File | Class/Function | Reuse For |
|------|----------------|-----------|
| `bengal/cache/dependency_tracker.py` | `DependencyTracker` | Add `track_data_file()` |
| `bengal/cache/dependency_tracker.py` | `track_taxonomy()` | Extend with reverse mapping |
| `bengal/cache/build_cache/taxonomy_index_mixin.py` | `TaxonomyIndexMixin` | Query term → pages |
| `bengal/orchestration/incremental/orchestrator.py` | `find_work_early()` | Add data/taxonomy checks |
| `bengal/rendering/template_functions/data.py` | `get_data()` | Instrument with tracker |
| `bengal/postprocess/sitemap.py` | `SitemapGenerator` | No changes needed |

### New Code Locations

| Feature | File | Notes |
|---------|------|-------|
| Data file tracking | `bengal/cache/dependency_tracker.py` | New methods in existing class |
| Data change detection | `bengal/orchestration/incremental/orchestrator.py` | Extend `find_work_early()` |
| Taxonomy reverse deps | `bengal/cache/dependency_tracker.py` | Extend `track_taxonomy()` |
| Metadata hash | `bengal/orchestration/incremental/change_detector.py` | New method |
| Sitemap always-run | `bengal/orchestration/build/finalization.py` | Simplify conditional |
