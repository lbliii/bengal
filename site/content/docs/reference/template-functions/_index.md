---
title: Template Functions Reference
nav_title: Functions
description: Complete reference for Bengal's template filters and functions
weight: 50
type: doc
draft: false
lang: en
tags:
- reference
- templates
- filters
- kida
- hugo
keywords:
- template functions
- filters
- where
- sort
- collections
- hugo migration
category: reference
---

Bengal provides powerful template filters for querying, filtering, and transforming content collections. Many filters are inspired by Hugo for easy migration.

## Functions vs Filters: Understanding the Difference

Bengal provides two types of template capabilities: **functions** and **filters**. Understanding when to use each helps you write clearer, more efficient templates.

### Filters: Transform Values

**Filters** transform a value using the pipe operator (`|` or `|>`). The value on the left becomes the first argument to the filter.

**Syntax:**
```kida
{{ value | filter }}
{{ value | filter(arg1, arg2) }}
{{ value |> filter1 |> filter2 }}
```

**When to use:** When you have a value to transform.

**Examples:**
```kida
{# Transform text #}
{{ page.title | upper }}
{{ page.content | markdown | safe }}

{# Transform collections #}
{{ site.pages | where('draft', false) | sort_by('date') }}

{# Chain transformations #}
{{ text |> slugify |> truncate(50) }}
```

**Registered in:** `env.filters` (available via pipe operator)

### Functions: Standalone Operations

**Functions** are called directly without a value to transform. They perform operations or retrieve data.

**Syntax:**
```kida
{{ function() }}
{{ function(arg1, arg2) }}
```

**When to use:** When performing an operation that doesn't transform an existing value.

**Examples:**
```kida
{# Retrieve data #}
{{ get_page('docs/about') }}
{{ get_data('data/authors.json') }}

{# Generate references #}
{{ ref('docs/getting-started') }}
{{ get_section('blog') }}

{# Check conditions #}
{{ page_exists('path/to/page') }}
```

**Registered in:** `env.globals` (available as direct function calls)

### Quick Decision Guide

| Use Case | Type | Example |
|----------|------|---------|
| Transform text | Filter | `{{ text \| upper }}` |
| Transform a collection | Filter | `{{ pages \| where('draft', false) }}` |
| Chain transformations | Filter | `{{ data \|> filter1 \|> filter2 }}` |
| Retrieve a page | Function | `{{ get_page('path') }}` |
| Load data file | Function | `{{ get_data('file.json') }}` |
| Generate cross-reference | Function | `{{ ref('docs/page') }}` |
| Check if page exists | Function | `{{ page_exists('path') }}` |

### Why This Matters

**Filters** are designed for **data transformation pipelines**:
- Read left-to-right: `data |> transform |> format |> output`
- Chain multiple operations: `pages |> filter |> sort |> limit`
- Functional programming style

**Functions** are designed for **operations and lookups**:
- No implicit left operand
- Direct calls: `get_page('path')` not `| get_page('path')`
- Procedural style

### Common Patterns

**Pattern 1: Filter a collection, then use a function**
```kida
{% let blog_posts = site.pages |> where('type', 'blog') |> sort_by('date', reverse=true) %}
{% for post in blog_posts %}
  {# Use function to get related page #}
  {% let related = get_page(post.metadata.related) %}
  {% if related %}
    <a href="{{ related.url }}">Related: {{ related.title }}</a>
  {% end %}
{% end %}
```

**Pattern 2: Function to get data, filter to transform**
```kida
{% let authors = get_data('data/authors.json') %}
{% let active_authors = authors |> where('active', true) |> sort_by('name') %}
```

**Pattern 3: Function result used in filter chain**
```kida
{% let section = get_section('blog') %}
{% let recent = section.pages |> sort_by('date', reverse=true) |> limit(5) %}
```

:::{note}
**Can't remember which is which?** Ask: "Do I have a value to transform?"
- **Yes** → Use a filter (`|` or `|>`)
- **No** → Use a function (direct call)
:::

## Topics

:::{child-cards}
:columns: 2
:include: sections
:fields: title, description, icon
:::

:::{toctree}
:maxdepth: 1
:hidden:

Collection Filters <collection-filters>
Navigation Functions <navigation-functions>
Linking Functions <linking-functions>
Internationalization <i18n-functions>
String & Date Filters <string-date-filters>
Page & Section Properties <page-properties>
Math & Data Functions <math-data-filters>
Content Filters <content-filters>
View Filters <view-filters>
SEO, Image & Theme Functions <seo-image-functions>
Debug Filters <debug-filters>
:::
