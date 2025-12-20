# RFC: Version-Aware Section Methods

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-20  
**Subsystem**: Core (bengal/core/section.py)  
**Confidence**: 92% 🟢

---

## Executive Summary

Move version-filtering logic from Jinja2 templates into Python methods on the `Section` class. This eliminates ~60 lines of complex template code, improves maintainability, and provides a cleaner API for version-aware navigation.

---

## Problem Statement

The `docs-nav.html` template contains significant inline version-filtering logic that is:

1. **Complex and repetitive** - The same filtering pattern appears 3+ times
2. **Hard to test** - Template logic is difficult to unit test
3. **Verbose** - Requires `{% break %}` extension and nested loops
4. **Fragile** - Easy to introduce bugs when modifying

### Evidence: Current Template Complexity

```67:73:bengal/themes/default/templates/partials/docs-nav.html
{% for p in subsection.sorted_pages %}
  {% if p.version == current_version_id %}
    {% set has_versioned_content = true %}
    {% break %}
  {% endif %}
{% endfor %}
```

This pattern repeats at lines 67-73, 155-161, and similar filtering at lines 57-58, 148-167, 176-177.

**Total**: 13 occurrences of `current_version_id` checks across the template.

---

## Goals

1. **Simplify templates** - Replace inline loops with method calls
2. **Improve testability** - Move logic to Python where it can be unit tested
3. **Maintain performance** - Use caching for repeated access
4. **Preserve API compatibility** - Existing `sorted_pages`/`sorted_subsections` unchanged

### Non-Goals

- Changing how versions are stored on pages
- Modifying the versioning configuration system
- Adding version-aware behavior to autodoc sections (separate scope)

---

## Design Options

### Option A: Instance Methods with Version Parameter (Recommended)

Add version-filtering methods to `Section` that accept a version ID parameter:

```python
@dataclass
class Section:
    # Existing fields...

    def pages_for_version(self, version_id: str | None) -> list[Page]:
        """
        Get pages matching the specified version.

        Args:
            version_id: Version to filter by, or None to return all pages

        Returns:
            Sorted list of pages matching the version
        """
        if version_id is None:
            return self.sorted_pages
        return [p for p in self.sorted_pages if getattr(p, 'version', None) == version_id]

    def subsections_for_version(self, version_id: str | None) -> list[Section]:
        """
        Get subsections that have content for the specified version.

        A subsection is included if:
        - Its index page matches the version, OR
        - It contains any pages matching the version

        Args:
            version_id: Version to filter by, or None to return all subsections

        Returns:
            Sorted list of subsections with content for the version
        """
        if version_id is None:
            return self.sorted_subsections

        result = []
        for subsection in self.sorted_subsections:
            if subsection.has_content_for_version(version_id):
                result.append(subsection)
        return result

    def has_content_for_version(self, version_id: str | None) -> bool:
        """
        Check if this section has any content for the specified version.

        Args:
            version_id: Version to check, or None (always returns True)

        Returns:
            True if section has matching index page or any matching pages
        """
        if version_id is None:
            return True

        # Check index page first
        if self.index_page and getattr(self.index_page, 'version', None) == version_id:
            return True

        # Check any regular page
        return any(
            getattr(p, 'version', None) == version_id
            for p in self.sorted_pages
        )
```

**Template simplification**:

```jinja
{# Before (lines 57-82): ~25 lines of complex logic #}
{% if current_version_id and site.versioning_enabled %}
  {% set sorted_pages = root_section.sorted_pages | selectattr('version', 'equalto', current_version_id) | list %}
  {% set filtered_subsections = [] %}
  {% for subsection in root_section.sorted_subsections %}
    {% set has_versioned_content = false %}
    {% if subsection.index_page and subsection.index_page.version == current_version_id %}
      {% set has_versioned_content = true %}
    {% else %}
      {% for p in subsection.sorted_pages %}
        {% if p.version == current_version_id %}
          {% set has_versioned_content = true %}
          {% break %}
        {% endif %}
      {% endfor %}
    {% endif %}
    {% if has_versioned_content %}
      {% set _ = filtered_subsections.append(subsection) %}
    {% endif %}
  {% endfor %}
  {% set sorted_subsections = filtered_subsections %}
{% else %}
  {% set sorted_pages = root_section.sorted_pages %}
  {% set sorted_subsections = root_section.sorted_subsections %}
{% endif %}

{# After: 2 lines #}
{% set version_id = current_version_id if site.versioning_enabled else none %}
{% set sorted_pages = root_section.pages_for_version(version_id) %}
{% set sorted_subsections = root_section.subsections_for_version(version_id) %}
```

**Pros**:
- Clean, simple API
- Easy to understand and use
- Backward compatible (existing properties unchanged)
- Testable in isolation
- Natural extension of existing `sorted_pages`/`sorted_subsections`

**Cons**:
- No caching (recomputes on each call)
- Slight overhead for repeated calls in same template render

---

### Option B: Cached Version-Aware Properties with Context

Use a thread-local or request-scoped context to cache version-filtered results:

```python
@dataclass
class Section:
    _version_cache: dict[str, list[Page]] = field(default_factory=dict, repr=False)

    def pages_for_version(self, version_id: str | None) -> list[Page]:
        if version_id is None:
            return self.sorted_pages

        cache_key = f"pages_{version_id}"
        if cache_key not in self._version_cache:
            self._version_cache[cache_key] = [
                p for p in self.sorted_pages
                if getattr(p, 'version', None) == version_id
            ]
        return self._version_cache[cache_key]
```

**Pros**:
- O(1) repeated access within same render
- Same clean API as Option A

**Cons**:
- More complex implementation
- Cache invalidation concerns
- Memory overhead for storing filtered lists
- Over-engineering for current use case

---

### Option C: Jinja2 Filter Extension

Add custom Jinja2 filters instead of methods:

```python
# In bengal/rendering/template_engine/filters.py
def filter_pages_by_version(pages, version_id):
    if version_id is None:
        return pages
    return [p for p in pages if getattr(p, 'version', None) == version_id]

def filter_subsections_by_version(subsections, version_id):
    if version_id is None:
        return subsections
    return [s for s in subsections if s.has_content_for_version(version_id)]
```

**Template usage**:
```jinja
{% set sorted_pages = root_section.sorted_pages | filter_by_version(current_version_id) %}
```

**Pros**:
- Follows Jinja2 patterns
- Could apply to any list of pages

**Cons**:
- Less discoverable (not on Section object)
- Requires `has_content_for_version` method anyway
- Filter syntax is slightly less readable than method call
- Harder to unit test in isolation

---

## Recommended Approach: Option A

**Rationale**:
1. **Simplicity** - Direct methods are easiest to understand and use
2. **Discoverability** - IDE autocomplete shows methods on Section
3. **Testability** - Pure Python methods are trivial to unit test
4. **Sufficient performance** - Filtering a few dozen pages is fast enough
5. **Future extensibility** - Can add caching later if needed (Option B)

---

## Architecture Impact

### Files Modified

| File | Change | Risk |
|------|--------|------|
| `bengal/core/section.py` | Add 3 methods (~40 lines) | Low |
| `bengal/themes/default/templates/partials/docs-nav.html` | Simplify filtering (~-50 lines) | Medium |

### Dependencies

- No new dependencies
- No changes to Page model
- No changes to versioning configuration

### Backward Compatibility

- **100% backward compatible** - Existing `sorted_pages` and `sorted_subsections` properties unchanged
- Templates can migrate incrementally
- No API breaking changes

---

## Implementation Plan

### Phase 1: Add Methods (30 min)

1. Add `pages_for_version(version_id)` method to Section
2. Add `subsections_for_version(version_id)` method to Section
3. Add `has_content_for_version(version_id)` method to Section
4. Add unit tests for all three methods

### Phase 2: Simplify Template (20 min)

1. Update `docs-nav.html` to use new methods
2. Remove `{% break %}` dependency (loopcontrols extension can remain)
3. Verify build works with versioned test site

### Phase 3: Cleanup (10 min)

1. Remove commented-out old logic
2. Update any other templates using version filtering
3. Document new methods in Section docstring

---

## Test Strategy

### Unit Tests

```python
# tests/unit/test_section_versioning.py

def test_pages_for_version_returns_matching_pages():
    """pages_for_version filters to matching version only."""
    section = Section(name="docs")
    section.add_page(make_page(version="v1"))
    section.add_page(make_page(version="v2"))
    section.add_page(make_page(version="v1"))

    v1_pages = section.pages_for_version("v1")

    assert len(v1_pages) == 2
    assert all(p.version == "v1" for p in v1_pages)

def test_pages_for_version_none_returns_all():
    """pages_for_version(None) returns all sorted pages."""
    section = Section(name="docs")
    section.add_page(make_page(version="v1"))
    section.add_page(make_page(version="v2"))

    all_pages = section.pages_for_version(None)

    assert len(all_pages) == 2
    assert all_pages == section.sorted_pages

def test_subsections_for_version_filters_by_content():
    """subsections_for_version includes only sections with matching content."""
    parent = Section(name="parent")

    child_v1 = Section(name="child_v1")
    child_v1.add_page(make_page(version="v1"))

    child_v2 = Section(name="child_v2")
    child_v2.add_page(make_page(version="v2"))

    parent.add_subsection(child_v1)
    parent.add_subsection(child_v2)

    v1_subsections = parent.subsections_for_version("v1")

    assert len(v1_subsections) == 1
    assert v1_subsections[0].name == "child_v1"

def test_has_content_for_version_checks_index_page():
    """has_content_for_version returns True if index page matches version."""
    section = Section(name="docs")
    section.index_page = make_page(version="v1")

    assert section.has_content_for_version("v1") is True
    assert section.has_content_for_version("v2") is False

def test_has_content_for_version_checks_regular_pages():
    """has_content_for_version checks regular pages if no matching index."""
    section = Section(name="docs")
    section.add_page(make_page(version="v2"))

    assert section.has_content_for_version("v2") is True
    assert section.has_content_for_version("v1") is False
```

### Integration Test

Verify versioned site builds correctly with new methods by running:
```bash
uv run bengal build --dir site
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template regression | Medium | High | Thorough testing with versioned content |
| Performance degradation | Low | Low | Methods are O(n) where n is small |
| Edge case in version matching | Low | Medium | Unit tests cover edge cases |

---

## Success Criteria

- [ ] `docs-nav.html` reduced by ~50 lines
- [ ] All 3 methods have unit tests
- [ ] Versioned site builds without errors
- [ ] No regression in non-versioned sites

---

## Open Questions

1. **Should we cache version-filtered results?**
   - Current recommendation: No, premature optimization
   - Can add caching in Phase 2 if profiling shows need

2. **Should virtual sections support versioning?**
   - Current scope: Physical sections only
   - Autodoc sections don't currently have versions
   - Can extend later if needed

---

## References

- Current template: `bengal/themes/default/templates/partials/docs-nav.html:57-82`
- Section class: `bengal/core/section.py:48-781`
- Versioning config: Site configuration (`site.versioning_enabled`)
