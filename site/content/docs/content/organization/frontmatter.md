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

## Custom Fields

Any fields not part of Bengal's standard frontmatter are automatically available as custom fields. Simply add them at the top level of your frontmatter.

**Standard fields** (extracted to PageCore):
- `title`, `description`, `date`, `draft`, `weight`, `slug`, `url`, `aliases`, `lang`
- `tags`, `categories`, `keywords`, `authors`, `category`
- `type`, `variant`, `layout`, `template`
- `canonical`, `noindex`, `og_image`, `og_type`
- `menu`, `nav_title`, `parent`
- `cascade`, `outputs`, `resources`, `toc`

**Custom fields** (any other fields):
- Any field not listed above goes into `page.props`
- Access via `page.metadata.get('field_name')` or `page.props.get('field_name')`

**Example:**
```yaml
---
title: My Page
description: Page description
weight: 10
type: doc
icon: code
card_color: blue
custom_setting: value
---
```

Access custom fields via:
- `page.metadata.get('icon')` or `page.props.get('icon')`
- `page.metadata.get('card_color')`
- `page.metadata.get('custom_setting')`

**Note**: The `props:` key is only used in skeleton manifests (`bengal project skeleton apply`). For regular markdown files, use flat frontmatter (all fields at top level).

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
