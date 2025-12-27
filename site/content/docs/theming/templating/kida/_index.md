---
title: Kida Template Engine
nav_title: Kida
description: High-performance template engine for Bengal with modern syntax and automatic caching
weight: 10
type: doc
draft: false
lang: en
tags:
- templates
- kida
category: explanation
---

# Kida Template Engine

Bengal's default template engine. Renders 5.6x faster than Jinja2, supports free-threaded Python, and caches site-scoped blocks automatically.

```kida
{% let posts = site.pages |> where('type', 'blog') |> take(5) %}

{% for post in posts %}
  <article>
    <h2>{{ post.title }}</h2>
    <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
  </article>
{% end %}
```

Your Jinja2 templates work without changes—Kida parses both syntaxes.

## Documentation

:::{cards}
:columns: 2
:gap: medium

:::{card} Overview
:link: ./overview
Why Kida exists and when to use it.
:::

:::{card} Architecture
:link: ./architecture
AST-to-AST compilation, StringBuilder rendering, thread safety.
:::

:::{card} Performance
:link: ./performance
Benchmarks and optimization strategies.
:::

:::{card} Comparison
:link: ./comparison
Feature-by-feature Kida vs Jinja2.
:::

:::

## How-To Guides

:::{cards}
:columns: 2
:gap: medium

:::{card} Create Custom Templates
:link: ./create-custom-template
Build templates from scratch.
:::

:::{card} Use Pattern Matching
:link: ./use-pattern-matching
Replace `if/elif` chains with `{% match %}`.
:::

:::{card} Use Pipeline Operator
:link: ./use-pipeline-operator
Left-to-right filter chains with `|>`.
:::

:::{card} Cache Fragments
:link: ./cache-fragments
Built-in `{% cache %}` for expensive operations.
:::

:::{card} Add Custom Filters
:link: ./add-custom-filter
Extend Kida with your own filters.
:::

:::{card} Migrate from Jinja2
:link: ./migrate-jinja-to-kida
Convert existing templates.
:::

:::

## Quick Syntax Reference

| Feature | Kida | Jinja2 |
|---------|------|--------|
| Block endings | `{% end %}` | `{% endif %}`, `{% endfor %}`, etc. |
| Template variables | `{% let x = ... %}` | `{% set x = ... %}` |
| Pattern matching | `{% match %}...{% case %}` | `{% if %}...{% elif %}` |
| While loops | `{% while cond %}` | Not available |
| Pipeline operator | `\|>` | Not available |
| Optional chaining | `?.` | Not available |
| Null coalescing | `??` | `\| default()` |
| Fragment caching | `{% cache %}` | Extension required |
| Functions | `{% def %}` (lexical scope) | `{% macro %}` (no closure) |
| Range literals | `1..10` | `range(1, 11)` |

:::{seealso}

- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Template Functions](/docs/reference/template-functions/) — Available filters and functions
:::
