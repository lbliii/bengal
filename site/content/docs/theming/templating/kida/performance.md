---
title: Kida Performance
nav_title: Performance
description: Benchmarks, automatic caching, and optimization strategies
weight: 20
type: doc
draft: false
lang: en
tags:
- reference
- kida
- performance
category: reference
---

# Kida Performance

Kida renders 5.6x faster than Jinja2 (arithmetic mean across benchmarks). This page covers benchmarks, automatic caching, and optimization strategies.

## Benchmarks

Test conditions: Both engines with `autoescape=True`, Python 3.12, 10,000 iterations.

| Template Type | Kida | Jinja2 | Speedup |
|--------------|------|--------|---------|
| Simple `{{ name }}` | 0.005s | 0.045s | 8.9x |
| Filter chain | 0.006s | 0.050s | 8.9x |
| Conditionals | 0.004s | 0.039s | 11.2x |
| For loop (100 items) | 0.014s | 0.028s | 2.1x |
| For loop (1000 items) | 0.013s | 0.024s | 1.8x |
| Dict attribute access | 0.006s | 0.026s | 4.3x |
| HTML escape heavy | 0.019s | 0.044s | 2.3x |

**Summary:** Arithmetic mean 5.6x, geometric mean 4.4x. Kida wins all 7 benchmarks.

:::{details} Benchmark methodology
Benchmarks run via `pytest-benchmark` with warmup. Source: `benchmarks/test_kida_vs_jinja.py`
:::

## Automatic Block Caching

Kida analyzes templates to identify site-scoped blocks (blocks that only access `site.*`, `config.*`, or other non-page data). These blocks render once per build.

```kida
{% block nav %}
  {# Accesses site.pages only — cached automatically #}
  {% for page in site.pages %}
    <a href="{{ page.url }}">{{ page.title }}</a>
  {% end %}
{% end %}

{% block content %}
  {# Accesses page.content — renders per page #}
  {{ page.content | safe }}
{% end %}
```

| Site Size | Without Caching | With Caching | Speedup |
|-----------|-----------------|--------------|---------|
| 100 pages | 6s | 1.2s | 5x |
| 500 pages | 30s | 5s | 6x |
| 1000 pages | 60s | 6-10s | 6-10x |

No template changes required.

## Fragment Caching

Manually cache expensive operations with `{% cache %}`:

```kida
{% cache "expensive-nav" %}
  {{ build_nav_tree(site.pages) }}
{% end %}

{% cache "weather-" ~ location, ttl="5m" %}
  {{ fetch_weather(location) }}
{% end %}
```

**TTL formats:** `"30s"`, `"5m"`, `"1h"`, `"1d"`

## Bytecode Caching

Compiled templates cache to disk in `.bengal/cache/kida/`. On subsequent builds, Kida loads bytecode directly without recompilation.

```yaml
# bengal.yaml
kida:
  bytecode_cache: true  # Default
```

Cold start reduction: ~90%.

## Optimization Strategies

### Structure templates for automatic caching

Separate site-wide blocks from page-specific blocks:

```kida
{# Site-wide — cached #}
{% block header %}{% include "partials/header.html" %}{% end %}
{% block nav %}{% include "partials/nav.html" %}{% end %}

{# Page-specific — renders per page #}
{% block content %}{{ page.content | safe }}{% end %}
```

### Cache expensive expressions

Store repeated lookups in variables:

```kida
{% let site_title = site.config.title %}
{% let nav_items = site.menus.main %}

<title>{{ page.title }} | {{ site_title }}</title>
```

### Minimize filter chains

Every filter call has overhead. Avoid unnecessary intermediate steps:

```kida
{# Good: Direct #}
{{ items |> where('published', true) |> take(10) }}

{# Avoid: Unnecessary list conversion #}
{{ items |> where('published', true) |> list |> take(10) }}
```

## Build Time Comparison

| Site Size | Jinja2 | Kida | Improvement |
|-----------|--------|------|-------------|
| 50 pages | 5s | 1s | 5x |
| 500 pages | 60s | 11s | 5.5x |
| 1000 pages | 60m | 6-10m | 6-10x |

For serverless cold starts: ~500ms (Jinja2) → ~50ms (Kida with bytecode cache).

:::{seealso}
- [Architecture](/docs/theming/templating/kida/architecture/) — How optimizations work
- [Cacheable Blocks](/docs/theming/templating/kida/cacheable-blocks/) — Automatic caching details
:::
