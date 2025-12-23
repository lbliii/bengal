---
title: Template Functions
nav_title: Functions
description: Filters and functions available in Jinja2 templates
weight: 30
draft: false
lang: en
tags:
- reference
- templates
- filters
- jinja2
keywords:
- template functions
- filters
- where
- sort
- collections
category: reference
---

# Template Functions

Bengal provides 80+ template functions and filters for use in Jinja2 templates, organized by category.

:::{tip}
For the **complete reference** with all functions, filters, and examples, see:
- [Template Functions Reference](/docs/reference/template-functions/) — Full API documentation
- [TEMPLATE-CONTEXT.md](https://github.com/lbliii/bengal/blob/main/bengal/themes/default/templates/TEMPLATE-CONTEXT.md) — Quick reference for theme developers
:::

## Quick Overview

### Collection Filters

Query and transform page collections:

```jinja2
{% set posts = site.pages
  | where('type', 'blog')
  | where('draft', false)
  | sort_by('date', reverse=true)
  | limit(10) %}
```

| Filter | Purpose |
|--------|---------|
| `where(key, val)` | Filter by value |
| `where(key, val, 'gt')` | Comparison operators (`gt`, `lt`, `in`, etc.) |
| `sort_by(key)` | Sort ascending/descending |
| `group_by(key)` | Group into dictionary |
| `limit(n)` / `offset(n)` | Pagination |
| `first` / `last` | Get single item |
| `union` / `intersect` / `complement` | Set operations |

### Navigation Functions

```jinja2
{% set docs = get_section('docs') %}
{% set nav = get_nav_tree(page) %}
{% set crumbs = breadcrumbs(page) %}
```

| Function | Purpose |
|----------|---------|
| `get_section(path)` | Get section by path |
| `section_pages(path)` | Get pages from section |
| `get_nav_tree(page)` | Build sidebar navigation |
| `breadcrumbs(page)` | Generate breadcrumb trail |
| `get_menu(name)` | Get configured menu |

### Linking Functions

```jinja2
{{ ref('docs/getting-started') }}
{{ ref('docs/api', 'API Reference') }}
{{ anchor('Installation', 'docs/setup') }}
```

| Function | Purpose |
|----------|---------|
| `ref(path)` | Cross-reference link to page |
| `doc(path)` | Get page object for custom links |
| `anchor(heading, page)` | Link to heading |
| `relref(path)` | Get URL only (no HTML) |

### i18n Functions

```jinja2
{{ t('nav.home') }}
{{ locale_date(page.date, 'long') }}
<html lang="{{ current_lang() }}">
```

| Function | Purpose |
|----------|---------|
| `t(key)` | Translate UI string |
| `current_lang()` | Get current language |
| `languages()` | List configured languages |
| `locale_date(date, format)` | Localized date formatting |

### Text & Date Filters

```jinja2
{{ page.content | truncate(200) }}
{{ page.date | dateformat('%B %d, %Y') }}
{{ page.date | days_ago }} days old
```

| Filter | Purpose |
|--------|---------|
| `truncate(n)` / `truncatewords(n)` | Shorten text |
| `slugify` | URL-safe string |
| `markdownify` | Render markdown |
| `dateformat(fmt)` | Format date |
| `days_ago` / `months_ago` | Content age |
| `reading_time` | Estimate read time |

### Social Sharing

```jinja2
<a href="{{ share_url('twitter', page) }}">Tweet</a>
<a href="{{ share_url('linkedin', page) }}">Share</a>
```

Supported: `twitter`, `linkedin`, `facebook`, `reddit`, `hackernews`, `email`, `mastodon`

---

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/) — Complete documentation with all parameters and examples
- [Variables Reference](/docs/theming/variables/) — Available template variables
- [Templating Basics](/docs/theming/templating/) — Template inheritance and syntax
:::
