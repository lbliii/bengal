---
title: Kida How-Tos
nav_title: How-Tos
description: Step-by-step guides for common Kida template tasks
weight: 30
type: doc
draft: false
lang: en
tags:
- how-to
- templates
- kida
keywords:
- kida how-to
- template tasks
- kida patterns
category: how-to
---

# Kida How-Tos

Step-by-step guides for common tasks when working with Kida templates in Bengal.

:::{cards}
:columns: 2
:gap: medium

:::{card} Create a Custom Template
:icon: code
:link: ./create-custom-template
:description: Build a custom template from scratch using Kida syntax
:color: blue
:::{/card}

:::{card} Add a Custom Filter
:icon: filter
:link: ./add-custom-filter
:description: Extend Kida with your own template filters
:color: green
:::{/card}

:::{card} Use Pattern Matching
:icon: code-branch
:link: ./use-pattern-matching
:description: Replace long if/elif chains with clean pattern matching
:color: purple
:::{/card}

:::{card} Cache Template Fragments
:icon: zap
:link: ./cache-fragments
:description: Improve performance with built-in fragment caching
:color: orange
:::{/card}

:::{card} Use Automatic Block Caching
:icon: lightning-bolt
:link: ./cacheable-blocks
:description: Leverage automatic caching for site-scoped blocks
:color: yellow
:::{/card}

:::{card} Migrate from Jinja2
:icon: arrow-right
:link: ./migrate-jinja-to-kida
:description: Convert existing Jinja2 templates to Kida syntax
:color: teal
:::{/card}

:::{card} Use Pipeline Operator
:icon: workflow
:link: ./use-pipeline-operator
:description: Write readable filter chains with the pipeline operator
:color: indigo
:::{/card}

:::{/cards}

## Common Patterns

### Blog Post List

```kida
{% let posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(10) %}

<ul>
  {% for post in posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
      <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
    </li>
  {% end %}
</ul>
```

### Tag Cloud

```kida
{% let tags = site.tags
  |> items()
  |> sort_by('count', reverse=true)
  |> take(20) %}

<div class="tag-cloud">
  {% for tag in tags %}
    <a href="{{ tag_url(tag.name) }}" class="tag">
      {{ tag.name }} ({{ tag.count }})
    </a>
  {% end %}
</div>
```

### Navigation with Active State

```kida
{% let current_path = page._path %}

<nav>
  {% for item in site.menus.main %}
    {% let is_active = current_path == item.url or current_path | startswith(item.url ~ '/') %}
    <a href="{{ item.url }}" {% if is_active %}aria-current="page"{% end %}>
      {{ item.title }}
    </a>
  {% end %}
</nav>
```

## Next Steps

- **Learn the syntax**: [Syntax Reference](/docs/reference/kida-syntax/)
- **See examples**: [Tutorial](/docs/tutorials/getting-started-with-kida/)
- **Understand performance**: [Performance Guide](/docs/theming/templating/kida/performance/)

:::{seealso}
- [Kida Overview](/docs/theming/templating/kida/overview/) — Why Kida is production-ready
- [Kida Comparison](/docs/theming/templating/kida/comparison/) — Feature-by-feature comparison with Jinja2
:::
