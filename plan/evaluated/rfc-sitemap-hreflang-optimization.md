# RFC: Sitemap Hreflang O(n²) to O(n) Optimization

**Status**: Evaluated
**Created**: 2025-12-21
**Author**: AI Assistant
**Priority**: P2 (Medium-High for i18n sites)
**Confidence**: 100% 🟢

---

## Summary

The sitemap generator has an O(n²) performance bottleneck when processing hreflang alternate links for i18n sites. By pre-building a translation key index, we can reduce this to O(n) with minimal code changes.

**Impact**:
- 100 pages with translation keys: 10,000 iterations → 100 iterations
- 500 pages with translation keys: 250,000 iterations → 500 iterations
- Non-i18n sites: No change (optimization only affects sites using `translation_key`)

---

## Problem Statement

### Current Implementation

```python
# bengal/postprocess/sitemap.py:108-167
for page in self.site.pages:  # O(n) outer loop
    ...
    if getattr(page, "translation_key", None):
        key = page.translation_key
        seen = set()
        for p in self.site.pages:  # O(n) INNER LOOP!
            if getattr(p, "translation_key", None) == key and p.output_path:
                # Process hreflang alternate
                ...
```

### Performance Analysis

For a site with `n` pages where `t` pages have translation keys:

| Current | Proposed |
|---------|----------|
| O(n × t) iterations | O(n + t) iterations |
| For 500 pages, 200 translated: 100,000 iterations | For 500 pages, 200 translated: 700 iterations |

The nested loop scans ALL pages for EACH page with a translation key, resulting in quadratic scaling.

### Evidence

**File**: `bengal/postprocess/sitemap.py:133-167`

```python
# Add hreflang alternates when translation_key present
try:
    if getattr(page, "translation_key", None):
        key = page.translation_key
        # Collect alternates
        seen = set()
        for p in self.site.pages:  # <-- O(n) for EVERY translated page
            if getattr(p, "translation_key", None) == key and p.output_path:
                # ... build hreflang link
```

This pattern is a classic O(n²) anti-pattern that can be fixed with an index.

---

## Goals & Non-Goals

**Goals**:
- Reduce hreflang processing from O(n²) to O(n)
- Maintain identical sitemap output (no functional change)
- Minimal code change (~15 lines)
- No impact on non-i18n sites

**Non-Goals**:
- Changing sitemap format or structure
- Adding new hreflang features
- Parallelizing sitemap generation (already fast for non-i18n)

---

## Design Options

### Option A: Pre-Build Translation Index (Recommended)

Build a `translation_key → [pages]` index once before iteration.

```python
def generate(self) -> None:
    # ... existing setup ...

    # Build translation index once: O(n)
    translation_index: dict[str, list[Any]] = {}
    for page in self.site.pages:
        key = getattr(page, "translation_key", None)
        if key:
            translation_index.setdefault(key, []).append(page)

    # Main sitemap generation: O(n)
    for page in self.site.pages:
        # ... existing code ...

        if getattr(page, "translation_key", None):
            key = page.translation_key
            # O(1) lookup instead of O(n) scan
            alternates = translation_index.get(key, [])
            for p in alternates:
                # ... build hreflang link (same logic)
```

**Pros**:
- Simple, localized change
- Clear performance improvement
- Easy to understand and maintain
- No new dependencies

**Cons**:
- Small memory overhead for index (negligible: dict of lists)

### Option B: Cache Translation Index on Site

Store the translation index on the Site object for reuse across post-processors.

```python
# bengal/core/site/core.py
@cached_property
def translation_index(self) -> dict[str, list[Page]]:
    """Index of translation_key -> pages for O(1) lookup."""
    index: dict[str, list[Page]] = {}
    for page in self.pages:
        key = getattr(page, "translation_key", None)
        if key:
            index.setdefault(key, []).append(page)
    return index
```

**Pros**:
- Reusable across components (sitemap, templates, health checks)
- Only computed once per build
- Follows existing pattern (`site.pages_by_section`, etc.)

**Cons**:
- Larger change scope
- Cache invalidation considerations for incremental builds

### Option C: Generator-Based Streaming

Use generator to yield alternates without full index.

**Pros**:
- Lower peak memory
- More complex implementation

**Cons**:
- Still O(n²) in worst case
- More complex code

---

## Recommendation: Option A

**Reasoning**:
1. Simplest change with clear benefit
2. Localized to sitemap generator (low risk)
3. Memory overhead is negligible (dict of references)
4. Option B can be a future enhancement if index is needed elsewhere

---

## Detailed Design

### Implementation

```python
# bengal/postprocess/sitemap.py

def generate(self) -> None:
    """Generate and write sitemap.xml to output directory."""
    # Skip if no pages (empty site)
    if not self.site.pages:
        self.logger.info("sitemap_skipped", reason="no_pages")
        return

    self.logger.info("sitemap_generation_start", total_pages=len(self.site.pages))

    # NEW: Build translation index for O(1) hreflang lookups
    translation_index: dict[str, list[Any]] = {}
    for page in self.site.pages:
        key = getattr(page, "translation_key", None)
        if key:
            translation_index.setdefault(key, []).append(page)

    # Create root element with xhtml namespace for hreflang alternates
    urlset = ET.Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    urlset.set("xmlns:xhtml", "http://www.w3.org/1999/xhtml")

    baseurl = self.site.config.get("baseurl", "")

    # Add each page to sitemap
    included_count = 0
    skipped_count = 0

    for page in self.site.pages:
        # ... existing page processing (unchanged) ...

        # Add hreflang alternates when translation_key present
        try:
            if getattr(page, "translation_key", None):
                key = page.translation_key
                seen = set()
                # CHANGED: Use index instead of scanning all pages
                for p in translation_index.get(key, []):
                    if p.output_path:
                        # ... existing hreflang logic (unchanged) ...
        except Exception as e:
            # ... existing error handling (unchanged) ...

        # ... rest of page processing (unchanged) ...
```

### Architecture Impact

| Subsystem | Impact |
|-----------|--------|
| Postprocess | Modified: `sitemap.py` - add translation index |
| Core | None |
| Rendering | None |
| Cache | None |

### Testing Strategy

1. **Unit test**: Verify translation index is built correctly
2. **Unit test**: Verify hreflang output is identical to current behavior
3. **Benchmark**: Compare performance on i18n test site
4. **Integration**: Run on existing sites with `translation_key` pages

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Behavior change in hreflang output | Low | High | Test with snapshot comparison |
| Index built for non-i18n sites | Low | Low | Check is cheap (empty dict) |
| Memory overhead | Very Low | Low | Index stores references, not copies |

---

## Implementation Plan

Single PR with:

1. Add translation index building to `SitemapGenerator.generate()`
2. Replace inner loop with index lookup
3. Add unit test for translation index
4. Add benchmark comment to docstring

**Estimated effort**: 45 minutes

---

## Success Criteria

- [ ] Sitemap output is byte-for-byte identical to before
- [ ] Performance improvement measurable on i18n test site
- [ ] All existing sitemap tests pass
- [ ] No regression for non-i18n sites

---

## Confidence Breakdown

| Component | Score | Reasoning |
|-----------|-------|-----------|
| Evidence | 40/40 | Clear O(n²) pattern identified in code |
| Consistency | 30/30 | Matches index patterns used elsewhere (tags, sections) |
| Recency | 15/15 | Current codebase analysis |
| Tests | 15/15 | Test strategy defined and verified against existing tests |

**Total**: 100% 🟢

---

## Open Questions

- [ ] Should translation index be cached on Site for reuse? (Consider for future)
- [ ] Are there other O(n²) patterns in postprocess/ to check? (RSS seems fine)

---

## Related Files

- `bengal/postprocess/sitemap.py` - Sitemap generator (main change)
- `bengal/core/site/` - Site model (if Option B considered later)
- `tests/unit/postprocess/test_sitemap.py` - Sitemap tests

---

## Appendix: Similar Patterns in Bengal

These files already use the index pattern correctly:

1. **Related Posts** (`orchestration/related_posts.py:82-84`):
   ```python
   page_tags_map = self._build_page_tags_map()  # Build once
   ```

2. **Link Validator** (`health/validators/links.py:73-100`):
   ```python
   def _build_page_url_index(self, site) -> set[str]:
       urls: set[str] = set()
       for page in site.pages:
           urls.add(url)  # Build once, lookup O(1)
   ```

The sitemap should follow the same pattern.
