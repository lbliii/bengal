# RFC: Theme Developer Ergonomic Methods

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-20  
**Subsystem**: Core (Site, Section, Page), Autodoc  
**Confidence**: 88% 🟢

---

## Executive Summary

Add ergonomic helper methods to core models (`Site`, `Section`, `Page`) to simplify common template patterns. Analysis of 52+ template usages shows repeated verbose `selectattr`/`rejectattr` chains that could be replaced with intuitive method calls.

**Goal**: Make Bengal templates more readable and reduce boilerplate for theme developers.

---

## Problem Statement

Theme developers frequently write verbose Jinja2 filter chains for common operations:

### Evidence: Common Verbose Patterns

**Pattern 1: Section Lookup** (5+ occurrences)
```jinja
{# Current: 3 lines, error-prone #}
{% set candidates = site.sections | selectattr('name', 'equalto', 'blog') | list %}
{% if candidates %}
  {% set blog_section = candidates[0] %}
{% endif %}
```
Files: `home.html`, `blog/home.html`, `doc/home.html`, `autodoc/*/home.html`

**Pattern 2: Recent Pages** (10+ occurrences)
```jinja
{# Current: verbose, repeated pattern #}
{% set recent = section.pages | selectattr('date') | sort_by('date', reverse=true) | limit(6) %}
```
Files: `home.html`, `blog/home.html`, `blog/list.html`

**Pattern 3: Content Pages** (5+ occurrences)
```jinja
{# Current: complex exclusion logic #}
{% set content_pages = section.regular_pages | rejectattr('relative_url', 'equalto', index_url) | list %}
```
Files: `tutorial/list.html`, `blog/list.html`, `page-hero/section.html`

**Pattern 4: Section-Filtered Posts** (8+ occurrences)
```jinja
{# Current: repeated in archive templates #}
{% set posts = posts | selectattr('_section.name', 'equalto', section_filter) | list %}
```
Files: `archive-year.html`, `author.html`, `author/single.html`, `archive-sidebar.html`

**Pattern 5: Autodoc Element Filtering** (20+ occurrences)
```jinja
{# Current: repeated for every element type #}
{% set methods = element.children | selectattr('element_type', 'eq', 'method') | list %}
{% set functions = element.children | selectattr('element_type', 'eq', 'function') | list %}
{% set classes = element.children | selectattr('element_type', 'eq', 'class') | list %}
{% set public = members | rejectattr('name', 'match', '^_') | list %}
```
Files: All autodoc templates (`partials/header.html`, `module.html`, `partials/members.html`, etc.)

---

## Goals

1. **Reduce template verbosity** - Replace multi-line filter chains with method calls
2. **Improve readability** - Self-documenting method names
3. **Reduce errors** - Type-safe methods with clear semantics
4. **Maintain compatibility** - Existing templates continue working

### Non-Goals

- Changing core data models structure
- Breaking existing template syntax
- Adding methods that only one template uses

---

## Design: Proposed Methods

### Tier 1: High Priority (implement first)

#### 1.1 `Site.get_section_by_name(name: str) -> Section | None`

**Replaces**:
```jinja
{% set candidates = site.sections | selectattr('name', 'equalto', 'blog') | list %}
{% set blog = candidates[0] if candidates else none %}
```

**Becomes**:
```jinja
{% set blog = site.get_section_by_name('blog') %}
```

**Implementation**:
```python
# bengal/core/site/site.py
def get_section_by_name(self, name: str) -> Section | None:
    """
    Get a section by its name.

    Args:
        name: Section name to find (e.g., 'blog', 'docs', 'api')

    Returns:
        Section if found, None otherwise

    Example:
        {% set blog = site.get_section_by_name('blog') %}
        {% if blog %}
          {{ blog.title }} has {{ blog.pages | length }} posts
        {% endif %}
    """
    for section in self.sections:
        if section.name == name:
            return section
    return None
```

**Complexity**: Low  
**Impact**: 5+ templates simplified

---

#### 1.2 `Section.recent_pages(limit: int = 10) -> list[Page]`

**Replaces**:
```jinja
{% set recent = section.pages | selectattr('date') | sort_by('date', reverse=true) | limit(6) %}
```

**Becomes**:
```jinja
{% set recent = section.recent_pages(6) %}
```

**Implementation**:
```python
# bengal/core/section.py
def recent_pages(self, limit: int = 10) -> list[Page]:
    """
    Get most recent pages by date.

    Returns pages that have a date, sorted newest first.
    Pages without dates are excluded.

    Args:
        limit: Maximum number of pages to return (default: 10)

    Returns:
        List of pages sorted by date descending

    Example:
        {% for post in section.recent_pages(5) %}
          <article>{{ post.title }} - {{ post.date }}</article>
        {% endfor %}
    """
    dated_pages = [p for p in self.sorted_pages if getattr(p, 'date', None)]
    dated_pages.sort(key=lambda p: p.date, reverse=True)
    return dated_pages[:limit]
```

**Complexity**: Low  
**Impact**: 10+ templates simplified

---

#### 1.3 `Section.content_pages` property

**Replaces**:
```jinja
{% set index_url = section.index_page.relative_url if section.index_page else '' %}
{% set content_pages = section.regular_pages | rejectattr('relative_url', 'equalto', index_url) | list %}
```

**Becomes**:
```jinja
{% set content_pages = section.content_pages %}
```

**Implementation**:
```python
# bengal/core/section.py
@cached_property
def content_pages(self) -> list[Page]:
    """
    Get content pages (regular pages excluding index).

    This is useful for listing a section's pages without
    including the section's own index page in the list.

    Returns:
        Sorted list of pages, excluding the section's index page

    Example:
        {% for page in section.content_pages %}
          <a href="{{ page.url }}">{{ page.title }}</a>
        {% endfor %}
    """
    index_url = self.index_page.relative_url if self.index_page else None
    return [p for p in self.sorted_pages if p.relative_url != index_url]
```

**Complexity**: Low  
**Impact**: 5+ templates simplified

---

### Tier 2: Medium Priority

#### 2.1 `Site.pages_by_section(section_name: str) -> list[Page]`

**Replaces**:
```jinja
{% set posts = posts | selectattr('_section.name', 'equalto', section_filter) | list %}
```

**Becomes**:
```jinja
{% set posts = site.pages_by_section('blog') %}
```

**Implementation**:
```python
# bengal/core/site/site.py
def pages_by_section(self, section_name: str) -> list[Page]:
    """
    Get all pages belonging to a section by name.

    Args:
        section_name: Section name to filter by

    Returns:
        List of pages in that section
    """
    return [
        p for p in self.pages
        if getattr(p, '_section', None) and p._section.name == section_name
    ]
```

**Complexity**: Low  
**Impact**: 8+ templates simplified

---

#### 2.2 `Section.pages_with_tag(tag: str) -> list[Page]`

**Replaces**:
```jinja
{% set tagged = section.pages | selectattr('tags', 'contains', 'python') | list %}
```

**Becomes**:
```jinja
{% set tagged = section.pages_with_tag('python') %}
```

**Implementation**:
```python
# bengal/core/section.py
def pages_with_tag(self, tag: str) -> list[Page]:
    """
    Get pages containing a specific tag.

    Args:
        tag: Tag to filter by (case-insensitive)

    Returns:
        Sorted list of pages with the tag
    """
    tag_lower = tag.lower()
    return [
        p for p in self.sorted_pages
        if tag_lower in [t.lower() for t in getattr(p, 'tags', [])]
    ]
```

**Complexity**: Low  
**Impact**: Moderate (tags pages, taxonomy)

---

### Tier 3: Autodoc-Specific Methods

#### 3.1 `children_by_type(element_type: str) -> list`

**Replaces**:
```jinja
{% set methods = element.children | selectattr('element_type', 'eq', 'method') | list %}
{% set functions = element.children | selectattr('element_type', 'eq', 'function') | list %}
{% set classes = element.children | selectattr('element_type', 'eq', 'class') | list %}
```

**Becomes**:
```jinja
{% set methods = element.children_by_type('method') %}
{% set functions = element.children_by_type('function') %}
{% set classes = element.children_by_type('class') %}
```

**Implementation** (on autodoc element metadata):
```python
def children_by_type(self, element_type: str) -> list:
    """
    Filter children by element_type.

    Args:
        element_type: Type to filter (method, function, class, attribute, etc.)

    Returns:
        List of children matching the type
    """
    children = getattr(self, 'children', []) or []
    return [c for c in children if getattr(c, 'element_type', None) == element_type]
```

**Complexity**: Medium (needs to be added to autodoc metadata)  
**Impact**: 20+ autodoc templates simplified

---

#### 3.2 `public_members` and `private_members` properties

**Replaces**:
```jinja
{% set public = members | rejectattr('name', 'match', '^_') | list %}
{% set private = members | selectattr('name', 'match', '^_') | list %}
```

**Becomes**:
```jinja
{% set public = element.public_members %}
{% set private = element.private_members %}
```

**Implementation**:
```python
@property
def public_members(self) -> list:
    """Members not starting with underscore."""
    members = getattr(self, 'children', []) or []
    return [m for m in members if not getattr(m, 'name', '').startswith('_')]

@property
def private_members(self) -> list:
    """Members starting with underscore (internal)."""
    members = getattr(self, 'children', []) or []
    return [m for m in members if getattr(m, 'name', '').startswith('_')]
```

**Complexity**: Medium  
**Impact**: 10+ autodoc templates simplified

---

## Implementation Plan

### Phase 1: Core Methods (1 hour)

1. Add `Site.get_section_by_name()`
2. Add `Section.recent_pages()`
3. Add `Section.content_pages`
4. Add unit tests for all three

### Phase 2: Medium Priority (30 min)

1. Add `Site.pages_by_section()`
2. Add `Section.pages_with_tag()`
3. Add unit tests

### Phase 3: Autodoc Methods (1 hour)

1. Add `children_by_type()` to autodoc metadata
2. Add `public_members`/`private_members` properties
3. Update autodoc templates to use new methods
4. Add unit tests

### Phase 4: Template Migration (optional)

1. Update templates to use new methods
2. Keep old patterns working (no breaking changes)
3. Add deprecation warnings to verbose patterns (future)

---

## Template Migration Examples

### Before/After Comparison

**home.html**:
```jinja
{# Before #}
{% set blog_section_name = page.metadata.get('blog_section', 'blog') %}
{% set blog_section_candidates = site.sections | selectattr('name', 'equalto', blog_section_name) | list %}
{% set blog_section = blog_section_candidates[0] if blog_section_candidates else none %}
{% if blog_section and blog_section.pages %}
  {% set recent = blog_section.pages | selectattr('date') | sort_by('date', reverse=true) | limit(3) %}
{% endif %}

{# After #}
{% set blog_section = site.get_section_by_name(page.metadata.get('blog_section', 'blog')) %}
{% if blog_section %}
  {% set recent = blog_section.recent_pages(3) %}
{% endif %}
```

**Lines reduced**: 6 → 4 (33% reduction)  
**Clarity improved**: Significantly more readable

---

**autodoc/partials/header.html**:
```jinja
{# Before #}
{% set children = getattr(element, 'children', []) %}
{% set options = children | selectattr('element_type', 'eq', 'option') | list %}
{% set arguments = children | selectattr('element_type', 'eq', 'argument') | list %}
{% set methods = children | selectattr('element_type', 'eq', 'method') | list %}
{% set functions = children | selectattr('element_type', 'eq', 'function') | list %}
{% set classes = children | selectattr('element_type', 'eq', 'class') | list %}
{% set attributes = children | selectattr('element_type', 'eq', 'attribute') | list %}

{# After #}
{% set options = element.children_by_type('option') %}
{% set arguments = element.children_by_type('argument') %}
{% set methods = element.children_by_type('method') %}
{% set functions = element.children_by_type('function') %}
{% set classes = element.children_by_type('class') %}
{% set attributes = element.children_by_type('attribute') %}
```

**Lines reduced**: 7 → 6  
**Clarity improved**: No `getattr` wrapper needed, cleaner API

---

## Architecture Impact

### Files Modified

| File | Change | Risk |
|------|--------|------|
| `bengal/core/site/site.py` | Add 2 methods | Low |
| `bengal/core/section.py` | Add 3 methods/properties | Low |
| `bengal/autodoc/models.py` | Add 3 methods/properties | Medium |

### Dependencies

- No new dependencies
- No breaking changes
- Fully backward compatible

---

## Test Strategy

### Unit Tests

```python
# tests/unit/core/test_site_helpers.py
class TestGetSectionByName:
    def test_returns_section_when_found(self):
        ...
    def test_returns_none_when_not_found(self):
        ...
    def test_finds_nested_section(self):
        ...

# tests/unit/core/test_section_helpers.py
class TestRecentPages:
    def test_returns_pages_sorted_by_date_desc(self):
        ...
    def test_excludes_pages_without_date(self):
        ...
    def test_respects_limit(self):
        ...
    def test_returns_empty_for_no_dated_pages(self):
        ...

class TestContentPages:
    def test_excludes_index_page(self):
        ...
    def test_returns_all_when_no_index(self):
        ...
    def test_maintains_weight_order(self):
        ...
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Method naming confusion | Low | Low | Follow existing naming patterns |
| Performance regression | Low | Low | Use cached_property where appropriate |
| Autodoc integration issues | Medium | Medium | Thorough testing with existing autodoc sites |

---

## Success Criteria

- [ ] Tier 1 methods implemented with tests
- [ ] At least 50% of verbose patterns replaceable
- [ ] No breaking changes to existing templates
- [ ] Documentation updated with examples

---

## Open Questions

1. **Should we add version-aware variants of new methods?**
   - `recent_pages_for_version(limit, version_id)`
   - Decision: Can add later if needed

2. **Should autodoc methods go on Page metadata or separate class?**
   - Recommendation: Add to existing autodoc metadata structure
   - Keeps autodoc-specific logic separate from core

3. **Should we deprecate verbose patterns in templates?**
   - Recommendation: Not initially; let both coexist
   - Future: Add optional linting for verbose patterns

---

## Related

- RFC: Version-Aware Section Methods (implemented)
- `bengal/core/section.py`: Existing Section class
- `bengal/core/site/site.py`: Existing Site class
- Template grep results: 52+ usages of selectattr/rejectattr
