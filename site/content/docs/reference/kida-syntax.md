---
title: Kida Syntax
nav_title: Kida Syntax
description: Kida template syntax overview — control flow, variables, functions, and pipelines
weight: 60
draft: false
lang: en
tags:
- reference
- templates
- kida
- syntax
- persona-themer
keywords:
- kida syntax
- template syntax
- unified endings
- pattern matching
- pipeline operator
category: reference
---

# Kida Syntax

Kida is Bengal's **default template engine** — optimized for performance and
free-threaded Python. This page covers syntax fundamentals; exhaustive filter
and operator lookup lives on
[[docs/reference/kida-syntax-reference|Kida Syntax Reference (detailed)]].

:::{note}
**Do I need this?** Yes when writing or reading Kida templates. Start with
[[docs/tutorials/theming/getting-started-with-kida|Kida Tutorial]] if you are
new. For a single filter or operator, jump to the detailed reference.
:::

:::{tip}
Most Jinja2 templates work without changes, but Kida does not support all
Jinja2 features (notably `{% macro %}` — use `{% def %}` instead). For full
Jinja2 compatibility, set `template_engine: jinja2` in config.
:::

## Quick Comparison: Kida vs Jinja2

| Feature            | Kida                           | Jinja2                              |
|--------------------|--------------------------------|-------------------------------------|
| Block endings      | `{% end %}` (unified)          | `{% endif %}`, `{% endfor %}`, etc. |
| Template variables | `{% let %}` (template-scoped)  | `{% set %}` (block-scoped only)     |
| Block variables    | `{% set %}` (block-scoped)     | `{% set %}` (block-scoped)          |
| Pattern matching   | `{% match %}...{% case %}`     | `{% if %}...{% elif %}` chains      |
| While loops        | `{% while cond %}...{% end %}` | ❌ Not available                    |
| Pipeline operator  | `\|>` (left-to-right)          | `\|` (right-to-left)                |
| Optional chaining  | `obj?.attr`, `obj?['key']`     | ❌ Not available                    |
| Null coalescing    | `value ?? default`             | `value \| default(...)`             |
| Fragment caching   | `{% cache key %}...{% end %}`  | Requires extension                  |
| Functions          | `{% def %}` (lexical scope)    | `{% macro %}` (isolated scope)      |

## Basic Syntax

### Variables

Output a variable:

```kida
{{ page.title }}
{{ site.config.title }}
{{ page.content | safe }}
```

### Comments

```kida
{# This is a comment #}
{# Multi-line
   comments work too #}
```

### Escaping

```kida
{# HTML is escaped by default #}
{{ user_input }}  {# Escaped #}
{{ user_input | safe }}  {# Raw HTML #}
{{ user_input | e }}  {# Explicit escape #}
```

## Control Flow

### Conditionals

```kida
{% if page.draft %}
  <span class="draft">Draft</span>
{% end %}

{% if page.published %}
  Published
{% elif page.scheduled %}
  Scheduled
{% else %}
  Unpublished
{% end %}
```

### Loops

```kida
{% for post in site.pages |> where('type', 'blog') %}
  <article>
    <h2>{{ post.title }}</h2>
    {{ post.content | safe }}
  </article>
{% end %}
```

**Loop variables**:

| Variable          | Description                     |
|-------------------|---------------------------------|
| `loop.index`      | Current iteration (1-indexed)   |
| `loop.index0`     | Current iteration (0-indexed)   |
| `loop.length`     | Total number of items           |
| `loop.first`      | True on first iteration         |
| `loop.last`       | True on last iteration          |
| `loop.revindex`   | Iterations remaining (1-indexed)|
| `loop.cycle(...)` | Cycle through values            |

```kida
{% for item in items %}
  {% if loop.first %}First item{% end %}
  {% if loop.last %}Last item{% end %}
  Item {{ loop.index }} of {{ loop.length }}
  <tr class="{{ loop.cycle('odd', 'even') }}">
{% end %}
```

### Pattern Matching

Kida's native pattern matching replaces long `if/elif` chains:

```kida
{% match page.type %}
  {% case "blog" %}
    <i class="icon-pen"></i> Blog Post
  {% case "doc" %}
    <i class="icon-book"></i> Documentation
  {% case "tutorial" %}
    <i class="icon-graduation-cap"></i> Tutorial
  {% case _ %}
    <i class="icon-file"></i> Page
{% end %}
```

## Variables and Scoping

**Scoping**: `{% let %}` is template-scoped, `{% set %}` is block-scoped, and `{% export %}` promotes variables to template scope.

```kida
{% let site_title = site.config.title %}
{% if page.published %}
  {% set status = "Published" %}
  <span>{{ status }}</span>
{% end %}
{# status not available here #}
```

Multi-let, tuple unpacking, and export patterns are documented in
[[docs/build-sites/customize/templating/kida/syntax/variables|Variables and Scoping]].

## Template Structure

### Extends

```kida
{% extends "baseof.html" %}
```

### Blocks

```kida
{% block content %}
  <article>
    {{ page.content | safe }}
  </article>
{% end %}
```

**Note**: Kida uses `{% end %}` as the preferred block ending. `{% endblock %}` is also accepted for Jinja2 compatibility.

### Includes

```kida
{% include "partials/header.html" %}
{% include "partials/footer.html" with context %}
```

Includes and extends can be relative to the current template with `./` and
`../`. Bengal can also expose Kida `@alias/` roots with `kida.template_aliases`:

```kida
{% include "./card.html" %}
{% include "../shared/sidebar.html" %}
{% include "@components/button.html" %}
```

### Imports

```kida
{% import "macros.html" as macros %}
{{ macros.card(page) }}

{% from "macros.html" import card %}
{{ card(page) }}
```

## Functions

### Defining Functions (`{% def %}`)

Kida functions can access variables from their surrounding context automatically—no need to pass site config, theme settings, or other shared values as parameters:

```kida
{% let site_name = site.config.title %}

{% def card(item) %}
  <div class="card">
    <h3>{{ item.title }}</h3>
    <p>{{ item.description }}</p>
    <span>From: {{ site_name }}</span>  {# ✅ Accesses outer variable #}
  </div>
{% end %}

{# Just pass the item—site_name is available automatically #}
{{ card(page) }}
```

**With parameters**:

```kida
{% def button(text, href, class="btn") %}
  <a href="{{ href }}" class="{{ class }}">{{ text }}</a>
{% end %}

{{ button("Click me", "/page", "btn-primary") }}
{{ button("Default", "/page") }}
```

## Filters and Pipeline

Kida supports **filters** (transform a value with `|` or `|>`) and **functions**
(called directly). Use `|>` for left-to-right chains of three or more filters:

```kida
{{ page.title | upper }}
{{ items |> where('published', true) |> sort_by('date') |> take(5) }}
{{ get_page('docs/about') }}
```

See [[docs/reference/template-functions|Template Functions]] for the full
functions-vs-filters guide and [[docs/reference/kida-syntax-reference|Kida Syntax Reference (detailed)]]
for exhaustive filter and operator lookup.

:::{dropdown} Exhaustive filter, operator, and caching reference
:icon: book-open

Built-in filters, fragment caching, Kida-only features, operators, tests, configuration, and migration examples live on the dedicated lookup page.
:::

## See Also

- [[docs/reference/kida-syntax-reference|Kida Syntax Reference (detailed)]] — filters, operators, caching, migration
- [[docs/tutorials/theming/getting-started-with-kida|Kida Tutorial]] — learn step-by-step
- [[docs/reference/template-functions|Template Functions]] — Bengal filters and functions
- [[docs/build-sites/customize/templating/kida|Kida How-Tos]] — common tasks and patterns
