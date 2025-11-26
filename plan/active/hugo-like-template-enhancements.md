# Hugo-like Template Function Enhancements

**Status**: Planning  
**Priority**: High  
**Created**: 2025-01-XX

## Overview

Bengal already has a solid foundation of template functions, but adding Hugo-like enhancements will enable more advanced template patterns and make Bengal more familiar to Hugo users. This document outlines the missing pieces and implementation plan.

## Current State

Bengal already has:
- ✅ `where` (with nested attribute support - just added!)
- ✅ `where_not`
- ✅ `group_by`
- ✅ `sort_by`
- ✅ `limit` / `offset`
- ✅ `uniq`
- ✅ `flatten`
- ✅ `chunk`
- ✅ `shuffle` / `sample`
- ✅ `get_page`
- ✅ `resolve_pages`

## Missing Hugo-like Functions

### 1. Collection Operations (High Priority)

#### `first` / `last`
Get first or last item from a list.

**Hugo**:
```go
{{ $first := (where site.Pages ".Params.featured" true) | first }}
{{ $last := $posts | last }}
```

**Bengal**:
```jinja
{% set first = site.pages | where('metadata.featured', true) | first %}
{% set last = posts | last %}
```

**Use Cases**:
- Getting featured post
- Getting latest post
- Getting first track page

**Implementation**: Simple - `items[0]` and `items[-1]` with safety checks

---

#### `where` with Operators
Support comparison operators like Hugo's `.Where`.

**Hugo**:
```go
{{ $recent := where site.Pages ".Date" ">" (now.AddDate -1 0 0) }}
{{ $published := where site.Pages ".Params.status" "eq" "published" }}
{{ $tags := where site.Pages ".Params.tags" "in" (slice "python" "web") }}
```

**Bengal** (proposed):
```jinja
{% set recent = site.pages | where('date', '>', one_year_ago) %}
{% set published = site.pages | where('metadata.status', 'eq', 'published') %}
{% set python_posts = site.pages | where('tags', 'in', ['python', 'web']) %}
```

**Operators to support**:
- `eq` / `==` - equals (current behavior)
- `ne` / `!=` - not equals
- `gt` / `>` - greater than
- `gte` / `>=` - greater than or equal
- `lt` / `<` - less than
- `lte` / `<=` - less than or equal
- `in` - value in list
- `not in` - value not in list

**Implementation**: Enhance `where` function to accept optional operator parameter

---

#### `complement` / `intersect` / `union`
Set operations for combining page collections.

**Hugo**:
```go
{{ $all := $posts | union $pages }}
{{ $common := $posts | intersect $pages }}
{{ $only_posts := $posts | complement $pages }}
```

**Bengal** (proposed):
```jinja
{% set all = posts | union(pages) %}
{% set common = posts | intersect(pages) %}
{% set only_posts = posts | complement(pages) %}
```

**Use Cases**:
- Combining different page types
- Finding pages in multiple categories
- Excluding certain pages

**Implementation**: Use sets for O(1) lookups, handle Page objects (hashable by source_path)

---

#### `reverse`
Reverse a list.

**Hugo**:
```go
{{ $reversed := $posts | reverse }}
```

**Bengal** (proposed):
```jinja
{% set reversed = posts | reverse %}
```

**Use Cases**:
- Displaying items in reverse chronological order
- Creating "previous/next" navigation

**Implementation**: `items[::-1]` or `list(reversed(items))`

---

### 2. Enhanced `where` with Nested Attributes

✅ **Already implemented!** We just added support for `'metadata.track_id'` style nested access.

**Next step**: Extend to support nested arrays/lists:
```jinja
{% set python_posts = site.pages | where('tags', 'contains', 'python') %}
```

---

### 3. Page Query Functions

#### Enhanced `get_page` with Multiple Strategies
Currently `get_page` supports path/slug lookup. Could add:
- `get_page_by_id` - Find by frontmatter ID
- `get_pages_by_tag` - Find all pages with tag
- `get_pages_by_section` - Find all pages in section

**Hugo**:
```go
{{ $page := site.GetPage "/posts/my-post" }}
{{ $section := site.GetPage "/posts" }}
{{ $pages := $section.Pages }}
```

**Bengal** (current):
```jinja
{% set page = get_page('posts/my-post') %}
{% set section_pages = site.pages | where('_section_path', section_path) %}
```

**Enhancement**: Add convenience functions for common patterns

---

### 4. String Functions (Medium Priority)

#### `humanize`
Convert strings to human-readable form.

**Hugo**:
```go
{{ "my-post-title" | humanize }}  // "My Post Title"
```

**Bengal** (proposed):
```jinja
{{ "my-post-title" | humanize }}  // "My Post Title"
```

**Implementation**: Title case, replace hyphens/underscores with spaces

---

#### `singularize` / `pluralize`
Handle singular/plural forms.

**Hugo**:
```go
{{ "posts" | singularize }}  // "post"
{{ "post" | pluralize }}    // "posts"
```

**Bengal** (proposed):
```jinja
{{ "posts" | singularize }}  // "post"
{{ "post" | pluralize }}     // "posts"
```

**Implementation**: Use `inflect` library or simple rules

---

### 5. Date Functions (Low Priority)

Bengal already has `dateformat`. Could add:
- `time` - Parse time strings
- `duration` - Format durations
- `ago` - Relative time ("2 days ago")

---

## Implementation Priority

### Phase 1: High-Impact, Low-Effort (Do First)
1. ✅ `where` with nested attributes - **DONE**
2. `first` / `last` - **~30 min**
3. `reverse` - **~15 min**
4. `where` with operators - **~2 hours**

### Phase 2: High-Impact, Medium-Effort
5. `complement` / `intersect` / `union` - **~1 hour**
6. Enhanced `where` for array contains - **~1 hour**

### Phase 3: Medium-Impact, Low-Effort
7. `humanize` - **~30 min**
8. `singularize` / `pluralize` - **~1 hour**

### Phase 4: Nice-to-Have
9. Enhanced `get_page` variants - **~2 hours**
10. Date enhancements - **~2 hours**

---

## Implementation Notes

### `where` with Operators

**Current signature**:
```python
def where(items: list, key: str, value: Any) -> list:
```

**Proposed signature**:
```python
def where(items: list, key: str, value: Any = None, operator: str = 'eq') -> list:
```

**Usage**:
```jinja
{# Current (still works) #}
{% set posts = site.pages | where('type', 'post') %}

{# New operator syntax #}
{% set recent = site.pages | where('date', '>', one_year_ago) %}
{% set python = site.pages | where('tags', 'in', ['python']) %}
```

**Implementation**:
```python
OPERATORS = {
    'eq': lambda a, b: a == b,
    'ne': lambda a, b: a != b,
    'gt': lambda a, b: a > b,
    'gte': lambda a, b: a >= b,
    'lt': lambda a, b: a < b,
    'lte': lambda a, b: a <= b,
    'in': lambda a, b: a in b if isinstance(b, (list, tuple, set)) else False,
    'not in': lambda a, b: a not in b if isinstance(b, (list, tuple, set)) else True,
}
```

### Set Operations

**Implementation**:
```python
def union(items1: list, items2: list) -> list:
    """Combine two lists, removing duplicates."""
    # Use source_path for Page objects, direct comparison for others
    seen = set()
    result = []

    for item in items1 + items2:
        key = _get_key(item)  # source_path for Page, item itself for hashable
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result
```

---

## Testing Strategy

1. **Unit tests** for each new function
2. **Template examples** in documentation
3. **Integration tests** with real site data
4. **Performance tests** for large page collections

---

## Documentation

Update:
- `docs/reference/template-functions.md` - Add new functions
- `docs/guides/hugo-migration.md` - Show Hugo → Bengal mappings
- Template examples in theme templates

---

## Success Criteria

✅ Users can write Hugo-like template patterns  
✅ Common page filtering/querying patterns work  
✅ Performance remains good with large page collections  
✅ Functions are intuitive and well-documented  

---

## Related

- [Hugo Template Functions](https://gohugo.io/functions/)
- Current implementation: `bengal/rendering/template_functions/collections.py`
- Enhancement PR: (to be created)
