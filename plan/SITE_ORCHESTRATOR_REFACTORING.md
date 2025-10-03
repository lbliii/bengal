# Site Orchestrator Refactoring Plan

## Problem
The `Site` class in `bengal/core/site.py` has grown to **1237 lines** and violates the Single Responsibility Principle. It's doing too much:
- Content discovery
- Build orchestration  
- Taxonomy management
- Dynamic page generation
- Menu building
- Asset processing
- Post-processing
- Incremental builds
- Build validation

## Solution: Orchestrator Pattern

Extract build logic into focused orchestrator classes. The `Site` class becomes a **data container** and simple coordinator, while specialized orchestrators handle each phase.

## New Architecture

```
bengal/
  core/
    site.py              # Simplified - just data + factory methods
  orchestration/         # NEW module
    __init__.py
    build_orchestrator.py       # Main build coordinator
    content_orchestrator.py     # Discovery & setup
    taxonomy_orchestrator.py    # Taxonomies & dynamic pages
    menu_orchestrator.py        # Menu building
    asset_orchestrator.py       # Asset processing
    render_orchestrator.py      # Page rendering
    postprocess_orchestrator.py # Sitemap, RSS, validation
    incremental_orchestrator.py # Incremental build logic
```

## Orchestrator Responsibilities

### 1. BuildOrchestrator
**Purpose**: Main build coordinator - delegates to other orchestrators

```python
class BuildOrchestrator:
    """Coordinates the entire build process."""
    
    def __init__(self, site: Site):
        self.site = site
        self.stats = BuildStats()
        self.content = ContentOrchestrator(site)
        self.taxonomy = TaxonomyOrchestrator(site)
        self.menu = MenuOrchestrator(site)
        self.render = RenderOrchestrator(site)
        self.assets = AssetOrchestrator(site)
        self.postprocess = PostprocessOrchestrator(site)
        self.incremental = IncrementalOrchestrator(site)
    
    def build(self, parallel: bool = True, incremental: bool = False, 
              verbose: bool = False) -> BuildStats:
        """Execute full build pipeline."""
        # 1. Initialize
        self._initialize_build(incremental)
        
        # 2. Discovery
        self.content.discover()
        
        # 3. Taxonomies & dynamic pages
        self.taxonomy.collect_and_generate()
        
        # 4. Menus
        self.menu.build()
        
        # 5. Determine work (incremental)
        pages, assets = self.incremental.find_work()
        
        # 6. Render pages
        self.render.process(pages, parallel)
        
        # 7. Process assets
        self.assets.process(assets, parallel)
        
        # 8. Post-process
        self.postprocess.run()
        
        # 9. Validate
        self._validate()
        
        return self.stats
```

**Responsibilities**:
- Coordinates build phases
- Tracks build statistics
- Manages cache initialization
- Handles errors and reporting

**Lines**: ~150-200

---

### 2. ContentOrchestrator  
**Purpose**: Content & asset discovery + setup

```python
class ContentOrchestrator:
    """Handles content and asset discovery."""
    
    def __init__(self, site: Site):
        self.site = site
    
    def discover(self) -> None:
        """Discover all content and assets."""
        self.discover_content()
        self.discover_assets()
        self._setup_references()
        self._apply_cascades()
```

**Responsibilities**:
- `discover_content()` - find pages/sections
- `discover_assets()` - find assets  
- `_setup_references()` - page/section references
- `_apply_cascades()` - cascade metadata

**Lines**: ~200 (from site.py lines 98-253)

---

### 3. TaxonomyOrchestrator
**Purpose**: Taxonomy collection & dynamic page generation

```python
class TaxonomyOrchestrator:
    """Handles taxonomies and dynamic page generation."""
    
    def __init__(self, site: Site):
        self.site = site
    
    def collect_and_generate(self) -> None:
        """Collect taxonomies and generate dynamic pages."""
        self.collect_taxonomies()
        self.generate_dynamic_pages()
    
    def collect_taxonomies(self) -> None:
        """Collect tags, categories, etc."""
        # From site.py lines 966-1013
    
    def generate_dynamic_pages(self) -> None:
        """Generate archive, tag pages."""
        # From site.py lines 1014-1173
```

**Responsibilities**:
- Collect tags/categories
- Generate tag pages (with pagination)
- Generate archive pages (with pagination)

**Lines**: ~220 (from site.py lines 966-1173)

---

### 4. MenuOrchestrator
**Purpose**: Menu building

```python
class MenuOrchestrator:
    """Handles menu building."""
    
    def __init__(self, site: Site):
        self.site = site
    
    def build(self) -> None:
        """Build all menus from config and frontmatter."""
        # From site.py lines 1175-1209
    
    def mark_active(self, current_page: Page) -> None:
        """Mark active menu items for current page."""
        # From site.py lines 1211-1221
```

**Responsibilities**:
- Build navigation menus
- Mark active items

**Lines**: ~60 (from site.py lines 1175-1221)

---

### 5. RenderOrchestrator
**Purpose**: Page rendering (sequential & parallel)

```python
class RenderOrchestrator:
    """Handles page rendering."""
    
    def __init__(self, site: Site):
        self.site = site
    
    def process(self, pages: List[Page], parallel: bool = True, 
                tracker: DependencyTracker = None, stats: BuildStats = None) -> None:
        """Render pages (parallel or sequential)."""
        if parallel and len(pages) > 1:
            self._render_parallel(pages, tracker, stats)
        else:
            self._render_sequential(pages, tracker, stats)
```

**Responsibilities**:
- Sequential rendering
- Parallel rendering
- Pipeline creation/management

**Lines**: ~100 (from site.py lines 374-500)

---

### 6. AssetOrchestrator
**Purpose**: Asset processing (copy, minify, optimize)

```python
class AssetOrchestrator:
    """Handles asset processing."""
    
    def __init__(self, site: Site):
        self.site = site
    
    def process(self, assets: List[Asset], parallel: bool = True) -> None:
        """Process assets (minify, optimize, copy)."""
        # From site.py lines 502-607
```

**Responsibilities**:
- Sequential asset processing
- Parallel asset processing
- Minification, optimization, fingerprinting

**Lines**: ~120 (from site.py lines 502-607)

---

### 7. PostprocessOrchestrator
**Purpose**: Post-processing tasks

```python
class PostprocessOrchestrator:
    """Handles post-processing tasks."""
    
    def __init__(self, site: Site):
        self.site = site
    
    def run(self, parallel: bool = True) -> None:
        """Run post-processing tasks."""
        tasks = self._collect_tasks()
        if parallel:
            self._run_parallel(tasks)
        else:
            self._run_sequential(tasks)
```

**Responsibilities**:
- Sitemap generation
- RSS generation  
- Link validation
- Build health checks
- Parallel/sequential execution

**Lines**: ~150 (from site.py lines 609-686, 851-964)

---

### 8. IncrementalOrchestrator
**Purpose**: Incremental build logic

```python
class IncrementalOrchestrator:
    """Handles incremental build logic."""
    
    def __init__(self, site: Site):
        self.site = site
        self.cache = None
        self.tracker = None
    
    def initialize(self, output_dir: Path, enabled: bool) -> tuple:
        """Initialize cache and tracker."""
        # Returns (cache, tracker)
    
    def find_work(self, cache: BuildCache, tracker: DependencyTracker) -> tuple:
        """Find pages/assets that need rebuilding."""
        # From site.py lines 688-810
        # Returns (pages_to_build, assets_to_process, change_summary)
```

**Responsibilities**:
- Cache management
- Change detection (content, assets, templates)
- Dependency tracking
- Taxonomy change detection

**Lines**: ~150 (from site.py lines 688-810 + initialization)

---

## Simplified Site Class

After refactoring, `Site` becomes:

```python
@dataclass
class Site:
    """
    Represents the entire website (data container).
    Build logic delegated to orchestrators.
    """
    
    # Data attributes (same as before)
    root_path: Path
    config: Dict[str, Any] = field(default_factory=dict)
    pages: List[Page] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    assets: List[Asset] = field(default_factory=list)
    theme: Optional[str] = None
    output_dir: Path = field(default_factory=lambda: Path("public"))
    build_time: Optional[datetime] = None
    taxonomies: Dict[str, Dict[str, List[Page]]] = field(default_factory=dict)
    menu: Dict[str, List[MenuItem]] = field(default_factory=dict)
    menu_builders: Dict[str, MenuBuilder] = field(default_factory=dict)
    
    @classmethod
    def from_config(cls, root_path: Path, config_path: Optional[Path] = None) -> 'Site':
        """Create from config (factory method)."""
        # Same as before
    
    @property
    def regular_pages(self) -> List[Page]:
        """Get regular pages (excludes generated)."""
        return [p for p in self.pages if not p.metadata.get('_generated')]
    
    def build(self, parallel: bool = True, incremental: bool = False, 
              verbose: bool = False) -> BuildStats:
        """Build the site (delegates to BuildOrchestrator)."""
        from bengal.orchestration import BuildOrchestrator
        orchestrator = BuildOrchestrator(self)
        return orchestrator.build(parallel=parallel, incremental=incremental, 
                                 verbose=verbose)
    
    def serve(self, host: str = "localhost", port: int = 8000, 
              watch: bool = True, auto_port: bool = True) -> None:
        """Start dev server."""
        from bengal.server.dev_server import DevServer
        server = DevServer(self, host=host, port=port, watch=watch, 
                          auto_port=auto_port)
        server.start()
    
    def clean(self) -> None:
        """Clean output directory."""
        # Same as before (~10 lines)
```

**Lines**: ~100-150 (down from 1237!)

---

## Migration Strategy

### Phase 1: Create Orchestrator Stub Module
1. Create `bengal/orchestration/` module
2. Create empty orchestrator classes
3. Add tests for each orchestrator

### Phase 2: Extract One Orchestrator at a Time
**Order** (from easiest to hardest):
1. ✅ **MenuOrchestrator** (simplest, ~60 lines, no dependencies)
2. ✅ **PostprocessOrchestrator** (independent, ~150 lines)
3. ✅ **AssetOrchestrator** (independent, ~120 lines)  
4. ✅ **TaxonomyOrchestrator** (~220 lines, depends on Site data)
5. ✅ **RenderOrchestrator** (~100 lines, uses RenderingPipeline)
6. ✅ **ContentOrchestrator** (~200 lines, foundational)
7. ✅ **IncrementalOrchestrator** (~150 lines, complex dependencies)
8. ✅ **BuildOrchestrator** (main coordinator, ties everything together)

For each orchestrator:
- Extract code from `site.py`
- Create orchestrator class
- Update `Site.build()` to delegate to orchestrator
- Run tests to ensure nothing breaks
- Update any affected tests

### Phase 3: Final Cleanup
1. Verify all tests pass
2. Update documentation
3. Check for any remaining duplication
4. Ensure `Site` class is now <200 lines

---

## Benefits

### Code Organization
- **Single Responsibility**: Each orchestrator has one clear purpose
- **Testability**: Easy to test each orchestrator in isolation
- **Maintainability**: Changes are localized to specific orchestrators
- **Readability**: ~150-200 lines per file vs 1237 in one file

### Extensibility
- Easy to add new build phases (just add new orchestrator)
- Easy to customize build process (swap orchestrators)
- Plugin system becomes natural (orchestrators as plugins)

### Performance
- Parallel processing already implemented, now better organized
- Easier to optimize individual phases
- Better visibility into what each phase is doing

---

## Risks & Mitigation

### Risk 1: Breaking Changes
**Mitigation**: Keep `Site.build()` API the same - orchestrators are internal implementation detail

### Risk 2: Circular Dependencies
**Mitigation**: Orchestrators depend on `Site` (data), but not each other. `BuildOrchestrator` coordinates them.

### Risk 3: Regression Bugs
**Mitigation**: 
- Extract one orchestrator at a time
- Run full test suite after each extraction
- Keep git history clean (one commit per orchestrator)

---

## Acceptance Criteria

✅ `Site` class is <200 lines  
✅ All orchestrators are <250 lines  
✅ All existing tests pass  
✅ Build performance is same or better  
✅ Public API unchanged (backward compatible)  
✅ Documentation updated  

---

## Timeline Estimate

- **Phase 1** (Stub module): 1 hour
- **Phase 2** (Extract orchestrators): 6-8 hours
  - 30-60 min per orchestrator × 8 orchestrators
- **Phase 3** (Cleanup): 1-2 hours

**Total**: ~8-11 hours of focused work

---

## Notes

- This is a **pure refactoring** - no new features, just reorganization
- The public API (`Site.build()`, `Site.serve()`, etc.) stays the same
- Tests should continue to work with minimal changes
- This sets up Bengal for future plugin architecture

