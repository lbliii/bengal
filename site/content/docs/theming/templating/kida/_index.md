---
title: Kida Template Engine
nav_title: Kida
description: Template engine with unified block endings, pattern matching, pipelines, and automatic caching
weight: 10
icon: zap
---

# Kida Template Engine

Bengal's default template engine. Kida renders templates faster than Jinja2, supports free-threaded Python, and caches site-scoped blocks automatically.

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

## Key Features

| Feature | Benefit |
|---------|---------|
| **Unified endings** | `{% end %}` for all blocks |
| **Pattern matching** | `{% match %}...{% case %}` replaces `if/elif` chains |
| **Pipeline operator** | `\|>` for left-to-right filter chains |
| **Optional chaining** | `?.` for safe navigation |
| **Null coalescing** | `??` for concise fallbacks |
| **Lexical scoping** | `{% def %}` functions access outer scope |
| **Automatic caching** | Site-wide blocks render once per build |

## Topics

:::{child-cards}
:columns: 2
:include: sections
:::

## Standalone Pages

:::{child-cards}
:columns: 2
:include: pages
:::

## Quick Syntax Reference

| Feature | Kida | Jinja2 |
|---------|------|--------|
| Block endings | `{% end %}` | `{% end %}`, `{% endfor %}`, etc. |
| Template variables | `{% let x = ... %}` | `{% let x = ... %}` |
| Pattern matching | `{% match %}...{% case %}` | `{% if %}...{% elif %}` |
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
