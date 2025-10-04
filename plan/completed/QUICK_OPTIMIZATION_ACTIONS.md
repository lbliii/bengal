# Quick Optimization Actions - Do These First! 🚀

**Date:** October 4, 2025  
**Goal:** 2-3x faster rendering with minimal risk  
**Time Required:** 4-6 hours total

---

## TL;DR - What to Do Right Now

**The Big Win:** Replace BeautifulSoup with regex in parser.py  
**Expected Impact:** 40% faster rendering (5-10x speedup on heading/TOC operations)  
**Difficulty:** Medium  
**Risk:** Medium (needs careful testing)

---

## Phase 1: Quick Wins (2 hours, 40% speedup) 🎯

### 1. Replace BeautifulSoup in `_inject_heading_anchors()` ⚡

**File:** `bengal/rendering/parser.py:357-421`

**Current:** Uses BeautifulSoup to parse HTML and inject heading anchors  
**Problem:** 5-10x slower than regex for simple operations  
**Impact:** ~50-100ms per page on large pages

**Replace with regex:**
```python
# At class level - compile once
_HEADING_PATTERN = re.compile(
    r'<(h[234])([^>]*)>(.*?)</\1>',
    re.IGNORECASE | re.DOTALL
)

def _inject_heading_anchors(self, html: str) -> str:
    """Inject IDs and headerlinks using fast regex (5-10x faster than BS4)."""
    if not html or not ('<h2' in html or '<h3' in html or '<h4' in html):
        return html
    
    def replace_heading(match):
        tag = match.group(1)  # 'h2', 'h3', or 'h4'
        attrs = match.group(2)
        content = match.group(3)
        
        # Skip if already has id=
        if 'id=' in attrs:
            return match.group(0)
        
        # Extract text for slug (strip any HTML tags)
        text = re.sub(r'<[^>]+>', '', content).strip()
        if not text:
            return match.group(0)
        
        slug = self._slugify(text)
        
        return (
            f'<{tag} id="{slug}"{attrs}>{content}'
            f'<a href="#{slug}" class="headerlink" title="Permanent link">¶</a>'
            f'</{tag}>'
        )
    
    return _HEADING_PATTERN.sub(replace_heading, html)
```

**Test:** Compare output byte-for-byte with existing BS4 implementation on showcase site.

---

### 2. Replace BeautifulSoup in `_extract_toc()` ⚡

**File:** `bengal/rendering/parser.py:423-483`

**Current:** Uses BeautifulSoup to extract TOC from HTML  
**Problem:** 5-8x slower than regex  
**Impact:** ~20-30ms per page

**Replace with regex:**
```python
def _extract_toc(self, html: str) -> str:
    """Extract TOC using fast regex (assumes _inject_heading_anchors was called)."""
    if not html or not ('<h2' in html or '<h3' in html or '<h4' in html):
        return ''
    
    # Match: <h2 id="slug" ...>Title<a ...>¶</a></h2>
    pattern = re.compile(
        r'<(h[234])\s+id="([^"]+)"[^>]*>(.*?)<a[^>]*>¶</a></\1>',
        re.IGNORECASE | re.DOTALL
    )
    
    toc_items = []
    for match in pattern.finditer(html):
        level = int(match.group(1)[1])  # 'h2' → 2
        heading_id = match.group(2)
        title_html = match.group(3).strip()
        
        # Strip HTML tags to get clean title text
        title = re.sub(r'<[^>]+>', '', title_html).strip()
        if not title:
            continue
        
        indent = '  ' * (level - 2)
        toc_items.append(f'{indent}<li><a href="#{heading_id}">{title}</a></li>')
    
    if not toc_items:
        return ''
    
    return (
        '<div class="toc">\n'
        '<ul>\n'
        + '\n'.join(toc_items) + '\n'
        '</ul>\n'
        '</div>'
    )
```

**Test:** Compare TOC output with existing BS4 implementation.

---

### 3. Lazy `toc_items` Property ⚡

**File:** `bengal/core/page.py`

**Current:** Always extracts TOC structure in pipeline  
**Problem:** Many templates don't use `toc_items`, wasteful HTMLParser overhead  
**Impact:** ~20-30ms saved per page

**Make it lazy:**
```python
class Page:
    def __init__(self, ...):
        # ... existing init ...
        self._toc_items_cache = None  # Add this
    
    @property
    def toc_items(self):
        """Lazy extraction of TOC structure (only when template accesses it)."""
        if self._toc_items_cache is None and self.toc:
            from bengal.rendering.pipeline import RenderingPipeline
            # Call the static extraction method
            self._toc_items_cache = RenderingPipeline._extract_toc_structure_static(self.toc)
        return self._toc_items_cache or []
```

**In pipeline.py:**
```python
# Remove from process_page():
# page.toc_items = self._extract_toc_structure(toc)  ← DELETE THIS LINE

# Make extraction method static
@staticmethod
def _extract_toc_structure_static(toc_html: str) -> list:
    """Parse TOC HTML into structured data."""
    # ... existing implementation ...
```

**Impact:** Pages that don't use `toc_items` skip HTMLParser entirely!

---

### 4. Quick Rejection in Cross-Reference Plugin ⚡

**File:** `bengal/rendering/plugins/cross_references.py:78-100`

**Add quick check:**
```python
def _substitute_xrefs(self, text: str) -> str:
    """Substitute [[link]] patterns in text with resolved links."""
    # Quick rejection: 90% of text doesn't have [[
    if '[[' not in text:
        return text
    
    def replace_xref(match: Match) -> str:
        # ... existing implementation ...
    
    return self.pattern.sub(replace_xref, text)
```

**Impact:** ~2-3ms per page (most pages don't use cross-refs)

---

### 5. Cache Directories in `_write_output()` ⚡

**File:** `bengal/rendering/pipeline.py:156-172`

**Current:** Calls `mkdir()` for every page  
**Problem:** Unnecessary syscalls  
**Impact:** ~5-10ms per page

**Add caching:**
```python
# At module level
_created_dirs = set()
_created_dirs_lock = threading.Lock()

def _write_output(self, page: Page) -> None:
    """Write rendered page to output directory."""
    parent_dir = page.output_path.parent
    
    # Only create directory if not already done
    if parent_dir not in _created_dirs:
        with _created_dirs_lock:  # Thread-safe
            if parent_dir not in _created_dirs:
                parent_dir.mkdir(parents=True, exist_ok=True)
                _created_dirs.add(parent_dir)
    
    # Write rendered HTML
    with open(page.output_path, 'w', encoding='utf-8') as f:
        f.write(page.rendered_html)
    
    if not self.quiet:
        print(f"  ✓ {page.output_path.relative_to(self.site.output_dir)}")
```

**Impact:** Reduces syscalls by 90%+

---

## Phase 2: Medium Wins (2 hours, +20% speedup) 🎯

### 6. Compile Regex in Directive Renderers ⚡

**Files:** `directives/tabs.py`, `directives/code_tabs.py`

**Replace inline regex with module constants:**

```python
# At module level in tabs.py
_TAB_PATTERN = re.compile(
    r'<div class="tab-title">(.*?)</div>\s*<div class="tab-content">(.*?)</div>',
    re.DOTALL
)

def render_tabs(renderer, text, **attrs):
    matches = _TAB_PATTERN.findall(text)  # Use compiled pattern
    # ... rest of implementation ...
```

**Similar for code_tabs.py:**
```python
_CODE_TAB_PATTERN = re.compile(
    r'<div class="code-tab-item" data-lang="(.*?)" data-code="(.*?)"></div>',
    re.DOTALL
)
```

**Impact:** ~2-5ms per page with tabs/code-tabs

---

### 7. String Building with List Comprehension ⚡

**Files:** `directives/tabs.py:104-135`, `directives/code_tabs.py:81-113`

**Replace string concatenation:**
```python
# OLD (O(n²) memory):
nav_html = f'<div class="tabs" id="{tab_id}">\n  <ul class="tab-nav">\n'
for i, (title, _) in enumerate(matches):
    nav_html += f'    <li>...</li>\n'  # String concatenation!

# NEW (O(n) memory):
nav_parts = [f'<div class="tabs" id="{tab_id}">\n  <ul class="tab-nav">']
nav_parts.extend(
    f'    <li{" class=\"active\"" if i == 0 else ""}>'
    f'<a href="#{tab_id}-{i}">{title.strip()}</a></li>'
    for i, (title, _) in enumerate(matches)
)
nav_parts.append('  </ul>')
nav_html = '\n'.join(nav_parts) + '\n'
```

**Impact:** Negligible for small pages, 5-10ms for pages with many tabs

---

### 8. Cache Documentation Directives ⚡

**File:** `bengal/rendering/parser.py:236-252`

**Current:** Creates new directive instances for each parser  
**Problem:** Wasteful memory/initialization  
**Impact:** ~10-20ms per thread-local parser creation

**Add module-level cache:**
```python
# At module level in plugins/__init__.py
_DOCUMENTATION_DIRECTIVES_CACHE = None

def get_documentation_directives():
    """Get cached documentation directives function."""
    global _DOCUMENTATION_DIRECTIVES_CACHE
    if _DOCUMENTATION_DIRECTIVES_CACHE is None:
        _DOCUMENTATION_DIRECTIVES_CACHE = create_documentation_directives()
    return _DOCUMENTATION_DIRECTIVES_CACHE

# In parser.py:
from bengal.rendering.plugins import get_documentation_directives

self._md_with_vars = self._mistune.create_markdown(
    plugins=[
        'table',
        'strikethrough',
        'task_lists',
        'url',
        'footnotes',
        'def_list',
        get_documentation_directives(),  # Reuse cached
        self._var_plugin,
    ],
    renderer='html',
)
```

---

## Phase 3: Optional Advanced (2 hours, +10% speedup) 🚀

### 9. Share Template Engine Across Threads

**File:** `bengal/rendering/pipeline.py:79`

**Problem:** Each thread creates its own Jinja2 Environment (expensive!)  
**Solution:** Jinja2 Environment is thread-safe for reading, share it!

**Implementation:**
```python
# At module level
_shared_template_engine = None
_template_engine_lock = threading.Lock()

class RenderingPipeline:
    def __init__(self, site, dependency_tracker=None, ...):
        # ... existing code ...
        
        # Reuse template engine across threads (Jinja2 is thread-safe)
        global _shared_template_engine
        with _template_engine_lock:
            if _shared_template_engine is None or _shared_template_engine.site != site:
                _shared_template_engine = TemplateEngine(site)
        self.template_engine = _shared_template_engine
        
        # ... rest of init ...
```

**Impact:** ~50-100ms saved per thread creation  
**Risk:** Need to verify thread-safety with our usage patterns

---

## Testing Checklist ✅

After each optimization:

1. **Unit Test:** Does the optimization produce identical output?
2. **Integration Test:** Does showcase site build without errors?
3. **Byte-for-Byte:** Compare HTML output before/after
4. **Benchmark:** Measure actual speedup
5. **Visual Check:** Does the site look correct?

---

## Expected Results

### Before Optimizations (Showcase Site, 30 pages):
- **Full build:** ~450ms
- **Per-page:** ~15ms

### After Phase 1 (Quick Wins):
- **Full build:** ~270ms (-40%)
- **Per-page:** ~9ms

### After Phase 2 (Medium Wins):
- **Full build:** ~220ms (-50% total)
- **Per-page:** ~7ms

### After Phase 3 (Advanced):
- **Full build:** ~200ms (-55% total)
- **Per-page:** ~6.5ms

**Total Speedup: 2-2.5x faster! 🎉**

---

## Rollback Plan

If anything breaks:
1. Each optimization is independent
2. Git commit after each successful optimization
3. Can revert individual optimizations without affecting others
4. Keep BS4 code commented out initially (don't delete immediately)

---

## Priority Order (Do In This Order)

1. ✅ Quick rejection in cross-refs (5 min, zero risk)
2. ✅ Cache directories (10 min, zero risk)
3. ✅ Compile regex in directives (15 min, zero risk)
4. ✅ Lazy toc_items property (30 min, low risk)
5. ⚠️ Replace BS4 in `_inject_heading_anchors()` (1 hour, medium risk)
6. ⚠️ Replace BS4 in `_extract_toc()` (45 min, medium risk)
7. ✅ String building in directives (30 min, low risk)
8. ✅ Cache documentation directives (20 min, low risk)
9. ⚠️ Share template engine (1 hour, medium risk - needs validation)

**Start with items marked ✅ (low risk), then move to ⚠️ (needs testing)**

---

## When You're Done

Move this file to `plan/completed/` and update the main STRATEGIC_PLAN.md with benchmark results!

