# Lessons Learned: TOC Property Bug

## Why This Was So Challenging

### 1. **Hidden Lifecycle Dependency**
The bug was caused by `toc_items` being accessed at **two different points** in the build lifecycle:
- **Too Early**: During xref indexing (`content.py:283`) - BEFORE parsing
- **Correct Time**: During template rendering - AFTER parsing

The property cached the "too early" result, preventing correct extraction later.

### 2. **Caching Made It Non-Obvious**
The property used simple `None` check caching:
```python
if self._toc_items_cache is None:
    # Extract and cache
```

Once set (even to `[]`), it never re-evaluated. This violated the principle that **incomplete data shouldn't be cached**.

### 3. **Lack of Documentation About Build Phases**
The code didn't clearly document:
- When each property should be accessed
- What data is available at each build stage
- Which properties are safe to access during discovery vs. rendering

### 4. **Property Pattern Complexity**
Using `@property` with internal caching is convenient but:
- Looks like a simple attribute access
- Hides complex lazy evaluation logic
- Makes it hard to debug when things go wrong
- No clear error when accessed "too early"

## Concrete Improvements to Implement

### 1. **Add Build Phase Documentation to Properties**

**Before:**
```python
@property
def toc_items(self) -> List[Dict[str, Any]]:
    """Get structured TOC data (lazy evaluation)."""
```

**After:**
```python
@property
def toc_items(self) -> List[Dict[str, Any]]:
    """
    Get structured TOC data (lazy evaluation).
    
    Build Phase: Available after Stage 2 (parsing), used in Stage 5 (rendering)
    Dependencies: Requires self.toc to be set by pipeline.process_page()
    
    Safe to access during:
        ✅ Template rendering
        ✅ Post-processing
    
    Unsafe to access during:
        ❌ Discovery phase (before parsing)
        ❌ Xref indexing (content.py:_build_xref_index)
    
    Note: Returns empty list [] if accessed before toc is set, but does not
    cache empty results to allow proper extraction after parsing.
    """
```

### 2. **Document Build Lifecycle in Page Class**

Add to `Page` docstring:
```python
@dataclass
class Page:
    """
    Represents a single content page.
    
    BUILD LIFECYCLE:
    ================
    1. Discovery (content_discovery.py)
       - Page object created with source_path, content, metadata
       - Available: title, date, slug, metadata
       - Not available: toc, parsed_ast, rendered_html
    
    2. Parsing (pipeline.py:process_page)
       - Markdown parsed to HTML
       - Available: parsed_ast, toc, links
       - Not available: rendered_html
    
    3. Cross-reference indexing (content.py:_build_xref_index)
       - Headings extracted for internal links
       - ⚠️ Can access toc_items but returns [] if called before parsing
    
    4. Link extraction (pipeline.py)
       - Links validated and resolved
       - Available: links, external_links
    
    5. Rendering (pipeline.py:process_page)
       - Template applied, final HTML generated
       - Available: rendered_html, toc_items (fully populated)
    
    6. Output (pipeline.py)
       - HTML written to disk
       - All properties available
    
    PROPERTIES BY PHASE:
    ====================
    Always available:
        - title, slug, date, metadata, source_path
    
    After parsing (stage 2+):
        - toc, parsed_ast, toc_items (populated)
    
    After rendering (stage 5+):
        - rendered_html, output_path
    """
```

### 3. **Add Defensive Assertions**

For properties that have hard dependencies:
```python
@property
def toc_items(self) -> List[Dict[str, Any]]:
    """..."""
    # Only extract and cache if we haven't extracted yet AND toc exists
    if self._toc_items_cache is None and self.toc:
        from bengal.rendering.pipeline import extract_toc_structure
        self._toc_items_cache = extract_toc_structure(self.toc)
        
        # DEBUG: Log if extracted very few items (possible issue)
        if self._toc_items_cache and len(self._toc_items_cache) < 2:
            from bengal.utils.logger import get_logger
            logger = get_logger(__name__)
            logger.debug("toc_items_small", 
                        path=str(self.source_path),
                        count=len(self._toc_items_cache),
                        hint="This may indicate parsing issues or short document")
    
    return self._toc_items_cache if self._toc_items_cache is not None else []
```

### 4. **Create Build Phase Enum**

Define explicit phases to make dependencies clear:
```python
# bengal/core/build_phase.py
from enum import Enum, auto

class BuildPhase(Enum):
    """Build pipeline phases for tracking page lifecycle."""
    DISCOVERY = auto()      # Content files discovered, Page objects created
    PARSING = auto()        # Markdown parsed to HTML, TOC generated
    XREF_INDEX = auto()     # Cross-references indexed
    LINK_EXTRACT = auto()   # Links extracted and validated
    RENDERING = auto()      # Templates applied, HTML generated
    OUTPUT = auto()         # Files written to disk
    COMPLETE = auto()       # Build finished

# Add to Page class:
@dataclass
class Page:
    # ...
    _build_phase: BuildPhase = field(default=BuildPhase.DISCOVERY, repr=False)
    
    @property
    def toc_items(self):
        # Optional: warn if accessed too early
        if self._build_phase < BuildPhase.PARSING:
            logger.warning("toc_items_accessed_early",
                          path=str(self.source_path),
                          phase=self._build_phase.name,
                          hint="toc_items should be accessed after PARSING phase")
        # ... rest of property
```

### 5. **Improve Property Naming Convention**

Establish naming convention to signal behavior:
- `@property def computed_X()` - Computed on every access (no cache)
- `@cached_property def cached_X()` - Cached after first computation
- `@property def lazy_X()` - Cached but may re-evaluate if deps change

Or use Python 3.8+ `@cached_property`:
```python
from functools import cached_property

@cached_property
def meta_description(self) -> str:
    """..."""  # Already using this correctly!

# But for toc_items we need custom logic:
@property
def toc_items(self) -> List[Dict[str, Any]]:
    """
    Lazy-evaluated TOC structure.
    Not cached when empty to allow re-evaluation after parsing.
    """
```

### 6. **Add Integration Tests for Build Phases**

```python
# tests/integration/test_build_lifecycle.py
def test_page_properties_available_after_parsing():
    """Ensure toc_items is populated after parsing."""
    pipeline = RenderingPipeline(...)
    page = Page(...)
    
    # Before parsing
    assert page.toc is None
    assert page.toc_items == []  # Returns empty but doesn't cache
    
    # After parsing
    pipeline.process_page(page)
    assert page.toc is not None
    assert len(page.toc_items) > 0  # Now populated
    
    # Verify it stays populated
    items_first = page.toc_items
    items_second = page.toc_items
    assert items_first is items_second  # Same cached object
```

### 7. **Create Architecture Documentation**

```markdown
# docs/architecture/BUILD_PIPELINE.md

## Build Pipeline Stages

### Stage 1: Discovery
**Orchestrator**: `content.py:discover_content()`
**Purpose**: Find and create Page objects from markdown files
**Output**: List of Page objects with source_path, content, metadata
**Page properties available**: title, slug, date, metadata
**Page properties NOT available**: toc, parsed_ast, toc_items, rendered_html

### Stage 2: Parsing
**Orchestrator**: `pipeline.py:process_page()`
**Purpose**: Parse markdown to HTML, generate TOC
**Output**: page.parsed_ast, page.toc set
**Page properties available**: All from Stage 1 + toc, parsed_ast, toc_items
**Cache**: Parsed HTML and toc_items stored for incremental builds

[... etc for each stage ...]
```

## Anti-Patterns to Avoid

### ❌ Accessing properties before dependencies are ready
```python
# In content.py discovery phase
if hasattr(page, 'toc_items') and page.toc_items:  # ❌ BAD - toc not set yet
    # Do something with TOC
```

### ❌ Caching incomplete/empty data
```python
@property
def toc_items(self):
    if self._cache is None:
        self._cache = self._extract() or []  # ❌ BAD - caches empty list
    return self._cache
```

### ❌ Silent failures in properties
```python
@property
def toc_items(self):
    try:
        return extract_toc_structure(self.toc)
    except:
        return []  # ❌ BAD - silently fails, hard to debug
```

## Best Practices Going Forward

### ✅ Document dependencies in docstrings
### ✅ Use defensive programming (assertions, logging)
### ✅ Don't cache incomplete data
### ✅ Make build phases explicit
### ✅ Test properties at different lifecycle stages
### ✅ Use type hints to indicate optional vs. required data
### ✅ Log warnings when properties accessed out of order

## Specific Files to Update

1. **`bengal/core/page.py`**
   - Add BUILD LIFECYCLE section to class docstring
   - Document each property with build phase availability
   - Add Optional typing for properties that may not be available

2. **`bengal/orchestration/content.py`**
   - Document why xref indexing accesses toc_items early
   - Add comment explaining it's safe because toc_items doesn't cache empty

3. **`bengal/rendering/pipeline.py`**
   - Add stage comments showing what's available at each point
   - Document cache invalidation triggers

4. **`docs/architecture/BUILD_PIPELINE.md`** (NEW)
   - Create comprehensive build pipeline documentation
   - Include data flow diagrams

## Impact Assessment

**Time saved on similar bugs**: 2-4 hours per bug (this took ~3 hours to debug)
**Developer onboarding**: Clearer understanding of build phases
**Code maintainability**: Easier to reason about property access
**Bug prevention**: Defensive programming catches issues early

## Conclusion

This bug was challenging because it involved:
1. **Temporal coupling** - property behavior depended on WHEN it was accessed
2. **Hidden state** - caching made the bug non-obvious
3. **Lack of documentation** - build phases weren't explicit

The fixes are straightforward but require discipline:
- **Document lifecycle dependencies**
- **Don't cache incomplete data**
- **Add defensive checks**
- **Test at different build phases**

