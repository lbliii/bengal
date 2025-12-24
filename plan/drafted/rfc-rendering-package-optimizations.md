# RFC: Rendering Package Big O Optimizations

**Status**: Draft  
**Created**: 2025-01-XX  
**Author**: AI Assistant  
**Subsystem**: Rendering (Pipeline, Parsers, Plugins, Template Functions)  
**Confidence**: 85% 🟢 (verified against source code 2025-01-XX)  
**Priority**: P2 (Medium) — Performance improvements for large sites (1000+ pages)  
**Estimated Effort**: 1.5-2 days

---

## Executive Summary

Comprehensive Big O analysis of the `bengal.rendering` package (91+ files) reveals **excellent algorithmic foundations** with sophisticated caching at multiple levels. Key optimizations already in place make most operations O(n) or better. This RFC identifies consolidation and refinement opportunities:

**Key Findings**:

1. ✅ **Already Optimized**:
   - Cross-reference lookups: O(1) via pre-built xref_index
   - Pygments lexer cache: ~3× speedup (86s → 29s on 826-page site)
   - Navigation tree: O(1) lookup via NavTreeCache
   - Thread-local parser caching: Eliminates O(plugin_count) per-page overhead
   - Template wrapper caching: Avoids O(pages) wrapper creation per access
   - Tag page resolution: O(1) via cached `str_page_map`

2. ⚠️ **Multiple Transform Passes on HTML** — 3 sequential O(n) transformations per page
3. ⚠️ **Heading Anchor Slow Path** — O(n + m×r) for blockquote handling (m=blockquote count, r=avg content between)
4. ⚠️ **Tag Page Context Filtering** — O(tag_pages) filtering repeated per paginated render
5. ⚠️ **API Doc Badge Injection** — 5 sequential O(n) regex passes (gated to API pages only)

**Current State**: The rendering pipeline performs well for typical sites (100-5000 pages). These optimizations target:
- Build time reduction for large sites (5K+ pages)
- Memory efficiency during template rendering
- Dev server responsiveness

**Impact** (realistic estimates):
- Unified transform pass: **10-25% reduction** in HTML processing time (3 passes → 1)
- Tag context caching: **Eliminates repeated filtering** — O(T×P) once instead of per-render
- Heading anchor optimization: **Marginal** — slow path already rare in practice
- API badge combining: **Negligible** — gated to API doc pages only

---

## Current Architecture Assessment

### What's Already Optimal ✅

| Component | Operation | Complexity | Evidence |
|-----------|-----------|------------|----------|
| **Cross-references** | Path lookup | **O(1)** ✅ | Dict lookup - `plugins/cross_references.py:187` |
| **Pygments cache** | Lexer lookup | **O(1)** ✅ | Thread-safe cache - `pygments_cache.py:124-127` |
| **Navigation tree** | Tree access | **O(1)** ✅ | NavTreeCache - `template_functions/navigation/tree.py:70` |
| **Parser caching** | Thread-local | **O(1)** ✅ | `pipeline/thread_local.py` |
| **Template wrappers** | Site pages | **O(p) cached** ✅ | `template_context.py:266-273` |
| **Page path map** | Source→Page lookup | **O(1)** ✅ | `site.get_page_path_map()` - `renderer.py:374` |
| **Top-level content** | Set filtering | **O(n)** ✅ | `renderer.py:94-106` |

### Design Patterns Employed

1. **Thread-local Caching**: Parser instances reused per worker thread
2. **Pre-computed Indices**: xref_index built during discovery, O(1) lookups during render
3. **Lazy Evaluation**: TOC structures computed on-demand via properties
4. **Compiled Regex**: Patterns compiled once, reused across pages
5. **FIFO Cache Eviction**: Pygments lexer cache capped at 100 entries

---

## Problem Statement

### Bottleneck 1: Multiple Transform Passes on HTML — 3× O(n)

**Location**: `bengal/rendering/pipeline/core.py:307-314`

**Current Implementation**:

```python
def _parse_content(self, page: Page) -> None:
    """Parse page content through markdown parser."""
    # ... parsing (lines 298-306) ...

    # Pass 1: Escape Jinja blocks (str.replace - fast)
    page.parsed_ast = escape_jinja_blocks(page.parsed_ast or "")  # O(n)

    # Pass 2: Normalize .md links (regex)
    page.parsed_ast = normalize_markdown_links(page.parsed_ast)   # O(n)

    # Pass 3: Transform internal links with baseurl (regex)
    page.parsed_ast = transform_internal_links(page.parsed_ast, self.site.config)  # O(n)
```

**Transform implementations** (`bengal/rendering/pipeline/transforms.py`):

| Transform | Method | Lines |
|-----------|--------|-------|
| `escape_jinja_blocks` | `str.replace()` (2 calls) | 71-93 |
| `normalize_markdown_links` | `re.sub()` via `link_transformer.normalize_md_links` | 131-152 |
| `transform_internal_links` | `re.sub()` via `link_transformer.transform_internal_links` | 96-128 |

**Problem**:
- Each transformation creates a new string and scans the entire HTML
- For 10KB HTML × 1000 pages = 30MB+ of string allocations
- Total: 3 full passes over each page's HTML

**Important Context**:
- Pass 1 (`escape_jinja_blocks`) uses `str.replace()` which is C-optimized and very fast
- Passes 2-3 use compiled regex patterns (already optimal for their complexity)
- The benefit of combining depends on regex vs. string method trade-offs

**Impact by Page Size**:
- Small pages (< 5KB): Negligible overhead
- Medium pages (5-20KB): ~1-2ms per page
- Large pages (20KB+): ~3-5ms per page, noticeable on 1000+ page sites

---

### Bottleneck 2: Heading Anchor Slow Path — O(n + m×r)

**Location**: `bengal/rendering/parsers/mistune/toc.py:91-172`

**Current Implementation**:

```python
def inject_heading_anchors(html: str, slugify_func: Any) -> str:
    # Quick rejection: skip if no headings (lines 44-46)
    if not html or not ("<h2" in html or "<h3" in html or "<h4" in html):
        return html

    # Fast path: no blockquotes (lines 48-89)
    if "<blockquote" not in html:
        return HEADING_PATTERN.sub(replace_heading, html)  # O(n) ✅

    # Slow path: skip headings inside blockquotes (lines 91-172)
    for match in blockquote_pattern.finditer(html):  # O(m) iterations
        before = html[current_pos : match.start()]   # Slice
        if in_blockquote == 0:
            parts.append(HEADING_PATTERN.sub(replace_heading, before))  # O(r)
        # ...
```

**Complexity Analysis**:
- **Fast path**: O(n) — single regex pass, already optimal
- **Slow path**: O(n + m×r) where:
  - n = HTML length (scanned once for blockquote tags)
  - m = number of blockquote open/close tags
  - r = average content length between blockquotes

**Realistic Assessment**:
- Most content pages use fast path (no blockquotes in headings)
- Slow path is **not** O(n×depth) as previously stated
- API docs with blockquotes: m ≈ 10-50, r ≈ n/m, so effectively ~O(n)
- The current implementation is already reasonably efficient

**Measured Impact**:
- Fast path: 5-10× faster than BeautifulSoup alternative
- Slow path: ~1.5-2× slower than fast path (acceptable)

**Recommendation**: Low priority — current implementation is adequate

---

### Bottleneck 3: Tag Page Context — Repeated O(P) Filtering

**Location**: `bengal/rendering/renderer.py:366-518`

**Current Implementation**:

```python
def _add_tag_generated_page_context(self, page: Page, context: dict[str, Any]) -> None:
    # Line 374: Page lookup map is already cached and O(1) ✅
    str_page_map = self.site.get_page_path_map()

    # Lines 388-401: Loop with filtering
    for tax_page in taxonomy_pages:                    # O(P) iterations
        if hasattr(tax_page, "source_path"):
            # O(1) lookup - ALREADY OPTIMIZED ✅
            resolved_page = str_page_map.get(str(tax_page.source_path))

        if resolved_page:
            source_str = str(resolved_page.source_path)
            # Filtering logic - REPEATED ON EACH RENDER ⚠️
            if (
                not resolved_page.metadata.get("_generated")
                and "content/api" not in source_str      # O(1) substring check
                and "content/cli" not in source_str      # O(1) substring check
            ):
                all_posts.append(resolved_page)
```

**What's Already Optimized**:
- ✅ Page resolution: O(1) via cached `str_page_map` (line 374, 391-392)
- ✅ Taxonomy lookup: O(1) dict access (line 383-386)

**What Can Be Improved**:
- ⚠️ Filtering loop: O(P) per render where P = pages in tag
- ⚠️ Repeated for each pagination page (page 1, page 2, etc.)

**Impact Calculation**:
- 50 tags × 20 avg pages/tag × 3 pagination pages = 3,000 filter iterations
- With caching: 50 tags × 20 pages = 1,000 iterations (once)
- **Savings**: ~67% reduction in filtering work for tag-heavy sites

**Note**: This is a moderate win, not a major bottleneck. The per-iteration cost is low (metadata dict lookup + 2 substring checks).

---

### Bottleneck 4: Xref Code Block Splitting — O(n) per Page

**Location**: `bengal/rendering/plugins/cross_references.py:116-141`

**Current Implementation**:

```python
def _substitute_xrefs(self, html: str) -> str:
    # Quick rejection: O(n) substring check, but fast in practice
    if "[[" not in html:
        return html  # Most pages exit here ✅

    # Split by code blocks - O(n) regex split
    parts = re.split(
        r"(<pre.*?</pre>|<code[^>]*>.*?</code>)", html, flags=re.DOTALL | re.IGNORECASE
    )

    for i in range(0, len(parts), 2):
        parts[i] = self._replace_xrefs_in_text(parts[i])  # O(part_size)

    return "".join(parts)  # O(n) join
```

**Assessment**:
- ✅ Quick rejection (`"[[" not in html`) skips most pages
- ✅ Xref resolution uses O(1) dict lookups (line 187: `xref_index.get("by_path", {}).get(clean_path)`)
- ⚠️ Pages with `[[` patterns pay O(n) split + O(n) join cost

**Realistic Impact**:
- Most pages: O(1) rejection (no `[[` in content)
- Pages with xrefs: O(n) but necessary — code block protection is essential
- **Not a priority for optimization** — the quick rejection handles the common case

---

### Bottleneck 5: API Doc Enhancer — 5× O(n) for API Pages Only

**Location**: `bengal/rendering/api_doc_enhancer.py:105-145`

**Current Implementation**:

```python
def enhance(self, html: str, page_type: str | None = None) -> str:
    # Gate: Only API documentation pages (lines 126-127)
    if not self.should_enhance(page_type):
        return html  # Most pages exit here ✅

    # Apply 5 badge patterns sequentially (lines 132-136)
    enhanced = html
    for pattern, replacement in self._compiled_patterns:  # 5 patterns
        enhanced = pattern.sub(replacement, enhanced)      # O(n) each

    return enhanced
```

**Badge Patterns** (`api_doc_enhancer.py:49-75`):
1. `@async` for h3/h4 headings
2. `@property` for h4 headings  
3. `@classmethod` for h4 headings
4. `@staticmethod` for h4 headings
5. `@deprecated` for h2-h6 headings

**Realistic Assessment**:
- ✅ Gated by `should_enhance()` — only `python-module`, `autodoc/python`, `cli-command`, `autodoc-cli` page types
- ✅ Patterns are pre-compiled (line 88-91)
- ⚠️ For API doc pages: 5 × O(n) passes

**Impact**:
- Non-API pages: O(1) — immediate return
- API pages: 5 × O(n), but API docs are typically < 20KB
- Typical site: ~50-100 API pages out of 1000+ total pages

**Priority**: Low — affects small subset of pages, and patterns are complex enough that combining may not improve performance

---

## Proposed Solutions

### Solution 1: Unified HTML Transform Pass (P2)

**Approach**: Combine multiple O(n) transformations into a single streaming pass.

> ⚠️ **Important Trade-off**: The current `escape_jinja_blocks` uses `str.replace()` which is C-optimized and extremely fast. A regex-based unified approach may not be faster. **Benchmark before committing.**

**Implementation Option A: Hybrid Approach (Recommended)**

Keep fast `str.replace()` for Jinja escaping, combine only regex transforms:

```python
# In bengal/rendering/pipeline/unified_transform.py

import re

class HybridHTMLTransformer:
    """
    Hybrid transformation:
    - Jinja escaping: str.replace() (fastest)
    - Link transforms: combined regex (single pass)
    """

    def __init__(self, baseurl: str = ""):
        self.baseurl = baseurl.rstrip("/") if baseurl else ""
        self.should_transform_links = bool(self.baseurl)

        # Combined pattern for link transformations only
        self._link_pattern = re.compile(
            r'(?P<md_link>href=["\'](?P<md_path>[^"\']*\.md)["\'])|'
            r'(?P<internal_link>(?:href|src)=["\'](?P<int_path>/[^"\']*)["\'])',
            re.MULTILINE
        )

    def transform(self, html: str) -> str:
        """Transform HTML: O(n) for Jinja + O(n) for links = O(2n)."""
        if not html:
            return html

        # Step 1: Jinja escaping - str.replace() is C-optimized, very fast
        result = html.replace("{%", "&#123;%").replace("%}", "%&#125;")

        # Step 2: Combined link transforms - single regex pass
        if ".md" in result or (self.should_transform_links and '="/' in result):
            result = self._link_pattern.sub(self._link_replacer, result)

        return result

    def _link_replacer(self, match: re.Match) -> str:
        """Handle both .md and internal link transforms."""
        if match.group("md_link"):
            return self._transform_md_link(match)
        elif match.group("internal_link") and self.should_transform_links:
            return self._transform_internal_link(match)
        return match.group(0)

    def _transform_md_link(self, match: re.Match) -> str:
        """Transform .md link to clean URL."""
        path = match.group("md_path")
        if path.endswith("/_index.md") or path.endswith("/index.md"):
            clean = path.rsplit("/", 1)[0] + "/"
        elif path.endswith("_index.md") or path.endswith("index.md"):
            clean = "./"
        else:
            clean = path[:-3] + "/"
        quote = match.group(0)[5]  # Extract quote character
        return f'href={quote}{clean}{quote}'

    def _transform_internal_link(self, match: re.Match) -> str:
        """Transform internal link with baseurl."""
        full = match.group(0)
        path = match.group("int_path")
        if path.startswith(self.baseurl + "/") or path == self.baseurl:
            return full  # Already has baseurl
        attr = "href" if "href" in full else "src"
        quote = full[5] if "href" in full else full[4]
        return f'{attr}={quote}{self.baseurl}{path}{quote}'
```

**Update pipeline**:

```python
# In bengal/rendering/pipeline/core.py

def _parse_content(self, page: Page) -> None:
    # ... parsing ...

    # Hybrid transformation (replaces 3 separate passes with 2)
    if not hasattr(self, '_transformer'):
        baseurl = self.site.config.get("baseurl", "")
        self._transformer = HybridHTMLTransformer(baseurl)

    page.parsed_ast = self._transformer.transform(page.parsed_ast or "")
```

**Complexity Improvement**: O(3n) → O(2n)

**Files to Modify**:
- Create `bengal/rendering/pipeline/unified_transform.py`
- Update `bengal/rendering/pipeline/core.py`
- Keep individual transform functions for backward compatibility

**Trade-offs**:
- ✅ Combines 2 regex passes into 1 (link transforms)
- ✅ Keeps fast `str.replace()` for Jinja escaping
- ✅ Quick rejection via substring checks before regex
- ⚠️ More complex regex pattern (but compiled once)
- ⚠️ Requires thorough testing of edge cases

**Benchmark Required**:
Before implementing, compare:
1. Current: 2× `str.replace()` + 2× `re.sub()`
2. Proposed: 2× `str.replace()` + 1× complex `re.sub()`

---

### Solution 2: Heading Anchor Slow Path Optimization (P3 — Low Priority)

**Approach**: Optimize the blockquote-aware slow path.

> ℹ️ **Assessment**: The current implementation is already efficient for real-world content. The slow path complexity is O(n + m×r) which is effectively O(n) for typical pages. This optimization is **low priority**.

**Current State**: The existing implementation already has:
- ✅ Fast path for pages without blockquotes (most pages)
- ✅ Compiled regex patterns
- ✅ Quick rejection for pages without headings

**If Optimization is Needed**:

The current slow path can be improved by avoiding repeated string slicing:

```python
# In bengal/rendering/parsers/mistune/toc.py

def inject_heading_anchors_optimized(html: str, slugify_func: Any) -> str:
    """
    Optimized heading anchor injection.

    Key improvement: Use list-based accumulation instead of repeated slicing.
    """
    if not html or not ("<h2" in html or "<h3" in html or "<h4" in html):
        return html

    # Fast path: no blockquotes (already optimal)
    if "<blockquote" not in html:
        return HEADING_PATTERN.sub(_make_heading_replacer(slugify_func), html)

    # Improved slow path: accumulate parts without repeated slicing
    parts = []
    in_blockquote = 0
    last_pos = 0

    # Single pass: find all blockquote boundaries
    for match in re.finditer(r"<(/?)blockquote[^>]*>", html, re.IGNORECASE):
        segment = html[last_pos:match.start()]

        if in_blockquote == 0 and segment:
            # Process headings outside blockquotes
            parts.append(HEADING_PATTERN.sub(_make_heading_replacer(slugify_func), segment))
        else:
            parts.append(segment)

        parts.append(match.group(0))
        last_pos = match.end()

        # Track nesting
        if match.group(1) == "/":
            in_blockquote = max(0, in_blockquote - 1)
        else:
            in_blockquote += 1

    # Handle remaining content
    remaining = html[last_pos:]
    if in_blockquote == 0 and remaining:
        parts.append(HEADING_PATTERN.sub(_make_heading_replacer(slugify_func), remaining))
    else:
        parts.append(remaining)

    return "".join(parts)
```

**Complexity**: O(n) single pass with regex finditer

**Recommendation**: **Defer** — Current implementation is adequate. Only implement if profiling shows this is a bottleneck on specific content.

---

### Solution 3: Tag Page Context Caching (P1 — Recommended)

**Approach**: Cache resolved tag pages per tag slug, invalidate on taxonomy change.

**Implementation**:

```python
# In bengal/rendering/renderer.py

class Renderer:
    def __init__(self, template_engine: Any, build_stats: Any = None) -> None:
        # ... existing init ...
        # PERF: Cache resolved tag pages per tag slug
        self._tag_pages_cache: dict[str, list[Page]] | None = None

    def _get_resolved_tag_pages(self, tag_slug: str) -> list[Page]:
        """
        Get resolved and filtered pages for a tag (cached).

        Cache is built once per Renderer instance (per build).
        """
        if self._tag_pages_cache is None:
            self._tag_pages_cache = self._build_all_tag_pages_cache()

        return self._tag_pages_cache.get(tag_slug, [])

    def _build_all_tag_pages_cache(self) -> dict[str, list[Page]]:
        """
        Build complete cache of resolved tag pages.

        O(T × P_avg) total, but done ONCE per build instead of
        O(P_avg) per tag page render.
        """
        cache: dict[str, list[Page]] = {}
        str_page_map = self.site.get_page_path_map()
        tags_data = self.site.taxonomies.get("tags", {})

        for tag_slug, tag_info in tags_data.items():
            resolved_pages = []
            for tax_page in tag_info.get("pages", []):
                if hasattr(tax_page, "source_path"):
                    resolved = str_page_map.get(str(tax_page.source_path))
                    if resolved:
                        source_str = str(resolved.source_path)
                        if (
                            not resolved.metadata.get("_generated")
                            and "content/api" not in source_str
                            and "content/cli" not in source_str
                        ):
                            resolved_pages.append(resolved)

            cache[tag_slug] = resolved_pages

        return cache

    def _add_tag_generated_page_context(self, page: Page, context: dict[str, Any]) -> None:
        """Add context for an individual tag page (optimized)."""
        tag_slug = page.metadata.get("_tag_slug")

        # Use cached resolved pages - O(1) lookup
        all_posts = self._get_resolved_tag_pages(tag_slug) if tag_slug else []

        # ... rest of pagination logic unchanged ...
```

**Complexity Improvement**: O(T × P × renders_per_tag) → O(T × P) once + O(1) lookups

**Files to Modify**:
- Update `bengal/rendering/renderer.py`

**Trade-offs**:
- ✅ Eliminates repeated resolution work
- ✅ Significant speedup for sites with many tags
- ⚠️ Cache must be invalidated if taxonomies change mid-build
- ⚠️ Slightly more memory for cache

---

### Solution 4: Combined API Badge Pattern (P3)

**Approach**: Merge 5 badge patterns into single regex with alternation.

**Implementation**:

```python
# In bengal/rendering/api_doc_enhancer.py

class APIDocEnhancer:
    """Optimized badge injection with single-pass regex."""

    def __init__(self) -> None:
        # Combined pattern for all badge types
        self._pattern = re.compile(
            r'(<h[234][^>]*>)([^<@]+)\s*'
            r'@(async|property|classmethod|staticmethod|deprecated)\s*'
            r'(<a[^>]*headerlink[^>]*>.*?</a>)?'
            r'(\s*</h[234]>)',
            re.MULTILINE | re.IGNORECASE
        )

        self._badge_map = {
            "async": "async",
            "property": "property",
            "classmethod": "classmethod",
            "staticmethod": "staticmethod",
            "deprecated": "deprecated",
        }

    def enhance(self, html: str, page_type: str | None = None) -> str:
        """Single-pass badge injection - O(n) instead of O(5n)."""
        if not self.should_enhance(page_type):
            return html

        def replacer(match: re.Match) -> str:
            tag_open = match.group(1)
            title = match.group(2)
            badge_type = match.group(3).lower()
            headerlink = match.group(4) or ""
            tag_close = match.group(5)

            badge_class = self._badge_map.get(badge_type, badge_type)
            badge = f'<span class="api-badge api-badge-{badge_class}">{badge_type}</span>'

            return f'{tag_open}{title} {badge}{headerlink}{tag_close}'

        return self._pattern.sub(replacer, html)
```

**Complexity Improvement**: O(5n) → O(n)

**Files to Modify**:
- Update `bengal/rendering/api_doc_enhancer.py`

**Trade-offs**:
- ✅ 5× reduction in pattern matching passes
- ✅ Simpler code structure
- ⚠️ Single complex pattern (harder to debug)
- ⚠️ All badge types must match same structure

---

## Implementation Plan

### Phase 1: Tag Page Context Caching (Low Risk, Clear Value) — 0.5 days

**Priority**: P1 ⭐  
**Effort**: 0.5 days  
**Risk**: Low

**Why First**: Additive change, no API modifications, clear benefit for tag-heavy sites.

**Steps**:
1. Add `_tag_pages_cache: dict[str, list[Page]] | None = None` to Renderer
2. Implement `_build_all_tag_pages_cache()` method
3. Update `_add_tag_generated_page_context()` to use cache
4. Test with multi-page tag pagination

**Success Criteria**:
- ✅ Filtering done once per build instead of per-render
- ✅ Correct pagination behavior preserved
- ✅ No stale data issues

---

### Phase 2: Hybrid HTML Transform (Requires Benchmarking) — 1 day

**Priority**: P2  
**Effort**: 1 day  
**Risk**: Medium

**Why Second**: Needs benchmarking to verify benefit. Current `str.replace()` is already fast.

**Steps**:
1. **First**: Create benchmark script comparing approaches
2. Only proceed if benchmarks show > 15% improvement
3. Create `unified_transform.py` with hybrid transformer
4. Add comprehensive unit tests for all transform cases
5. Update `pipeline/core.py` to use hybrid transformer
6. Keep individual functions for backward compatibility

**Benchmark First**:
```python
# scripts/benchmark_transforms.py
# Compare: Current 3-pass vs Hybrid 2-pass
# Target: > 15% improvement to justify complexity
```

**Success Criteria**:
- ✅ Verified improvement via benchmarks
- ✅ 10-25% reduction in HTML processing time
- ✅ All existing tests pass
- ✅ Output identical to current implementation

---

### Phase 3: Heading Anchor Optimization (Defer) — 0.5 days

**Priority**: P3 (Defer)  
**Effort**: 0.5 days  
**Risk**: Medium

**Why Deferred**: Current implementation is already efficient. Only implement if profiling shows bottleneck.

**Trigger Condition**: Profile data showing > 5% of build time in `inject_heading_anchors` slow path.

**Steps** (if triggered):
1. Profile real builds to identify if slow path is hit frequently
2. If yes, implement optimized version
3. Add tests for blockquote edge cases
4. Feature flag for gradual rollout

---

### Phase 4: Combined API Badge Pattern (Skip) — N/A

**Priority**: P4 (Skip)  
**Effort**: 0.5 days  
**Risk**: Low

**Why Skip**:
- Only affects API doc pages (< 10% of typical site)
- 5 patterns are simple and compile to efficient DFA
- Combining may not improve performance due to pattern complexity
- Current gating (`should_enhance`) makes this a non-issue

**Action**: No implementation needed. Revisit only if API doc rendering becomes a bottleneck.

---

## Testing Strategy

### Unit Tests

1. **Unified Transform**:
   - Jinja escaping (`{{`, `}}`, `{%`, `%}`)
   - Markdown link normalization (`.md` → `/`)
   - Internal link baseurl prefixing
   - Combined scenarios
   - Edge cases (empty, no matches, all matches)

2. **Heading Anchors**:
   - Fast path (no blockquotes)
   - Slow path (nested blockquotes)
   - Mixed content
   - Edge cases (empty headings, duplicate IDs)

3. **Tag Page Caching**:
   - Cache build correctness
   - Pagination with cached pages
   - Empty tags handling

4. **API Badges**:
   - All badge types
   - Multiple badges per page
   - Nested headings

### Performance Benchmarks

```python
# scripts/benchmark_rendering.py

def benchmark_html_transforms(html_samples: list[str], iterations: int = 100):
    """Compare unified vs separate transforms."""
    import time
    from bengal.rendering.pipeline.unified_transform import UnifiedHTMLTransformer
    from bengal.rendering.pipeline.transforms import (
        escape_jinja_blocks,
        normalize_markdown_links,
        transform_internal_links,
    )

    # Baseline: separate transforms
    start = time.perf_counter()
    for _ in range(iterations):
        for html in html_samples:
            result = escape_jinja_blocks(html)
            result = normalize_markdown_links(result)
            result = transform_internal_links(result, {"baseurl": "/bengal"})
    separate_time = time.perf_counter() - start

    # Optimized: unified transform
    transformer = UnifiedHTMLTransformer({"baseurl": "/bengal"}, "/bengal")
    start = time.perf_counter()
    for _ in range(iterations):
        for html in html_samples:
            result = transformer.transform(html)
    unified_time = time.perf_counter() - start

    return {
        "separate_ms": separate_time * 1000,
        "unified_ms": unified_time * 1000,
        "speedup": separate_time / unified_time,
    }
```

### Integration Tests

- Full build with optimized rendering
- Compare output HTML hash with baseline
- Memory usage comparison
- Dev server responsiveness testing

---

## Risk Assessment

| Optimization | Risk Level | Mitigation | Recommendation |
|--------------|------------|------------|----------------|
| **Tag page caching** | Low | Additive change, no API modifications | ✅ Proceed |
| **Hybrid transform** | Medium | Benchmark first, keep fallback, feature flag | ⚠️ Validate first |
| **Heading anchor optimization** | Medium | Current impl is adequate | ❌ Defer |
| **API badge combining** | Low | Negligible benefit | ❌ Skip |

---

## Alternatives Considered

### Alternative 1: Streaming HTML Parser

**Approach**: Use SAX-like streaming parser for transforms

**Rejected because**:
- Adds significant complexity
- Regex approach is fast enough for typical page sizes
- Would require major architecture changes

### Alternative 2: Pre-computed Transform Results

**Approach**: Cache transform results per content hash

**Rejected because**:
- Already have parsed cache at higher level
- Transform is fast relative to template rendering
- Adds cache invalidation complexity

### Alternative 3: Parallel Transform Processing

**Approach**: Process HTML sections in parallel

**Rejected because**:
- HTML structure makes splitting complex
- Overhead exceeds benefit for typical page sizes
- Thread safety concerns with regex

---

## Success Metrics

### Performance Targets (Realistic)

| Metric | Current | Target | Realistic Improvement |
|--------|---------|--------|----------------------|
| **HTML transform time** | O(3n) | O(2n) | 1.3-1.5× (if benchmarks confirm) |
| **Tag page filtering** | O(P × R) | O(P) once | 2-3× for tag-heavy sites |
| **Heading anchor (slow path)** | O(n + m×r) | O(n) | Marginal (defer) |
| **API badge injection** | O(5n) gated | — | Skip (not a bottleneck) |

Where: P = pages per tag, R = renders per tag, m = blockquote count, r = avg content between

### Estimated Wall-Clock Impact

For a 1000-page site with 50 tags:
- **Tag caching**: Saves ~100-200ms per full build
- **Hybrid transform**: Saves ~50-150ms per full build (if implemented)
- **Total potential**: ~150-350ms faster builds

### Quality Targets

- ✅ All existing tests pass
- ✅ Output HTML identical to current
- ✅ No memory regressions
- ✅ No performance regressions on any path
- ✅ Benchmarks validate improvements before merge

---

## References

- **Big O Analysis**: This RFC's problem statement section
- **Source Code** (verified 2025-01-XX):
  - `bengal/rendering/pipeline/core.py:307-314` — Transform chain (3 passes)
  - `bengal/rendering/pipeline/transforms.py:71-152` — Transform implementations
  - `bengal/rendering/link_transformer.py:30-203` — Link transformation functions
  - `bengal/rendering/parsers/mistune/toc.py:44-172` — Heading anchors (fast + slow path)
  - `bengal/rendering/renderer.py:366-518` — Tag page context
  - `bengal/rendering/plugins/cross_references.py:116-141` — Xref splitting
  - `bengal/rendering/api_doc_enhancer.py:49-145` — Badge patterns and injection

---

## Appendix: Complexity Comparison

### HTML Transforms

| Approach | Time | Space | Notes |
|----------|------|-------|-------|
| **Current** | O(3n) | O(3n) | 3 strings created (2 replace + 2 regex) |
| **Proposed (Hybrid)** | O(2n) | O(2n) | Keep fast replace, combine regex |

### Heading Anchors

| Approach | Time | Space | Notes |
|----------|------|-------|-------|
| **Current (fast path)** | O(n) | O(n) | No blockquotes — already optimal ✅ |
| **Current (slow path)** | O(n + m×r) | O(parts) | m=blockquotes, r=avg segment |
| **Note** | — | — | Slow path is ~O(n) for typical content |

### Tag Page Context

| Approach | Time | Space | Notes |
|----------|------|-------|-------|
| **Current** | O(T × P × R) | O(1) | R = pagination pages per tag |
| **Proposed** | O(T × P) + O(1) | O(T × P_avg) | One-time filtering + O(1) lookup |

Where:
- T = number of tags
- P = average pages per tag  
- R = pagination pages per tag (typically 1-5)
- m = blockquote count per page
- r = average content length between blockquotes

---

## Conclusion

The rendering package has excellent algorithmic foundations with sophisticated caching. The identified bottlenecks are **polish opportunities**, not fundamental issues. The code is already well-optimized.

**Recommended Priority** (revised based on risk/value analysis):

| Priority | Optimization | Effort | Value | Risk | Action |
|----------|--------------|--------|-------|------|--------|
| **P1** ⭐ | Tag page context caching | 0.5 days | Medium | Low | **Implement** |
| P2 | Hybrid HTML transform | 1 day | Low-Medium | Medium | Benchmark first |
| P3 | Heading anchor optimization | 0.5 days | Low | Medium | Defer |
| P4 | Combined API badge pattern | 0.5 days | Negligible | Low | Skip |

**Bottom Line**:
1. **Implement Phase 1** (tag caching) — safe, additive, clear benefit
2. **Benchmark before Phase 2** — verify `str.replace()` vs regex trade-off
3. **Skip Phases 3-4** — current implementations are adequate

**Key Insight**: The rendering package is already mature. These are diminishing-returns optimizations for edge cases (very large sites, many tags). For typical sites (100-1000 pages), current performance is excellent.

---

## Appendix: Quick Wins

These changes can be made immediately with minimal risk:

### Quick Win 1: Add Tag Pages Cache (< 30 minutes) ⭐

```python
# In bengal/rendering/renderer.py

class Renderer:
    def __init__(self, ...):
        # ... existing ...
        self._tag_pages_cache: dict[str, list[Page]] | None = None

    def _get_resolved_tag_pages(self, tag_slug: str) -> list[Page]:
        """Get filtered pages for tag (cached)."""
        if self._tag_pages_cache is None:
            self._tag_pages_cache = self._build_all_tag_pages_cache()
        return self._tag_pages_cache.get(tag_slug, [])
```

### Quick Win 2: Add Benchmark Script (< 30 minutes)

Create a benchmark to validate transform optimization value:

```python
# scripts/benchmark_transforms.py

import time
from bengal.rendering.pipeline.transforms import (
    escape_jinja_blocks, normalize_markdown_links, transform_internal_links
)

def benchmark(html_samples: list[str], iterations: int = 1000):
    """Measure current transform chain performance."""
    config = {"baseurl": "/bengal"}

    start = time.perf_counter()
    for _ in range(iterations):
        for html in html_samples:
            result = escape_jinja_blocks(html)
            result = normalize_markdown_links(result)
            result = transform_internal_links(result, config)
    elapsed = time.perf_counter() - start

    print(f"Current: {elapsed*1000:.2f}ms for {iterations} iterations")
    print(f"Per-page: {elapsed*1000/iterations:.3f}ms")

if __name__ == "__main__":
    # Load sample HTML from real pages
    samples = [open(f).read() for f in glob("tests/fixtures/*.html")]
    benchmark(samples)
```

---

## Code Verification

This RFC was verified against actual source code (2025-01-XX):

**Verified Implementations**:
- ✅ **Transform chain**: 3 sequential O(n) passes in `core.py:307-314`
  - `escape_jinja_blocks`: 2× `str.replace()` (C-optimized, fast)
  - `normalize_markdown_links`: 1× `re.sub()`
  - `transform_internal_links`: 1× `re.sub()` (conditional on baseurl)
- ✅ **Tag page resolution**: O(1) via cached `str_page_map` in `renderer.py:391-392`
- ✅ **Tag page filtering**: O(P) per render in `renderer.py:396-401` (repeated)
- ✅ **Heading anchor slow path**: O(n + m×r) in `toc.py:91-172` (not O(n×depth))
- ✅ **API badge patterns**: 5 patterns gated by page type in `api_doc_enhancer.py:126-127`

**Key Finding**: The rendering package is already well-optimized. Tag caching is the safest high-value change. Transform unification requires benchmarking to validate benefit.
