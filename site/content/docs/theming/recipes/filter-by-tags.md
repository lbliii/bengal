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

```jinja2
{# Pages tagged with 'python' #}
{% set python_posts = site.pages
  | where('tags', 'python', 'in') %}

{# Chain multiple filters #}
{% set tutorials = site.pages
  | where('category', 'tutorial')
  | where('tags', 'python', 'in')
  | where('draft', false)
  | sort_by('date', reverse=true) %}
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

### Pages with Any of These Tags

```jinja2
{# Has 'python' OR 'javascript' tag #}
{% set python = site.pages | where('tags', 'python', 'in') %}
{% set js = site.pages | where('tags', 'javascript', 'in') %}
{% set either = python | union(js) %}
```

### Pages with ALL of These Tags

```jinja2
{# Has both 'python' AND 'tutorial' tags #}
{% set python = site.pages | where('tags', 'python', 'in') %}
{% set tutorials = site.pages | where('tags', 'tutorial', 'in') %}
{% set both = python | intersect(tutorials) %}
```

### Exclude Certain Tags

```jinja2
{# Everything except archived posts #}
{% set active = site.pages
  | where('tags', 'archived', 'not_in') %}
```

### Filter by Nested Field

```jinja2
{# Access frontmatter via metadata #}
{% set featured = site.pages
  | where('metadata.featured', true) %}

{% set series = site.pages
  | where('metadata.series', 'getting-started') %}
```

## Build a Tag Filter Page

```jinja2
{# In a page with frontmatter: filter_tags: ['python', 'beginner'] #}

{% set matches = site.pages %}

{% for tag in page.metadata.filter_tags %}
  {% set tag_pages = site.pages | where('tags', tag, 'in') %}
  {% set matches = matches | intersect(tag_pages) %}
{% endfor %}

<h1>Posts tagged: {{ page.metadata.filter_tags | join(', ') }}</h1>

{% for post in matches | sort_by('date', reverse=true) %}
  <li><a href="{{ post.url }}">{{ post.title }}</a></li>
{% endfor %}
```

## See Also

- [Template Functions](/docs/theming/templating/functions/) — All filter options
- [Group by Category](/docs/theming/recipes/group-by-category/) — Organize filtered results
