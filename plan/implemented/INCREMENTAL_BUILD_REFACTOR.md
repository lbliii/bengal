# Incremental Build Architecture Refactor

**Status**: 🚧 In Progress  
**Date**: 2024-10-09  
**Priority**: High - Fixes stale reference bug + establishes correct patterns

---

## Executive Summary

Refactoring the incremental build system to eliminate stale object references and establish a clear separation between cached data (persisted to disk) and ephemeral data (rebuilt each build).

**Problem**: Current system caches `site.taxonomies` dict containing Page object references between builds, causing stale data bugs in dev server mode.

**Solution**: Cache only paths/hashes, always reconstruct relationships from current Page objects using inverted indices for O(1) lookup performance.

---

## Design Principles

### 1. The Persistence Contract

**RULE: Never persist object references across builds**

| Data Type | Persistence | Storage | Rationale |
|-----------|-------------|---------|-----------|
| File hashes | Disk (JSON) | `BuildCache.file_hashes` | Change detection |
| Page tags | Disk (JSON) | `BuildCache.page_tags` | Detect tag changes |
| Tag→Pages index | Disk (JSON) | `BuildCache.tag_to_pages` | O(1) reconstruction |
| Dependencies | Disk (JSON) | `BuildCache.dependencies` | Template invalidation |
| Page objects | **NEVER** | Rebuilt each build | Content may change |
| Taxonomies dict | **NEVER** | Reconstructed | Contains object refs |
| Indices (xref, etc) | **NEVER** | Reconstructed | Derived data |

### 2. Separation of Concerns

```
Change Detection (BuildCache)
  ↓ provides: Set[Path] of changed files
Work Planning (IncrementalOrchestrator)
  ↓ provides: WorkPlan (pages to build, tags affected)
Execution (TaxonomyOrchestrator, RenderOrchestrator, etc)
  ↓ uses: WorkPlan to minimize work
Output (rendered files)
```

Each layer is stateless and operates on current data.

### 3. Optimization Strategy

- **Optimize DETECTION**: Which tags are affected? → O(changed)
- **Optimize GENERATION**: Which tag pages to rebuild? → O(affected)
- **DON'T optimize COLLECTION**: Always use current objects → O(all pages, but fast)

Rationale: Collection is fast (just iterating objects), optimization complexity not worth it.

---

## Implementation Plan

### Phase 1: BuildCache Inverted Index

**File**: `bengal/cache/build_cache.py`

Add inverted index for O(1) tag→pages lookups:

```python
@dataclass
class BuildCache:
    """
    Tracks file hashes and dependencies between builds.
    
    IMPORTANT: This cache must NEVER contain object references.
    All data must be serializable to JSON (paths, strings, numbers, lists, dicts).
    """
    
    file_hashes: Dict[str, str] = field(default_factory=dict)
    dependencies: Dict[str, Set[str]] = field(default_factory=dict)
    output_sources: Dict[str, str] = field(default_factory=dict)
    taxonomy_deps: Dict[str, Set[str]] = field(default_factory=dict)
    page_tags: Dict[str, Set[str]] = field(default_factory=dict)
    
    # NEW: Inverted index for fast taxonomy reconstruction
    # Maps tag slug → set of page paths (strings, not objects)
    tag_to_pages: Dict[str, Set[str]] = field(default_factory=dict)
    
    # NEW: Track which tags existed in previous build (for detecting deletions)
    known_tags: Set[str] = field(default_factory=set)
    
    parsed_content: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_build: Optional[str] = None
    
    def update_page_tags(self, page_path: Path, tags: Set[str]) -> Set[str]:
        """
        Update tag index when a page's tags change.
        
        Maintains bidirectional index:
        - page_tags: path → tags (forward)
        - tag_to_pages: tag → paths (inverted)
        
        Args:
            page_path: Path to page source file
            tags: Current set of tags for this page
            
        Returns:
            Set of affected tag slugs (tags added, removed, or modified)
        """
        page_path_str = str(page_path)
        affected_tags = set()
        
        # Get old tags for this page
        old_tags = self.page_tags.get(page_path_str, set())
        old_slugs = {tag.lower().replace(' ', '-') for tag in old_tags}
        new_slugs = {tag.lower().replace(' ', '-') for tag in tags}
        
        # Find changes
        removed_slugs = old_slugs - new_slugs
        added_slugs = new_slugs - old_slugs
        unchanged_slugs = old_slugs & new_slugs
        
        # Remove page from old tags
        for tag_slug in removed_slugs:
            if tag_slug in self.tag_to_pages:
                self.tag_to_pages[tag_slug].discard(page_path_str)
                # Remove empty tag entries
                if not self.tag_to_pages[tag_slug]:
                    del self.tag_to_pages[tag_slug]
                    self.known_tags.discard(tag_slug)
            affected_tags.add(tag_slug)
        
        # Add page to new tags
        for tag_slug in added_slugs:
            self.tag_to_pages.setdefault(tag_slug, set()).add(page_path_str)
            self.known_tags.add(tag_slug)
            affected_tags.add(tag_slug)
        
        # Mark unchanged tags as affected if page content changed
        # (affects sort order, which affects tag page rendering)
        affected_tags.update(unchanged_slugs)
        
        # Update forward index
        self.page_tags[page_path_str] = tags
        
        return affected_tags
    
    def get_pages_for_tag(self, tag_slug: str) -> Set[str]:
        """
        Get all page paths for a given tag.
        
        Args:
            tag_slug: Tag slug (e.g., 'python', 'web-dev')
            
        Returns:
            Set of page path strings
        """
        return self.tag_to_pages.get(tag_slug, set()).copy()
    
    def get_all_tags(self) -> Set[str]:
        """Get all known tag slugs from previous build."""
        return self.known_tags.copy()
```

**Key changes:**
- `tag_to_pages` maps tag slug → set of page path strings
- `update_page_tags()` maintains both directions of the index
- Returns `affected_tags` for downstream optimization
- All data is JSON-serializable (no object references)

### Phase 2: TaxonomyOrchestrator Refactor

**File**: `bengal/orchestration/taxonomy.py`

Replace `collect_taxonomies_incremental()` with proper path-based reconstruction:

```python
def collect_and_generate_incremental(self, changed_pages: List['Page'], cache: 'BuildCache') -> Set[str]:
    """
    Incrementally update taxonomies for changed pages only.
    
    Architecture:
    1. Always rebuild site.taxonomies from current Page objects (correct)
    2. Use cache to determine which tag PAGES need regeneration (fast)
    3. Never reuse taxonomy structure with object references (prevents bugs)
    
    Performance:
    - Change detection: O(changed pages)
    - Taxonomy reconstruction: O(all pages) - but fast, just object iteration
    - Tag page generation: O(affected tags)
    
    Args:
        changed_pages: List of pages that changed (NOT generated pages)
        cache: Build cache with tag index
        
    Returns:
        Set of affected tag slugs (for regenerating tag pages)
    """
    print("\n🏷️  Taxonomies (incremental):")
    
    # STEP 1: Determine which tags are affected
    # This is the O(changed) optimization - only look at changed pages
    affected_tags = set()
    for page in changed_pages:
        if page.metadata.get('_generated'):
            continue
        
        # Update cache and get affected tags
        new_tags = set(page.tags) if page.tags else set()
        page_affected = cache.update_page_tags(page.source_path, new_tags)
        affected_tags.update(page_affected)
    
    # STEP 2: Rebuild taxonomy structure from current Page objects
    # This is ALWAYS done from scratch to avoid stale references
    # Performance: O(all pages) but very fast (just iteration + dict ops)
    self._rebuild_taxonomy_structure_from_cache(cache)
    
    print(f"   ├─ Tags:      {len(self.site.taxonomies.get('tags', {}))}")
    print(f"   ├─ Updated:   {len(changed_pages)} page(s)")
    print(f"   └─ Affected:  {len(affected_tags)} tag(s) ✓")
    
    # STEP 3: Generate tag pages only for affected tags
    if affected_tags:
        self.generate_dynamic_pages_for_tags(affected_tags)
    
    return affected_tags

def _rebuild_taxonomy_structure_from_cache(self, cache: 'BuildCache') -> None:
    """
    Rebuild site.taxonomies from cache using CURRENT Page objects.
    
    This is the key to avoiding stale references:
    1. Cache tells us which pages have which tags (paths only)
    2. We map paths to current Page objects (from site.pages)
    3. We reconstruct taxonomy dict with current objects
    
    Performance: O(tags * pages_per_tag) which is O(all pages) worst case,
    but in practice very fast because it's just dict lookups and list appends.
    """
    # Initialize fresh structure
    self.site.taxonomies = {'tags': {}, 'categories': {}}
    
    # Build lookup map: path → current Page object
    current_page_map = {
        p.source_path: p 
        for p in self.site.pages 
        if not p.metadata.get('_generated')
    }
    
    # For each tag in cache, map paths to current Page objects
    for tag_slug in cache.get_all_tags():
        page_paths = cache.get_pages_for_tag(tag_slug)
        
        # Map paths to current Page objects
        current_pages = []
        for path_str in page_paths:
            path = Path(path_str)
            if path in current_page_map:
                current_pages.append(current_page_map[path])
        
        if not current_pages:
            # Tag has no pages - skip it (was removed)
            continue
        
        # Get original tag name (not slug) from first page's tags
        # This handles "Python" vs "python" correctly
        original_tag = None
        for page in current_pages:
            if page.tags:
                for tag in page.tags:
                    if tag.lower().replace(' ', '-') == tag_slug:
                        original_tag = tag
                        break
            if original_tag:
                break
        
        if not original_tag:
            original_tag = tag_slug  # Fallback
        
        # Create tag entry with CURRENT page objects
        self.site.taxonomies['tags'][tag_slug] = {
            'name': original_tag,
            'slug': tag_slug,
            'pages': sorted(
                current_pages,
                key=lambda p: p.date if p.date else datetime.min,
                reverse=True
            )
        }
```

**Key changes:**
- Split into two clear steps: detect affected, then rebuild structure
- `_rebuild_taxonomy_structure_from_cache()` always uses current Page objects
- Cache provides paths, we map to objects
- Simple, clear, correct

### Phase 3: Dev Server State Management

**File**: `bengal/server/dev_server.py`

Add explicit state clearing between builds:

```python
def _clear_ephemeral_state(self) -> None:
    """
    Clear ephemeral state that shouldn't persist between builds.
    
    This is critical in dev server mode where the Site object
    persists across multiple builds. We must clear derived state
    to avoid stale references.
    
    Persistence contract:
    - root_path, config, theme: Persist (static config)
    - output_dir, build_time: Persist (metadata)
    - pages, sections, assets: CLEAR (will be rediscovered)
    - taxonomies, menu, xref_index: CLEAR (derived from pages)
    """
    logger.debug("clearing_ephemeral_state",
                site_root=str(self.site.root_path))
    
    # Clear content (will be rediscovered)
    self.site.pages = []
    self.site.sections = []
    self.site.assets = []
    
    # Clear derived structures (contain object references)
    self.site.taxonomies = {}
    self.site.menu = {}
    self.site.menu_builders = {}
    
    # Clear indices (rebuilt from pages)
    if hasattr(self.site, 'xref_index'):
        self.site.xref_index = {}
    
    # Clear caches on pages (if any survived somehow)
    self.site.invalidate_regular_pages_cache()

def _rebuild_site(self):
    """Rebuild site with clean state."""
    # Clear ephemeral state before rebuild
    self._clear_ephemeral_state()
    
    # Build with clean slate
    show_building_indicator("Rebuilding")
    stats = self.site.build(incremental=True)
    display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))
```

**Key changes:**
- Explicit contract about what persists vs. what's cleared
- Called before every incremental build in dev server
- Prevents ALL stale reference bugs, not just taxonomy

### Phase 4: IncrementalOrchestrator Cleanup

**File**: `bengal/orchestration/incremental.py`

Remove the now-obsolete `find_work()` method and simplify:

```python
def find_work_early(self, verbose: bool = False) -> Tuple[List['Page'], List['Asset'], Dict[str, List]]:
    """
    Find pages/assets that need rebuilding.
    
    Returns changed content and affected dependencies. Does NOT
    attempt to filter generated pages - that's handled by orchestrators
    after they determine which generated pages are affected.
    
    Args:
        verbose: Whether to collect detailed change information
        
    Returns:
        Tuple of (pages_to_build, assets_to_process, change_summary)
    """
    if not self.cache or not self.tracker:
        raise RuntimeError("Cache not initialized - call initialize() first")
    
    pages_to_rebuild: Set[Path] = set()
    assets_to_process: List['Asset'] = []
    change_summary: Dict[str, List] = {
        'Modified content': [],
        'Modified assets': [],
        'Modified templates': [],
    }
    
    # Find changed content files (skip generated pages)
    for page in self.site.pages:
        if page.metadata.get('_generated'):
            continue
        
        if self.cache.is_changed(page.source_path):
            pages_to_rebuild.add(page.source_path)
            if verbose:
                change_summary['Modified content'].append(page.source_path)
    
    # Find changed assets
    for asset in self.site.assets:
        if self.cache.is_changed(asset.source_path):
            assets_to_process.append(asset)
            if verbose:
                change_summary['Modified assets'].append(asset.source_path)
    
    # Check for template changes
    theme_templates_dir = self._get_theme_templates_dir()
    if theme_templates_dir and theme_templates_dir.exists():
        for template_file in theme_templates_dir.rglob("*.html"):
            if self.cache.is_changed(template_file):
                if verbose:
                    change_summary['Modified templates'].append(template_file)
                # Template changed - find affected pages
                affected = self.cache.get_affected_pages(template_file)
                pages_to_rebuild.update(Path(p) for p in affected)
            else:
                # Template unchanged - update hash for next build
                self.cache.update_file(template_file)
    
    # Convert to Page objects
    pages_to_build_list = [
        page for page in self.site.pages 
        if page.source_path in pages_to_rebuild and not page.metadata.get('_generated')
    ]
    
    return pages_to_build_list, assets_to_process, change_summary

# DELETE: find_work() method - no longer needed
```

**Key changes:**
- Remove obsolete `find_work()` method (was never called anyway)
- Simplify to just "what content/assets/templates changed"
- Let orchestrators handle generated page logic

### Phase 5: Build Orchestrator Updates

**File**: `bengal/orchestration/build.py`

Update to use new taxonomy API:

```python
# Phase 4: Taxonomies & Dynamic Pages (line ~223)
with self.logger.phase("taxonomies"):
    taxonomy_start = time.time()
    
    if incremental and pages_to_build:
        # Incremental: Update cache and rebuild affected tags
        affected_tags = self.taxonomy.collect_and_generate_incremental(
            pages_to_build,
            cache
        )
        
        # Store affected tags for related posts
        self.site._affected_tags = affected_tags
    
    elif not incremental:
        # Full build: Collect and generate everything
        self.taxonomy.collect_and_generate()
        
        # Update cache with full taxonomy data
        for page in self.site.pages:
            if not page.metadata.get('_generated') and page.tags:
                cache.update_page_tags(page.source_path, set(page.tags))
    # else: No pages changed, skip taxonomy updates
    
    self.stats.taxonomy_time_ms = (time.time() - taxonomy_start) * 1000
    if hasattr(self.site, 'taxonomies'):
        self.logger.info("taxonomies_built",
                       taxonomy_count=len(self.site.taxonomies),
                       total_terms=sum(len(terms) for terms in self.site.taxonomies.values()))
    
    # Invalidate regular_pages cache
    self.site.invalidate_regular_pages_cache()
```

**Key changes:**
- Cache update happens in both incremental and full builds
- Consistent interface

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/cache/test_build_cache_inverted_index.py

def test_update_page_tags_adds_to_index():
    """Test that updating tags adds page to tag index."""
    cache = BuildCache()
    page_path = Path("content/post.md")
    tags = {"Python", "Web Dev"}
    
    affected = cache.update_page_tags(page_path, tags)
    
    assert "python" in affected
    assert "web-dev" in affected
    assert str(page_path) in cache.get_pages_for_tag("python")
    assert str(page_path) in cache.get_pages_for_tag("web-dev")

def test_update_page_tags_removes_old_tags():
    """Test that updating tags removes page from old tag index."""
    cache = BuildCache()
    page_path = Path("content/post.md")
    
    # Initial tags
    cache.update_page_tags(page_path, {"Python"})
    assert str(page_path) in cache.get_pages_for_tag("python")
    
    # Change tags
    affected = cache.update_page_tags(page_path, {"Rust"})
    
    assert "python" in affected  # Was affected
    assert "rust" in affected
    assert str(page_path) not in cache.get_pages_for_tag("python")
    assert str(page_path) in cache.get_pages_for_tag("rust")

def test_tag_index_serializes_to_json():
    """Test that cache with tag index can be saved/loaded."""
    cache = BuildCache()
    cache.update_page_tags(Path("a.md"), {"Python"})
    cache.update_page_tags(Path("b.md"), {"Python", "Web"})
    
    # Save
    cache.save(Path("test-cache.json"))
    
    # Load
    loaded = BuildCache.load(Path("test-cache.json"))
    
    assert loaded.get_pages_for_tag("python") == {str(Path("a.md")), str(Path("b.md"))}
    assert loaded.get_pages_for_tag("web") == {str(Path("b.md"))}
```

### Integration Tests

```python
# tests/integration/test_incremental_taxonomy.py

def test_incremental_taxonomy_no_stale_references(tmp_site):
    """Test that incremental builds don't keep stale Page references."""
    # Build 1: 3 pages with "python" tag
    site = create_test_site_with_tags(tmp_site, [
        ("a.md", ["python"]),
        ("b.md", ["python"]),
        ("c.md", ["python"])
    ])
    site.build(incremental=True)
    
    # Check taxonomy has 3 pages
    assert len(site.taxonomies['tags']['python']['pages']) == 3
    page_ids_build1 = {id(p) for p in site.taxonomies['tags']['python']['pages']}
    
    # Build 2: Change only page A
    modify_page(site, "a.md", content="Updated content")
    site.pages = []  # Simulate rediscovery (dev server mode)
    site.taxonomies = {}
    site.build(incremental=True)
    
    # Check taxonomy still has 3 pages, but NEW objects
    assert len(site.taxonomies['tags']['python']['pages']) == 3
    page_ids_build2 = {id(p) for p in site.taxonomies['tags']['python']['pages']}
    
    # Verify objects are NEW (no stale references)
    assert page_ids_build1.isdisjoint(page_ids_build2), "Found stale Page objects!"

def test_tag_count_correct_after_deletion(tmp_site):
    """Test the original bug: tag count wrong after page deletion."""
    # Build 1: 3 pages
    site = create_test_site_with_tags(tmp_site, [
        ("a.md", ["python"]),
        ("b.md", ["python"]),
        ("c.md", ["python"])
    ])
    site.build(incremental=True)
    assert len(site.taxonomies['tags']['python']['pages']) == 3
    
    # Build 2: Delete 2 pages
    delete_pages(site, ["b.md", "c.md"])
    site.pages = []
    site.taxonomies = {}
    site.build(incremental=True)
    
    # Should see only 1 page now (not 3!)
    assert len(site.taxonomies['tags']['python']['pages']) == 1
```

---

## Migration Notes

### Breaking Changes

**NONE** - This is an internal refactor. Public API unchanged.

### Performance Impact

**Positive:**
- O(changed) detection (was: O(all pages))
- O(tags) reconstruction (was: attempted O(changed) but buggy)
- Clearer separation means future optimizations easier

**Neutral:**
- First incremental build after upgrade: ~same speed
- Subsequent builds: faster (better cache utilization)

### Rollout Plan

1. Implement Phase 1-3 in single PR
2. Run full test suite
3. Test manually with dev server (main use case)
4. Deploy to main
5. Monitor for issues

---

## Success Metrics

- ✅ Tag count bug fixed (original issue)
- ✅ No stale Page references in dev server
- ✅ All unit tests pass
- ✅ Integration tests validate correct behavior
- ✅ Performance same or better
- ✅ Code clarity improved (clearer contracts)

---

## Future Enhancements

Once this foundation is solid:

1. **Parsed Content Cache** - Cache rendered HTML, not just tags
2. **Related Posts Optimization** - Use tag index for O(1) lookups
3. **Menu Cache** - Similar pattern for menu structures
4. **Smart Invalidation** - Detect when metadata-only changes don't need re-render

All follow same pattern: **Cache paths/data, reconstruct relationships**.

