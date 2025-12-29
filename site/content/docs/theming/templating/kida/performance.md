---
title: Kida Performance
nav_title: Performance
description: Automatic caching, free-threading, and optimization strategies
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

Kida uses automatic block caching, bytecode caching, and free-threading to reduce rendering time. This page covers the mechanisms and optimization strategies.

## Free-Threading Support

Kida renders templates without holding the Global Interpreter Lock (GIL). On Python 3.14t+, templates render in parallel across CPU cores.

```yaml
# bengal.yaml
build:
  parallel: true  # Default on Python 3.14t+
```

## Automatic Block Caching

Kida analyzes templates at compile time to identify **site-scoped blocks**—blocks that only access `site.*`, `config.*`, or other non-page data. These blocks render once per build and reuse the cached result for every page.

```kida
{% block nav %}
  {# Accesses site.pages only — renders once, cached for all pages #}
  {% for page in site.pages %}
    <a href="{{ page.url }}">{{ page.title }}</a>
  {% end %}
{% end %}

{% block content %}
  {# Accesses page.content — renders per page #}
  {{ page.content | safe }}
{% end %}
```

**How it works:**

1. During template compilation, Kida traces variable access in each block
2. Blocks that never access `page.*` or other page-specific variables are marked site-scoped
3. At render time, site-scoped blocks execute once and cache their output
4. Subsequent pages reuse the cached HTML without re-rendering

No template changes required—caching happens automatically based on variable access patterns.

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

Use fragment caching for:
- Expensive function calls
- External API responses
- Complex computations that don't change often

## Bytecode Caching

Compiled templates cache to disk in `.bengal/cache/kida/`. On subsequent builds, Kida loads bytecode directly without recompilation.

```yaml
# bengal.yaml
kida:
  bytecode_cache: true  # Default
```

**How it works:**

1. First build: Kida parses and compiles templates to Python bytecode
2. Bytecode writes to `.bengal/cache/kida/`
3. Subsequent builds: Kida loads cached bytecode (skips parsing/compilation)
4. Template changes: Kida detects file modification time and recompiles only changed templates

## Optimization Strategies

### Structure templates for automatic caching

Separate site-wide blocks from page-specific blocks:

```kida
{# Site-wide — cached automatically #}
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

### Avoid re-computing in loops

Move invariant expressions outside loops:

```kida
{# Good: Compute once #}
{% let base_url = site.config.base_url %}
{% for page in pages %}
  <a href="{{ base_url }}{{ page.url }}">{{ page.title }}</a>
{% end %}

{# Avoid: Recomputes site.config.base_url on every iteration #}
{% for page in pages %}
  <a href="{{ site.config.base_url }}{{ page.url }}">{{ page.title }}</a>
{% end %}
```

:::{seealso}
- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Fragment Caching](/docs/theming/templating/kida/syntax/caching/) — Detailed caching guide
:::
