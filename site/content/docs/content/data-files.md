---
title: Data Files
description: How site.data and get_data work; type expectations and coercion
weight: 25
category: guide
icon: database
tags:
- data
- site.data
- get_data
- yaml
- json
keywords:
- data files
- site.data
- get_data
- type coercion
---

# Data Files

Bengal loads JSON, YAML, and TOML files from your `data/` directory into `site.data`, and provides `get_data()` for ad-hoc loading. Values from these sources can have type uncertainty — use coercion when passing to numeric filters.

## How site.data Is Populated

The `data/` directory is scanned at build time. File paths map to nested keys:

| File Path | Template Access |
|-----------|-----------------|
| `data/authors.yaml` | `site.data.authors` |
| `data/team/members.json` | `site.data.team.members` |
| `data/products/resume.yaml` | `site.data.products.resume` |

Supported formats: `.json`, `.yaml`, `.yml`, `.toml`

## Type Expectations

YAML and JSON can produce different types for the same logical value:

- **YAML**: `count: 5` → int; `count: "5"` → string
- **JSON**: Preserves types as parsed (`5` → int, `"5"` → string)
- **No coercion at load** — Values pass through from file parsers

When using `site.data` or `get_data()` with filters that expect numeric params (e.g. `percentage`, `divided_by`, `times`), apply `| coerce_int` or use filters that coerce internally.

```kida
{# Safe: coerce before arithmetic #}
{{ site.data.stats.count | coerce_int(0) | times(100) }}

{# get_data returns {} on missing file #}
{% let products = get_data('data/products.json') %}
{% for p in products %}
  {{ p.price | coerce_int(0) | times(1.1) }}
{% end %}
```

## get_data

Load data from any path under the site root. Returns empty dict `{}` if the file is missing, invalid, or unsupported format.

```kida
{% let authors = get_data('data/authors.json') %}
{% let config = get_data('data/config.yaml') %}
```

## DotDict Behavior

`site.data` uses DotDict for dot-notation access. Missing keys return `""` (empty string), not `None`. Nested dicts are auto-wrapped.

## Related

- [Math & Data Functions](../../reference/template-functions/math-data-filters.md) — get_data, merge, get_nested, keys, values, items
- [Shortcodes](../../extending/shortcodes.md) — Shortcode context includes `site` and `site.data`
