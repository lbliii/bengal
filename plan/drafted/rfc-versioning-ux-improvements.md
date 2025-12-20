# RFC: Versioning UX Improvements

**Status**: Draft  
**Created**: 2025-12-20  
**Subsystem**: core/version, rendering/templates, discovery  

---

## Problem Statement

When a user toggles to a previous version and that specific page doesn't exist in the target version, they get a 404 error. This creates a poor user experience.

**Current behavior**:
1. User is on `/docs/content/versioning/folder-mode/` (v2)
2. User selects "v1" from version dropdown
3. JavaScript constructs `/docs/v1/content/versioning/folder-mode/`
4. Browser navigates → 404 (page doesn't exist in v1)

**Expected behavior**:
1. User is on `/docs/content/versioning/folder-mode/` (v2)
2. User selects "v1" from version dropdown
3. System **already knows** target page doesn't exist (computed at build time)
4. System navigates directly to best fallback:
   - `/docs/v1/content/versioning/` (section index), OR
   - `/docs/v1/` (version root)
5. User lands on valid page instantly

### Secondary Issue: Ordering/Nesting Validation

The current v1 test fixture (`site/content/_versions/v1/`) is minimal (only 3 pages) and doesn't adequately exercise:
- Weight-based ordering across versions
- Nested section hierarchy in versioned content
- Subsection filtering in navigation

---

## Industry Context

### How Other SSGs Handle This

| SSG | Versioning | 404 on Version Switch? |
|-----|------------|------------------------|
| **Docusaurus** | `versioned_docs/` + manifest | **Yes, 404** - no smart fallback |
| **MkDocs + mike** | Separate deployments | **Yes, 404** - no smart fallback |
| **VitePress** | No built-in versioning | N/A |
| **Hugo** | No built-in versioning | N/A |
| **ReadTheDocs** | Server-side platform | **No** - has server-side redirects |
| **GitBook** | SaaS platform | **No** - has server-side logic |

**Key insight**: Most pure static SSGs don't solve this problem. They show 404s. Platforms that handle it gracefully have server-side logic (ReadTheDocs, GitBook) or are SPAs with client-side routing (Docusaurus with React).

**Opportunity**: Bengal can differentiate by solving this elegantly at build time.

---

## Evidence

### Current Implementation

**Version selector** (`version-selector.html:57-104`):
```javascript
function handleVersionChange(versionPrefix) {
  const currentPath = window.location.pathname;
  // ... URL construction logic ...

  // Navigate directly without validation
  window.location.href = newPath;  // ← Problem: no existence check
}
```

**URL construction** is correct, but there's no validation that the target exists.

### Version-aware navigation works correctly

`bengal/core/section.py:463-510` provides `pages_for_version()` and `subsections_for_version()` methods that properly filter content by version. Navigation sidebar already uses these.

---

## Goals

1. **Zero latency fallback**: Pre-compute fallback URLs at build time
2. **Zero 404s from version switching**: All version switches land on valid pages
3. **Preserve user context**: Land as close to the original context as possible
4. **Static-site compatible**: No server-side logic required
5. **Industry-leading UX**: Better than Docusaurus, MkDocs, and other pure SSGs

### Non-Goals

- Cross-version content comparison
- Automatic content migration hints
- Server-side redirect support (out of scope for static hosting)

---

## Design Options

### Option A: Pre-computed Fallback URLs (Recommended) ⭐

At build time, compute the fallback URL for each (page, version) pair and embed it in the version selector. **No runtime lookup needed**.

**Template output** (`version-selector.html`):
```html
<select onchange="handleVersionChange(this.selectedOptions[0])">
  {% for v in versions %}
  <option
    value="{{ v.url_prefix or '/' }}"
    data-target="{{ site.get_version_target_url(page, v) }}"
    {% if current_version and current_version.id == v.id %}selected{% endif %}
  >
    {{ v.label }}{% if v.latest %} (Latest){% endif %}
  </option>
  {% endfor %}
</select>

<script>
function handleVersionChange(option) {
  // Target URL is pre-computed at build time - instant navigation
  window.location.href = option.dataset.target;
}
</script>
```

**Engine-Agnostic**: Uses `site.get_version_target_url()` method which works with any template engine (Jinja2, Mako, or BYORenderer).

**Build-time template function** (`get_version_target_url`):
```python
def get_version_target_url(page: Page, target_version: Version, site: Site) -> str:
    """
    Compute the best URL for this page in the target version.

    Fallback cascade:
    1. Exact page exists → use it
    2. Section index exists → use it
    3. Version root → use it
    """
    # Construct equivalent path in target version
    target_path = construct_version_path(page, target_version)

    # Check if exact page exists in target version
    if page_exists_in_version(target_path, target_version, site):
        return target_path

    # Fallback to section index
    section_index = get_section_index_path(target_path, target_version)
    if page_exists_in_version(section_index, target_version, site):
        return section_index

    # Fallback to version root
    return get_version_root_url(target_version, site)
```

**Pros**:
- ✅ **Zero latency** - fallback pre-computed, no runtime lookup
- ✅ **No extra files** - data embedded in HTML
- ✅ **No JavaScript complexity** - trivial one-liner handler
- ✅ **Works offline** - no fetch needed
- ✅ **Build-time validated** - errors caught during build, not at runtime

**Cons**:
- ❌ Slight HTML size increase (~50 bytes per version per page)
- ❌ Requires build-time page existence checking

**Performance**: For 5 versions × 1000 pages = ~250KB total overhead across entire site (~50 bytes/page/version)

---

### Option B: Runtime Version Manifest

Generate a JSON manifest during build listing all pages per version. Client fetches and caches it.

```json
{
  "v2": ["/docs/", "/docs/get-started/", ...],
  "v1": ["/docs/", "/docs/get-started/", ...]
}
```

**Pros**:
- ✅ Works with static hosting
- ✅ Single source of truth

**Cons**:
- ❌ **Extra network request** on first version switch
- ❌ **Runtime lookup latency** (must search manifest)
- ❌ **Extra build artifact** to maintain
- ❌ Manifest can grow large for huge sites

---

### Option C: Client-side HEAD Request

Before navigating, use `fetch()` with HEAD method to check if target URL exists.

**Cons**:
- ❌ **Network latency** on every switch
- ❌ **Multiple requests** for fallback cascade
- ❌ **CORS issues** on some static hosts
- ❌ **Poor UX** - visible loading delay

---

### Option D: Smart 404 Page

Generate a version-aware 404 page that redirects on load.

**Cons**:
- ❌ **User sees 404 briefly** before redirect
- ❌ **Two navigations** (original + redirect)
- ❌ **Less granular** - can't know section context

---

## Recommendation

**Option A (Pre-computed Fallback URLs)** is the most elegant and performant solution:

| Metric | Option A | Option B | Option C | Option D |
|--------|----------|----------|----------|----------|
| Latency | **0ms** | 50-200ms | 100-500ms | 200-400ms |
| Extra requests | **0** | 1 | 1-5 | 1 |
| Build artifacts | **0** | 1 | 0 | 0 |
| Complexity | Medium | Medium | Low | Low |
| UX quality | **Best** | Good | Poor | Poor |

**This approach is better than any major static SSG** because fallback is instant and invisible to the user.

---

## Implementation Plan

### Phase 1: Engine-Agnostic Site Method ✅

**Key Design Decision**: Expose the version URL logic as a **Site method** rather than a Jinja-specific global function. This enables BYORenderer support.

1. Add `Site.get_version_target_url()` method (`bengal/core/site/core.py`):
   ```python
   def get_version_target_url(
       self, page: Page | None, target_version: dict[str, Any] | None
   ) -> str:
       """
       Get the best URL for a page in the target version.

       Works with any template engine (Jinja2, Mako, BYORenderer).
       """
       from bengal.rendering.template_functions.version_url import (
           get_version_target_url as _get_version_target_url,
       )
       return _get_version_target_url(page, target_version, self)
   ```

2. Core logic in `bengal/rendering/template_functions/version_url.py`:
   ```python
   def get_version_target_url(page: Page, version: dict, site: Site) -> str:
       """Compute best URL for page in target version with fallback cascade."""
       ...

   def page_exists_in_version(path: str, version_id: str, site: Site) -> bool:
       """Check if a page exists in the given version."""
       ...
   ```

3. Jinja registration for backward compatibility only:
   - Templates using `{{ get_version_target_url(page, v) }}` still work
   - Preferred: `{{ site.get_version_target_url(page, v) }}`

4. O(1) lookups via LRU-cached version→pages index:
   ```python
   @lru_cache(maxsize=1)
   def _build_version_page_index(site: Site) -> dict[str, set[str]]:
       """Index of page URLs by version for fast existence checks."""
       ...
   ```

### Phase 2: Update Version Selector Template ✅

1. Update `bengal/themes/default/templates/partials/version-selector.html`:
   ```html
   <option
     value="{{ v.url_prefix or '/' }}"
     data-target="{{ site.get_version_target_url(page, v) }}"
     ...
   >
   ```

2. Simplify JavaScript handler:
   ```javascript
   function handleVersionChange(option) {
     window.location.href = option.dataset.target;
   }
   ```

3. Optional: Add visual indicator when landing on fallback:
   ```html
   {% if page_is_version_fallback %}
   <div class="version-fallback-notice">
     This page doesn't exist in {{ current_version.label }}.
     Showing {{ page.title }} instead.
   </div>
   {% endif %}
   ```

**BYORenderer Example (Mako)**:
```mako
% for v in versions:
<option data-target="${site.get_version_target_url(page, v)}">
  ${v['label']}
</option>
% endfor
```

### Phase 3: Expand Test Fixtures

1. Expand `site/content/_versions/v1/`:
   - Add more nested sections matching v2 structure
   - Include weight-based ordering examples
   - Create pages that DON'T exist in v2 (to test both directions)

2. Update `tests/roots/test-versioned/`:
   - Add explicit ordering tests
   - Add pages with different weights per version
   - Add subsection nesting tests

### Phase 4: Tests

1. Unit tests for `get_version_target_url`:
   - Exact page exists → returns exact URL
   - Page missing, section exists → returns section index
   - Section missing → returns version root
   - All missing → returns site root

2. Integration tests:
   - Build versioned site
   - Verify all version selector options have valid `data-target` URLs
   - Verify fallback cascade logic

---

## Files Changed

| File | Change | Status |
|------|--------|--------|
| `bengal/core/site/core.py` | Add `get_version_target_url()` method (engine-agnostic) | ✅ Done |
| `bengal/rendering/template_functions/version_url.py` | Core fallback URL computation logic | ✅ Done |
| `bengal/rendering/template_functions/__init__.py` | Register functions (backward compat) | ✅ Done |
| `bengal/themes/default/templates/partials/version-selector.html` | Use `site.get_version_target_url()` | ✅ Done |
| `site/content/_versions/v1/` | Expand test content | Pending |
| `tests/roots/test-versioned/` | Expand test fixture | Pending |
| `tests/unit/test_versioning_template_functions.py` | Unit tests | ✅ Done |
| `tests/integration/test_versioning_ux.py` | Integration tests | ✅ Done |
| `tests/unit/test_version_url.py` | NEW: Unit tests |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Build time increase | Slight slowdown | Pages indexed once, O(1) lookups |
| HTML size increase | ~50 bytes/version/page | Negligible for typical sites |
| Complex edge cases | Incorrect fallback | Comprehensive test coverage |

---

## Success Criteria

- [ ] Version switching never results in 404 (when target version has any content)
- [ ] Fallback is **instant** (no visible delay)
- [ ] Fallback lands on logical page (exact → section index → version root)
- [ ] Build time increase <5% for 1000 page site
- [ ] HTML size increase <100 bytes per page
- [ ] Ordering/nesting works correctly across versions

---

## Open Questions

1. **Fallback notice UX**: Should we show a subtle banner when user lands on fallback? Or is silent fallback better?
2. **URL parameter**: Should we add `?fallback=true` to track fallback navigations for analytics?

---

## Comparison with Industry

| Feature | Bengal (proposed) | Docusaurus | MkDocs | ReadTheDocs |
|---------|------------------|------------|--------|-------------|
| Smart fallback | ✅ Pre-computed | ❌ 404 | ❌ 404 | ✅ Server-side |
| Latency | **0ms** | N/A | N/A | ~50ms |
| Static hosting | ✅ | ✅ | ✅ | ❌ |
| Build artifact | None | `versions.json` | None | N/A |

**Bengal will have the best version-switching UX of any pure static site generator.**

---

## References

- `bengal/themes/default/templates/partials/version-selector.html` - Current implementation
- `bengal/core/version.py` - Version model
- `bengal/core/section.py:463-510` - Version-aware section methods
- `site/content/docs/content/versioning/` - User documentation
