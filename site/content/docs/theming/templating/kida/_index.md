---
title: Kida Template Engine
nav_title: Kida
description: Template engine with unified block endings, pattern matching, pipelines, and automatic caching
weight: 10
icon: zap
---

# Kida Template Engine

Bengal's default template engine. Kida renders templates faster than Jinja2, supports free-threaded Python, and caches site-scoped blocks automatically.

**Performance**: Single-threaded, Kida is 3.4x faster on minimal templates. Under concurrent workloads (8 workers), Kida is **1.81x faster** than Jinja2 due to its thread-safe, GIL-independent design.

```kida
{% let posts = site.pages |> where('type', 'blog') |> take(5) %}

{% for post in posts %}
  <article>
    <h2>{{ post.title }}</h2>
    <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
  </article>
{% end %}
```

**Jinja2 compatibility**: Most Jinja2 templates work without changes. Kida parses both Jinja2 syntax (`{% endif %}`, `{% endfor %}`, etc.) and Kida-native syntax (`{% end %}`, `|>`, `?.`, `??`). However, Kida does not support all Jinja2 features—notably, `{% macro %}` is not supported (use `{% def %}` instead). If you need full Jinja2 compatibility, you can use the Jinja2 engine by setting `template_engine: jinja2` in your config.

## Key Features

| Feature | Benefit | Example |
| ------- | ------- | ------- |
| **Unified endings** | `{% end %}` for all blocks | `{% if %}...{% end %}` instead of `{% endif %}` |
| **Pattern matching** | `{% match %}...{% case %}` replaces `if/elif` chains | Cleaner branching logic |
| **Pipeline operator** | `\|>` for left-to-right filter chains | `items \|> filter() \|> sort() \|> take(5)` |
| **Optional chaining** | `?.` for safe navigation | `user?.profile?.name` returns `None` if any part is missing |
| **Null coalescing** | `??` for concise fallbacks | `page.subtitle ?? page.title` uses subtitle if available |
| **Scope-aware functions** | `{% def %}` functions access outer variables | No need to pass `site` or `config` as parameters |
| **Automatic caching** | Site-wide blocks render once per build | Navigation, footer cached automatically |

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

| Feature | Kida | Jinja2 | Notes |
| ------- | ---- | ------ | ----- |
| Block endings | `{% end %}` | `{% endif %}`, `{% endfor %}`, etc. | Unified syntax for all blocks |
| Template variables | `{% let x = ... %}` | `{% set x = ... %}` | Template-scoped assignment |
| Pattern matching | `{% match %}...{% case %}` | `{% if %}...{% elif %}` | Replaces long if/elif chains |
| Pipeline operator | `\|>` | Not available | Left-to-right filter chains |
| Optional chaining | `?.`, `?[` | Not available | Safe navigation: `obj?.attr`, `obj?['key']` |
| Null coalescing | `??` | `\| default()` | Fallback operator: `value ?? default` |
| Fragment caching | `{% cache key %}...{% end %}` | Extension required | Built-in caching directive |
| Functions | `{% def %}` (lexical scope) | `{% macro %}` (isolated) | Functions see outer variables |
| Range literals | `1..10` | `range(1, 11)` | Inclusive range syntax |

## Learn More

- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Operators Guide](/docs/theming/templating/kida/syntax/operators/) — Pipeline, optional chaining, and null coalescing
- [Template Functions](/docs/reference/template-functions/) — Available filters and functions
- [Migrating from Jinja2](/docs/theming/templating/kida/migration/from-jinja/) — Step-by-step migration guide

## Kida Documentation

Kida is developed as a standalone template engine. For comprehensive documentation including API reference, extending the engine, and standalone usage:

- [[ext:kida:docs/get-started|Getting Started with Kida]] — Installation and quickstart
- [[ext:kida:docs/syntax|Syntax Reference]] — Complete syntax documentation
- [[ext:kida:docs/reference/filters|Filters Reference]] — All built-in filters
- [[ext:kida:docs/about/performance|Performance]] — Benchmarks and optimization tips
