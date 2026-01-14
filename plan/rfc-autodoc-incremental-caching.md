# RFC: Autodoc Incremental Caching

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2026-01-14  
**Related**: rfc-output-cache-architecture.md

## Problem Statement

Autodoc pages (Python API docs, CLI reference, REST API docs) are rebuilt on **every incremental build**, even when:
- No Python source files changed
- No CLI command definitions changed
- The output HTML already exists and is valid

### Evidence

```bash
# After simple text edit to _index.md:
Incremental build: 847 pages, 0 assets (skipped 224 cached)

# Breakdown:
# - 224 content pages: CACHED ✅
# - 726 autodoc-python pages: REBUILT ❌
# - 96 autodoc-cli pages: REBUILT ❌  
# - 23 autodoc-rest pages: REBUILT ❌
# Total autodoc: 845 pages rebuilt unnecessarily
```

### Impact

| Metric | Current | Target |
|--------|---------|--------|
| Incremental build time | ~15s | <2s |
| Pages rebuilt (no code change) | 845 | ~5 |
| Dev server responsiveness | Poor | Instant |

## Root Cause Analysis

### Current Autodoc Flow

```
1. Discovery phase scans Python files
2. AutodocOrchestrator generates virtual pages for every symbol
3. ALL autodoc pages added to pages_to_build
4. ALL autodoc pages rendered (even if unchanged)
5. ~12 seconds spent rendering unchanged API docs
```

### Why Autodoc Pages Always Rebuild

Location: `bengal/orchestration/incremental/taxonomy_detector.py:351-376`

```python
def check_autodoc_changes(...) -> set[str]:
    """Check for autodoc source file changes."""
    # Returns ALL autodoc pages if ANY source file changed
    # No granular tracking of which symbols are affected
```

Location: `bengal/orchestration/incremental/change_detector.py:301-308`

```python
# Check autodoc changes
autodoc_pages = self._taxonomy_detector.check_autodoc_changes(...)

# Convert to Page objects - adds ALL autodoc pages
pages_to_build = self._collect_pages(pages_to_rebuild, autodoc_pages)
```

**Problem**: The autodoc system lacks:
1. **Source → Symbol mapping**: No tracking of which Python file affects which autodoc page
2. **Output validation**: No check if existing HTML is still valid
3. **Content hashing**: No hash of source docstrings to detect actual changes

## Proposed Solution

### Phase 1: Source-Symbol Dependency Tracking

Track which autodoc pages depend on which source files:

```python
# New: bengal/cache/autodoc_dependencies.py
@dataclass
class AutodocDependency:
    """Tracks source → autodoc page dependencies."""
    
    # Source file path → set of autodoc page paths
    source_to_pages: dict[str, set[str]]
    
    # Autodoc page path → source file hash
    page_source_hashes: dict[str, str]
    
    # Autodoc page path → output content hash  
    page_output_hashes: dict[str, str]
```

**Integration points**:
- `bengal/orchestration/content.py:phase_autodoc()` — Build dependency map during discovery
- `bengal/orchestration/incremental/taxonomy_detector.py:check_autodoc_changes()` — Use dependency map for selective rebuild

### Phase 2: Docstring Content Hashing

Hash the actual docstring content, not just file mtime:

```python
def compute_symbol_hash(symbol: Any) -> str:
    """Compute hash of symbol's docstring and signature."""
    parts = [
        symbol.__doc__ or "",
        str(getattr(symbol, "__annotations__", {})),
        str(getattr(symbol, "__signature__", "")),
    ]
    return hash_str("|".join(parts), truncate=16)
```

**Why this matters**: A Python file can change (imports, formatting) without affecting the docstring that becomes the API doc content.

### Phase 3: Output Validation Cache

Before regenerating, check if existing output is valid:

```python
class AutodocOutputCache:
    """Cache for autodoc output validation."""
    
    def should_regenerate(
        self,
        page_path: Path,
        source_hash: str,
        template_hash: str,
    ) -> bool:
        """Check if autodoc page needs regeneration."""
        entry = self.entries.get(str(page_path))
        if not entry:
            return True
        
        # Check source content changed
        if entry.source_hash != source_hash:
            return True
            
        # Check template changed
        if entry.template_hash != template_hash:
            return True
            
        # Check output exists
        if not self._output_exists(page_path):
            return True
            
        return False
```

### Phase 4: Selective Autodoc Rebuild

Modify `check_autodoc_changes()` to return only affected pages:

```python
def check_autodoc_changes(self, ...) -> set[str]:
    """Check for autodoc source file changes - SELECTIVE."""
    
    affected_pages: set[str] = set()
    
    # Get changed Python files
    changed_sources = self._get_changed_python_files()
    
    if not changed_sources:
        return affected_pages  # Nothing changed → skip all autodoc
    
    # Use dependency map to find affected pages
    for source_path in changed_sources:
        affected = self.autodoc_deps.source_to_pages.get(str(source_path), set())
        affected_pages.update(affected)
    
    return affected_pages
```

## Implementation Plan

### Sprint 1: Dependency Tracking (3-4 hours)

1. Create `AutodocDependencyTracker` class
2. Build source → page mapping during autodoc discovery
3. Persist mapping to `.bengal/autodoc_deps.json.zst`
4. Add unit tests for dependency tracking

**Files to modify**:
- `bengal/cache/autodoc_dependencies.py` (new)
- `bengal/orchestration/content.py` (integrate tracker)
- `bengal/cache/paths.py` (add path)

### Sprint 2: Source Hashing (2-3 hours)

1. Implement `compute_symbol_hash()` for docstrings
2. Store hashes in dependency cache
3. Compare hashes before rebuild decision
4. Add unit tests

**Files to modify**:
- `bengal/utils/primitives/hashing.py` (add symbol hashing)
- `bengal/cache/autodoc_dependencies.py` (store hashes)

### Sprint 3: Selective Rebuild (2-3 hours)

1. Modify `check_autodoc_changes()` to use dependency map
2. Only return affected autodoc pages
3. Add integration tests
4. Verify with real site

**Files to modify**:
- `bengal/orchestration/incremental/taxonomy_detector.py`
- `bengal/orchestration/incremental/change_detector.py`

### Sprint 4: Output Validation (2 hours)

1. Add output existence check
2. Skip regeneration if output exists and source unchanged
3. Add behavioral test

**Files to modify**:
- `bengal/orchestration/incremental/filter_engine.py`

## Performance Analysis

### Expected Improvement

| Scenario | Before | After |
|----------|--------|-------|
| No Python changes | 845 pages rebuilt | 0 pages rebuilt |
| One file changed | 845 pages rebuilt | ~10 pages rebuilt |
| Template changed | 845 pages rebuilt | 845 pages rebuilt |
| Full build | 845 pages | 845 pages (no change) |

### Incremental Build Time

```
Before: 15s (845 autodoc pages @ 18ms each)
After:  <2s (hash checks only, no rendering)
Improvement: 87% reduction
```

## API Design

### AutodocDependencyTracker

```python
class AutodocDependencyTracker:
    """Tracks autodoc source → page dependencies."""
    
    def __init__(self, cache_path: Path) -> None:
        """Initialize tracker, loading from cache if exists."""
    
    def track_symbol(
        self,
        source_file: Path,
        symbol_name: str,
        page_path: Path,
        docstring_hash: str,
    ) -> None:
        """Track a symbol's source → page dependency."""
    
    def get_affected_pages(
        self,
        changed_sources: set[Path],
    ) -> set[Path]:
        """Get autodoc pages affected by source changes."""
    
    def should_regenerate(
        self,
        page_path: Path,
        current_source_hash: str,
    ) -> bool:
        """Check if page needs regeneration based on source hash."""
    
    def save(self) -> None:
        """Persist tracker to disk."""
```

## Migration Path

### Backward Compatibility

- First build after upgrade: Full autodoc rebuild (no cache yet)
- Subsequent builds: Selective rebuild (cache populated)
- No breaking changes to config or CLI

### Cache Invalidation

The autodoc cache should invalidate when:
1. Template files change (`autodoc.html`, etc.)
2. Bengal version changes (format might differ)
3. Autodoc config changes (`autodoc.exclude`, etc.)

## Testing Strategy

### Unit Tests

```python
class TestAutodocDependencyTracker:
    def test_track_symbol_builds_mapping(self): ...
    def test_get_affected_pages_returns_correct_set(self): ...
    def test_should_regenerate_true_when_source_changed(self): ...
    def test_should_regenerate_false_when_unchanged(self): ...
    def test_cache_persistence(self): ...
```

### Behavioral Tests

```python
class TestAutodocIncrementalBehavior:
    def test_no_python_changes_skips_all_autodoc(self):
        """When no Python files change, no autodoc pages rebuild."""
        # Build site
        # Edit content/_index.md (no Python)
        # Rebuild
        # Assert: 0 autodoc pages in pages_to_build
    
    def test_single_file_change_rebuilds_affected_only(self):
        """When one Python file changes, only affected autodoc rebuilds."""
        # Build site
        # Edit bengal/core/page.py
        # Rebuild
        # Assert: Only Page-related autodoc pages rebuild
```

## Risks and Mitigations

### Risk 1: Incorrect Dependency Tracking

**Risk**: Missing a dependency causes stale docs.

**Mitigation**: 
- Include all imports in dependency tracking
- Add "last full rebuild" timestamp for periodic validation
- Conservative fallback: rebuild all if tracking fails

### Risk 2: Hash Collisions

**Risk**: Different docstrings produce same hash.

**Mitigation**:
- Use 16-char truncated SHA-256 (collision probability ~1 in 10^19)
- Store full docstring hash, not truncated

### Risk 3: Complex Inheritance

**Risk**: Docstring inherited from parent class not tracked.

**Mitigation**:
- Track `__mro__` for classes
- Include parent docstrings in hash computation

## Success Criteria

1. **Incremental build with no Python changes**: 0 autodoc pages rebuilt
2. **Single Python file change**: Only affected autodoc pages rebuilt
3. **Build time reduction**: From 15s to <2s for no-Python-change builds
4. **No false negatives**: Changing docstring always triggers rebuild

## Appendix: Current Autodoc Architecture

### File Locations

```
bengal/orchestration/autodoc/
├── __init__.py           # Main AutodocOrchestrator
├── python_inspector.py   # Python symbol discovery
├── cli_inspector.py      # CLI command discovery
└── rest_inspector.py     # REST API discovery

bengal/orchestration/incremental/
├── taxonomy_detector.py  # check_autodoc_changes() lives here
└── change_detector.py    # Calls check_autodoc_changes()
```

### Page Counts (Bengal site)

| Type | Count | Template |
|------|-------|----------|
| autodoc-python | 726 | autodoc.html |
| autodoc-cli | 96 | autodoc-cli.html |
| autodoc-rest | 23 | autodoc-rest.html |
| **Total** | **845** | |

## References

- [RFC: Output Cache Architecture](rfc-output-cache-architecture.md) — Parent RFC for caching strategy
- [RFC: Behavioral Test Hardening](rfc-behavioral-test-hardening.md) — Testing approach
- `bengal/orchestration/autodoc/` — Current autodoc implementation
