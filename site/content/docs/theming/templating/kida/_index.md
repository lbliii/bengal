---
title: Kida Template Engine
nav_title: Kida
description: Next-generation template engine optimized for performance and free-threaded Python
weight: 10
type: doc
draft: false
lang: en
tags:
- templates
- kida
- performance
- free-threading
keywords:
- kida template engine
- template engine
- performance
- free-threading
category: explanation
---

# Kida Template Engine

**Kida** is a next-generation template engine designed from the ground up for **free-threaded Python (3.14t+)** and optimized for performance. It serves as Bengal's default template engine, achieving **5.6x faster rendering than Jinja2** with zero external C dependencies.

:::{tip}
**New to Kida?** Start with the [Kida Tutorial](/docs/tutorials/getting-started-with-kida/) for a hands-on introduction, or read the [Overview](/docs/theming/templating/kida/overview/) to understand why Kida is a serious choice for production applications.
:::

## Why Kida?

Kida is not just another template engine—it's a **production-ready, high-performance solution** built for modern Python applications:

### Performance

- **5.6x faster** than Jinja2 (arithmetic mean across benchmarks)
- **AST-to-AST compilation**: Direct Python AST generation (no string manipulation)
- **StringBuilder pattern**: O(n) output construction vs O(n²) string concatenation
- **Automatic block caching**: 10-100x faster builds for navigation-heavy sites
- **Bytecode caching**: Near-instant cold starts for serverless environments

### Modern Architecture

- **Free-threading ready**: Declares GIL independence via PEP 703's `_Py_mod_gil = 0`
- **Thread-safe by design**: All public APIs are thread-safe
- **Compile-time optimizations**: Constant folding, dead code elimination, filter inlining
- **Precise error reporting**: Source location tracking for actionable error messages

### Developer Experience

- **Familiar syntax**: Jinja2-compatible, so existing templates work without changes
- **Modern features**: Pattern matching, pipeline operator, optional chaining, null coalescing
- **Built-in caching**: Fragment caching as a language feature
- **True lexical scoping**: Functions with access to outer scope (unlike Jinja2 macros)

## Quick Start

Kida is Bengal's default template engine. No configuration needed:

```kida
{# templates/page.html #}
<h1>{{ page.title }}</h1>
{{ page.content | safe }}

{% if page.published %}
  <time>{{ page.date | dateformat('%B %d, %Y') }}</time>
{% end %}
```

Your existing Jinja2 templates work without changes—Kida can parse Jinja2 syntax automatically.

## Documentation Structure

:::{cards}
:columns: 2
:gap: medium

:::{card} Overview
:icon: info-circle
:link: ./overview
:description: Understand why Kida is a serious, production-ready template engine
:color: blue
:::{/card}

:::{card} Architecture
:icon: sitemap
:link: ./architecture
:description: Deep dive into Kida's AST-to-AST compilation and performance optimizations
:color: purple
:::{/card}

:::{card} Performance
:icon: tachometer-alt
:link: ./performance
:description: Benchmarks, optimization strategies, and automatic caching
:color: orange
:::{/card}

:::{card} Syntax Reference
:icon: book
:link: /docs/reference/kida-syntax
:description: Complete reference for Kida template syntax, operators, and features
:color: green
:::{/card}

:::{card} Tutorial
:icon: graduation-cap
:link: /docs/tutorials/getting-started-with-kida
:description: Learn Kida step-by-step with hands-on examples
:color: teal
:::{/card}

:::{card} Migration Guide
:icon: arrow-right
:link: ./migrate-jinja-to-kida
:description: Convert existing Jinja2 templates to Kida syntax
:color: indigo
:::{/card}

:::{card} How-Tos
:icon: wrench
:link: ./how-tos
:description: Step-by-step guides for common Kida tasks
:color: cyan
:::{/card}

:::{card} Comparison
:icon: git-compare
:link: ./comparison
:description: Feature-by-feature comparison with Jinja2
:color: gray
:::{/card}

:::{/cards}

## Key Features

### Unified Block Endings

```kida
{% if page.draft %}...{% end %}
{% for post in posts %}...{% end %}
{% block content %}...{% end %}
```

One closing tag (`{% end %}`) for all blocks—no need to remember `{% endif %}`, `{% endfor %}`, etc.

### Pattern Matching

```kida
{% match page.type %}
  {% case "blog" %}
    <article class="blog-post">...</article>
  {% case "doc" %}
    <article class="doc">...</article>
  {% case _ %}
    <article>...</article>
{% end %}
```

Replace verbose `if/elif` chains with clean pattern matching.

### Pipeline Operator

```kida
{% let posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(10) %}
```

Left-to-right readable filter chains (unlike Jinja2's inside-out filter chains).

### Built-in Fragment Caching

```kida
{% cache "sidebar-nav" %}
  {{ build_nav_tree(site.pages) }}
{% end %}
```

Fragment caching as a language feature—no extensions required.

### Automatic Block Caching

Kida automatically detects and caches site-scoped blocks (navigation, footer, sidebar) that don't depend on page-specific data. This provides **10-100x faster builds** with zero template changes.

```kida
{# Automatically cached - depends only on site.pages #}
{% block nav %}
  <nav>
    {% for page in site.pages %}
      <a href="{{ page.url }}">{{ page.title }}</a>
    {% end %}
  </nav>
{% end %}

{# Renders per-page - depends on page.content #}
{% block content %}
  {{ page.content | safe }}
{% end %}
```

### Modern Operators

```kida
{# Optional chaining #}
{{ user?.profile?.name | default('Anonymous') }}

{# Null coalescing #}
{{ page.subtitle ?? page.title }}

{# Range literals #}
{% for i in 1..10 %}...{% end %}
{% for i in 1..10 by 2 %}...{% end %}
```

### True Lexical Scoping

```kida
{% let site_name = site.config.title %}

{% def card(item) %}
  <div class="card">
    <h3>{{ item.title }}</h3>
    <small>From: {{ site_name }}</small>  {# Accesses outer scope! #}
  </div>
{% end %}
```

Functions have access to outer scope (unlike Jinja2 macros).

## Production Ready

Kida is used in production by Bengal and is designed for:

- **High-traffic websites**: 5.6x faster rendering means lower server costs
- **Large sites**: Automatic block caching enables 10-100x faster builds
- **Free-threaded Python**: Optimized for Python 3.14t+ concurrent rendering
- **Serverless**: Bytecode caching provides near-instant cold starts
- **Enterprise**: Thread-safe, well-tested, production-ready

## Next Steps

- **New to Kida?** → [Tutorial](/docs/tutorials/getting-started-with-kida/)
- **Want to understand why?** → [Overview](/docs/theming/templating/kida/overview/)
- **Need syntax help?** → [Syntax Reference](/docs/reference/kida-syntax/)
- **Migrating from Jinja2?** → [Migration Guide](/docs/theming/templating/kida/migrate-jinja-to-kida/)
- **Looking for patterns?** → [How-Tos](/docs/theming/templating/kida/how-tos/)

:::{seealso}
- [Kida Architecture](/docs/theming/templating/kida/architecture/) — Deep dive into how Kida works
- [Kida Performance](/docs/theming/templating/kida/performance/) — Benchmarks and optimization strategies
- [Template Functions Reference](/docs/reference/template-functions/) — Available filters and functions
:::
