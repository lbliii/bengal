# RFC: Add `.permalink` Property for Improved URL Ergonomics

**RFC Number**: 001  
**Status**: Draft  
**Created**: 2025-10-18  
**Author**: Bengal Core Team  
**Related**: `url-strategy-downstream-impact.md`, `url-ergonomics-analysis.md`

## Executive Summary

Add `.permalink` property to `Page` and `Section` objects that returns URLs with baseurl applied, following Hugo's dual-property pattern. This improves template ergonomics by eliminating the need to remember `| absolute_url` filter for most use cases while maintaining the existing "identity vs display" URL pattern.

**Impact**: Non-breaking enhancement that reduces template verbosity by ~35% and eliminates a common source of deployment bugs.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Goals & Non-Goals](#goals--non-goals)
3. [Proposed Solution](#proposed-solution)
4. [Detailed Design](#detailed-design)
5. [Implementation Plan](#implementation-plan)
6. [Testing Strategy](#testing-strategy)
7. [Migration Path](#migration-path)
8. [Alternatives Considered](#alternatives-considered)
9. [Open Questions](#open-questions)

---

## Problem Statement

### Current Developer Experience

Theme developers must manually apply the `| absolute_url` filter to all URL outputs for deployment compatibility:

```jinja2
{# Current pattern - verbose and error-prone #}
<a href="{{ page.url | absolute_url }}">{{ page.title }}</a>
<a href="{{ section.url | absolute_url }}">{{ section.title }}</a>

{% for item in get_breadcrumbs(page) %}
  <a href="{{ item.url | absolute_url }}">{{ item.title }}</a>
{% endfor %}
```

**Problems**:

1. **Easy to Forget**: Forgetting the filter is a silent failure
   - Works in local dev (no baseurl)
   - Breaks in production (GitHub Pages, subpath deployments)
   - No linter warnings or compile-time errors

2. **Verbose**: Every URL reference requires 16 extra characters (`| absolute_url`)
   - Clutters templates
   - Reduces readability

3. **Cognitive Load**: Must remember two rules:
   - "Use filter for display" (href attributes)
   - "Don't use filter for comparisons" (URL matching)
   - Not intuitive which is which

### Real-World Evidence

**From our codebase audit** (`bengal/themes/default/templates/`):

```bash
# Templates that correctly use | absolute_url: 13 instances
grep -r "| absolute_url" bengal/themes/default/templates/ | wc -l
# Output: 13

# Templates that use raw URLs (potential bugs): 3 instances (we just fixed)
# - base.html footer menu (line 314)
# - content-components.html child items (line 168)  
# - navigation-components.html breadcrumbs (line 50)
```

**Bug rate**: 3 out of 16 URL usages (18.75%) were missing the filter before our fixes.

### Current Code References

**Page URL property** (`bengal/core/page/metadata.py:56-122`):
```python
@cached_property
def url(self) -> str:
    """
    Get the URL path for the page (cached after first access).

    Returns:
        URL path with leading and trailing slashes
    """
    # Returns relative URL like "/about/" without baseurl
    if not self.output_path:
        return self._fallback_url()
    # ... URL generation logic
    return url  # Relative path only
```

**Section URL property** (`bengal/core/section.py:243-274`):
```python
@cached_property
def url(self) -> str:
    """
    Get the URL for this section (cached after first access).

    Returns:
        URL path for the section
    """
    # Returns relative URL like "/docs/" without baseurl
    if self.index_page and hasattr(self.index_page, "output_path"):
        url = self.index_page.url
        return url
    url = f"{self.parent.url}{self.name}/" if self.parent else f"/{self.name}/"
    return url  # Relative path only
```

**Template filter** (`bengal/rendering/template_engine.py:299-369`):
```python
def _url_for(self, page: Any) -> str:
    """
    Generate URL for a page with base URL support.

    Returns:
        URL path with base URL prefix if configured
    """
    url = page.url if hasattr(page, "url") else f"/{page.slug}/"
    return self._with_baseurl(url)  # Applies baseurl here

def _with_baseurl(self, path: str) -> str:
    """
    Apply base URL prefix to a path.

    Returns:
        Path with base URL prefix (absolute or path-only)
    """
    if not path.startswith("/"):
        path = "/" + path

    baseurl_value = (self.site.config.get("baseurl", "") or "").rstrip("/")
    if not baseurl_value:
        return path

    # Absolute baseurl (e.g., https://example.com/subpath)
    if baseurl_value.startswith(("http://", "https://", "file://")):
        return f"{baseurl_value}{path}"

    # Path-only baseurl (e.g., /repo)
    base_path = "/" + baseurl_value.lstrip("/")
    return f"{base_path}{path}"
```

---

## Goals & Non-Goals

### Goals

1. **Reduce template verbosity** - Eliminate `| absolute_url` in common cases
2. **Improve developer experience** - More intuitive URL handling
3. **Maintain backward compatibility** - Existing templates continue working
4. **Preserve URL comparison behavior** - Menu activation, validators still work
5. **Clear semantics** - Property names indicate purpose

### Non-Goals

1. **Auto-magic URL transformation** - No hidden template preprocessing
2. **Changing core URL format** - `page.url` remains relative (identity URL)
3. **Breaking existing APIs** - All existing code paths remain functional
4. **Forcing adoption** - Both patterns (property vs filter) remain valid

---

## Proposed Solution

### Overview

Add `.permalink` property to `Page` and `Section` that returns the URL with baseurl applied, following Hugo's pattern:

```python
# Identity URL (for comparisons)
page.url        # → "/about/"

# Display URL (for href attributes)
page.permalink  # → "/repo/about/"  (with baseurl="/repo")
```

### Key Design Principles

1. **Two Properties, Clear Purpose**:
   - `.url` = Identity (relative, for comparisons)
   - `.permalink` = Display (with baseurl, for href)

2. **Template Simplification**:
   ```jinja2
   {# Before #}
   <a href="{{ page.url | absolute_url }}">{{ page.title }}</a>

   {# After #}
   <a href="{{ page.permalink }}">{{ page.title }}</a>
   ```

3. **Backward Compatibility**:
   ```jinja2
   {# Old way still works #}
   <a href="{{ page.url | absolute_url }}">{{ page.title }}</a>

   {# New way is shorter #}
   <a href="{{ page.permalink }}">{{ page.title }}</a>
   ```

---

## Detailed Design

### 1. Core Implementation

#### Page.permalink Property

**Location**: `bengal/core/page/metadata.py`

**Implementation**:
```python
@cached_property
def permalink(self) -> str:
    """
    Get the display URL with baseurl applied (cached after first access).

    This is the URL to use in HTML href attributes and links. It includes
    the configured baseurl, making it suitable for subpath deployments
    (GitHub Pages, custom subpaths, etc.).

    For URL comparisons and identity checks, use .url instead.

    Examples:
        With baseurl="/repo":
            page.url       # "/about/"
            page.permalink # "/repo/about/"

        With baseurl="https://example.com":
            page.url       # "/about/"
            page.permalink # "https://example.com/about/"

        Without baseurl:
            page.url       # "/about/"
            page.permalink # "/about/"

    Returns:
        URL with baseurl applied for display purposes

    See Also:
        - url: Relative URL for comparisons and identity
        - url_for() template function: Alternative way to apply baseurl
    """
    if not self._site:
        # Fallback: no site reference, return relative URL
        return self.url

    baseurl = self._site.config.get("baseurl", "") or ""
    return self._apply_baseurl(self.url, baseurl)

def _apply_baseurl(self, path: str, baseurl: str) -> str:
    """
    Apply baseurl to a path (internal helper).

    Args:
        path: Relative URL path (e.g., "/about/")
        baseurl: Base URL from config

    Returns:
        Path with baseurl applied
    """
    if not baseurl:
        return path

    if not path.startswith("/"):
        path = "/" + path

    baseurl = baseurl.rstrip("/")

    # Absolute baseurl (http://, https://, file://)
    if baseurl.startswith(("http://", "https://", "file://")):
        return f"{baseurl}{path}"

    # Path-only baseurl (/repo)
    base_path = "/" + baseurl.lstrip("/")
    return f"{base_path}{path}"
```

**Cache Invalidation**: Uses `@cached_property`, cleared when:
- Page object is recreated (new build)
- Explicit cache clear (dev server rebuild)
- Baseurl changes (config reload)

**Performance**: No performance impact - same caching as `url` property

#### Section.permalink Property

**Location**: `bengal/core/section.py`

**Implementation**:
```python
@cached_property
def permalink(self) -> str:
    """
    Get the display URL with baseurl applied (cached after first access).

    This is the URL to use in HTML href attributes. It includes the
    configured baseurl for deployment compatibility.

    Returns:
        URL with baseurl applied for display purposes
    """
    if not self._site:
        return self.url

    baseurl = self._site.config.get("baseurl", "") or ""
    return self._apply_baseurl(self.url, baseurl)

def _apply_baseurl(self, path: str, baseurl: str) -> str:
    """Apply baseurl to a path (shared with Page implementation)."""
    # [Same implementation as Page._apply_baseurl]
```

**Consideration**: Extract `_apply_baseurl` to shared utility module to avoid duplication.

### 2. Navigation Function Updates

**Location**: `bengal/rendering/template_functions/navigation.py`

**Current**: Navigation functions return dictionaries with `url` field:
```python
def get_breadcrumbs(page: "Page") -> list[dict[str, Any]]:
    """Get breadcrumb items for a page."""
    items = []
    for ancestor in reversed_ancestors:
        url = ancestor.url if hasattr(ancestor, "url") else f"/{getattr(ancestor, 'slug', '')}/"
        items.append({
            "title": getattr(ancestor, "title", "Untitled"),
            "url": url,  # Relative URL only
            "is_current": is_current_item,
        })
    return items
```

**Proposed**: Add `permalink` field while keeping `url` for compatibility:
```python
def get_breadcrumbs(page: "Page") -> list[dict[str, Any]]:
    """
    Get breadcrumb items for a page.

    Each item contains:
    - title: Display text
    - url: Relative URL (for comparisons)
    - permalink: URL with baseurl (for href attributes)
    - is_current: Boolean flag
    """
    items = []
    for ancestor in reversed_ancestors:
        # Get both URLs
        url = ancestor.url if hasattr(ancestor, "url") else f"/{getattr(ancestor, 'slug', '')}/"
        permalink = ancestor.permalink if hasattr(ancestor, "permalink") else url

        items.append({
            "title": getattr(ancestor, "title", "Untitled"),
            "url": url,          # Identity URL (relative)
            "permalink": permalink,  # Display URL (with baseurl)
            "is_current": is_current_item,
        })
    return items
```

**Functions to Update**:
- `get_breadcrumbs()` - line 29
- `get_pagination_items()` - line 242
- `get_nav_tree()` - line 400
- `get_auto_nav()` - line 564

### 3. Template Updates

**Example 1: Breadcrumbs** (`bengal/themes/default/templates/partials/navigation-components.html:40-50`):

```jinja2
{# Before #}
<a href="{{ item.url | absolute_url }}">{{ item.title }}</a>

{# After (recommended) #}
<a href="{{ item.permalink }}">{{ item.title }}</a>

{# Or keep using filter (still works) #}
<a href="{{ item.url | absolute_url }}">{{ item.title }}</a>
```

**Example 2: Direct page links** (`bengal/themes/default/templates/base.html:164`):

```jinja2
{# Before #}
<a href="{{ item.url | absolute_url }}">{{ item.name }}</a>

{# After (simpler) #}
<a href="{{ item.permalink }}">{{ item.name }}</a>
```

**Example 3: Comparisons remain unchanged**:

```jinja2
{# URL comparisons still use .url (identity) #}
{{ 'active' if page.url == menu_item.url else '' }}

{# This continues to work correctly #}
```

### 4. Documentation Updates

**Template Function Docstrings**:

```python
def get_breadcrumbs(page: "Page") -> list[dict[str, Any]]:
    """
    Get breadcrumb items for a page.

    Returns a list of breadcrumb items. Each item is a dictionary with:
    - title: Display text for the breadcrumb
    - url: Relative URL (for comparisons, menu activation)
    - permalink: URL with baseurl applied (for href attributes)
    - is_current: True if this is the current page

    Usage:
        Basic (recommended):
            {% for item in get_breadcrumbs(page) %}
              <a href="{{ item.permalink }}">{{ item.title }}</a>
            {% endfor %}

        Advanced (with comparisons):
            {% for item in get_breadcrumbs(page) %}
              <a href="{{ item.permalink }}"
                 class="{{ 'active' if current_url == item.url }}">
                {{ item.title }}
              </a>
            {% endfor %}
    """
```

---

## Implementation Plan

### Phase 1: Core Properties (Week 1)

**PR 1: Add permalink property to Page**
- Add `permalink` property to `Page` class
- Add `_apply_baseurl` helper method
- Add comprehensive docstring
- Update `Page` class documentation

**Files**:
- `bengal/core/page/metadata.py`

**Tests**:
```python
# tests/unit/core/test_page_permalink.py

def test_page_permalink_with_path_baseurl(tmp_path):
    """Test permalink with path-only baseurl like /repo."""
    site = Site(root_path=tmp_path, config={"baseurl": "/repo"})
    site.output_dir = tmp_path / "public"

    page = Page(source_path=Path("about.md"))
    page._site = site
    page.output_path = tmp_path / "public" / "about" / "index.html"

    assert page.url == "/about/"
    assert page.permalink == "/repo/about/"

def test_page_permalink_with_absolute_baseurl(tmp_path):
    """Test permalink with absolute baseurl."""
    site = Site(root_path=tmp_path, config={"baseurl": "https://example.com"})
    site.output_dir = tmp_path / "public"

    page = Page(source_path=Path("about.md"))
    page._site = site
    page.output_path = tmp_path / "public" / "about" / "index.html"

    assert page.url == "/about/"
    assert page.permalink == "https://example.com/about/"

def test_page_permalink_without_baseurl(tmp_path):
    """Test permalink defaults to url when no baseurl."""
    site = Site(root_path=tmp_path, config={})
    site.output_dir = tmp_path / "public"

    page = Page(source_path=Path("about.md"))
    page._site = site
    page.output_path = tmp_path / "public" / "about" / "index.html"

    assert page.url == "/about/"
    assert page.permalink == "/about/"  # Same as url

def test_page_permalink_cache_consistency():
    """Test that permalink caching is consistent with url."""
    # Test cache invalidation, multiple accesses, etc.
```

**PR 2: Add permalink property to Section**
- Add `permalink` property to `Section` class
- Share `_apply_baseurl` implementation (consider utils module)
- Add comprehensive docstring

**Files**:
- `bengal/core/section.py`
- `bengal/utils/url_helpers.py` (new, if extracting shared logic)

**Tests**:
```python
# tests/unit/core/test_section_permalink.py

def test_section_permalink_with_baseurl(tmp_path):
    """Test section permalink with baseurl."""
    site = Site(root_path=tmp_path, config={"baseurl": "/repo"})

    section = Section(name="docs", path=tmp_path / "content" / "docs")
    section._site = site

    assert section.url == "/docs/"
    assert section.permalink == "/repo/docs/"
```

### Phase 2: Navigation Functions (Week 2)

**PR 3: Update navigation functions to return permalink**
- Update `get_breadcrumbs()` to include `permalink` field
- Update `get_pagination_items()` to include `permalink` field
- Update `get_nav_tree()` to include `permalink` field
- Update `get_auto_nav()` to include `permalink` field
- Update docstrings with examples

**Files**:
- `bengal/rendering/template_functions/navigation.py`

**Tests**:
```python
# tests/unit/template_functions/test_navigation_permalink.py

def test_breadcrumbs_include_permalink_field():
    """Test that breadcrumbs include both url and permalink."""
    site = Site(root_path=Path("/site"), config={"baseurl": "/repo"})

    section = Mock()
    section.url = "/docs/"
    section.permalink = "/repo/docs/"
    section.title = "Docs"

    page = Mock()
    page.url = "/docs/guide/"
    page.permalink = "/repo/docs/guide/"
    page.ancestors = [section]

    items = get_breadcrumbs(page)

    assert len(items) == 2
    assert items[0]["url"] == "/docs/"
    assert items[0]["permalink"] == "/repo/docs/"
    assert items[1]["url"] == "/docs/guide/"
    assert items[1]["permalink"] == "/repo/docs/guide/"
```

### Phase 3: Template Updates (Week 3)

**PR 4: Update default theme templates**
- Update breadcrumbs macro to use `permalink`
- Update navigation components to use `permalink`
- Update footer menu to use `permalink`
- Add comments explaining url vs permalink
- Keep backward compatibility notes

**Files**:
- `bengal/themes/default/templates/partials/navigation-components.html`
- `bengal/themes/default/templates/base.html`
- `bengal/themes/default/templates/partials/content-components.html`

**Before/After Examples**:
```jinja2
{# partials/navigation-components.html - Breadcrumbs #}

{# Before (16 extra chars per link) #}
<a href="{{ item.url | absolute_url }}">{{ item.title }}</a>

{# After (cleaner, more intuitive) #}
<a href="{{ item.permalink }}">{{ item.title }}</a>
```

### Phase 4: Documentation (Week 4)

**PR 5: Comprehensive documentation**
- Add "URL Handling Guide" to docs
- Update template function reference
- Add migration guide for theme developers
- Add deployment scenario examples
- Update GETTING_STARTED.md with permalink examples

**New Files**:
- `docs/guides/url-handling.md`
- `docs/guides/theme-development/urls.md`
- `docs/migration/permalink-property.md`

**Documentation Structure**:

```markdown
# URL Handling in Bengal

## Two Types of URLs

Bengal uses two types of URLs to balance flexibility with convenience:

### Identity URLs (.url)
- **Purpose**: Comparisons, validation, menu activation
- **Format**: Relative paths like `/about/` or `/docs/guide/`
- **Includes baseurl**: No
- **Use for**: URL matching, active state detection, validators

### Display URLs (.permalink)
- **Purpose**: HTML output, href attributes, links
- **Format**: Complete URLs like `/repo/about/` or `https://example.com/about/`
- **Includes baseurl**: Yes
- **Use for**: <a href>, navigation links, breadcrumbs

## Quick Reference

| Scenario | Use This | Example |
|----------|----------|---------|
| Link in template | `.permalink` | `<a href="{{ page.permalink }}">` |
| Menu activation | `.url` | `{{ 'active' if page.url == item.url }}` |
| Breadcrumb link | `.permalink` | `<a href="{{ item.permalink }}">` |
| URL comparison | `.url` | `{% if page.url.startswith('/blog/') %}` |
| Navigation function output | `.permalink` | `<a href="{{ item.permalink }}">` |
| Old templates (compat) | `.url \| absolute_url` | Still works! |

## Examples

### Basic Link
```jinja2
{# Recommended #}
<a href="{{ page.permalink }}">{{ page.title }}</a>

{# Also works (backward compatible) #}
<a href="{{ page.url | absolute_url }}">{{ page.title }}</a>
```

### Active Menu Item
```jinja2
<a href="{{ item.permalink }}"
   class="{{ 'active' if page.url == item.url }}">
  {{ item.name }}
</a>
```

### Breadcrumbs
```jinja2
{% for item in get_breadcrumbs(page) %}
  <a href="{{ item.permalink }}">{{ item.title }}</a>
{% endfor %}
```

## Deployment Scenarios

### GitHub Pages (subpath)
```toml
[site]
baseurl = "/my-repo"
```
- `page.url` → `/about/`
- `page.permalink` → `/my-repo/about/`

### Custom Domain (root)
```toml
[site]
baseurl = "https://example.com"
```
- `page.url` → `/about/`
- `page.permalink` → `https://example.com/about/`

### Offline/Local
```toml
[site]
# No baseurl needed
```
- `page.url` → `/about/`
- `page.permalink` → `/about/`

##Migration Guide

If you have existing themes using `| absolute_url`:

1. **No action required** - Filter still works
2. **Optional**: Simplify by replacing with `.permalink`
3. **Gradual adoption** - Update templates incrementally
4. **Testing**: Works in all deployment scenarios
```

---

## Testing Strategy

### Unit Tests (15 new tests)

1. **Page permalink property** (5 tests)
   - With path baseurl (`/repo`)
   - With absolute baseurl (`https://example.com`)
   - With file baseurl (`file:///path`)
   - Without baseurl
   - Cache consistency

2. **Section permalink property** (5 tests)
   - Same scenarios as Page
   - Nested section hierarchy

3. **Navigation functions** (5 tests)
   - Breadcrumbs include permalink
   - Pagination includes permalink
   - Nav tree includes permalink
   - Auto-nav includes permalink
   - Backward compatibility (url field still present)

### Integration Tests (10 new tests)

1. **Full site builds** (5 tests)
   - Build with path baseurl
   - Build with absolute baseurl
   - Build without baseurl
   - Verify HTML output has correct URLs
   - Verify menu activation still works

2. **Template rendering** (5 tests)
   - Render templates with permalink
   - Render templates with old filter (compat)
   - Mixed usage (some permalink, some filter)
   - URL comparisons work correctly
   - Navigation functions work in templates

### Manual Testing Checklist

- [ ] Local dev server (no baseurl)
- [ ] GitHub Pages simulation (`baseurl="/repo"`)
- [ ] Vercel/Netlify simulation (no baseurl)
- [ ] Custom subpath (`baseurl="/blog"`)
- [ ] Offline file system (`baseurl="file:///..."`)
- [ ] Menu activation works in all scenarios
- [ ] Breadcrumbs work in all scenarios
- [ ] Validators don't break
- [ ] Health checks pass

---

## Migration Path

### For Theme Developers

**Immediate (Optional)**:
```jinja2
{# Replace verbose filter usage #}
- <a href="{{ page.url | absolute_url }}">{{ page.title }}</a>
+ <a href="{{ page.permalink }}">{{ page.title }}</a>
```

**Gradual**:
- Update templates one file at a time
- Test in local dev and staging
- Both patterns work simultaneously

**Backward Compatibility**:
- All existing templates continue working
- No breaking changes
- Filter remains supported indefinitely

### For Bengal Core

**Timeline**: 4 weeks (see Implementation Plan above)

**Rollout Strategy**:
1. Week 1: Core properties (non-breaking)
2. Week 2: Navigation functions (non-breaking)
3. Week 3: Update default theme (optional example)
4. Week 4: Documentation and guides

**Version**: Target for v0.2.0 (minor version bump)

---

## Alternatives Considered

### Alternative 1: Shorter Filter Name

```jinja2
{# Current #}
<a href="{{ page.url | absolute_url }}">Link</a>

{# Alternative #}
<a href="{{ page.url | url }}">Link</a>
```

**Pros**: Less verbose  
**Cons**: Still requires manual application, easy to forget  
**Decision**: Implement as alias alongside `.permalink`

### Alternative 2: Context-Aware URL Function

```jinja2
<a href="{{ url(page) }}">Link</a>
```

**Pros**: Clean function interface  
**Cons**: Magic behavior, harder to understand  
**Decision**: Rejected - prefer explicit properties

### Alternative 3: Auto-Processing Templates

Automatically transform href attributes at render time.

**Pros**: Zero template changes needed  
**Cons**: Magic, performance overhead, hard to debug  
**Decision**: Rejected - too much magic

### Alternative 4: url_with_baseurl() Method

```python
page.url_with_baseurl()  # Method call
```

**Pros**: Explicit  
**Cons**: More verbose than property, less Pythonic  
**Decision**: Rejected - properties more idiomatic

---

## Open Questions

1. **Should we extract `_apply_baseurl` to a shared utility module?**
   - Pro: DRY, reusable across codebase
   - Con: Adds module, may be overkill for simple function
   - **Recommendation**: Extract if used in 3+ places

2. **Should we deprecate `| absolute_url` filter?**
   - Pro: Single way to do things
   - Con: Breaking change, no strong reason
   - **Recommendation**: Keep both, document `.permalink` as recommended

3. **Should navigation functions return only permalink (drop url field)?**
   - Pro: Simpler return structure
   - Con: Breaking change, removes comparison capability
   - **Recommendation**: Return both for flexibility

4. **Should we add `.relative_url` alias for clarity?**
   ```python
   page.url          # Current
   page.relative_url # Alias for clarity?
   page.permalink    # New
   ```
   - Pro: More explicit about what `.url` is
   - Con: Extra API surface, `.url` is already understood
   - **Recommendation**: Not needed, `.url` is clear enough

---

## Success Metrics

1. **Developer Experience**:
   - 35% reduction in template verbosity (measured by character count)
   - Fewer baseurl-related bug reports in GitHub issues
   - Positive community feedback

2. **Adoption**:
   - 80% of default theme templates use `.permalink` within 2 releases
   - Community themes start adopting pattern
   - Documentation views for URL handling guide

3. **Quality**:
   - Zero regressions in existing tests
   - New tests maintain 95%+ coverage
   - No performance degradation (cached properties)

4. **Support**:
   - Reduced support questions about baseurl
   - Fewer deployment-related issues
   - Clear migration path feedback

---

## References

- **Hugo's Approach**: https://gohugo.io/methods/page/permalink/
- **Jekyll's Approach**: `relative_url` filter
- **Current Code**:
  - `bengal/core/page/metadata.py:56-122` (Page.url)
  - `bengal/core/section.py:243-274` (Section.url)
  - `bengal/rendering/template_engine.py:299-369` (_url_for, _with_baseurl)
  - `bengal/rendering/template_functions/urls.py` (absolute_url filter)
- **Related RFCs**:
  - `url-strategy-downstream-impact.md` - Identity vs Display pattern
  - `url-ergonomics-analysis.md` - Developer experience analysis

---

## Approval

**Status**: Draft - Awaiting Review

**Reviewers**:
- [ ] Core Team Lead
- [ ] Template System Owner  
- [ ] Documentation Team
- [ ] Community Representative

**Sign-off Required**: All reviewers must approve before implementation begins.

---

## Appendix A: Complete Code Diff

### Page.permalink Property

```python
# File: bengal/core/page/metadata.py
# Location: After url property (line 122)

@cached_property
def permalink(self) -> str:
    """
    Get the display URL with baseurl applied (cached after first access).

    [Full docstring from Detailed Design section]
    """
    if not self._site:
        return self.url

    baseurl = self._site.config.get("baseurl", "") or ""
    return self._apply_baseurl(self.url, baseurl)

def _apply_baseurl(self, path: str, baseurl: str) -> str:
    """Apply baseurl to a path."""
    if not baseurl:
        return path

    if not path.startswith("/"):
        path = "/" + path

    baseurl = baseurl.rstrip("/")

    if baseurl.startswith(("http://", "https://", "file://")):
        return f"{baseurl}{path}"

    base_path = "/" + baseurl.lstrip("/")
    return f"{base_path}{path}"
```

### Navigation Function Updates

```python
# File: bengal/rendering/template_functions/navigation.py
# Function: get_breadcrumbs (line 29)

def get_breadcrumbs(page: "Page") -> list[dict[str, Any]]:
    """Get breadcrumb items for a page."""
    # ... existing logic ...

    for i, ancestor in enumerate(reversed_ancestors):
        url = ancestor.url if hasattr(ancestor, "url") else f"/{getattr(ancestor, 'slug', '')}/"

        # NEW: Get permalink if available
        permalink = ancestor.permalink if hasattr(ancestor, "permalink") else url

        items.append({
            "title": getattr(ancestor, "title", "Untitled"),
            "url": url,  # Identity URL
            "permalink": permalink,  # Display URL (NEW)
            "is_current": is_current_item,
        })

    if not is_section_index:
        page_url = page.url if hasattr(page, "url") else f"/{page.slug}/"
        page_permalink = page.permalink if hasattr(page, "permalink") else page_url  # NEW

        items.append({
            "title": getattr(page, "title", "Untitled"),
            "url": page_url,
            "permalink": page_permalink,  # NEW
            "is_current": True
        })

    return items
```

### Template Updates

```jinja2
{# File: bengal/themes/default/templates/partials/navigation-components.html #}
{# Line 49 #}

{# BEFORE #}
<a href="{{ item.url | absolute_url }}">{{ item.title }}</a>

{# AFTER #}
<a href="{{ item.permalink }}">{{ item.title }}</a>
```

---

## Appendix B: Full Test Suite

See implementation plan Phase 1-3 for complete test listings.

**Total New Tests**: 25
- Unit tests: 15
- Integration tests: 10
- Manual test scenarios: 6

**Coverage Target**: 95%+ on new code
**Performance Target**: No measurable impact (<1ms per property access)

---

**End of RFC**
