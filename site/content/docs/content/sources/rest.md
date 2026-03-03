---
title: REST Source
description: Fetch content from REST APIs; frontmatter type expectations
weight: 30
category: guide
icon: cloud
tags:
- rest
- api
- content-source
keywords:
- RESTSource
- REST API
- content adapter
---

# REST Source

RESTSource fetches content from REST APIs that return JSON. Configure field mappings for content and frontmatter. Requires `pip install bengal[rest]` (aiohttp).

:::{note}
**Status**: ContentSource (including RESTSource) is not yet wired into the build pipeline. This doc describes the contract for when integration exists and for external/plugin use.
:::

## Frontmatter Types

Frontmatter values come from the API JSON response. Types are preserved as returned by `json.loads`:

| Field | Typical Type | Notes |
|-------|--------------|-------|
| title | str | |
| date | str or datetime | Use `| dateformat` in templates |
| weight | int or str | API may return `"5"`; use `| coerce_int` for arithmetic |
| tags | list | |
| slug | str | |

When templates use `page.weight` in arithmetic or `page.date | dateformat`, ensure types match. Apply `| coerce_int` for weight when the API returns a string.

## Configuration

```toml
[content_sources.rest]
url = "https://api.example.com/posts"
content_field = "body"
frontmatter_fields = { title = "title", date = "published_at", tags = "categories" }
```

## Related

- [Data Files](../data-files.md) — site.data type expectations and coercion
