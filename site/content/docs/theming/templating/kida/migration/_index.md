---
title: Migration
description: Migrating to Kida from Jinja2
weight: 30
icon: arrow-right
---

# Migration

Kida is Jinja2-compatible: your existing templates work without changes. Migrate incrementally to use unified `{% end %}` blocks, pattern matching, and pipeline operators.

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
