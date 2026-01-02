---
title: Template Functions
nav_title: Functions
description: Quick overview of filters and functions available in templates
weight: 30
---

# Template Functions

Bengal provides 80+ template functions and filters organized by category.

## Functions vs Filters

Bengal provides **filters** (transform values) and **functions** (standalone operations).

**Filters** use the pipe operator:
```kida
{{ text | upper }}
{{ pages |> where('draft', false) |> sort_by('date') }}
```

**Functions** are called directly:
```kida
{{ get_page('docs/about') }}
{{ get_data('data/config.json') }}
{{ ref('docs/getting-started') }}
```

:::{tip}
**Quick rule:** Transform a value? Use a filter (`|`). Perform an operation? Use a function (direct call).
:::

See [Template Functions Reference](/docs/reference/template-functions/#functions-vs-filters-understanding-the-difference) for complete explanation.

## Function Categories

| Category | Examples | Use For |
|----------|----------|---------|
| **Collection** | `where`, `sort_by`, `group_by`, `limit` | Querying and filtering pages |
| **Navigation** | `get_section`, `get_breadcrumbs`, `get_nav_tree` | Building navigation |
| **Linking** | `ref`, `doc`, `anchor`, `relref` | Cross-references |
| **Text** | `truncatewords`, `slugify`, `markdownify` | Text transformations |
| **Date** | `time_ago`, `days_ago`, `date_iso` | Date formatting |
| **i18n** | `t`, `current_lang`, `locale_date` | Internationalization |

## Quick Examples

### Filter Pages

```kida
{% let posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> limit(10) %}
```

### Build Navigation

```kida
{% let docs = get_section('docs') %}
{% let crumbs = get_breadcrumbs(page) %}
```

### Cross-Reference

```kida
{{ ref('docs/getting-started') }}
{{ ref('docs/api', 'API Reference') }}
```

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/) — Complete documentation with all parameters and examples
- [Theme Variables Reference](/docs/reference/theme-variables/) — Available template variables (`page`, `site`, `section`)
- [Kida Syntax](/docs/reference/kida-syntax/) — Kida template engine syntax
:::
