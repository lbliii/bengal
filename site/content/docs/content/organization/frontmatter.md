---
title: Frontmatter Reference
description: Complete reference for all frontmatter fields
weight: 10
draft: false
lang: en
tags:
- frontmatter
- reference
- metadata
keywords:
- frontmatter
- yaml
- metadata
- fields
- reference
category: reference
---

# Frontmatter Reference

Complete reference for all frontmatter fields available in Bengal pages.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Page title, used in navigation and `<title>` tag |

## Common Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `description` | string | — | Page description for SEO and previews |
| `date` | datetime | file mtime | Publication date |
| `draft` | boolean | `false` | If `true`, page is excluded from production builds |
| `weight` | integer | `0` | Sort order (lower = first) |
| `slug` | string | filename | URL slug override |
| `url` | string | — | Complete URL path override |
| `aliases` | list | `[]` | Additional URLs that redirect to this page |

## Taxonomy Fields

| Field | Type | Description |
|-------|------|-------------|
| `tags` | list | Tags for categorization |
| `categories` | list | Categories for grouping |
| `keywords` | list | SEO keywords |
| `authors` | list | Page authors |

## Layout Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `layout` | string | — | Visual variant (maps to `data-variant` on body). To change the template file, use `template`. |
| `type` | string | section name | Content type (determines default strategy and template) |
| `template` | string | — | Explicit template path (e.g., `blog/single.html`) |

## SEO Fields

| Field | Type | Description |
|-------|------|-------------|
| `canonical` | string | Canonical URL for duplicate content |
| `noindex` | boolean | If `true`, adds `noindex` meta tag |
| `og_image` | string | Open Graph image path |
| `og_type` | string | Open Graph type (article, website, etc.) |

## Navigation Fields

| Field | Type | Description |
|-------|------|-------------|
| `menu` | object | Menu placement configuration |
| `nav_title` | string | Short title for navigation (falls back to `title`) |
| `parent` | string | Parent page for breadcrumbs |

## Advanced Fields

| Field | Type | Description |
|-------|------|-------------|
| `cascade` | object | Values to cascade to child pages |
| `outputs` | list | Output formats (html, rss, json) |
| `resources` | list | Page bundle resource metadata |

## Custom Fields (Props)

Custom fields that aren't part of Bengal's standard frontmatter should be placed under the `props:` key. This keeps standard fields separate from custom data, following the Component Model pattern.

**Standard fields** (extracted to PageCore):
- `title`, `description`, `date`, `draft`, `weight`, `slug`, `url`, `aliases`, `lang`
- `tags`, `categories`, `keywords`, `authors`, `category`
- `type`, `variant`, `layout`, `template`
- `canonical`, `noindex`, `og_image`, `og_type`
- `menu`, `nav_title`, `parent`
- `cascade`, `outputs`, `resources`

**Custom fields** (go into `props`):
- Any field not listed above
- Fields under `props:` in frontmatter

**Example:**
```yaml
---
title: My Page
description: Page description
weight: 10
type: doc
props:
  icon: code
  card_color: blue
  custom_setting: value
---
```

Access custom fields via:
- `page.props.get('icon')` or `page.metadata.get('icon')`
- `page.props.get('card_color')`
- `page.props.get('custom_setting')`

**Note**: You can also put custom fields at the top level (they'll automatically go into props), but using `props:` makes the separation explicit and clearer.

## Example

```yaml
---
title: Getting Started with Bengal
description: Learn how to install and configure Bengal for your first site
date: 2025-01-15
draft: false
weight: 10
tags: [tutorial, beginner]
categories: [Getting Started]
authors: [jane-doe]
layout: tutorial
cascade:
  type: doc
difficulty: beginner
time_estimate: 15 minutes
---
```

## Cascade Configuration

The `cascade` field applies values to all descendant pages:

```yaml
---
title: Documentation
cascade:
  type: doc
  layout: docs
  draft: false
---
```

All pages under this section inherit these values unless they override them.
