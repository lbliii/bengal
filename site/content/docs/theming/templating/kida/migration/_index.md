---
title: Migration
description: Migrating to Kida from Jinja2
weight: 30
icon: arrow-right
---

# Migration

Most Jinja2 templates work without changes in Kida. Migrate incrementally to use unified `{% end %}` blocks, pattern matching, and pipeline operators. Note that Kida does not support all Jinja2 features (notably `{% macro %}`—use `{% def %}` instead). If you need full Jinja2 compatibility, use the Jinja2 engine by setting `template_engine: jinja2` in your config.

## Migration Strategy

1. **Compatibility Mode** — Existing Jinja2 templates work as-is
2. **Gradual Migration** — Convert templates incrementally as you edit them
3. **Full Migration** — Use Kida syntax throughout

## Quick Syntax Changes

| Jinja2 | Kida |
|--------|------|
| `{% endif %}`, `{% endfor %}` | `{% end %}` |
| `{% set x = ... %}` | `{% let x = ... %}` |
| `{% if %}...{% elif %}` | `{% match %}...{% case %}` |
| `\| selectattr('key', 'eq', val)` | `\|> where('key', val)` |
| `\| sort(attribute='key')` | `\|> sort_by('key')` |
| `\| default(value)` | `?? value` (simple) |

:::{note}
**Template Functions**: `where` and `sort_by` are Bengal template functions (not Kida built-ins) that are automatically available in all templates. They work with both `\|` (Jinja2-style) and `\|>` (Kida pipeline) operators.
:::

## Topics

:::{child-cards}
:columns: 1
:::
