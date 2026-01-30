---
title: Frontmatter Reference
nav_title: Frontmatter
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
| `weight` | integer | — | Sort order (lower = first). Pages without weight sort last. |
| `slug` | string | filename | URL slug override |
| `url` | string | — | Complete URL path override |
| `aliases` | list | `[]` | Additional URLs that redirect to this page |
| `lang` | string | site default | Language code for i18n (e.g., `en`, `fr`) |

## Taxonomy Fields

| Field | Type | Description |
|-------|------|-------------|
| `tags` | list | Tags for categorization (generates tag pages) |
| `category` | string | Single category for grouping (generates category pages) |
| `keywords` | list | SEO keywords (metadata only, no pages generated) |
| `author` | string/object | Page author (see Author Patterns below) |

:::{note}
Only `tags` and `category` generate taxonomy pages by default. Use `author` (singular) for author attribution.
:::

### Author Patterns

Bengal supports multiple author patterns for flexibility:

**Simple string** (reference to data registry):

```yaml
author: lbliii
```

**Nested object** (inline):

```yaml
author:
  name: Lawrence Lane
  github: lbliii
  bio: Technical writer and developer
```

**Multiple authors** (list of strings or objects):

```yaml
authors:
  - lbliii
  - name: Jane Smith
    github: janesmith
```

**Flat author fields** (legacy pattern):

```yaml
author: Lawrence Lane
author_avatar: /images/lawrence.jpg
author_title: Senior Developer
author_bio: Technical writer and developer
author_links:
  - text: GitHub
    url: https://github.com/lbliii
```

### Author Data Registry

Define authors once in `data/authors.yaml` and reference by key:

```yaml
# data/authors.yaml
lbliii:
  name: Lawrence Lane
  github: lbliii
  bio: Technical writer and developer
  avatar: /images/lawrence.jpg
```

Then reference in frontmatter:

```yaml
author: lbliii
```

Access in templates:

```jinja
{% let author_info = site.data.authors[page.metadata.author] %}
{{ author_info.name }} — {{ author_info.bio }}
```

## Component Model Fields

Bengal uses a Component Model where every page has three aspects: identity (`type`), appearance (`variant`), and data (`props`).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | — | Content type for sorting and template selection (e.g., `doc`, `blog`, `page`). Inherits from section cascade if not set. |
| `variant` | string | — | Visual presentation variant (e.g., `editorial`, `magazine`, `wide`, `overview`) |
| `layout` | string | — | Legacy field, normalized to `variant`. Use `variant` instead. |
| `template` | string | — | Explicit template path override (e.g., `blog/single.html`) |
| `nav_title` | string | `title` | Short title for navigation menus and sidebar |

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

Any fields not part of Bengal's standard frontmatter are automatically available as custom props. Add them at the top level of your frontmatter.

**Standard fields** (extracted to PageCore):
- `title`, `description`, `date`, `draft`, `weight`, `slug`, `url`, `aliases`, `lang`
- `tags`, `categories`, `keywords`, `authors`, `category`
- `type`, `variant`, `layout`, `template`
- `canonical`, `noindex`, `og_image`, `og_type`
- `menu`, `nav_title`, `parent`
- `cascade`, `outputs`, `resources`, `toc`

**Custom fields** (Component Model props):
- Any field not listed above goes into `page.props`
- Access in templates via `page.params` (includes all frontmatter) or `page.props` (custom fields only)

:::{example-label}
:::

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

Access custom fields in templates:

```jinja
{# page.params includes all frontmatter (standard + custom) #}
{{ page.params.icon }}
{{ page.params.get('card_color', 'default') }}

{# page.props contains only custom fields #}
{{ page.props.icon }}
```

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
type: tutorial
variant: wide
cascade:
  type: doc
difficulty: beginner
time_estimate: 15 minutes
---
```

In this example:
- Standard fields (`title`, `date`, `weight`, etc.) are extracted to PageCore
- `difficulty` and `time_estimate` are custom props accessible via `page.params`
- `cascade` propagates `type: doc` to all child pages

## Cascade Configuration

The `cascade` field applies values to all descendant pages:

```yaml
---
title: Documentation
cascade:
  type: doc
  variant: docs
  draft: false
---
```

All pages under this section inherit these values unless they override them. Page-level values always take precedence over cascaded values.
