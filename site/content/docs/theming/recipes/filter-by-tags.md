---
title: Filter by Multiple Tags
description: Query content matching multiple criteria using Bengal's filters
weight: 30
draft: false
lang: en
tags:
- cookbook
- filters
- where
- tags
keywords:
- filter
- tags
- multiple criteria
- in operator
category: cookbook
---

# Filter by Multiple Tags

Find content that matches multiple criteria — tags, categories, or custom fields.

## The Pattern

```kida
{# Pages tagged with 'python' #}
{% let python_posts = site.pages
  |> where('tags', 'python', 'in') %}

{# Chain multiple filters #}
{% let tutorials = site.pages
  |> where('category', 'tutorial')
  |> where('tags', 'python', 'in')
  |> where('draft', false)
  |> sort_by('date', reverse=true) %}
```

## Filter Operators

| Operator | Purpose | Example |
|----------|---------|---------|
| `eq` (default) | Equals | `where('status', 'published')` |
| `ne` | Not equals | `where('status', 'draft', 'ne')` |
| `in` | Value in list | `where('tags', 'python', 'in')` |
| `not_in` | Value not in list | `where('status', ['draft', 'archived'], 'not_in')` |
| `gt`, `gte` | Greater than | `where('date', cutoff, 'gt')` |
| `lt`, `lte` | Less than | `where('weight', 100, 'lt')` |

## Variations

:::{tab-set}
:::{tab-item} Any of These Tags

```kida
{# Has 'python' OR 'javascript' tag #}
{% let python = site.pages |> where('tags', 'python', 'in') %}
{% let js = site.pages |> where('tags', 'javascript', 'in') %}
{% let either = python |> union(js) %}
```

:::{/tab-item}
:::{tab-item} ALL of These Tags

```kida
{# Has both 'python' AND 'tutorial' tags #}
{% let python = site.pages |> where('tags', 'python', 'in') %}
{% let tutorials = site.pages |> where('tags', 'tutorial', 'in') %}
{% let both = python |> intersect(tutorials) %}
```

:::{/tab-item}
:::{tab-item} Exclude Tags

```kida
{# Everything except archived posts #}
{% let active = site.pages
  |> where('tags', 'archived', 'not_in') %}
```

:::{/tab-item}
:::{tab-item} Nested Field

```kida
{# Access frontmatter via metadata #}
{% let featured = site.pages
  |> where('metadata.featured', true) %}

{% let series = site.pages
  |> where('metadata.series', 'getting-started') %}
```

:::{/tab-item}
:::{/tab-set}

## Build a Tag Filter Page

```kida
{# In a page with frontmatter: filter_tags: ['python', 'beginner'] #}

{% let matches = site.pages %}

{% for tag in page.metadata.filter_tags %}
  {% let tag_pages = site.pages |> where('tags', tag, 'in') %}
  {% let matches = matches |> intersect(tag_pages) %}
{% end %}

<h1>Posts tagged: {{ page.metadata.filter_tags | join(', ') }}</h1>

{% for post in matches |> sort_by('date', reverse=true) %}
  <li><a href="{{ post.href }}">{{ post.title }}</a></li>
{% end %}
```

:::{seealso}
- [Template Functions](/docs/theming/templating/functions/) — All filter options
- [Group by Category](/docs/theming/recipes/group-by-category/) — Organize filtered results
:::
