# RFC: Rendering Package Big O Optimizations

**Status**: Draft  
**Created**: 2025-01-XX  
**Author**: AI Assistant  
**Subsystem**: Rendering (Pipeline, Parsers, Plugins, Template Functions)  
**Confidence**: 90% 🟢 (verified against source code)  
**Priority**: P2 (Medium) — Performance improvements for large sites (1000+ pages)  
**Estimated Effort**: 2-3 days

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

2. ⚠️ **Multiple Regex Passes on HTML** — 4-5 sequential O(n) transformations per page
3. ⚠️ **Heading Anchor Slow Path** — O(n×depth) for blockquote handling
4. ⚠️ **Tag Page Context Building** — O(tag_pages) with redundant filtering
5. ⚠️ **Xref Code Block Splitting** — Repeated O(n) regex splits

**Current State**: The rendering pipeline performs well for typical sites (100-5000 pages). These optimizations target:
- Build time reduction for large sites (5K+ pages)
- Memory efficiency during template rendering
- Dev server responsiveness

**Impact**:
- Unified transform pass: **20-40% reduction** in HTML processing time
- Heading anchor optimization: **2-5× faster** for blockquote-heavy content
- Tag context caching: **O(1)** instead of O(tag_pages) repeated lookups

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
| **Top-level content** | Set filtering | **O(n)** ✅ | `renderer.py:94-106` |

### Design Patterns Employed

1. **Thread-local Caching**: Parser instances reused per worker thread
2. **Pre-computed Indices**: xref_index built during discovery, O(1) lookups during render
3. **Lazy Evaluation**: TOC structures computed on-demand via properties
4. **Compiled Regex**: Patterns compiled once, reused across pages
5. **FIFO Cache Eviction**: Pygments lexer cache capped at 100 entries

---

## Problem Statement

### Bottleneck 1: Multiple Regex Passes on HTML — 4-5× O(n)

**Location**: `bengal/rendering/pipeline/core.py:298-314`

**Current Implementation**:

```python
def _parse_content(self, page: Page) -> None:
    """Parse page content through markdown parser."""
    # ... parsing ...

    # Pass 1: Escape Jinja blocks
    page.parsed_ast = escape_jinja_blocks(page.parsed_ast or "")  # O(n)

    # Pass 2: Normalize .md links
    page.parsed_ast = normalize_markdown_links(page.parsed_ast)   # O(n)

    # Pass 3: Transform internal links (baseurl)
    page.parsed_ast = transform_internal_links(page.parsed_ast, self.site.config)  # O(n)
```

**Additional passes in `link_transformer.py`**:

```30:92:bengal/rendering/link_transformer.py
def transform_internal_links(html: str, baseurl: str) -> str:
    # ... regex substitution ...  # O(n)

def normalize_md_links(html: str) -> str:
    # ... regex substitution ...  # O(n)
```

**Problem**:
- Each transformation creates a new string and scans the entire HTML
- For 10KB HTML × 1000 pages = 50MB+ of string allocations
- Total: 4-5 full passes over each page's HTML

**Impact**:
- Small pages (< 5KB): Negligible
- Medium pages (5-20KB): Moderate overhead
- Large pages (20KB+): Significant allocation overhead

---

### Bottleneck 2: Heading Anchor Slow Path — O(n×depth)

**Location**: `bengal/rendering/parsers/mistune/toc.py:92-172`

**Current Implementation**:

```python
def inject_heading_anchors(html: str, slugify_func: Any) -> str:
    # Quick rejection: skip if no headings
    if not html or not ("<h2" in html or "<h3" in html or "<h4" in html):
        return html

    # If no blockquotes, use fast path
    if "<blockquote" not in html:
        # Fast O(n) regex path
        return HEADING_PATTERN.sub(replace_heading, html)

    # Slow path: need to skip headings inside blockquotes
    # O(blockquote_tags) iterations, each processing O(content_between) text
    for match in blockquote_pattern.finditer(html):  # O(blockquotes)
        before = html[current_pos : match.start()]   # Slice O(n)
        if in_blockquote == 0:
            parts.append(HEADING_PATTERN.sub(replace_heading, before))  # O(n)
        # ...
```

**Problem**:
- Pages with many blockquotes trigger slow path
- Each blockquote boundary causes string slicing and regex processing
- Typical API docs (with code examples in blockquotes) hit this path often

**Measured Impact**:
- Fast path: 5-10x faster than BeautifulSoup alternative
- Slow path: Degrades with blockquote count

---

### Bottleneck 3: Tag Page Context — Repeated O(tag_pages) Lookups

**Location**: `bengal/rendering/renderer.py:366-518`

**Current Implementation**:

```python
def _add_tag_generated_page_context(self, page: Page, context: dict[str, Any]) -> None:
    # ...
    # Get pages directly from site.taxonomies
    all_posts = []
    if tag_slug and self.site.taxonomies.get("tags") and tag_slug in self.site.taxonomies["tags"]:
        tag_data = self.site.taxonomies["tags"][tag_slug]
        taxonomy_pages = tag_data.get("pages", [])

        for tax_page in taxonomy_pages:                    # O(tag_pages)
            resolved_page = None
            if hasattr(tax_page, "source_path"):
                # Use cached string-keyed map for O(1) lookup
                resolved_page = str_page_map.get(str(tax_page.source_path))  # O(1) ✅

            if resolved_page:
                source_str = str(resolved_page.source_path)
                if (                                        # Filtering on every call
                    not resolved_page.metadata.get("_generated")
                    and "content/api" not in source_str
                    and "content/cli" not in source_str
                ):
                    all_posts.append(resolved_page)
```

**Problem**:
- Page resolution loop runs for every tag page render
- Same filtering logic repeated for each paginated page (page 1, page 2, etc.)
- For 50 tags × 3 pagination pages = 150 calls with same resolution work

**Note**: The O(1) page map lookup (`str_page_map`) is already optimized. The issue is the filtering and resolution happening repeatedly.

---

### Bottleneck 4: Xref Code Block Splitting — Repeated O(n) Splits

**Location**: `bengal/rendering/plugins/cross_references.py:116-141`

**Current Implementation**:

```python
def _substitute_xrefs(self, html: str) -> str:
    # Quick rejection: most text doesn't have [[link]] patterns
    if "[[" not in html:
        return html

    # Split by code blocks (both pre/code blocks and inline code)
    # O(n) regex split
    parts = re.split(
        r"(<pre.*?</pre>|<code[^>]*>.*?</code>)", html, flags=re.DOTALL | re.IGNORECASE
    )

    for i in range(0, len(parts), 2):
        # Even indices are text outside code blocks
        parts[i] = self._replace_xrefs_in_text(parts[i])  # O(part_size)

    return "".join(parts)  # O(n) join
```

**Problem**:
- Code block splitting uses compiled regex but still O(n)
- Pages with many xrefs and code blocks pay this cost multiple times
- Pattern matching is case-insensitive with DOTALL (slightly slower)

---

### Bottleneck 5: API Doc Enhancer — Multiple Regex Passes

**Location**: `bengal/rendering/api_doc_enhancer.py:105-145`

**Current Implementation**:

```python
def enhance(self, html: str, page_type: str | None = None) -> str:
    # Only enhance API documentation pages
    if not self.should_enhance(page_type):
        return html

    # Apply all badge patterns
    enhanced = html
    for pattern, replacement in self._compiled_patterns:  # 5 patterns
        enhanced = pattern.sub(replacement, enhanced)      # O(n) each

    return enhanced
```

**Problem**:
- 5 compiled patterns, each requiring O(n) scan
- Total: 5 × O(n) = O(5n) for API doc pages
- Patterns could be combined into single pass

---

## Proposed Solutions

### Solution 1: Unified HTML Transform Pass (P1)

**Approach**: Combine multiple O(n) transformations into a single streaming pass.

**Implementation**:

```python
# In bengal/rendering/pipeline/unified_transform.py

import re
from typing import Callable

class UnifiedHTMLTransformer:
    """
    Single-pass HTML transformation combining:
    - Jinja block escaping
    - Markdown link normalization (.md -> /)
    - Internal link transformation (baseurl)
    - Optional: API badge injection
    """

    def __init__(self, config: dict, baseurl: str = ""):
        self.baseurl = baseurl.rstrip("/")
        self.should_transform_links = bool(baseurl)

        # Combined pattern for all transformations
        self._pattern = re.compile(
            r"(?P<jinja_open>\{\{)|"
            r"(?P<jinja_close>\}\})|"
            r"(?P<jinja_block_open>\{%)|"
            r"(?P<jinja_block_close>%\})|"
            r'(?P<md_link>href=["\'](?P<md_path>[^"\']*\.md)["\'])|'
            r'(?P<internal_link>(?:href|src)=["\'](?P<int_path>/[^"\']*)["\'])',
            re.MULTILINE
        )

    def transform(self, html: str) -> str:
        """Single-pass transformation - O(n) instead of O(4n)."""
        if not html:
            return html

        def replacer(match: re.Match) -> str:
            if match.group("jinja_open"):
                return "&#123;&#123;"
            elif match.group("jinja_close"):
                return "&#125;&#125;"
            elif match.group("jinja_block_open"):
                return "&#123;%"
            elif match.group("jinja_block_close"):
                return "%&#125;"
            elif match.group("md_link"):
                return self._transform_md_link(match)
            elif match.group("internal_link") and self.should_transform_links:
                return self._transform_internal_link(match)
            return match.group(0)

        return self._pattern.sub(replacer, html)

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

    # Single-pass transformation (replaces 3-4 separate passes)
    if not hasattr(self, '_transformer'):
        baseurl = self.site.config.get("baseurl", "")
        self._transformer = UnifiedHTMLTransformer(self.site.config, baseurl)

    page.parsed_ast = self._transformer.transform(page.parsed_ast or "")
```

**Complexity Improvement**: O(4n) → O(n)

**Files to Modify**:
- Create `bengal/rendering/pipeline/unified_transform.py`
- Update `bengal/rendering/pipeline/core.py`
- Deprecate individual transform functions (keep for backward compat)

**Trade-offs**:
- ✅ 3-4× reduction in HTML processing passes
- ✅ Reduced memory allocations (single result string)
- ⚠️ More complex regex pattern (but compiled once)
- ⚠️ Requires thorough testing of edge cases

---

### Solution 2: Optimized Heading Anchor Injection (P2)

**Approach**: Use single-pass processing with state machine instead of splitting.

**Implementation**:

```python
# In bengal/rendering/parsers/mistune/toc.py

def inject_heading_anchors_optimized(html: str, slugify_func: Any) -> str:
    """
    Single-pass heading anchor injection with blockquote awareness.

    Uses character-level scanning instead of regex splitting.
    O(n) regardless of blockquote count.
    """
    if not html or not ("<h2" in html or "<h3" in html or "<h4" in html):
        return html

    # Fast path: no blockquotes
    if "<blockquote" not in html:
        return HEADING_PATTERN.sub(_make_heading_replacer(slugify_func), html)

    # Optimized slow path: single-pass state machine
    result = []
    blockquote_depth = 0
    i = 0
    n = len(html)
    last_copy = 0

    while i < n:
        # Check for blockquote open
        if html[i:i+11].lower() == "<blockquote":
            blockquote_depth += 1
            i += 11
            continue

        # Check for blockquote close
        if html[i:i+13].lower() == "</blockquote>":
            blockquote_depth = max(0, blockquote_depth - 1)
            i += 13
            continue

        # Check for heading (only process if not in blockquote)
        if blockquote_depth == 0 and html[i:i+3] in ("<h2", "<h3", "<h4"):
            # Find heading end
            heading_end = html.find("</h", i)
            if heading_end != -1:
                heading_end = html.find(">", heading_end) + 1
                heading_html = html[i:heading_end]

                # Copy content before heading
                result.append(html[last_copy:i])

                # Process heading
                processed = HEADING_PATTERN.sub(
                    _make_heading_replacer(slugify_func),
                    heading_html
                )
                result.append(processed)
                last_copy = heading_end
                i = heading_end
                continue

        i += 1

    # Copy remaining content
    result.append(html[last_copy:])
    return "".join(result)


def _make_heading_replacer(slugify_func):
    """Create heading replacer function."""
    def replace_heading(match: re.Match) -> str:
        tag = match.group(1)
        attrs = match.group(2)
        content = match.group(3)

        if "id=" in attrs:
            return match.group(0)

        # Check for explicit {#custom-id}
        id_match = EXPLICIT_ID_PATTERN.search(content)
        if id_match:
            slug = id_match.group(1)
            content = EXPLICIT_ID_PATTERN.sub("", content)
        else:
            text = HTML_TAG_PATTERN.sub("", content).strip()
            if not text:
                return match.group(0)
            slug = slugify_func(text)

        return f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'

    return replace_heading
```

**Complexity Improvement**: O(n × blockquote_count) → O(n)

**Files to Modify**:
- Update `bengal/rendering/parsers/mistune/toc.py`

**Trade-offs**:
- ✅ O(n) regardless of blockquote count
- ✅ No string slicing for each blockquote boundary
- ⚠️ More complex character-level logic
- ⚠️ Requires careful testing of edge cases

---

### Solution 3: Tag Page Context Caching (P2)

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

### Phase 1: Unified HTML Transform (High Impact) — 1 day

**Priority**: P1  
**Effort**: 1 day  
**Risk**: Medium

**Steps**:
1. Create `unified_transform.py` with combined transformer
2. Add comprehensive unit tests for all transform cases
3. Update `pipeline/core.py` to use unified transformer
4. Benchmark before/after on test sites
5. Keep individual functions for backward compatibility

**Success Criteria**:
- ✅ 20-40% reduction in HTML processing time
- ✅ All existing tests pass
- ✅ Output identical to current implementation
- ✅ No memory regression

---

### Phase 2: Tag Page Context Caching — 0.5 days

**Priority**: P2  
**Effort**: 0.5 days  
**Risk**: Low

**Steps**:
1. Add `_tag_pages_cache` to Renderer
2. Implement `_build_all_tag_pages_cache()`
3. Update `_add_tag_generated_page_context()` to use cache
4. Test with multi-page tag pagination

**Success Criteria**:
- ✅ O(1) tag page lookups after initial build
- ✅ Correct pagination behavior
- ✅ No stale data issues

---

### Phase 3: Heading Anchor Optimization — 0.5 days

**Priority**: P2  
**Effort**: 0.5 days  
**Risk**: Medium

**Steps**:
1. Implement state machine approach in `toc.py`
2. Add tests for blockquote edge cases
3. Benchmark on blockquote-heavy content
4. Feature flag for gradual rollout

**Success Criteria**:
- ✅ O(n) regardless of blockquote count
- ✅ All heading anchor tests pass
- ✅ 2-5× faster on API documentation

---

### Phase 4: Combined API Badge Pattern — 0.5 days

**Priority**: P3  
**Effort**: 0.5 days  
**Risk**: Low

**Steps**:
1. Create combined regex pattern
2. Update `APIDocEnhancer.enhance()`
3. Test all badge types
4. Verify badge appearance unchanged

**Success Criteria**:
- ✅ Single regex pass for all badges
- ✅ Visual output unchanged
- ✅ 5× fewer regex operations

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

| Optimization | Risk Level | Mitigation |
|--------------|------------|------------|
| **Unified transform** | Medium | Comprehensive test suite, feature flag |
| **Tag page caching** | Low | Additive change, no API changes |
| **Heading anchor optimization** | Medium | Keep fallback to current impl |
| **API badge combining** | Low | Visual regression tests |

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

### Performance Targets

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **HTML transform time** | O(4n) | O(n) | 3-4× |
| **Heading anchor (blockquotes)** | O(n×depth) | O(n) | 2-5× |
| **Tag page context** | O(renders × pages) | O(1) lookup | 10-50× |
| **API badge injection** | O(5n) | O(n) | 5× |

### Quality Targets

- ✅ All existing tests pass
- ✅ Output HTML identical to current
- ✅ No memory regressions
- ✅ No performance regressions on any path

---

## References

- **Big O Analysis**: This RFC's problem statement section
- **Source Code**:
  - `bengal/rendering/pipeline/core.py:298-314` — Transform chain
  - `bengal/rendering/parsers/mistune/toc.py:92-172` — Heading anchors
  - `bengal/rendering/renderer.py:366-518` — Tag page context
  - `bengal/rendering/plugins/cross_references.py:116-141` — Xref splitting
  - `bengal/rendering/api_doc_enhancer.py:105-145` — Badge injection

---

## Appendix: Complexity Comparison

### HTML Transforms

| Approach | Time | Space | Notes |
|----------|------|-------|-------|
| **Current** | O(4n) | O(4n) | 4 strings created |
| **Proposed** | O(n) | O(n) | Single result string |

### Heading Anchors

| Approach | Time | Space | Notes |
|----------|------|-------|-------|
| **Current (fast path)** | O(n) | O(n) | No blockquotes |
| **Current (slow path)** | O(n × depth) | O(parts) | With blockquotes |
| **Proposed** | O(n) | O(n) | Always linear |

### Tag Page Context

| Approach | Time | Space | Notes |
|----------|------|-------|-------|
| **Current** | O(T × P × R) | O(1) | R = renders per tag |
| **Proposed** | O(T × P) + O(1) | O(T × P_avg) | One-time build + lookup |

---

## Conclusion

The rendering package has excellent algorithmic foundations with sophisticated caching. These optimizations provide **incremental improvements** for large sites while maintaining full backward compatibility.

**Recommended Priority**:

| Priority | Optimization | Effort | Value | Risk |
|----------|--------------|--------|-------|------|
| P1 | Unified HTML transform | 1 day | High | Medium |
| P2 | Tag page context caching | 0.5 days | Medium | Low |
| P2 | Heading anchor optimization | 0.5 days | Medium | Medium |
| P3 | Combined API badge pattern | 0.5 days | Low | Low |

**Bottom Line**: Focus on Phase 1 (unified transform) for the biggest wins. Phases 2-4 can be implemented opportunistically when working in related areas.

---

## Appendix: Quick Wins

These changes can be made immediately with minimal risk:

### Add Tag Pages Cache (< 30 minutes)

```python
# In bengal/rendering/renderer.py

class Renderer:
    def __init__(self, ...):
        # ... existing ...
        self._tag_pages_cache: dict[str, list[Page]] | None = None
```

### Pre-compile All Regex Patterns (< 15 minutes)

Ensure all regex patterns in transform functions are module-level compiled:

```python
# At module level (not inside functions)
_JINJA_PATTERN = re.compile(r"\{\{|\}\}|\{%|%\}")
_MD_LINK_PATTERN = re.compile(r'href=["\']([^"\']*\.md)["\']')
_INTERNAL_LINK_PATTERN = re.compile(r'(href|src)=["\'](/[^"\']*)["\']')
```

---

## Code Verification

This RFC was verified against actual source code:

**Verified Implementations**:
- ✅ **Transform chain**: Confirmed 3-4 sequential O(n) passes in `core.py:298-314`
- ✅ **Heading anchor slow path**: Confirmed O(n×depth) in `toc.py:92-172`
- ✅ **Tag page context**: Confirmed repeated O(pages) resolution in `renderer.py:366-518`
- ✅ **API badge patterns**: Confirmed 5 sequential pattern matches in `api_doc_enhancer.py`

**Key Finding**: The rendering package has mature, well-optimized code. These are polish optimizations, not fundamental fixes.
