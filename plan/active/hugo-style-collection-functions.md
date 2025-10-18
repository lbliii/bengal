# Hugo-Style Collection Functions Feature Plan

**Status:** Draft  
**Created:** 2025-10-18  
**Type:** Feature Enhancement  
**Complexity:** Medium  
**Priority:** High (User Experience Impact)

---

## Executive Summary

This plan proposes adding Hugo-style dynamic collection query functions to Bengal's template system. While Bengal has basic filtering (`where`, `group_by`), it lacks Hugo's powerful collection operations like `intersect`, `union`, `complement`, and advanced filtering with operators. These functions enable dynamic relationship building in templates without requiring centralized relationship tables (like DITA reltables).

**Goal:** Enable users to build complex page relationships and queries directly in templates using frontmatter data, similar to Hugo's collection functions.

---

## Current State Analysis

### What Bengal Has (bengal/rendering/template_functions/)

#### collections.py (8 functions)
```python
where(items, key, value)           # Exact equality match
where_not(items, key, value)       # Exact inequality match
group_by(items, key)               # Group by field
sort_by(items, key, reverse)       # Sort by field
limit(items, count)                # Take first N
offset(items, count)               # Skip first N
uniq(items)                        # Remove duplicates
flatten(items)                     # Flatten nested lists
```

#### advanced_collections.py (3 functions)
```python
sample(items, count, seed)         # Random sample
shuffle(items, seed)               # Randomize order
chunk(items, size)                 # Split into chunks
```

#### taxonomies.py (4 functions)
```python
related_posts(page, limit)         # Pre-computed related posts
popular_tags(limit)                # Tag frequency
tag_url(tag)                       # Tag URL generation
has_tag(page, tag)                 # Tag membership check
```

### Limitations

1. **No comparison operators** - Only exact equality (`==`)
2. **No set operations** - Can't intersect, union, or complement collections
3. **No nested property access** - Can't query `page.metadata.author.name`
4. **No complex conditions** - Can't combine multiple filters efficiently
5. **Limited relationship building** - Relies on pre-computed `related_posts`

---

## What Hugo Offers

From [Hugo's collections functions](https://gohugo.io/functions/collections/), key capabilities:

### Set Operations
```go-html-template
{{ $common := intersect $set1 $set2 }}        # Intersection
{{ $all := union $set1 $set2 }}               # Union
{{ $diff := complement $set1 $set2 }}         # Difference
{{ $symdiff := collections.SymDiff $set1 $set2 }}  # Symmetric difference
```

### Advanced Filtering
```go-html-template
{{ $posts := where .Site.Pages ".Params.tags" "intersect" (slice "api" "docs") }}
{{ $recent := where .Site.Pages "Date" "gt" (now.AddDate 0 -1 0) }}
{{ $featured := where .Site.Pages ".Params.featured" "eq" true }}
```

**Operators:** `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `in`, `not in`, `intersect`

### Advanced Collection Manipulation
```go-html-template
{{ $grouped := .Site.Pages | group "Date.Year" }}
{{ $indexed := collections.Index $data "key1" "key2" }}  # Deep access
{{ $merged := merge $map1 $map2 }}
{{ $isSet := isset .Params "author" }}
```

### Dynamic Queries
```go-html-template
{{/* Find all pages by same author */}}
{{ $sameAuthor := where site.Pages ".Params.author" "eq" .Params.author }}

{{/* Find pages sharing any tags */}}
{{ $relatedByTags := where site.Pages ".Params.tags" "intersect" .Params.tags }}

{{/* Find pages in date range */}}
{{ $thisMonth := where site.Pages "Date" "ge" $monthStart }}
{{ $thisMonth = where $thisMonth "Date" "lt" $monthEnd }}
```

---

## Gap Analysis

### Critical Missing Features

| Feature | Bengal | Hugo | Priority |
|---------|--------|------|----------|
| Comparison operators | ❌ | ✅ | **High** |
| Set operations (intersect, union) | ❌ | ✅ | **High** |
| Nested property access | ❌ | ✅ | **Medium** |
| Multi-level filtering | ⚠️ (manual chain) | ✅ | **Medium** |
| Dynamic grouping | ✅ (basic) | ✅ (advanced) | **Low** |
| Type checking (isset) | ❌ | ✅ | **Low** |

### Real-World Use Cases We Can't Do

```jinja2
{# WANT: Find pages by same author #}
{% set same_author = site.pages | where('metadata.author', 'eq', page.author) %}

{# WANT: Find pages sharing any tags #}
{% set related = site.pages | where('tags', 'intersect', page.tags) %}

{# WANT: Find recent posts (last 30 days) #}
{% set recent = site.pages | where('date', 'gt', thirty_days_ago) %}

{# WANT: Find pages NOT in a set #}
{% set others = site.pages | complement(featured_pages) %}

{# WANT: Combine multiple conditions #}
{% set filtered = site.pages
   | where('section', 'eq', 'blog')
   | where('draft', 'eq', false)
   | where('date', 'gt', last_year) %}
```

---

## Implementation Options

### Option 1: Extend Existing `where` Function (Incremental)

**Approach:** Add operator parameter to existing `where` filter

```python
def where(items, key, operator='eq', value=None):
    """
    Filter items with operator support.

    Operators: eq, ne, lt, le, gt, ge, in, not_in, intersect

    Examples:
        {{ posts | where('date', 'gt', cutoff_date) }}
        {{ posts | where('tags', 'intersect', ['api', 'docs']) }}
    """
    # Implementation
```

**Pros:**
- Backward compatible (operator defaults to 'eq')
- Minimal API surface change
- Familiar pattern for existing users

**Cons:**
- Three-argument calls get awkward: `where('key', 'eq', 'value')`
- Doesn't match Hugo's syntax exactly
- Harder to discover operators

**Effort:** Small (1-2 days)

---

### Option 2: New Module `query_collections.py` (Clean Slate)

**Approach:** Create dedicated query module with Hugo-like syntax

```python
# bengal/rendering/template_functions/query_collections.py

def where_eq(items, key, value): ...
def where_ne(items, key, value): ...
def where_gt(items, key, value): ...
def where_lt(items, key, value): ...
def where_in(items, key, values): ...
def where_intersect(items, key, values): ...

def intersect(set1, set2): ...
def union(set1, set2): ...
def complement(set1, set2): ...
def symdiff(set1, set2): ...
```

**Usage:**
```jinja2
{% set recent = site.pages | where_gt('date', cutoff) %}
{% set tagged = site.pages | where_intersect('tags', page.tags) %}
{% set common = featured_pages | intersect(recommended_pages) %}
```

**Pros:**
- Clean, explicit function names
- Easy to understand and document
- No backward compatibility concerns
- Follows existing Bengal pattern (separate modules)

**Cons:**
- More functions to maintain
- Slightly verbose
- Not exactly Hugo-compatible

**Effort:** Medium (3-5 days)

---

### Option 3: Query Builder Pattern (Advanced)

**Approach:** Fluent API for complex queries

```python
# bengal/rendering/template_functions/query_builder.py

class QueryBuilder:
    def __init__(self, items):
        self.items = items

    def where(self, key, operator, value):
        # Filter and return new QueryBuilder
        return QueryBuilder(filtered_items)

    def intersect(self, other_items):
        # Set intersection
        return QueryBuilder(result)

    def all(self):
        return self.items

# Register as template global
def query(items):
    return QueryBuilder(items)
```

**Usage:**
```jinja2
{% set results = query(site.pages)
    .where('section', 'eq', 'blog')
    .where('draft', 'eq', false)
    .where('date', 'gt', cutoff)
    .all() %}
```

**Pros:**
- Most powerful and flexible
- Chainable operations
- Extensible for future features
- Type-safe with proper implementation

**Cons:**
- Most complex to implement
- Unfamiliar pattern for Jinja2 users
- Potential performance overhead
- May not work well with Jinja2's filter syntax

**Effort:** Large (7-10 days)

---

### Option 4: Hybrid Approach (Recommended)

**Approach:** Combine Options 1 & 2 for best of both worlds

#### Phase 1: Enhance Core Functions (collections.py)
```python
def where(items, key, value=None, operator='eq'):
    """
    Filter items with optional operator.

    Backward compatible:
        {{ posts | where('status', 'published') }}  # eq implied

    With operator:
        {{ posts | where('date', cutoff, operator='gt') }}
        {{ posts | where('tags', page.tags, operator='intersect') }}
    """
```

#### Phase 2: Add Set Operations (new: set_operations.py)
```python
def intersect(set1, set2): ...
def union(set1, set2): ...
def complement(set1, set2): ...
def symdiff(set1, set2): ...
```

#### Phase 3: Add Query Helpers (new: query_helpers.py)
```python
def where_contains(items, key, value): ...
def where_matches(items, key, pattern): ...
def nested_get(obj, key_path): ...  # For "metadata.author.name"
```

**Pros:**
- Incremental rollout
- Backward compatible
- Leverages existing patterns
- Can evolve based on feedback

**Cons:**
- Spreads functionality across modules
- Need clear documentation strategy

**Effort:** Medium (5-7 days across phases)

---

## Recommended Approach: Option 4 (Hybrid)

### Why This Is Best Long-Term

1. **Backward Compatibility:** Existing templates keep working
2. **Incremental Adoption:** Users can adopt new features gradually
3. **Familiar Patterns:** Follows Bengal's existing module structure
4. **Flexibility:** Can add query builder later if needed
5. **Low Risk:** Each phase can be tested independently

---

## Implementation Plan

### Phase 1: Enhanced Filtering (Week 1)

**Files to modify:**
- `bengal/rendering/template_functions/collections.py`

**New functions:**
```python
# Enhance existing
def where(items, key, value=None, operator='eq'): ...

# Add comparison helpers
def where_gt(items, key, value): ...
def where_lt(items, key, value): ...
def where_gte(items, key, value): ...
def where_lte(items, key, value): ...
def where_in(items, key, values): ...
def where_contains(items, key, value): ...
```

**Template usage:**
```jinja2
{% set recent = posts | where('date', cutoff, operator='gt') %}
{% set in_category = posts | where_in('category', ['tech', 'api']) %}
```

**Tests:** `tests/unit/rendering/template_functions/test_collections_enhanced.py`

### Phase 2: Set Operations (Week 2)

**New file:**
- `bengal/rendering/template_functions/set_operations.py`

**Functions:**
```python
def intersect(set1, set2): ...
def union(set1, set2): ...
def complement(set1, set2): ...
def symdiff(set1, set2): ...
```

**Template usage:**
```jinja2
{% set common_tags = page1.tags | intersect(page2.tags) %}
{% set all_pages = featured | union(recommended) %}
{% set not_featured = site.pages | complement(featured) %}
```

**Tests:** `tests/unit/rendering/template_functions/test_set_operations.py`

### Phase 3: Advanced Queries (Week 3)

**New file:**
- `bengal/rendering/template_functions/advanced_queries.py`

**Functions:**
```python
def where_intersect(items, key, values):
    """Find items where key field intersects with values."""

def where_regex(items, key, pattern):
    """Filter items where key matches regex pattern."""

def nested_get(obj, key_path):
    """Access nested properties: 'metadata.author.name'"""

def multi_where(items, conditions):
    """Apply multiple where conditions efficiently."""
```

**Template usage:**
```jinja2
{# Find pages sharing ANY tags #}
{% set related = site.pages | where_intersect('tags', page.tags) %}

{# Find pages by nested property #}
{% set by_author = site.pages | where('metadata.author.name', 'eq', page.author_name) %}

{# Complex multi-condition #}
{% set filtered = site.pages | multi_where({
    'section': {'op': 'eq', 'value': 'blog'},
    'draft': {'op': 'eq', 'value': false},
    'date': {'op': 'gt', 'value': last_year}
}) %}
```

**Tests:** `tests/unit/rendering/template_functions/test_advanced_queries.py`

---

## Integration Points

### 1. Template Engine Registration

**File:** `bengal/rendering/template_functions/__init__.py`

```python
from . import (
    # Existing
    advanced_collections,
    collections,
    # New
    set_operations,      # Phase 2
    advanced_queries,    # Phase 3
)

def register_all(env, site):
    # ...existing...
    collections.register(env, site)          # Enhanced in Phase 1
    advanced_collections.register(env, site)

    # New modules
    set_operations.register(env, site)       # Phase 2
    advanced_queries.register(env, site)     # Phase 3
```

### 2. Page Object Access

Current Page attributes available for querying:
```python
# Direct attributes
page.title: str
page.slug: str
page.url: str
page.date: datetime | None
page.draft: bool
page.tags: list[str]
page.lang: str | None
page.kind: str  # 'home', 'section', 'page'
page.is_home: bool
page.is_section: bool
page.is_page: bool

# Metadata (nested)
page.metadata: dict[str, Any]
page.metadata.get('author')
page.metadata.get('category')
page.metadata.get('featured')
# ... any custom frontmatter fields
```

Need to support both:
- Direct access: `page.date`
- Metadata access: `page.metadata['author']` or `metadata.author` (nested)

### 3. Site Object Access

```python
site.pages: list[Page]          # All pages
site.sections: list[Section]    # All sections
site.taxonomies: dict           # Tags, categories, etc.
```

---

## Performance Considerations ⚠️ CRITICAL

### The Brutal Truth

**Bengal already has performance issues at scale.** From actual profiling:

| Pages | Full Build | Page Equality Checks | Why This Matters |
|-------|-----------|---------------------|------------------|
| 400   | 3.3s      | 446,758 calls (0.092s) | Excessive O(n) iterations |
| 10,000| ~100s     | ~11M calls (~2.3s)     | Extrapolated from measurements |

**Real example:** `related_posts()` was O(n²) in templates and took **120 seconds** for 10K pages. We moved it to build-time pre-computation → **16 seconds**.

### Why This Feature Is Risky

Adding Hugo-style collection functions means **users can recreate O(n²) problems in templates:**

```jinja2
{# THIS IS A PERFORMANCE BOMB 💣 #}
{% for page in site.pages %}  {# Loop 1: n times #}
  {% set same_author = site.pages
     | where('metadata.author', page.author) %}  {# Loop 2: n times #}
  {# Total: n × n = O(n²) = 100M operations at 10K pages! #}
{% endfor %}
```

At 10K pages: **100,000,000 comparisons** = site won't build.

### Specific Concerns

#### 1. **Multiple Filter Chains = Multiple Passes**
```jinja2
{# Each filter is a full O(n) pass #}
{% set result = site.pages
   | where('section', 'blog')        # Pass 1: 10,000 checks
   | where_gt('date', cutoff)         # Pass 2: 2,000 checks  
   | where_not('draft', true)         # Pass 3: 1,500 checks
   | sort_by('date', reverse=true)   # Pass 4: 1,500 comparisons
   | limit(10) %}                     # Pass 5: slice operation

{# Total: 15,000+ operations for 10 results #}
```

**At template render time** (400ms per page × 10K pages = **1+ hour** just for this query).

#### 2. **Set Operations Are Expensive**
```jinja2
{# Intersection of two 10K arrays = 10K comparisons #}
{% set common = list1 | intersect(list2) %}

{# Union with deduplication = O(n) + O(n log n) #}
{% set all = list1 | union(list2) %}
```

#### 3. **Nested Property Access**
```python
# Direct attribute: ~0.1 µs
page.date

# Nested access: ~1-2 µs (10-20x slower)
get_nested(page, 'metadata.author.name')
```

At 10K pages: 10µs → 20ms per query.

### Real-World Performance Impact

#### Scenario 1: Blog with Author Pages
```jinja2
{# On each author page, find all posts by that author #}
{% set author_posts = site.pages
   | where('metadata.author', page.author) %}

{# 50 authors × 10K pages = 500K comparisons PER BUILD #}
```

**Without caching:** +5-10 seconds per build  
**With pre-computation:** < 0.1 seconds

#### Scenario 2: Related Posts by Tags
```jinja2
{# On each blog post, find posts sharing tags #}
{% set related = site.pages
   | where_intersect('tags', page.tags)
   | limit(5) %}

{# 5K blog posts × 10K pages = 50M tag comparisons #}
```

**Without caching:** Site won't build (minutes to hours)  
**With pre-computation:** Already solved (16s for 10K pages)

### Why Related Posts Was Pre-Computed

From `bengal/orchestration/related_posts.py`:

```python
"""
Builds related posts index during build phase for O(1) template access.

This moves expensive related posts computation from render-time (O(n²))
to build-time (O(n·t)), resulting in O(1) template access.
"""

# Before: O(n²) in templates = 120 seconds at 10K pages
# After: O(n·t) at build time = 16 seconds at 10K pages
```

**The same problem will happen with any collection queries in templates.**

### Optimization Strategies

#### 1. **Performance Budgets & Warnings**

Add runtime warnings when expensive operations detected:

```python
def where(items, key, value, operator='eq'):
    if len(items) > 1000:
        logger.warning(
            "collection_query_large",
            operation="where",
            size=len(items),
            advice="Consider pre-computing this query at build time"
        )
    # ... filter logic
```

#### 2. **Query Result Caching**

Cache queries within a single template render:

```python
# In template_engine.py
@lru_cache(maxsize=128)
def cached_where(items_hash, key, value, operator='eq'):
    return where(items, key, value, operator)
```

**Limitation:** Cache invalidation is hard; only cache immutable queries.

#### 3. **Lazy Evaluation (Future - Phase 4)**

Combine multiple filters into single pass:

```python
class LazyCollection:
    def __init__(self, items):
        self.items = items
        self.operations = []

    def where(self, key, value, operator='eq'):
        self.operations.append(('where', key, value, operator))
        return self  # Don't execute yet

    def __iter__(self):
        # Execute all operations in single pass
        result = self.items
        for op in self.operations:
            result = apply_operation(result, op)
        return iter(result)
```

**Benefit:** 3 filters = 1 pass instead of 3 passes

#### 4. **Pre-Computed Indexes (Future - Phase 5)**

Build indexes during build phase:

```python
# Pre-compute during build (like related_posts)
site._indexes = {
    'pages_by_section': defaultdict(list),      # section -> [pages]
    'pages_by_author': defaultdict(list),       # author -> [pages]
    'pages_by_tag': defaultdict(list),          # tag -> [pages]
    'pages_by_date_range': {},                  # (start, end) -> [pages]
}

# O(1) template access instead of O(n) filtering
{% set blog_posts = site.indexes.pages_by_section['blog'] %}
```

**Trade-off:** Memory vs speed (indexes ~10-20MB for 10K pages)

#### 5. **Smart Short-Circuits**

Optimize common patterns automatically:

```python
def where_intersect(items, key, values):
    """Special optimization for tag intersection."""
    if key == 'tags' and hasattr(site, '_indexes'):
        # Use pre-built tag index (O(1) per tag)
        result_sets = [site._indexes['pages_by_tag'][tag] for tag in values]
        return list(set.intersection(*result_sets))
    # Fallback to O(n) scan
    return [item for item in items if set(getattr(item, key, [])) & set(values)]
```

#### 6. **Document Best Practices**

```jinja2
{# ✅ GOOD: Filter narrow first #}
{% set blog_posts = site.pages | where('section', 'blog') %}  {# 2000 → 500 #}
{% set recent = blog_posts | where_gt('date', cutoff) %}       {# 500 → 50 #}

{# ✅ GOOD: Use pre-computed relationships #}
{% set related = page.related_posts | limit(5) %}  {# O(1) access #}

{# ⚠️ SLOW: Filter wide collection multiple times #}
{% for post in site.pages %}  {# 10,000 iterations #}
  {% set same_author = site.pages | where('author', post.author) %}  {# 10K × 10K #}
{% endfor %}

{# 💣 NEVER: Nested loops on large collections #}
{% for p1 in site.pages %}
  {% for p2 in site.pages %}
    {# This is O(n²) = 100M operations at 10K pages #}
  {% endfor %}
{% endfor %}
```

#### 7. **Size Limits**

Hard limits to prevent accidents:

```python
MAX_QUERY_SIZE = 5000  # Configurable in bengal.toml

def where(items, key, value, operator='eq'):
    if len(items) > MAX_QUERY_SIZE:
        raise PerformanceError(
            f"Query too large ({len(items)} items > {MAX_QUERY_SIZE}). "
            f"Consider pre-computing this query at build time or "
            f"increasing max_query_size in bengal.toml"
        )
```

---

## Testing Strategy

### Unit Tests

**Test structure:**
```
tests/unit/rendering/template_functions/
├── test_collections_enhanced.py        # Phase 1
│   ├── test_where_with_operators
│   ├── test_where_backward_compatibility
│   ├── test_where_gt_lt_comparisons
│   ├── test_where_in_membership
│   └── test_nested_property_access
│
├── test_set_operations.py              # Phase 2
│   ├── test_intersect_basic
│   ├── test_intersect_pages
│   ├── test_union_deduplication
│   ├── test_complement
│   └── test_symdiff
│
└── test_advanced_queries.py            # Phase 3
    ├── test_where_intersect_tags
    ├── test_where_regex
    ├── test_multi_where
    └── test_complex_queries
```

### Integration Tests

**File:** `tests/integration/test_collection_queries.py`

Test real-world scenarios:
```python
def test_related_posts_by_shared_tags(tmp_site):
    """Find related posts using tag intersection."""

def test_filter_by_date_range(tmp_site):
    """Filter posts by date range."""

def test_complex_multi_condition_query(tmp_site):
    """Combine multiple filters efficiently."""
```

### Documentation Tests

**File:** `examples/showcase/content/docs/templates/collection-queries.md`

Live examples users can run:
```markdown
## Find Related Posts by Tags

{% set related = site.pages
   | where_intersect('tags', page.tags)
   | where_not('slug', page.slug)
   | limit(5) %}
```

---

## Documentation Plan

### New Documentation Pages

1. **User Guide:** `docs/templates/collection-queries.md`
   - Basic filtering with operators
   - Set operations
   - Complex queries
   - Performance tips

2. **API Reference:** Update `docs/templates/function-reference/collections.md`
   - Function signatures
   - Parameters
   - Examples
   - Return types

3. **Migration Guide:** `docs/migration/hugo-collection-functions.md`
   - Hugo vs Bengal syntax comparison
   - Common patterns translation
   - Gotchas and differences

### Example Templates

**File:** `bengal/themes/default/templates/examples/`
```
├── related-by-author.html
├── related-by-tags.html
├── recent-posts.html
└── filtered-lists.html
```

---

## Backward Compatibility

### Guarantees

1. **Existing `where` calls** continue to work:
   ```jinja2
   {{ posts | where('status', 'published') }}  # Still works
   ```

2. **All existing functions** unchanged:
   ```jinja2
   {{ posts | group_by('category') }}          # Still works
   {{ posts | sort_by('date', reverse=true) }} # Still works
   ```

3. **New features** are opt-in:
   ```jinja2
   {{ posts | where('date', cutoff, operator='gt') }}  # New, opt-in
   ```

### Deprecation Policy

- No deprecations required
- New features additive only
- Existing APIs unchanged

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance degradation on large sites | High | Add lazy evaluation, document best practices |
| Template complexity increases | Medium | Provide clear examples, limit feature scope |
| Backward compatibility issues | High | Extensive testing, careful parameter defaults |
| User confusion (too many options) | Medium | Strong documentation, focus on common use cases |
| Maintenance burden | Medium | Modular design, comprehensive tests |

---

## Success Metrics

### User-Facing

1. **Users can build relationships dynamically** in templates
2. **No need for pre-computation** of all relationship types
3. **Hugo migration** becomes easier
4. **Template code** is more expressive and readable

### Technical

1. **Zero breaking changes** to existing templates
2. **< 50ms** overhead for typical queries (< 1000 pages)
3. **100% test coverage** for new functions
4. **Zero performance regressions** on existing builds

---

## Timeline & Effort Estimate

| Phase | Effort | Duration | Deliverables |
|-------|--------|----------|--------------|
| **Phase 1: Enhanced Filtering** | 2-3 days | Week 1 | Enhanced `where`, comparison operators |
| **Phase 2: Set Operations** | 2-3 days | Week 2 | `intersect`, `union`, `complement` |
| **Phase 3: Advanced Queries** | 2-3 days | Week 3 | `where_intersect`, nested access |
| **Documentation** | 1-2 days | Ongoing | Examples, guides, API docs |
| **Testing & Polish** | 1-2 days | Week 4 | Integration tests, performance validation |

**Total Estimate:** 8-12 days

---

## Related Work

### Similar Features in Other SSGs

- **Hugo:** [Collections functions](https://gohugo.io/functions/collections/)
- **Jekyll:** Liquid filters (more limited)
- **Eleventy:** JavaScript filter functions (most flexible)
- **Gatsby:** GraphQL queries (different paradigm)

### Bengal's Unique Position

- **Jinja2-based:** Familiar to Python developers
- **Type-safe Pages:** Rich Page/Section objects
- **Pre-computed relationships:** Can still optimize common queries
- **Incremental builds:** Cache-aware query optimization possible

---

## Open Questions

1. **Should we support date arithmetic in templates?**
   ```jinja2
   {{ posts | where('date', 'gt', now() | add_days(-30)) }}
   ```

2. **Should we add SQL-like syntax?**
   ```jinja2
   {% set results = query(site.pages)
       .select('title', 'date', 'author')
       .where('section', 'blog')
       .order_by('date', 'desc')
       .limit(10) %}
   ```

3. **Should we cache query results?**
   - Per-template? Per-page? Per-build?

4. **How to handle i18n in queries?**
   ```jinja2
   {# Should this auto-filter by current language? #}
   {{ site.pages | where('lang', page.lang) }}
   ```

---

## Revised Conclusion: Performance-First Approach

### The Performance Dilemma

Hugo-style collection functions are **high-value** but **high-risk**:

**✅ Benefits:**
- Dynamic relationship building in templates
- Hugo migration easier
- Flexible queries without pre-computation

**⚠️ Risks:**
- Users can easily create O(n²) performance bombs
- Related posts took 120s at 10K pages before pre-computation
- Bengal builds at 100pps vs Hugo's 1000pps (10x slower)

### Recommendation: Staged Rollout with Safeguards

**Phase 1: Safe Subset (Weeks 1-2)**

Implement only operations that **cannot create O(n²) problems:**

✅ **Safe Operations:**
```python
where_gt(items, key, value)    # Single-pass O(n)
where_lt(items, key, value)    # Single-pass O(n)
where_in(items, key, values)   # O(n × m) where m is small
sort_by(items, key)            # O(n log n) - unavoidable
intersect(set1, set2)          # O(n + m) - not nested
union(set1, set2)              # O(n + m) - not nested
```

**Add safeguards:**
- Performance warnings for collections > 1000 items
- Document best practices prominently
- Include anti-patterns in docs

❌ **Defer for Phase 2:**
```python
where_intersect()              # Can be O(n²) if misused
nested property access         # Slower, complex caching
query builder                  # Too easy to abuse
```

---

### Alternative Approach: Pre-Computed Indexes

**Instead of template-time queries, build indexes at build time:**

```python
# During build phase (O(n) once)
class SiteIndexes:
    def __init__(self, site):
        self.by_section = defaultdict(list)
        self.by_author = defaultdict(list)
        self.by_tag = defaultdict(list)

        for page in site.pages:
            self.by_section[page.section].append(page)
            if 'author' in page.metadata:
                self.by_author[page.metadata['author']].append(page)
            for tag in page.tags:
                self.by_tag[tag].append(page)

# In templates (O(1) access)
{% set blog_posts = site.indexes.by_section['blog'] %}
{% set author_posts = site.indexes.by_author[page.author] %}
```

**Pros:**
- O(1) template access (same as related_posts)
- No performance bombs possible
- Memory overhead is acceptable (~10-20MB for 10K pages)

**Cons:**
- Less flexible than dynamic queries
- Requires defining indexes upfront
- Not quite Hugo-compatible

---

### Final Recommendation: Hybrid + Indexes

**Phase 1a: Pre-Computed Indexes (Week 1)**
- Add `site.indexes` with common lookups
- `by_section`, `by_author`, `by_tag`, `by_category`
- Document as the **preferred** approach
- **Effort:** 2-3 days

**Phase 1b: Safe Collection Functions (Week 2)**  
- Add comparison operators (`where_gt`, `where_lt`, etc.)
- Add set operations (`intersect`, `union`)
- Add performance warnings
- Document anti-patterns prominently
- **Effort:** 3-4 days

**Phase 2: Advanced Functions (Future - if needed)**
- Only add if users demonstrate need
- Require opt-in via config flag
- Include hard limits on query sizes

---

### Success Criteria

**Must have:**
1. ✅ Zero O(n²) patterns in default templates
2. ✅ Performance warnings on large collections
3. ✅ Documented anti-patterns with examples
4. ✅ Benchmark showing no regression on 10K pages

**Nice to have:**
1. ⚠️ Pre-computed indexes for common patterns
2. ⚠️ Lazy evaluation for filter chains
3. ⚠️ Query result caching

---

### The Honest Answer to "Is This Performant?"

**For small-medium sites (< 1000 pages):** Yes, fine  
**For large sites (1000-5000 pages):** Use with care, follow best practices  
**For very large sites (> 5000 pages):** Pre-computed indexes only

**Hugo can do this because:**
- Go is 10-50x faster than Python
- Compiled code has lower per-operation overhead
- Their architecture is optimized for this workload

**Bengal cannot match Hugo's performance**, so we need to be more careful about exposing APIs that can create performance problems.

---

### Updated Recommendation

**START WITH:** Pre-computed indexes (Phase 1a) - safe, fast, covers 80% of use cases  
**THEN ADD:** Safe collection functions (Phase 1b) - for the remaining 20%  
**DEFER:** Advanced queries until we see actual demand and can benchmark them

**Key principle:** Make the right thing easy and the wrong thing hard.
