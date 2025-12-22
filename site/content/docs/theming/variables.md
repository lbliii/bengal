---
title: Theme Variables Reference
nav_title: Variables
description: Complete reference of all variables available in Jinja2 templates
weight: 40
draft: false
lang: en
tags:
- reference
- templates
- variables
- jinja2
keywords:
- theme variables
- templates
- jinja2
- site
- page
category: reference
---

# Theme Variables Reference

Complete reference for all variables, objects, and functions available in Bengal templates.

## Global Objects

These variables are available in **all** templates.

### `site`

The global site object.

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `site.title` | `str` | Site title from config |
| `site.baseurl` | `str` | Base URL (e.g., `https://example.com`) |
| `site.author` | `str` | Site author name |
| `site.language` | `str` | Language code (e.g., `en`) |
| `site.pages` | `list[Page]` | All pages in the site |
| `site.regular_pages` | `list[Page]` | Content pages only (no list pages) |
| `site.sections` | `list[Section]` | Top-level sections |
| `site.taxonomies` | `dict` | Map of taxonomies (tags, categories) |
| `site.data` | `dict` | Data loaded from `data/` directory |
| `site.config` | `dict` | Full configuration object |

### `page`

The current page being rendered.

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `page.title` | `str` | Page title |
| `page.content` | `str` | Raw content |
| `page.rendered_html` | `str` | Rendered HTML content |
| `page.date` | `datetime` | Publication date |
| `page.href` | `str` | URL with baseurl applied (for display in templates) |
| `page._path` | `str` | Site-relative URL without baseurl (for comparisons) |
| `page.metadata` | `dict` | All frontmatter keys |
| `page.toc` | `str` | Auto-generated Table of Contents |
| `page.is_home` | `bool` | True if homepage |
| `page.is_section` | `bool` | True if section index |
| `page.reading_time` | `int` | Estimated reading time in minutes |

#### URL Properties

Bengal provides two URL properties with clear purposes:

**`page.href`** - **Primary property for display**
- Automatically includes baseurl (e.g., `/bengal/docs/page/`)
- Use in `<a href>`, `<link>`, `<img src>` attributes
- Works correctly for all deployment scenarios

**`page._path`** - **For comparisons and logic**
- Site-relative URL without baseurl (e.g., `/docs/page/`)
- Use for comparisons: `{% if page._path == '/docs/' %}`
- Use for menu activation, filtering, and conditional logic

:::{example-label} Usage
:::

```jinja2
{# Display URL (includes baseurl) #}
<a href="{{ page.href }}">{{ page.title }}</a>

{# Comparison (without baseurl) #}
{% if page._path == '/docs/' %}
  <span class="active">Current Section</span>
{% endif %}
```

## Global Functions

Functions available in all templates.

### `asset_url(path)`

Generates a fingerprint-aware URL for an asset.

```jinja2
<link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
{# Outputs: /assets/css/style.a1b2c3d4.css #}
```

### `url_for(page_or_slug)`

Generates a URL for a page object or slug.

```jinja2
<a href="{{ url_for(page) }}">Link</a>
```

### `dateformat(date, format)`

Formats a date object.

```jinja2
{{ dateformat(page.date, "%B %d, %Y") }}
```

### `get_menu(menu_name)`

Retrieves a navigation menu.

```jinja2
{% for item in get_menu('main') %}
  <a href="{{ item.href }}">{{ item.name }}</a>
{% endfor %}
```

### `get_nav_tree(page)`

Builds navigation tree with active trail marking. Returns a list of navigation items for sidebar menus.

```jinja2
{% for item in get_nav_tree(page) %}
  <a href="{{ item.href }}"
     {% if item.is_current %}class="active"{% endif %}>
    {{ item.title }}
  </a>
{% endfor %}
```

## Template Helpers

Bengal includes categorized helper modules:

- **Strings**: `truncate`, `slugify`, `markdownify`
- **Collections**: `where`, `group_by`, `sort_by`
- **Dates**: `time_ago`, `date_iso`
- **Images**: `image_processed`, `image_url`
- **Taxonomies**: `related_posts`, `popular_tags`

:::{tip}
**Debugging**
You can inspect available variables by printing them in a comment:
`<!-- {{ page.metadata }} -->`
:::

:::{seealso}
- [Template Functions](/docs/theming/templating/functions/) — Filter and function reference
- [Templating](/docs/theming/templating/) — Template basics
:::
