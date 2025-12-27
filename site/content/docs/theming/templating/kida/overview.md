---
title: Kida Overview
nav_title: Overview
description: Why Kida exists and when to use it over Jinja2
weight: 5
type: doc
draft: false
lang: en
tags:
- explanation
- kida
category: explanation
---

# Kida Overview

Kida is a template engine built for free-threaded Python and static site generation. It compiles templates to Python AST (not source strings), renders via StringBuilder pattern, and automatically caches site-scoped blocks.

## Why Kida Exists

Template engines are evaluated on every page render. For a 1000-page site, the navigation template executes 1000 times. Traditional engines (Jinja2, Django templates) were designed before:

- **Free-threaded Python** (PEP 703) — GIL removal enables parallel rendering
- **Large static sites** — Build times grow linearly without caching
- **Serverless** — Cold starts include template compilation overhead

Kida addresses these gaps.

## Key Differences from Jinja2

:::{details} Performance: 5.6x faster rendering
:open:

Kida uses **AST-to-AST compilation** and **StringBuilder rendering**:

```
Jinja2: Template → Tokens → AST → Python source string → Code object
Kida:   Template → Tokens → AST → Python ast.Module → Code object
```

No string manipulation during compilation. Rendering appends to a list and joins once (O(n)) instead of yielding from generators.
:::

:::{details} Automatic Block Caching
:open:

Kida analyzes templates to identify blocks that only access site-wide data (`site.*`, `config.*`). These blocks render once per build, not once per page.

```kida
{% block nav %}
  {# Depends only on site.pages — cached automatically #}
  {% for page in site.pages %}
    <a href="{{ page.url }}">{{ page.title }}</a>
  {% end %}
{% end %}

{% block content %}
  {# Depends on page.content — renders per page #}
  {{ page.content | safe }}
{% end %}
```

For navigation-heavy sites: **10-100x faster builds** with zero template changes.
:::

:::{details} Free-Threading Ready

Kida declares GIL independence via `_Py_mod_gil = 0`. All AST nodes are frozen dataclasses (immutable). Rendering uses only local state.

In Python 3.14t+, multiple templates render concurrently without contention.
:::

:::{details} Modern Syntax

Kida adds syntax that Jinja2 lacks:

| Feature | Kida | Benefit |
|---------|------|---------|
| Unified endings | `{% end %}` | No need to remember `{% endif %}`, `{% endfor %}` |
| Pattern matching | `{% match x %}{% case "a" %}...` | Replaces long `if/elif` chains |
| Pipeline operator | `items \|> where(...) \|> take(5)` | Left-to-right readable |
| Optional chaining | `user?.profile?.name` | Safe navigation without conditionals |
| Null coalescing | `x ?? default` | Concise fallbacks |
| Lexical scope | `{% def %}` functions | Access outer scope (unlike Jinja2 macros) |

:::

## When to Use Kida

**Use Kida when:**
- Building sites with 100+ pages (automatic caching matters)
- Targeting free-threaded Python
- You want modern syntax features
- Cold start latency matters (serverless)

**Use Jinja2 when:**
- You need 100% Jinja2 extension compatibility
- You're committed to the Jinja2 ecosystem
- Site size is small (<50 pages)

## Jinja2 Compatibility

Kida parses Jinja2 syntax. Existing templates work without changes:

```jinja2
{# Jinja2 syntax works #}
{% if page.draft %}
  Draft
{% endif %}

{% for post in posts %}
  {{ post.title }}
{% endfor %}
```

You can migrate incrementally by converting templates to Kida syntax as you edit them.

:::{seealso}
- [Architecture](/docs/theming/templating/kida/architecture/) — How the compilation pipeline works
- [Performance](/docs/theming/templating/kida/performance/) — Benchmarks and optimization
- [Comparison](/docs/theming/templating/kida/comparison/) — Feature-by-feature Kida vs Jinja2
:::
