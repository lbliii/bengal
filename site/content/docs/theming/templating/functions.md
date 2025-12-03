---
title: Template Functions Reference
description: Complete reference for Bengal's template filters and functions
weight: 30
draft: false
lang: en
tags: [reference, templates, filters, jinja2]
keywords: [template functions, filters, where, sort, collections]
category: reference
aliases:
  - /docs/reference/template-functions/
---

# Template Functions Reference

Bengal provides powerful template filters for querying, filtering, and transforming content collections.

## Collection Filters

These filters work with lists of pages, dictionaries, or any iterable.

### where

Filter items where a key matches a value. Supports comparison operators.

**Basic Usage:**

```jinja2
{# Filter by exact value (default) #}
{% set tutorials = site.pages | where('category', 'tutorial') %}

{# Filter by nested attribute #}
{% set track_pages = site.pages | where('metadata.track_id', 'getting-started') %}
```

**With Comparison Operators:**

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal (default) | `where('status', 'published', 'eq')` |
| `ne` | Not equal | `where('status', 'draft', 'ne')` |
| `gt` | Greater than | `where('date', one_year_ago, 'gt')` |
| `gte` | Greater than or equal | `where('priority', 5, 'gte')` |
| `lt` | Less than | `where('weight', 100, 'lt')` |
| `lte` | Less than or equal | `where('order', 10, 'lte')` |
| `in` | Value in list | `where('tags', 'python', 'in')` |
| `not_in` | Value not in list | `where('status', ['archived'], 'not_in')` |

**Operator Examples:**

```jinja2
{# Pages newer than a year ago #}
{% set recent = site.pages | where('date', one_year_ago, 'gt') %}

{# Pages tagged with 'python' #}
{% set python_posts = site.pages | where('tags', 'python', 'in') %}

{# Exclude archived pages #}
{% set live = site.pages | where('status', ['archived', 'draft'], 'not_in') %}
```

### where_not

Filter items where a key does NOT equal a value.

```jinja2
{# Exclude drafts #}
{% set published = site.pages | where_not('draft', true) %}
```

### sort_by

Sort items by a key, with optional reverse order.

```jinja2
{# Sort by date, newest first #}
{% set recent = site.pages | sort_by('date', reverse=true) %}

{# Sort alphabetically by title #}
{% set alphabetical = site.pages | sort_by('title') %}
```

### group_by

Group items by a key value, returning a dictionary.

```jinja2
{% set by_category = site.pages | group_by('category') %}

{% for category, pages in by_category.items() %}
<h2>{{ category }}</h2>
<ul>
  {% for page in pages %}
  <li><a href="{{ page.url }}">{{ page.title }}</a></li>
  {% endfor %}
</ul>
{% endfor %}
```

### limit

Take the first N items from a list.

```jinja2
{# Latest 5 posts #}
{% set latest = site.pages | sort_by('date', reverse=true) | limit(5) %}
```

### offset

Skip the first N items from a list.

```jinja2
{# Skip first 10 items (pagination page 2) #}
{% set page_2 = items | offset(10) | limit(10) %}
```

### first / last

Get the first or last item from a list.

```jinja2
{% set featured = site.pages | where('metadata.featured', true) | first %}
{% set oldest = site.pages | sort_by('date') | last %}
```

### reverse

Reverse a list (returns a new list).

```jinja2
{% set newest_first = chronological | reverse %}
```

### uniq

Remove duplicate items while preserving order.

```jinja2
{% set unique_tags = all_tags | uniq %}
```

### flatten

Flatten nested lists into a single list.

```jinja2
{% set all_tags = nested_tags | flatten | uniq %}
```

## Set Operations

Perform set operations on lists.

### union

Combine two lists, removing duplicates.

```jinja2
{% set combined = featured | union(recent) %}
```

### intersect

Get items that appear in both lists.

```jinja2
{% set featured_python = featured | intersect(python) %}
```

### complement

Get items in the first list that are NOT in the second list.

```jinja2
{% set regular = all_posts | complement(featured) %}
```

## Chaining Filters

Filters can be chained for powerful queries:

```jinja2
{% set result = site.pages
  | where('category', 'tutorial')
  | where('tags', 'python', 'in')
  | where('draft', false)
  | sort_by('date', reverse=true)
  | limit(10) %}
```

## Quick Reference

| Filter | Purpose | Example |
|--------|---------|---------|
| `where(key, val)` | Filter by value | `pages \| where('type', 'post')` |
| `where(key, val, 'gt')` | Greater than | `pages \| where('date', cutoff, 'gt')` |
| `where(key, val, 'in')` | Value in list | `pages \| where('tags', 'python', 'in')` |
| `where_not(key, val)` | Exclude value | `pages \| where_not('draft', true)` |
| `sort_by(key)` | Sort ascending | `pages \| sort_by('title')` |
| `sort_by(key, reverse=true)` | Sort descending | `pages \| sort_by('date', reverse=true)` |
| `group_by(key)` | Group by value | `pages \| group_by('category')` |
| `limit(n)` | Take first N | `pages \| limit(5)` |
| `offset(n)` | Skip first N | `pages \| offset(10)` |
| `first` | First item | `pages \| first` |
| `last` | Last item | `pages \| last` |
| `reverse` | Reverse order | `pages \| reverse` |
| `uniq` | Remove duplicates | `tags \| uniq` |
| `flatten` | Flatten nested lists | `nested \| flatten` |
| `union(list2)` | Combine lists | `list1 \| union(list2)` |
| `intersect(list2)` | Common items | `list1 \| intersect(list2)` |
| `complement(list2)` | Difference | `list1 \| complement(list2)` |

## See Also

- [Variables Reference](/docs/theming/variables/) — Available template variables
- [Templating](/docs/theming/templating/) — Template basics

