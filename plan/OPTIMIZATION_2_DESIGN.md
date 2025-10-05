# Optimization #2: Parsed Content Caching - Design Document

**Date:** October 5, 2025  
**Status:** 🔨 In Design  
**Target:** 20-30% faster incremental builds

---

## Problem Statement

**Current Behavior:**
When running incremental builds, Bengal:
1. Checks if file changed (SHA256 hash) ✅
2. If unchanged: Skips rebuild... but **still has to re-parse markdown** to get HTML
3. Result: We save I/O but **not** parsing time

**Example:**
```python
# Current incremental build:
if cache.is_changed(page.source_path):
    # Changed - full rebuild
    html, toc = parser.parse(content)  # ← Parse
    render_and_write(html)
else:
    # Unchanged - but we don't have the parsed HTML!
    # So we either:
    # A) Skip entirely (don't write output) ← Current
    # B) Re-parse to get HTML ← Wasteful!
```

---

## Solution: Cache Parsed HTML

Store the **parsed HTML output** in the build cache alongside file hashes.

```python
# Proposed:
if cache.is_changed(page.source_path):
    # Changed - parse and cache
    html, toc = parser.parse(content)
    cache.store_parsed_content(page.source_path, html, toc, metadata)  # NEW
    render_and_write(html)
else:
    # Unchanged - load from cache!
    cached = cache.get_parsed_content(page.source_path)  # NEW
    if cached:
        html = cached['html']  # ← Skip parsing!
        toc = cached['toc']
        render_and_write(html)
```

---

## Architecture

### Data Structure

Add to `BuildCache`:
```python
@dataclass
class BuildCache:
    # Existing fields:
    file_hashes: Dict[str, str]
    dependencies: Dict[str, Set[str]]
    taxonomy_deps: Dict[str, Set[str]]
    page_tags: Dict[str, Set[str]]
    
    # NEW: Parsed content cache
    parsed_content: Dict[str, ParsedContentCache] = field(default_factory=dict)


@dataclass
class ParsedContentCache:
    """Cached parsed content for a page."""
    html: str                    # Rendered HTML (post-markdown, pre-template)
    toc: str                     # Table of contents HTML
    toc_items: List[Dict]        # Structured TOC data
    metadata_hash: str           # SHA256 of frontmatter (detect metadata changes)
    template: str                # Template used (invalidate if changed)
    parser_version: str          # Parser version (invalidate on upgrades)
    timestamp: str               # When cached
    size_bytes: int              # For cache size management
```

### Cache Invalidation

Parsed content cache is invalidated when:
1. **File content changes** (detected by file_hashes) ✅
2. **Frontmatter/metadata changes** (metadata_hash mismatch) ✅
3. **Template changes** (template dependency tracking) ✅
4. **Parser upgrade** (parser_version mismatch) ✅

---

## Implementation Plan

### Phase 1: Core Caching (Week 1)

**File:** `bengal/cache/build_cache.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import hashlib

@dataclass
class ParsedContentCache:
    """Cached parsed markdown content."""
    html: str
    toc: str
    toc_items: List[Dict[str, Any]]
    metadata_hash: str
    template: str
    parser_version: str  # e.g., "mistune-3.0"
    timestamp: str
    size_bytes: int

@dataclass
class BuildCache:
    # ... existing fields ...
    parsed_content: Dict[str, ParsedContentCache] = field(default_factory=dict)
    
    def store_parsed_content(
        self,
        file_path: Path,
        html: str,
        toc: str,
        toc_items: List[Dict],
        metadata: Dict[str, Any],
        template: str,
        parser_version: str
    ) -> None:
        """Store parsed content in cache."""
        # Hash metadata to detect changes
        metadata_str = json.dumps(metadata, sort_keys=True)
        metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()
        
        # Calculate size
        size_bytes = len(html) + len(toc)
        
        # Store
        self.parsed_content[str(file_path)] = ParsedContentCache(
            html=html,
            toc=toc,
            toc_items=toc_items,
            metadata_hash=metadata_hash,
            template=template,
            parser_version=parser_version,
            timestamp=datetime.now().isoformat(),
            size_bytes=size_bytes
        )
    
    def get_parsed_content(
        self,
        file_path: Path,
        metadata: Dict[str, Any],
        template: str,
        parser_version: str
    ) -> Optional[ParsedContentCache]:
        """Get cached parsed content if valid."""
        key = str(file_path)
        
        # Check if cached
        if key not in self.parsed_content:
            return None
        
        cached = self.parsed_content[key]
        
        # Validate file hasn't changed
        if self.is_changed(file_path):
            return None
        
        # Validate metadata hasn't changed
        metadata_str = json.dumps(metadata, sort_keys=True)
        metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()
        if cached.metadata_hash != metadata_hash:
            return None
        
        # Validate template hasn't changed
        if cached.template != template:
            return None
        
        # Validate parser version (invalidate on upgrades)
        if cached.parser_version != parser_version:
            return None
        
        return cached
    
    def invalidate_parsed_content(self, file_path: Path) -> None:
        """Remove cached parsed content for a file."""
        self.parsed_content.pop(str(file_path), None)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(c.size_bytes for c in self.parsed_content.values())
        return {
            'cached_pages': len(self.parsed_content),
            'total_size_mb': total_size / 1024 / 1024,
            'avg_size_kb': (total_size / len(self.parsed_content) / 1024) if self.parsed_content else 0
        }
```

### Phase 2: Pipeline Integration (Week 1)

**File:** `bengal/rendering/pipeline.py`

```python
def process_page(self, page: Page) -> None:
    """Process a single page through the pipeline."""
    
    # Determine template early
    template = self._determine_template(page)
    
    # Get parser version for cache validation
    parser_version = self._get_parser_version()
    
    # Try parsed content cache first (OPTIMIZATION #2)
    if self.cache and not page.metadata.get('_generated'):
        cached = self.cache.get_parsed_content(
            page.source_path,
            page.metadata,
            template,
            parser_version
        )
        
        if cached:
            # Cache HIT - skip parsing!
            page.parsed_ast = cached.html
            page.toc = cached.toc
            page._toc_items = cached.toc_items  # Direct assignment
            
            # Jump to template rendering
            page.rendered_html = self.renderer.render_page(page, cached.html)
            self._write_output(page)
            
            # Track cache hit for stats
            if self.build_stats:
                self.build_stats.cache_hits = getattr(self.build_stats, 'cache_hits', 0) + 1
            
            return  # EARLY RETURN - parsing skipped!
    
    # Cache MISS - parse markdown
    if hasattr(self.parser, 'parse_with_toc_and_context'):
        context = {'page': page, 'site': self.site, 'config': self.site.config}
        parsed_content, toc = self.parser.parse_with_toc_and_context(
            page.content, page.metadata, context
        )
    else:
        parsed_content, toc = self.parser.parse_with_toc(page.content, page.metadata)
    
    page.parsed_ast = parsed_content
    page.toc = toc
    
    # Extract TOC items
    from bengal.rendering.pipeline import extract_toc_structure
    page._toc_items = extract_toc_structure(toc)
    
    # Store in cache for next build
    if self.cache and not page.metadata.get('_generated'):
        self.cache.store_parsed_content(
            page.source_path,
            parsed_content,
            toc,
            page._toc_items,
            page.metadata,
            template,
            parser_version
        )
    
    # Continue with template rendering...
    page.rendered_html = self.renderer.render_page(page, parsed_content)
    self._write_output(page)

def _determine_template(self, page: Page) -> str:
    """Determine which template will be used for this page."""
    # Logic from renderer to determine template name
    if hasattr(page, 'template') and page.template:
        return page.template
    if page.metadata.get('type') == 'page':
        return 'page.html'
    return 'single.html'

def _get_parser_version(self) -> str:
    """Get parser version string for cache validation."""
    parser_name = type(self.parser).__name__
    
    # Try to get actual version
    if parser_name == 'MistuneParser':
        try:
            import mistune
            return f"mistune-{mistune.__version__}"
        except:
            return "mistune-unknown"
    elif parser_name == 'PythonMarkdownParser':
        try:
            import markdown
            return f"markdown-{markdown.__version__}"
        except:
            return "markdown-unknown"
    
    return "unknown"
```

### Phase 3: Statistics & Monitoring (Week 2)

**File:** `bengal/utils/build_stats.py`

```python
@dataclass
class BuildStats:
    # ... existing fields ...
    
    # NEW: Cache statistics
    cache_hits: int = 0      # Pages loaded from cache
    cache_misses: int = 0    # Pages that were parsed
    cache_size_mb: float = 0 # Size of parsed content cache
```

**Display in build output:**
```
📦 Cache Performance:
   ├─ Hits:   45 pages (90%)
   ├─ Misses:  5 pages (10%)
   └─ Size:   12.5 MB
```

---

## Performance Projections

### Scenario: 100-page site, 1 page changed

**Before (current incremental):**
```
Check 100 pages for changes:
  - 1 changed:   Parse (20ms) + Render (15ms) + Write (5ms) = 40ms
  - 99 unchanged: Skip entirely
  
Total: 40ms
```

**After (with parsed content cache):**
```
Check 100 pages for changes:
  - 1 changed:   Parse (20ms) + Cache + Render (15ms) + Write (5ms) = 42ms
  - 99 unchanged: Load cache (1ms) + Render (15ms) + Write (5ms) = 21ms each
  
Wait, that's WORSE! We're now rendering unchanged pages!
```

**Issue Identified:** We need to decide WHEN to use the cache.

### Revised Strategy:

**Option A: Cache for Skip**
- Don't render unchanged pages at all (current behavior)
- Cache is only for **validation** that nothing changed
- **Gain:** None (just makes skipping faster)

**Option B: Cache for Rebuild**
- Always render all pages (no skip)
- Cache speeds up the markdown parsing step
- **Gain:** 20-30% faster **full** builds, not incremental

**Option C: Smart Hybrid**
- If template changed: Render all pages with cached HTML (skip re-parsing)
- If content changed: Parse and render that page only
- **Gain:** Best of both worlds

---

## Revised Design: Hybrid Approach

```python
def process_pages(self, pages, incremental_mode):
    if incremental_mode:
        changed_pages = [p for p in pages if cache.is_changed(p.source_path)]
        template_changed = any(cache.is_changed(t) for t in templates)
        
        if template_changed:
            # Template changed - render ALL pages with cached HTML
            for page in pages:
                cached = cache.get_parsed_content(page.source_path)
                if cached:
                    # Use cached HTML, re-render with new template
                    render_with_cache(page, cached.html)
                else:
                    # Parse and render
                    parse_and_render(page)
        else:
            # Only content changed - render changed pages only
            for page in changed_pages:
                parse_and_render(page)
```

**This gives us:**
- **Content change:** Skip unchanged pages (current behavior) ✅
- **Template change:** Use cached HTML for all pages (30% faster!) 🔥

---

## Expected Impact

| Scenario | Current | With Cache | Speedup |
|----------|---------|------------|---------|
| 1 file changed (content) | 0.047s | 0.047s | 0% (no change) |
| Template changed | 1.66s (full rebuild) | 1.20s | 28% faster |
| Many files changed | 0.5s | 0.35s | 30% faster |

**Key Insight:** Biggest win is **template changes**, not content changes!

---

## Cache Size Management

### Storage Estimates:
- Average page HTML: ~15KB
- Average TOC: ~2KB
- Total per page: ~17KB
- 1000 pages: ~17MB

### Limits:
```toml
[build.cache]
max_parsed_content_mb = 50  # Default: 50MB
max_age_days = 30           # Purge old entries
```

### LRU Eviction:
```python
def _evict_if_needed(self):
    """Evict old entries if cache too large."""
    max_size = self.config.get('max_parsed_content_mb', 50) * 1024 * 1024
    current_size = sum(c.size_bytes for c in self.parsed_content.values())
    
    if current_size > max_size:
        # Sort by timestamp, remove oldest
        sorted_items = sorted(
            self.parsed_content.items(),
            key=lambda x: x[1].timestamp
        )
        # Remove 20% oldest
        remove_count = len(sorted_items) // 5
        for key, _ in sorted_items[:remove_count]:
            del self.parsed_content[key]
```

---

## Testing Plan

### Test 1: Cache Hit
```python
def test_parsed_content_cache_hit():
    # Build site twice
    # Second build should use cache for unchanged pages
    assert second_build_time < first_build_time * 0.7  # 30% faster
```

### Test 2: Cache Invalidation
```python
def test_cache_invalidation_on_metadata_change():
    # Build site
    # Change frontmatter only
    # Cache should invalidate, page re-parsed
```

### Test 3: Template Change
```python
def test_template_change_uses_cache():
    # Build site
    # Change template
    # All pages re-rendered but NOT re-parsed
```

---

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Cache too large | LRU eviction, configurable limits |
| Stale cache | Multiple invalidation checks |
| Template detection | Track template dependencies |
| Parser upgrades | Version checking |
| Metadata in HTML | Hash metadata separately |

---

## Timeline

**Week 1:**
- Day 1-2: Implement `BuildCache` changes
- Day 3-4: Integrate into `RenderingPipeline`
- Day 5: Basic testing

**Week 2:**
- Day 1-2: Add statistics & monitoring
- Day 3-4: Comprehensive testing
- Day 5: Documentation & examples

---

## Success Criteria

✅ Template changes are 25-30% faster  
✅ Cache invalidation is reliable  
✅ No false positives (rendering stale content)  
✅ Cache size stays under 50MB for 1000-page sites  
✅ All existing tests still pass  

---

**Next:** Implement Phase 1 (Core Caching) in `build_cache.py`

