---
title: Kida Performance
nav_title: Performance
description: Benchmarks, optimization strategies, and automatic caching for maximum performance
weight: 20
type: doc
draft: false
lang: en
tags:
- explanation
- kida
- performance
- benchmarks
keywords:
- kida performance
- template engine benchmarks
- optimization
- caching
category: explanation
---

# Kida Performance

Kida achieves **5.6x faster rendering than Jinja2** (arithmetic mean) through architectural optimizations and intelligent caching. This page covers benchmarks, optimization strategies, and automatic caching features.

## Benchmarks

**Test conditions**: Both engines with `autoescape=True`, Python 3.12

| Template Type | Kida | Jinja2 | Speedup |
|--------------|------|--------|---------|
| Simple `{{ name }}` | 0.005s | 0.045s | **8.9x** |
| Filter chain | 0.006s | 0.050s | **8.9x** |
| Conditionals `{% if %}` | 0.004s | 0.039s | **11.2x** |
| For loop (100 items) | 0.014s | 0.028s | **2.1x** |
| For loop (1000 items) | 0.013s | 0.024s | **1.8x** |
| Dict attr `{{ item.name }}` | 0.006s | 0.026s | **4.3x** |
| HTML escape heavy | 0.019s | 0.044s | **2.3x** |

**Summary**:
- Arithmetic mean: **5.6x faster**
- Geometric mean: **4.4x faster**
- Wins: **7/7 benchmarks**

## Performance Optimizations

### 1. AST-to-AST Compilation

**Jinja2**: Template → Tokens → AST → Python source string → Code object

**Kida**: Template → Tokens → AST → Python `ast.Module` → Code object

**Benefits**:
- No string manipulation overhead
- Compile-time optimizations (constant folding, dead code elimination)
- Precise error source mapping

**Impact**: **10-20% faster compilation**

### 2. StringBuilder Rendering Pattern

**Jinja2** (generator yields):
```python
def render():
    yield "Hello, "
    yield escape(name)
    yield "!"
    # Concat all at end
```

**Kida** (list append + join):
```python
def render(ctx):
    buf = []
    _append = buf.append  # Cached method lookup
    _e = _escape           # Cached function
    _append("Hello, ")
    _append(_e(ctx["name"]))
    _append("!")
    return ''.join(buf)
```

**Benefits**:
- No generator suspension/resumption overhead
- O(n) final join vs O(n²) string concatenation
- Cached method lookups (LOAD_FAST vs LOAD_GLOBAL)

**Impact**: **25-40% faster rendering**

### 3. O(n) HTML Escaping

**Jinja2**: 5 chained `.replace()` calls = O(5n)

**Kida**: Single-pass `str.translate()` = O(n)

```python
_ESCAPE_TABLE = str.maketrans({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;",
})

def escape(s):
    if not _ESCAPE_CHECK.search(s):
        return s  # Fast path: no escapable chars
    return s.translate(_ESCAPE_TABLE)
```

**Impact**: **2-3x faster HTML escaping** for templates with heavy escaping

### 4. Local Variable Caching

Kida caches frequently-used functions as local variables:

```python
def render(ctx):
    _e = _escape    # LOAD_FAST (fast)
    _s = _str
    _append = buf.append

    # Use cached locals instead of LOAD_GLOBAL
    _append(_e(_s(ctx["name"])))
```

**Impact**: **5-10% faster** for templates with many filter calls

### 5. O(1) Operator Dispatch

Kida uses dict-based dispatch for node compilation:

```python
dispatch = {
    "Data": self._compile_data,
    "Output": self._compile_output,
    "If": self._compile_if,
    ...
}
handler = dispatch[type(node).__name__]
```

**Impact**: **O(1) dispatch** vs O(n) if/elif chains

## Automatic Block Caching

Kida automatically detects and caches site-scoped template blocks, providing **10-100x faster builds** for navigation-heavy sites.

### How It Works

1. **Analysis**: Kida analyzes templates to identify blocks that only depend on site-wide context (not page-specific data)
2. **Pre-rendering**: These blocks are rendered once at build start
3. **Automatic reuse**: During page rendering, cached blocks are used automatically instead of re-rendering

### Example

```kida
{# base.html #}
{% block nav %}
  <nav>
    {% for page in site.pages %}
      <a href="{{ page.url }}">{{ page.title }}</a>
    {% end %}
  </nav>
{% end %}

{% block content %}
  {{ page.content | safe }}
{% end %}
```

**Analysis**:
- `nav` block: Depends only on `site.pages` (site-wide) → **Cached**
- `content` block: Depends on `page.content` (page-specific) → **Rendered per page**

**Result**: For a 1000-page site:
- Without caching: Render `nav` block 1000 times
- With caching: Render `nav` block once, reuse 1000 times
- **Speedup**: 100-1000x for navigation-heavy sites

### Cache Scope Detection

Kida automatically detects cache scope:

- **Site-scoped**: Blocks that only access `site.*`, `config.*`, or no page-specific variables
- **Page-scoped**: Blocks that access `page.*` or other page-specific data
- **Not cacheable**: Blocks with non-deterministic behavior (random, shuffle, etc.)

### Benefits

- **Zero template changes**: Works automatically, no syntax changes needed
- **Transparent**: Templates render normally, caching is invisible
- **10-100x faster builds**: For navigation-heavy sites with many pages

## Fragment Caching

Kida provides built-in fragment caching for expensive operations:

```kida
{% cache "sidebar-nav" %}
  {{ build_nav_tree(site.pages) }}
{% end %}

{% cache "weather-widget", ttl="5m" %}
  {{ fetch_weather_data() }}
{% end %}

{% cache "posts-" ~ site.nav_version %}
  {% for post in recent_posts %}
    {{ post.title }}
  {% end %}
{% end %}
```

### Cache Keys

- **Static strings**: `"sidebar"`
- **Expressions**: `"posts-" ~ page.id`
- **Variables**: `cache_key`

### TTL (Time To Live)

- `ttl="5m"` - 5 minutes
- `ttl="1h"` - 1 hour
- `ttl="30s"` - 30 seconds

### Benefits

- **Built-in**: No extensions required (unlike Jinja2)
- **Template-level**: Cache at template level, not application level
- **Version-aware**: Cache invalidation based on site version

## Bytecode Caching

Kida optionally caches compiled bytecode to disk for near-instant cold starts.

### Benefits

- **90%+ cold-start reduction**: Compiled templates cached, no recompilation needed
- **Serverless-friendly**: Critical for serverless applications
- **Version-aware**: Cache invalidated when Kida version changes

### Configuration

```yaml
# bengal.yaml
kida:
  bytecode_cache: true  # Default: true
```

### Cache Location

- **Default**: `.bengal/cache/kida/`
- **Customizable**: Set `Kida_CACHE_DIR` environment variable

## Optimization Strategies

### 1. Structure Templates for Caching

Separate site-wide blocks from page-specific blocks:

```kida
{# Good: Site-wide block separate #}
{% block nav %}
  {% for page in site.pages %}...{% end %}
{% end %}

{% block content %}
  {{ page.content | safe }}
{% end %}
```

**Result**: `nav` block automatically cached, `content` block renders per page

### 2. Use Fragment Caching for Expensive Operations

Cache expensive computations:

```kida
{% cache "expensive-calculation" %}
  {% let result = expensive_function(site.pages) %}
  {{ result }}
{% end %}
```

### 3. Minimize Filter Chains

Use pipeline operator for readability, but minimize unnecessary filters:

```kida
{# Good: Minimal filters #}
{{ items |> where('published', true) |> take(10) }}

{# Avoid: Unnecessary filters #}
{{ items |> where('published', true) |> list |> take(10) }}
```

### 4. Use Template Variables for Repeated Expressions

Cache repeated expressions:

```kida
{% let site_title = site.config.title %}
{% let nav_items = site.menus.main %}

{# Use cached variables instead of repeated lookups #}
<h1>{{ site_title }}</h1>
<nav>
  {% for item in nav_items %}...{% end %}
</nav>
```

### 5. Enable Bytecode Caching

Enable bytecode caching for faster cold starts:

```yaml
# bengal.yaml
kida:
  bytecode_cache: true  # Default
```

## Real-World Performance

### Small Site (<50 pages)

**Build time**:
- Jinja2: ~5 seconds
- Kida: ~1 second
- **Speedup**: 5x

**Impact**: Minimal (build time already fast)

### Medium Site (100-500 pages)

**Build time**:
- Jinja2: ~60 seconds
- Kida: ~11 seconds (with automatic block caching)
- **Speedup**: 5.5x

**Impact**: Significant (faster iteration cycles)

### Large Site (1000+ pages)

**Build time**:
- Jinja2: ~60 minutes
- Kida: ~6-10 minutes (with automatic block caching)
- **Speedup**: 6-10x

**Impact**: Critical (enables faster deployments)

### Serverless Applications

**Cold start**:
- Jinja2: ~500ms (template compilation)
- Kida: ~50ms (with bytecode cache)
- **Speedup**: 10x

**Impact**: Critical (lower latency, better user experience)

## Performance Monitoring

Monitor template rendering performance:

```python
import time
from bengal.rendering.kida import Environment

env = Environment()

# Measure compilation time
start = time.time()
template = env.from_string("{{ name }}")
compile_time = time.time() - start

# Measure rendering time
start = time.time()
result = template.render(name="World")
render_time = time.time() - start

print(f"Compile: {compile_time*1000:.2f}ms")
print(f"Render: {render_time*1000:.2f}ms")
```

## Next Steps

- **Understand the architecture**: [Architecture Guide](/docs/theming/templating/kida/architecture/)
- **Learn optimization strategies**: [How-Tos](/docs/theming/templating/kida/how-tos/)
- **See benchmarks**: [Kida Benchmarks](https://github.com/bengal/bengal/tree/main/benchmarks)

:::{seealso}
- [Kida Overview](/docs/theming/templating/kida/overview/) — Why Kida is production-ready
- [Kida Architecture](/docs/theming/templating/kida/architecture/) — Deep dive into how Kida works
- [Automatic Block Caching](/docs/theming/templating/kida/cacheable-blocks/) — How automatic caching works
:::
