# RFC: Autodoc Incremental Build Support

**Status**: Draft  
**Created**: 2025-01-09  
**Author**: AI Assistant  
**Related**: `bengal/orchestration/incremental.py`, `bengal/autodoc/virtual_orchestrator.py`

---

## Executive Summary

Autodoc pages currently rebuild on **every** dev server change because they're virtual pages with synthetic source paths that don't exist on disk. This RFC proposes adding proper dependency tracking and selective regeneration for autodoc pages, enabling true incremental builds.

## Problem Statement

### Current Behavior (Patch Solution)

The current patch always includes autodoc pages in incremental builds:

```python
# bengal/orchestration/incremental.py
pages_to_build_list = [
    page
    for page in self.site.pages
    if (page.source_path in pages_to_rebuild and not page.metadata.get("_generated"))
    or page.metadata.get("is_autodoc")  # Always rebuild ALL autodoc pages
]
```

**Issues**:
1. **Performance**: ALL autodoc pages rebuild on ANY change (even unrelated content changes)
2. **Wasted work**: For a site with 200 autodoc pages + 50 content pages, changing one markdown file rebuilds 250 pages instead of 1
3. **No Python file watching**: Changes to Python source files aren't detected at all

### Root Cause Analysis

1. **Virtual source paths**: Autodoc pages have paths like `python/api/config/hash.md` that don't exist on disk
2. **No file watching**: Autodoc source directories (`bengal/`) aren't in the watched directories list
3. **No dependency tracking**: The system doesn't know which Python file produced which autodoc page

## Proposed Solution

### Phase 1: Watch Autodoc Source Directories (Quick Win)

Add autodoc source directories to the file watcher.

**File**: `bengal/server/dev_server.py`

```python
def _get_watched_directories(self) -> list[str]:
    watch_dirs = [
        self.site.root_path / "content",
        self.site.root_path / "assets",
        # ... existing directories ...
    ]

    # NEW: Watch autodoc source directories
    autodoc_config = self.site.config.get("autodoc", {})
    
    # Python source directories
    python_config = autodoc_config.get("python", {})
    if python_config.get("enabled", False):
        for source_dir in python_config.get("source_dirs", []):
            source_path = self.site.root_path / source_dir
            if source_path.exists():
                watch_dirs.append(source_path)
    
    # OpenAPI spec file directory
    openapi_config = autodoc_config.get("openapi", {})
    if openapi_config.get("enabled", False):
        spec_file = openapi_config.get("spec_file")
        if spec_file:
            spec_path = self.site.root_path / Path(spec_file).parent
            if spec_path.exists():
                watch_dirs.append(spec_path)

    return [str(d) for d in watch_dirs if d.exists()]
```

**File**: `bengal/server/build_handler.py`

```python
def _should_regenerate_autodoc(self, changed_paths: set[str]) -> bool:
    """Check if any changed file is in autodoc source directories."""
    autodoc_config = self.site.config.get("autodoc", {})
    python_config = autodoc_config.get("python", {})
    
    if not python_config.get("enabled", False):
        return False
    
    source_dirs = python_config.get("source_dirs", [])
    for changed_path in changed_paths:
        path = Path(changed_path)
        for source_dir in source_dirs:
            source_path = self.site.root_path / source_dir
            try:
                path.relative_to(source_path)
                if path.suffix == ".py":
                    return True
            except ValueError:
                continue
    
    return False
```

**Behavior**: When any `.py` file in autodoc source directories changes, trigger full autodoc regeneration (similar to config change behavior).

### Phase 2: Dependency Tracking (Full Solution)

Track which Python source files produce which autodoc pages.

#### 2a. Store Dependencies During Extraction

**File**: `bengal/autodoc/virtual_orchestrator.py`

```python
def _create_pages(self, elements, sections, doc_type, result, cache=None):
    """Create virtual pages with dependency tracking."""
    for element in elements:
        page = Page.create_virtual(...)
        
        # Track source file dependency
        if cache and element.source_file:
            cache.add_autodoc_dependency(
                source_file=element.source_file,
                autodoc_page=page.source_path,
            )
```

**File**: `bengal/cache/build_cache/autodoc_tracking.py` (new mixin)

```python
class AutodocTrackingMixin:
    """Track autodoc source file to page dependencies."""
    
    autodoc_dependencies: dict[str, set[str]]  # source_file → set[autodoc_page_paths]
    
    def add_autodoc_dependency(self, source_file: Path, autodoc_page: Path) -> None:
        """Register that source_file produces autodoc_page."""
        source_key = str(source_file)
        page_key = str(autodoc_page)
        
        if source_key not in self.autodoc_dependencies:
            self.autodoc_dependencies[source_key] = set()
        self.autodoc_dependencies[source_key].add(page_key)
    
    def get_affected_autodoc_pages(self, changed_source: Path) -> set[str]:
        """Get autodoc pages affected by a source file change."""
        return self.autodoc_dependencies.get(str(changed_source), set())
```

#### 2b. Selective Regeneration in Incremental Builds

**File**: `bengal/orchestration/incremental.py`

```python
def find_work_early(self, verbose=False):
    # ... existing code ...
    
    # Check for autodoc source changes
    autodoc_pages_to_rebuild = set()
    for page in self.site.pages:
        if not page.metadata.get("is_autodoc"):
            continue
        
        source_file = page.metadata.get("source_file")
        if source_file and self.cache.is_changed(Path(source_file)):
            autodoc_pages_to_rebuild.add(page.source_path)
    
    # Convert to Page objects (selective autodoc rebuild)
    pages_to_build_list = [
        page
        for page in self.site.pages
        if (page.source_path in pages_to_rebuild and not page.metadata.get("_generated"))
        or (page.metadata.get("is_autodoc") and page.source_path in autodoc_pages_to_rebuild)
    ]
```

### Phase 3: Granular Module Re-extraction (Advanced)

For large codebases, re-extract only changed modules instead of full package scan.

**File**: `bengal/autodoc/extractors/python.py`

```python
def extract_module(self, module_path: Path) -> list[DocElement]:
    """Extract single module without full package scan."""
    # Parse just this file, not the whole package
    # Useful for incremental updates
```

**File**: `bengal/orchestration/content.py`

```python
def _discover_autodoc_content_incremental(self, changed_files: set[Path]):
    """Incrementally update autodoc for changed Python files only."""
    # Only re-extract modules that changed
    # Merge with existing autodoc pages/sections
```

## Implementation Plan

### Phase 1: Watch Autodoc Directories (1-2 hours)

1. [ ] Add autodoc source dirs to `_get_watched_directories()`
2. [ ] Add `_should_regenerate_autodoc()` to `BuildHandler`
3. [ ] Trigger full autodoc rebuild when Python files change
4. [ ] Test with dev server

**Benefit**: Python changes now trigger autodoc rebuilds (better than nothing)

### Phase 2: Dependency Tracking (4-6 hours)

1. [ ] Add `AutodocTrackingMixin` to `BuildCache`
2. [ ] Store `source_file` → `autodoc_page` mappings during extraction
3. [ ] Modify `find_work_early()` to use dependency lookup
4. [ ] Remove "always rebuild all autodoc" patch
5. [ ] Add tests for selective autodoc rebuilds

**Benefit**: Only affected autodoc pages rebuild (true incremental)

### Phase 3: Granular Re-extraction (8-12 hours)

1. [ ] Add `extract_module()` for single-file extraction
2. [ ] Add `_discover_autodoc_content_incremental()`
3. [ ] Handle module additions/deletions
4. [ ] Handle cross-module dependencies (imports, inheritance)
5. [ ] Add tests for edge cases

**Benefit**: Faster extraction for large codebases

## Trade-offs

| Approach | Performance | Complexity | Dev Time |
|----------|-------------|------------|----------|
| Current Patch | Poor (rebuilds all) | Low | Done |
| Phase 1 (Watch) | Medium (full autodoc on .py change) | Low | 1-2 hrs |
| Phase 2 (Deps) | Good (selective rebuild) | Medium | 4-6 hrs |
| Phase 3 (Granular) | Best (selective extract + rebuild) | High | 8-12 hrs |

## Recommendation

**Start with Phase 1** as a quick win, then implement **Phase 2** for production-ready incremental autodoc builds. Phase 3 is only needed for very large codebases (>500 modules).

## Related Files

- `bengal/server/dev_server.py` - File watching
- `bengal/server/build_handler.py` - Build triggering
- `bengal/orchestration/incremental.py` - Incremental build logic
- `bengal/orchestration/content.py` - Autodoc discovery
- `bengal/autodoc/virtual_orchestrator.py` - Autodoc page creation
- `bengal/cache/build_cache/` - Cache and dependency tracking

## Questions for Review

1. Should Phase 1 trigger a full site rebuild or just autodoc regeneration when Python files change?
2. For Phase 2, should we track dependencies at module level or file level?
3. Is Phase 3 worth the complexity for typical Bengal users?

---

## Appendix: Current Autodoc Data Flow

```
1. ContentOrchestrator.discover_content()
   └── _discover_autodoc_content()
       └── VirtualAutodocOrchestrator.generate()
           ├── _extract_python() → list[DocElement]
           ├── _create_python_sections() → dict[str, Section]
           └── _create_pages() → list[Page]
               └── Page.create_virtual(..., metadata={
                       "is_autodoc": True,
                       "source_file": element.source_file,  # ← KEY: Python file path
                   })

2. IncrementalOrchestrator.find_work_early()
   └── pages_to_build = [p for p in site.pages if p.source_path in pages_to_rebuild]
       # BUG: autodoc pages have virtual source_paths, never in pages_to_rebuild
       # PATCH: or page.metadata.get("is_autodoc")  ← Always rebuild all

3. RenderingPipeline.process()
   └── _process_virtual_page(page)
       └── _render_autodoc_page(page)  # Uses page.metadata["autodoc_element"]
```

