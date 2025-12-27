# KIDA Cache Block Variable Scoping Analysis

**Date**: 2025-12-26  
**Question**: Is the inability to access variables from `{% cache %}` blocks a functionality gap or intentional design?

---

## Answer: **Intentional Design** ✅

`{% cache %}` blocks are designed for **fragment caching** (HTML output), not for caching computed variable values.

---

## How Cache Blocks Work

Looking at the compiler implementation (`special_blocks.py:325-480`), cache blocks:

1. **Capture HTML output**: Redirect `_append` to capture rendered HTML into `_cache_buf`
2. **Cache the HTML string**: Store `''.join(_cache_buf)` in the cache
3. **On cache hit**: Skip body execution entirely, just append cached HTML
4. **On cache miss**: Execute body, capture output, cache it, then append

**Key insight**: Cache blocks cache **rendered HTML output**, not variable assignments.

### Generated Code Pattern

```python
# Cache hit path (fast)
if _cached is not None:
    _append(_cached)  # Just append cached HTML, skip body

# Cache miss path (slow)
else:
    _cache_buf = []
    _append = _cache_buf.append  # Redirect output
    ... body executes (variables assigned here) ...
    _cached = ''.join(_cache_buf)  # Cache HTML string
    _cache_set(_cache_key, _cached, ttl)
    _append(_cached)  # Append cached HTML
```

**Problem**: Variables assigned inside the cache block body are only executed on cache miss. On cache hit, the body is skipped entirely, so variables never get assigned.

---

## Why This Design Makes Sense

### 1. **Fragment Caching is the Primary Use Case**

Cache blocks are optimized for caching expensive HTML generation:

```jinja
{% cache "sidebar-" ~ site.nav_version %}
  {{ build_nav_tree(site.pages) }}  {# Expensive HTML generation #}
{% end %}
```

This is the most common pattern - cache the rendered HTML, not intermediate values.

### 2. **Performance Optimization**

On cache hit, the entire body is skipped:
- No variable assignments executed
- No function calls made
- Just append pre-rendered HTML

This is the fastest possible path.

### 3. **Clear Separation of Concerns**

- **Cache blocks**: For caching HTML output
- **Variable assignments**: For computed values (use `{% let %}` outside cache blocks)
- **Capture blocks**: For capturing block output into variables

---

## The Limitation

**What doesn't work**:
```jinja
{% cache 'menu-' ~ lang %}
  {% let _main_menu = get_menu_lang('main', lang) %}
{% end %}
{{ _main_menu }}  {# ❌ Undefined - variable only exists on cache miss #}
```

**Why**: On cache hit, the body is skipped, so `_main_menu` is never assigned.

---

## Workarounds

### Option 1: Cache the HTML Output (Recommended)

```jinja
{% cache 'menu-' ~ lang %}
  {% let menu_items = get_menu_lang('main', lang) %}
  <nav>
    {% for item in menu_items %}
      <a href="{{ item.href }}">{{ item.title }}</a>
    {% end %}
  </nav>
{% end %}
```

Cache the entire HTML fragment, not just the variable.

### Option 2: Compute Outside Cache Block

```jinja
{% let _main_menu = get_menu_lang('main', lang) %}
{% cache 'menu-html-' ~ lang %}
  <nav>
    {% for item in _main_menu %}
      <a href="{{ item.href }}">{{ item.title }}</a>
    {% end %}
  </nav>
{% end %}
```

Compute the variable once, cache the HTML rendering.

### Option 3: Use Capture for Variable Caching

```jinja
{% capture menu_html %}
  {% let menu_items = get_menu_lang('main', lang) %}
  {% for item in menu_items %}
    <a href="{{ item.href }}">{{ item.title }}</a>
  {% end %}
{% end %}
{{ menu_html | safe }}
```

Capture the output, but this doesn't provide caching - it's just for variable assignment.

---

## Could This Be Enhanced?

### Potential Enhancement: Variable Export from Cache Blocks

A potential enhancement could allow exporting variables from cache blocks:

```jinja
{% cache 'menu-' ~ lang, export=['_main_menu'] %}
  {% let _main_menu = get_menu_lang('main', lang) %}
  {# HTML output #}
{% end %}
{{ _main_menu }}  {# ✅ Available outside #}
```

**Implementation challenges**:
1. Need to store variable values alongside cached HTML
2. Cache structure becomes more complex: `{html: str, vars: dict}`
3. Variable values must be serializable (JSON-compatible)
4. Cache hit path becomes slightly slower (need to restore variables)

**Trade-off**: Adds complexity for a use case that can be solved with workarounds.

---

## Current Best Practice

For caching expensive computations that need to be used as variables:

1. **If you need the HTML**: Cache the entire HTML fragment
   ```jinja
   {% cache 'key' %}
     {{ expensive_computation() }}
   {% end %}
   ```

2. **If you need the value**: Compute outside cache, cache the HTML that uses it
   ```jinja
   {% let value = expensive_computation() %}
   {% cache 'key' %}
     {{ value }}
   {% end %}
   ```

3. **If computation is expensive AND you need the value**: Consider caching at the application level (Python-side caching) rather than template-level

---

## Conclusion

**This is intentional design**, not a gap. Cache blocks are optimized for fragment caching (HTML output), which is the most common and highest-impact use case.

The limitation (variables not accessible outside) is a reasonable trade-off for:
- Maximum performance on cache hits (skip all execution)
- Simple implementation (cache just stores HTML strings)
- Clear semantics (cache blocks cache output, not state)

For caching computed values, use the workarounds above or consider application-level caching.

---

## Recommendation

**Keep current design** - it's optimized for the primary use case (fragment caching).

If variable export from cache blocks becomes a common need, consider:
1. Documenting the workarounds clearly
2. Adding a `{% cache %}` enhancement RFC if there's strong demand
3. Evaluating if application-level caching (Python-side) is more appropriate

For now, the workarounds are sufficient and maintain the performance benefits of fragment caching.
