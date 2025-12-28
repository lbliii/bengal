---
title: Kida How-Tos
nav_title: How-Tos
description: Task-oriented guides for common Kida template patterns
weight: 30
type: doc
draft: false
lang: en
tags:
- how-to
- kida
category: how-to
---

# Kida How-Tos

Task-oriented guides for working with Kida templates.

::::{cards}
:columns: 2
:gap: medium

:::{card} Create Custom Templates
:link: /docs/theming/templating/kida/create-custom-template/
Build a template from scratch with extends, blocks, and includes.
:::

:::{card} Use Pattern Matching
:link: /docs/theming/templating/kida/use-pattern-matching/
Replace `if/elif` chains with `{% match %}...{% case %}`.
:::

:::{card} Use Pipeline Operator
:link: /docs/theming/templating/kida/use-pipeline-operator/
Filter collections with left-to-right `|>` syntax.
:::

:::{card} Cache Fragments
:link: /docs/theming/templating/kida/cache-fragments/
Wrap expensive operations in `{% cache %}`.
:::

:::{card} Automatic Block Caching
:link: /docs/theming/templating/kida/cacheable-blocks/
Structure templates for automatic site-scoped caching.
:::

:::{card} Add Custom Filters
:link: /docs/theming/templating/kida/add-custom-filter/
Register Python functions as template filters.
:::

:::{card} Migrate from Jinja2
:link: /docs/theming/templating/kida/migrate-jinja-to-kida/
Convert existing templates to Kida syntax.
:::

::::

## Common Patterns

### Blog Post List

```kida
{% let posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(10) %}

{% for post in posts %}
  <article>
    <a href="{{ post.url }}">{{ post.title }}</a>
    <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
  </article>
{% end %}
```

### Navigation with Active State

```kida
{% let current = page._path %}

<nav>
  {% for item in site.menus.main %}
    {% let active = current == item.url or current | startswith(item.url ~ '/') %}
    <a href="{{ item.url }}" {% if active %}aria-current="page"{% end %}>
      {{ item.title }}
    </a>
  {% end %}
</nav>
```

### Conditional Content by Page Type

```kida
{% match page.type %}
  {% case "blog" %}
    {% include "partials/blog-meta.html" %}
  {% case "doc" %}
    {% include "partials/doc-nav.html" %}
  {% case _ %}
    {# Default: no extra content #}
{% end %}
```

:::{seealso}
- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Template Functions](/docs/reference/template-functions/) — Available filters
:::
