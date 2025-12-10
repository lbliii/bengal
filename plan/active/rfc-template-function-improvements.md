# RFC: Template Function Improvements

**Status**: Draft  
**Created**: 2025-12-10  
**Author**: AI Assistant  
**Subsystems**: rendering/template_functions, core/page, core/section

---

## Problem Statement

Bengal's template system provides 80+ functions and filters for themers, but audit reveals several gaps that force complex workarounds:

1. **No direct section access** - Themers cannot query sections by path
2. **No sequential navigation helpers** - `next_page`/`prev_page` requires manual sibling filtering
3. **No word count filter** - Common theming need (word count vs reading time)
4. **No page existence check** - Conditional links require loading full pages
5. **Complex breadcrumb logic** - 200+ line function with edge cases scattered across template function

These gaps create friction for theme development and result in verbose, error-prone templates.

---

## Goals

1. Add 5-6 high-value template functions addressing identified gaps
2. Maintain backward compatibility with existing templates
3. Keep function implementations focused (<100 lines each)
4. Provide comprehensive docstrings with usage examples
5. Add unit tests for all new functions

## Non-Goals

- Major refactoring of existing functions (separate RFC)
- Breaking changes to current API
- Performance optimization (existing caching patterns sufficient)
- Template syntax changes

---

## Evidence

### Gap 1: No `get_section(path)` function

**Current workaround** (verbose, fragile):
```jinja2
{# Must iterate all sections to find one #}
{% set target_section = none %}
{% for section in site.sections %}
  {% if section.name == 'docs' %}
    {% set target_section = section %}
  {% endif %}
{% endfor %}
{% if target_section %}
  {% for page in target_section.pages %}...{% endfor %}
{% endif %}
```

**Proposed API**:
```jinja2
{% set docs = get_section('docs') %}
{% for page in docs.pages %}...{% endfor %}
```

**Evidence**: `bengal/rendering/template_functions/get_page.py:154-258` shows similar pattern for pages.

### Gap 2: No sequential navigation

**Current workaround**:
```jinja2
{# Complex sibling iteration #}
{% set siblings = page.siblings | sort(attribute='weight') %}
{% set current_idx = none %}
{% for i, sib in enumerate(siblings) %}
  {% if sib == page %}{% set current_idx = i %}{% endif %}
{% endfor %}
{% if current_idx and current_idx > 0 %}
  {% set prev = siblings[current_idx - 1] %}
{% endif %}
```

**Proposed API**:
```jinja2
{% set prev = prev_page(page) %}
{% set next = next_page(page) %}
{# or via Page model #}
{{ page.prev_in_section.title }}
{{ page.next_in_section.title }}
```

**Evidence**: Hugo/Jekyll both provide `.Next` and `.Prev` on pages.

### Gap 3: No word count

**Evidence**: `bengal/rendering/template_functions/strings.py:394-422` has `reading_time` but no `word_count`.

```python
# reading_time calculates words internally but doesn't expose count
words = len(clean_text.split())
minutes = words / wpm
```

### Gap 4: No page existence check

**Current workaround**:
```jinja2
{# Must load page to check existence #}
{% set page = get_page('guides/advanced') %}
{% if page %}
  <a href="{{ page.url }}">{{ page.title }}</a>
{% endif %}
```

**Problem**: Loads and parses full page just for existence check.

**Proposed API**:
```jinja2
{% if page_exists('guides/advanced') %}
  <a href="/guides/advanced/">Advanced Guide</a>
{% endif %}
```

---

## Design Options

### Option A: Template Functions Only (Recommended)

Add new functions to `bengal/rendering/template_functions/`:

| Function | Module | Type |
|----------|--------|------|
| `get_section(path)` | `navigation.py` | Global |
| `prev_page(page)` | `navigation.py` | Global |
| `next_page(page)` | `navigation.py` | Global |
| `page_exists(path)` | `get_page.py` | Global |
| `word_count` | `strings.py` | Filter |
| `section_pages(path)` | `navigation.py` | Global |

**Pros**:
- Minimal code changes
- Clear separation of concerns
- Easy to test in isolation

**Cons**:
- prev/next may need site context in closure

### Option B: Page Model Extensions

Add properties to `Page` class:

```python
class Page:
    @property
    def prev_in_section(self) -> Page | None:
        """Previous page in section by weight."""
        ...
    
    @property  
    def next_in_section(self) -> Page | None:
        """Next page in section by weight."""
        ...
```

**Pros**:
- Cleaner template syntax: `{{ page.prev_in_section.title }}`
- Consistent with existing model (ancestors, siblings)

**Cons**:
- Requires Page to have section context
- May complicate caching

### Option C: Hybrid (Page + Functions)

Add `prev_in_section`/`next_in_section` to Page model, other gaps via functions.

**Pros**: Best of both options

**Cons**: Mixed approaches

---

## Recommended Approach: Option C (Hybrid)

### Phase 1: Template Functions (Week 1)

1. **`get_section(path)`** in `navigation.py`
2. **`page_exists(path)`** in `get_page.py`
3. **`word_count`** filter in `strings.py`
4. **`section_pages(path)`** in `navigation.py`

### Phase 2: Page Model Extensions (Week 2)

1. **`page.prev_in_section`** property
2. **`page.next_in_section`** property

---

## Detailed Design

### 1. `get_section(path)` Function

**Location**: `bengal/rendering/template_functions/navigation.py`

```python
def get_section(path: str) -> Section | None:
    """
    Get a section by its path or name.

    Args:
        path: Section path (e.g., 'docs', 'blog/tutorials')

    Returns:
        Section object if found, None otherwise

    Example:
        {% set docs = get_section('docs') %}
        {% for page in docs.pages | sort_by('weight') %}
          <a href="{{ page.url }}">{{ page.title }}</a>
        {% endfor %}
    """
    if not path:
        return None
    
    # Normalize path
    normalized = path.strip('/').replace('\\', '/')
    
    # Try direct lookup via site registry
    section = site.get_section_by_name(normalized)
    if section:
        return section
    
    # Try path-based lookup
    content_path = site.root_path / 'content' / normalized
    return site.get_section_by_path(content_path)
```

### 2. `page_exists(path)` Function

**Location**: `bengal/rendering/template_functions/get_page.py`

```python
def page_exists(path: str) -> bool:
    """
    Check if a page exists without loading it.

    Uses cached page lookup maps for O(1) existence check.

    Args:
        path: Page path (e.g., 'guides/setup.md' or 'guides/setup')

    Returns:
        True if page exists

    Example:
        {% if page_exists('guides/advanced') %}
          <a href="/guides/advanced/">Advanced Guide</a>
        {% endif %}
    """
    if not path:
        return False
    
    # Reuse existing lookup maps (already built by get_page)
    if site._page_lookup_maps is None:
        # Build maps lazily (same logic as get_page)
        _build_lookup_maps(site)
    
    maps = site._page_lookup_maps
    normalized = path.replace('\\', '/')
    
    # Check all lookup strategies
    if normalized in maps['relative']:
        return True
    if f"{normalized}.md" in maps['relative']:
        return True
    if normalized.startswith('content/'):
        stripped = normalized[8:]
        if stripped in maps['relative'] or f"{stripped}.md" in maps['relative']:
            return True
    
    return False
```

### 3. `word_count` Filter

**Location**: `bengal/rendering/template_functions/strings.py`

```python
def word_count(text: str) -> int:
    """
    Count words in text.

    Strips HTML tags before counting.

    Args:
        text: Text to count (can contain HTML)

    Returns:
        Number of words

    Example:
        {{ page.content | word_count }} words
        # Output: 1234 words
    """
    if not text:
        return 0
    
    # Strip HTML if present
    clean_text = strip_html(text)
    
    # Count words
    return len(clean_text.split())
```

### 4. `section_pages(path)` Function

**Location**: `bengal/rendering/template_functions/navigation.py`

```python
def section_pages(path: str, recursive: bool = False) -> list[Page]:
    """
    Get pages in a section.

    Args:
        path: Section path (e.g., 'docs', 'blog')
        recursive: Include pages from subsections (default: False)

    Returns:
        List of pages in section (empty if section not found)

    Example:
        {% for page in section_pages('docs') | sort_by('weight') %}
          <a href="{{ page.url }}">{{ page.title }}</a>
        {% endfor %}

        {# Recursive to include subsection pages #}
        {% for page in section_pages('docs', recursive=true) %}
    """
    section = get_section(path)
    if not section:
        return []
    
    if recursive:
        return list(section.all_pages)
    return list(section.pages)
```

### 5. Page Model: `prev_in_section` / `next_in_section`

**Location**: `bengal/core/page/navigation.py`

```python
class PageNavigationMixin:
    @property
    def prev_in_section(self) -> Page | None:
        """
        Previous page in the same section (by weight, then date, then title).

        Returns:
            Previous Page or None if this is the first page

        Example:
            {% if page.prev_in_section %}
              <a href="{{ page.prev_in_section.url }}">← Previous</a>
            {% endif %}
        """
        section = self._section
        if not section:
            return None
        
        # Get sorted siblings
        siblings = sorted(
            section.regular_pages,
            key=lambda p: (p.weight or 999, p.date or datetime.min, p.title or '')
        )
        
        try:
            idx = siblings.index(self)
            if idx > 0:
                return siblings[idx - 1]
        except ValueError:
            pass
        
        return None

    @property
    def next_in_section(self) -> Page | None:
        """
        Next page in the same section (by weight, then date, then title).

        Returns:
            Next Page or None if this is the last page

        Example:
            {% if page.next_in_section %}
              <a href="{{ page.next_in_section.url }}">Next →</a>
            {% endif %}
        """
        section = self._section
        if not section:
            return None
        
        siblings = sorted(
            section.regular_pages,
            key=lambda p: (p.weight or 999, p.date or datetime.min, p.title or '')
        )
        
        try:
            idx = siblings.index(self)
            if idx < len(siblings) - 1:
                return siblings[idx + 1]
        except ValueError:
            pass
        
        return None
```

---

## Architecture Impact

### Subsystem Changes

| Subsystem | Change | Risk |
|-----------|--------|------|
| `rendering/template_functions/` | Add 4 functions | Low |
| `core/page/navigation.py` | Add 2 properties | Low |
| `core/site.py` | Add `get_section_by_name()` | Low |

### No Impact To

- Cache system (no new cacheable fields)
- Orchestration (no build changes)
- CLI (no new commands)
- Existing templates (backward compatible)

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_template_functions_navigation.py

def test_get_section_by_name(site_factory):
    """get_section returns section by name."""
    site = site_factory('test-basic')
    section = get_section('docs', site)
    assert section is not None
    assert section.name == 'docs'

def test_get_section_not_found(site_factory):
    """get_section returns None for missing section."""
    site = site_factory('test-basic')
    assert get_section('nonexistent', site) is None

def test_page_exists_true(site_factory):
    """page_exists returns True for existing page."""
    site = site_factory('test-basic')
    assert page_exists('docs/getting-started.md', site) is True
    assert page_exists('docs/getting-started', site) is True  # Without .md

def test_page_exists_false(site_factory):
    """page_exists returns False for missing page."""
    site = site_factory('test-basic')
    assert page_exists('nonexistent', site) is False

def test_word_count():
    """word_count counts words correctly."""
    assert word_count('Hello world') == 2
    assert word_count('<p>Hello <b>world</b></p>') == 2  # Strips HTML
    assert word_count('') == 0

def test_prev_next_in_section(site_factory):
    """prev/next_in_section navigate within section."""
    site = site_factory('test-basic')
    # Assuming docs has page1, page2, page3 by weight
    page2 = get_page('docs/page2.md', site)
    assert page2.prev_in_section.slug == 'page1'
    assert page2.next_in_section.slug == 'page3'
```

### Integration Tests

```python
# tests/integration/test_template_navigation.py

def test_section_pages_in_template(site_factory, template_env):
    """section_pages works in templates."""
    site = site_factory('test-basic')
    template = template_env.from_string('''
        {% for page in section_pages('docs') %}{{ page.title }},{% endfor %}
    ''')
    result = template.render(site=site)
    assert 'Getting Started' in result
```

---

## Migration Guide

No migration needed - all changes are additive. Existing templates continue to work unchanged.

### Optional Upgrades

Themers can optionally simplify existing patterns:

**Before**:
```jinja2
{% set siblings = page.siblings | sort(attribute='weight') %}
{% for sib in siblings %}
  {% if loop.index < loop.length and siblings[loop.index] == page %}
    {% set next = siblings[loop.index + 1] %}
  {% endif %}
{% endfor %}
```

**After**:
```jinja2
{% set next = page.next_in_section %}
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance regression from prev/next computation | Low | Medium | Lazy computation via @property; cache if needed |
| Section lookup collision with similar names | Low | Low | Use path-based lookup as primary; name as fallback |
| Breaking existing sibling patterns | None | N/A | Additive only; no changes to existing behavior |

---

## Timeline

| Phase | Tasks | Duration |
|-------|-------|----------|
| **Phase 1** | Template functions (4 functions) | 1 day |
| **Phase 2** | Page model extensions (2 properties) | 0.5 day |
| **Phase 3** | Tests | 0.5 day |
| **Phase 4** | Documentation | 0.5 day |
| **Total** | | 2.5 days |

---

## Open Questions

1. **Should `section_pages()` default to recursive?** - Hugo does, Jekyll doesn't
2. **Sort order for prev/next** - Weight → Date → Title, or configurable?
3. **Should `get_section()` support nested paths?** - e.g., `blog/tutorials`

---

## Appendix: Current Template Function Inventory

<details>
<summary>Click to expand full inventory (80+ functions)</summary>

### Globals (27)
- Navigation: `get_breadcrumbs`, `get_toc_grouped`, `get_pagination_items`, `get_nav_tree`, `get_auto_nav`, `combine_track_toc`
- Content: `get_page`, `get_data`, `related_posts`, `popular_tags`
- URLs: `tag_url`, `canonical_url`, `og_image`, `ensure_trailing_slash`, `asset_url`
- Images: `image_url`, `image_dimensions`, `image_srcset_gen`, `image_data_uri`
- Icons: `icon`, `render_icon`
- i18n: `t`, `current_lang`, `languages`, `alternate_links`, `locale_date`
- Menus: `get_menu`, `get_menu_lang`

### Filters (55+)
- Strings: `truncatewords`, `truncatewords_html`, `slugify`, `markdownify`, `strip_html`, `truncate_chars`, `replace_regex`, `pluralize`, `reading_time`, `excerpt`, `strip_whitespace`, `first_sentence`, `filesize`, `nl2br`, `smartquotes`, `emojify`
- Collections: `where`, `where_not`, `group_by`, `sort_by`, `limit`, `offset`, `uniq`, `flatten`, `first`, `last`, `reverse`, `union`, `intersect`, `complement`, `resolve_pages`, `sample`, `shuffle`, `chunk`
- Dates: `time_ago`, `date_iso`, `date_rfc822`
- URLs: `absolute_url`, `url`, `url_encode`, `url_decode`
- Data: `jsonify`, `merge`, `has_key`, `get_nested`, `keys`, `values`, `items`, `get`
- SEO: `meta_description`, `meta_keywords`
- HTML: `safe_html`, `html_escape`, `html_unescape`, `extract_content`
- Images: `image_srcset`, `image_alt`
- Taxonomies: `has_tag`

### Tests (6)
- `draft`, `featured`, `outdated`, `translated`, `section`, `match`

</details>

---

## References

- `bengal/rendering/template_functions/__init__.py` - Function registry
- `bengal/rendering/template_functions/navigation.py:42-236` - Breadcrumb implementation
- `bengal/rendering/template_functions/get_page.py:154-258` - Page lookup pattern
- `bengal/core/page/__init__.py` - Page model
- Hugo template functions: https://gohugo.io/functions/
- Jekyll Liquid filters: https://jekyllrb.com/docs/liquid/filters/

