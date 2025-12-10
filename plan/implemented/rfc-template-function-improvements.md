# RFC: Template Function Convenience Wrappers

**Status**: Implemented  
**Created**: 2025-12-10  
**Revised**: 2025-12-10 (v2)  
**Author**: AI Assistant  
**Subsystems**: rendering/template_functions  
**Confidence**: 92% 🟢

---

## Background

This RFC was revised after research revealed that some originally proposed features already exist. Specifically:

| Originally Proposed | Actual Status | Documentation |
|---------------------|---------------|---------------|
| `prev_in_section` / `next_in_section` | ✅ Already exists | `site/content/docs/reference/theme-variables.md:106-135` |
| `site.get_section_by_path()` | ✅ Already exists (site method) | Internal only |
| Page lookup maps | ✅ Already exists (internal) | Not exposed |
| Word count logic | ✅ Exists inside `reading_time` | Not exposed |

**Key Finding**: Bengal has more functionality than initially apparent. The gaps are not missing features but rather **missing convenience wrappers** for existing internal functionality.

---

## Problem Statement

Bengal's template system provides 80+ functions and filters, with robust internal infrastructure. However, audit reveals **three convenience gaps** where existing functionality is not exposed to templates:

1. **Section lookup requires verbose syntax** - `site.get_section_by_path()` exists but no simple `get_section('docs')` template global
2. **Word count hidden inside reading_time** - Internal logic calculates words but doesn't expose the count
3. **Page existence check requires full load** - `get_page()` triggers parsing; no lightweight existence check

These gaps create friction for theme development and result in verbose templates.

---

## Goals

1. Expose 4 convenience functions wrapping existing functionality
2. Maintain backward compatibility with existing templates
3. Keep implementations focused (<30 lines each, mostly delegation)
4. Provide comprehensive docstrings with usage examples
5. Add unit tests for all new functions

## Non-Goals

- Adding new core functionality (these are wrappers)
- Breaking changes to current API
- Performance optimization (existing patterns are sufficient)
- Template syntax changes
- Page model extensions (navigation already exists - see below)

---

## Already Implemented (No Changes Needed)

These features already exist and are documented:

| Feature | Location | Documentation |
|---------|----------|---------------|
| `page.prev_in_section` | `core/page/navigation.py:122-157` | `docs/reference/theme-variables.md:106-107` |
| `page.next_in_section` | `core/page/navigation.py:84-119` | `docs/reference/theme-variables.md:106-107` |
| `page.prev` / `page.next` | `core/page/navigation.py:31-81` | `docs/reference/theme-variables.md` |
| `page.ancestors` | `core/page/navigation.py:175-194` | `docs/reference/theme-variables.md:105` |

**Usage examples from existing documentation:**

```jinja2
{# From docs/reference/theme-variables.md:126-135 #}
<nav class="prev-next">
  {% if page.prev_in_section %}
    <a href="{{ page.prev_in_section.url }}">← {{ page.prev_in_section.title }}</a>
  {% endif %}
  {% if page.next_in_section %}
    <a href="{{ page.next_in_section.url }}">{{ page.next_in_section.title }} →</a>
  {% endif %}
</nav>
```

---

## Evidence for Proposed Functions

### Gap 1: No `get_section()` template global

**Internal capability**: `site.get_section_by_path()` at `core/site/section_registry.py:82-130`

**Current template syntax** (verbose):
```jinja2
{% set docs = site.get_section_by_path('docs') %}
```

**Proposed syntax** (cleaner):
```jinja2
{% set docs = get_section('docs') %}
```

**Verification**: Searched codebase - no existing `get_section` template function registered in `navigation.py:30-39`.

### Gap 2: No `word_count` filter

**Internal capability**: `strings.py:415-416` calculates words inside `reading_time`:

```python
clean_text = strip_html(text)
words = len(clean_text.split())  # <-- This logic exists but not exposed
```

**Current workaround**: None - must use `reading_time` and back-calculate.

**Proposed syntax**:
```jinja2
{{ page.content | word_count }} words
```

**Verification**: Checked `strings.py:28-45` filter registration - no `word_count` filter.

### Gap 3: No `page_exists()` function

**Internal capability**: `get_page.py:191-216` builds lookup maps stored on `site._page_lookup_maps`.

**Current template syntax** (loads full page):
```jinja2
{% set target = get_page('guides/advanced') %}
{% if target %}...{% endif %}
```

**Problem**: Triggers `_ensure_page_parsed()` at line 254 - unnecessary for existence check.

**Proposed syntax**:
```jinja2
{% if page_exists('guides/advanced') %}...{% endif %}
```

**Verification**: Checked `get_page.py` - no `page_exists` function registered.

---

## Design

### Approach: Thin Wrappers

Add convenience wrappers to existing template function modules:

| Function | Module | Implementation |
|----------|--------|----------------|
| `get_section(path)` | `navigation.py` | Delegates to `site.get_section_by_path()` |
| `section_pages(path)` | `navigation.py` | Combines `get_section()` + `.pages` access |
| `page_exists(path)` | `get_page.py` | Uses existing lookup maps without parsing |
| `word_count` | `strings.py` | Extracts logic from `reading_time` |

**Total new code**: ~80 lines (mostly docstrings)

---

## Implementation

### 1. `get_section(path)` - Add to `navigation.py`

```python
def get_section(path: str) -> Section | None:
    """
    Get a section by its path.

    Convenience wrapper around site.get_section_by_path() with
    path normalization.

    Args:
        path: Section path (e.g., 'docs', 'blog/tutorials')

    Returns:
        Section object if found, None otherwise

    Example:
        {% set docs = get_section('docs') %}
        {% if docs %}
          {% for page in docs.pages | sort_by('weight') %}
            <a href="{{ page.url }}">{{ page.title }}</a>
          {% endfor %}
        {% endif %}
    """
    if not path:
        return None
    normalized = path.strip('/').replace('\\', '/')
    return site.get_section_by_path(normalized)
```

**Registration** (add to `navigation.py:30-39`):
```python
env.globals["get_section"] = lambda path: get_section_with_site(path)
```

### 2. `section_pages(path)` - Add to `navigation.py`

```python
def section_pages(path: str, recursive: bool = False) -> list[Page]:
    """
    Get pages in a section.

    Convenience function combining get_section() with pages access.

    Args:
        path: Section path (e.g., 'docs', 'blog')
        recursive: Include pages from subsections (default: False)

    Returns:
        List of pages (empty if section not found)

    Example:
        {% for page in section_pages('docs') | sort_by('weight') %}
          <a href="{{ page.url }}">{{ page.title }}</a>
        {% endfor %}
    """
    section = get_section(path)
    if not section:
        return []
    return list(section.all_pages) if recursive else list(section.pages)
```

### 3. `page_exists(path)` - Add to `get_page.py`

```python
def page_exists(path: str) -> bool:
    """
    Check if a page exists without loading it.

    Uses cached lookup maps for O(1) existence check.
    More efficient than get_page() when you only need existence.

    Args:
        path: Page path (e.g., 'guides/setup.md' or 'guides/setup')

    Returns:
        True if page exists, False otherwise

    Example:
        {% if page_exists('guides/advanced') %}
          <a href="/guides/advanced/">Advanced Guide</a>
        {% endif %}
    """
    if not path:
        return False
    
    if site._page_lookup_maps is None:
        _build_lookup_maps(site)
    
    maps = site._page_lookup_maps
    normalized = path.replace('\\', '/')
    
    if normalized in maps['relative']:
        return True
    if f"{normalized}.md" in maps['relative']:
        return True
    if normalized.startswith('content/'):
        stripped = normalized[8:]
        return stripped in maps['relative'] or f"{stripped}.md" in maps['relative']
    return False
```

### 4. `word_count` Filter - Add to `strings.py`

```python
def word_count(text: str) -> int:
    """
    Count words in text.

    Strips HTML tags before counting. Uses same logic as reading_time.

    Args:
        text: Text to count (can contain HTML)

    Returns:
        Number of words

    Example:
        {{ page.content | word_count }} words
        {{ page.content | word_count }} words ({{ page.content | reading_time }} min read)
    """
    if not text:
        return 0
    clean_text = strip_html(text)
    return len(clean_text.split())
```

**Registration** (add to `strings.py:28-45`):
```python
"word_count": word_count,
```

---

## Architecture Impact

| Subsystem | Change | Risk |
|-----------|--------|------|
| `rendering/template_functions/navigation.py` | +2 functions (~30 lines) | Low |
| `rendering/template_functions/get_page.py` | +1 function (~20 lines) | Low |
| `rendering/template_functions/strings.py` | +1 filter (~10 lines) | Low |

**No impact to**: Cache, Core models, Orchestration, CLI, Existing templates

---

## Testing Strategy

```python
# tests/unit/template_functions/test_navigation_convenience.py

class TestGetSection:
    def test_returns_section_by_path(self, site_factory):
        site = site_factory('test-basic')
        section = get_section('docs', site)
        assert section is not None
        assert section.name == 'docs'

    def test_returns_none_for_missing(self, site_factory):
        site = site_factory('test-basic')
        assert get_section('nonexistent', site) is None

    def test_normalizes_path(self, site_factory):
        site = site_factory('test-basic')
        assert get_section('/docs/', site) is not None


class TestSectionPages:
    def test_returns_pages(self, site_factory):
        site = site_factory('test-basic')
        pages = section_pages('docs', site)
        assert len(pages) > 0

    def test_empty_for_missing_section(self, site_factory):
        site = site_factory('test-basic')
        assert section_pages('nonexistent', site) == []


# tests/unit/template_functions/test_page_exists.py

class TestPageExists:
    def test_true_for_existing(self, site_factory):
        site = site_factory('test-basic')
        assert page_exists('docs/getting-started.md', site) is True

    def test_true_without_extension(self, site_factory):
        site = site_factory('test-basic')
        assert page_exists('docs/getting-started', site) is True

    def test_false_for_missing(self, site_factory):
        site = site_factory('test-basic')
        assert page_exists('nonexistent', site) is False


# tests/unit/template_functions/test_word_count.py

class TestWordCount:
    def test_counts_plain_text(self):
        assert word_count('Hello world') == 2

    def test_strips_html(self):
        assert word_count('<p>Hello <b>world</b></p>') == 2

    def test_empty_returns_zero(self):
        assert word_count('') == 0
        assert word_count(None) == 0
```

---

## Timeline

| Phase | Tasks | Duration |
|-------|-------|----------|
| Implementation | 4 functions (~80 lines) | 0.5 day |
| Tests | Unit tests | 0.25 day |
| Documentation | Update template-functions.md | 0.25 day |
| **Total** | | **1 day** |

---

## Open Questions

1. **Should `section_pages()` default to recursive?** 
   - Hugo: Yes
   - Jekyll: No
   - Proposed: Default to `False` for predictability and performance

---

## References

### Verified Existing Functionality
- `site/content/docs/reference/theme-variables.md:100-135` - Navigation properties documentation
- `bengal/core/page/navigation.py:84-157` - `prev_in_section`/`next_in_section` implementation
- `bengal/core/site/section_registry.py:82-130` - `get_section_by_path()` implementation

### Implementation Targets
- `bengal/rendering/template_functions/navigation.py:30-39` - Registration for globals
- `bengal/rendering/template_functions/get_page.py:191-216` - Lookup maps
- `bengal/rendering/template_functions/strings.py:394-422` - `reading_time` word counting logic

### Documentation to Update
- `site/content/docs/reference/template-functions.md` - Add new functions
- `site/content/docs/reference/theme-variables.md` - Add `get_section()`, `section_pages()`
