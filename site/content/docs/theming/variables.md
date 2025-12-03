---
title: Theme Variables Reference
description: Complete reference of all variables available in Jinja2 templates
weight: 40
draft: false
lang: en
tags: [reference, templates, variables, jinja2]
keywords: [theme variables, templates, jinja2, site, page]
category: reference
aliases:
  - /docs/reference/theme-variables/
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
| `page.url` | `str` | URL with baseurl applied (for display in templates) |
| `page.relative_url` | `str` | Relative URL without baseurl (for comparisons) |
| `page.permalink` | `str` | Alias for `url` (backward compatibility) |
| `page.metadata` | `dict` | All frontmatter keys |
| `page.toc` | `str` | Auto-generated Table of Contents |
| `page.is_home` | `bool` | True if homepage |
| `page.is_section` | `bool` | True if section index |

#### URL Properties

Bengal provides three URL properties with clear purposes:

**`page.url`** - **Primary property for display**
- Automatically includes baseurl (e.g., `/bengal/docs/page/`)
- Use in `<a href>`, `<link>`, `<img src>` attributes
- Works correctly for all deployment scenarios

**`page.relative_url`** - **For comparisons and logic**
- Relative URL without baseurl (e.g., `/docs/page/`)
- Use for comparisons: `{% if page.relative_url == '/docs/' %}`
- Use for menu activation, filtering, and conditional logic

**`page.permalink`** - **Backward compatibility**
- Alias for `url` (same value)
- Maintained for compatibility with existing themes

**Example Usage:**

```jinja2
{# Display URL (includes baseurl) #}
<a href="{{ page.url }}">{{ page.title }}</a>

{# Comparison (without baseurl) #}
{% if page.relative_url == '/docs/' %}
  <span class="active">Current Section</span>
{% endif %}
```

## Global Functions

Functions available in all templates.

### `asset_url(path)`

Generates a fingerprint-aware URL for an asset.

```html
<link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
<!-- Outputs: /assets/css/style.a1b2c3d4.css -->
```

### `url_for(page_or_slug)`

Generates a URL for a page object or slug.

```html
<a href="{{ url_for(page) }}">Link</a>
```

### `dateformat(date, format)`

Formats a date object.

```html
{{ dateformat(page.date, "%B %d, %Y") }}
```

### `get_menu(menu_name)`

Retrieves a navigation menu.

```html
{% for item in get_menu('main') %}
  <a href="{{ item.url }}">{{ item.name }}</a>
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

## See Also

- [Template Functions](/docs/theming/templating/functions/) — Filter and function reference
- [Templating](/docs/theming/templating/) — Template basics

