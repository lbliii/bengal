---
title: Functions vs Filters Quick Reference
nav_title: Quick Reference
description: One-page guide to when to use functions vs filters
weight: 25
draft: false
lang: en
tags:
- reference
- templates
- filters
- functions
- quick-reference
keywords:
- functions
- filters
- quick reference
- template syntax
category: reference
---

# Functions vs Filters Quick Reference

## Filters: Transform Values

**Syntax:** `{{ value | filter }}` or `{{ value |> filter }}`

**Use when:** You have a value to transform

**Examples:**
```kida
{{ text | upper }}
{{ pages |> where('draft', false) |> sort_by('date') }}
{{ page.content | markdown | safe }}
```

## Functions: Standalone Operations

**Syntax:** `{{ function() }}` or `{{ function(arg) }}`

**Use when:** Performing an operation or lookup

**Examples:**
```kida
{{ get_page('docs/about') }}
{{ get_data('data/authors.json') }}
{{ ref('docs/getting-started') }}
{{ page_exists('path') }}
```

## Decision Tree

```
Do I have a value to transform?
├─ Yes → Use filter (| or |>)
│   └─ Example: {{ text | upper }}
│
└─ No → Use function (direct call)
    └─ Example: {{ get_page('path') }}
```

## Common Patterns

**Filter a collection:**
```kida
{{ site.pages |> where('type', 'blog') |> sort_by('date') }}
```

**Get data, then filter:**
```kida
{% let authors = get_data('data/authors.json') %}
{% let active = authors |> where('active', true) %}
```

**Function result in filter chain:**
```kida
{% let section = get_section('blog') %}
{{ section.pages |> limit(5) }}
```

## Quick Examples

| Task | Type | Code |
|------|------|------|
| Uppercase text | Filter | `{{ text \| upper }}` |
| Filter pages | Filter | `{{ pages \|> where('draft', false) }}` |
| Get a page | Function | `{{ get_page('path') }}` |
| Load data | Function | `{{ get_data('file.json') }}` |
| Generate link | Function | `{{ ref('docs/page') }}` |
| Chain filters | Filter | `{{ data \|> filter1 \|> filter2 }}` |

:::{seealso}
- [Complete Reference](/docs/reference/template-functions/) — All available functions and filters
- [Functions vs Filters Explanation](/docs/reference/template-functions/#functions-vs-filters-understanding-the-difference) — Detailed explanation
:::
