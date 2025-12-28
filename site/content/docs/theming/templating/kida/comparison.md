---
title: Kida vs Jinja2 Comparison
nav_title: Comparison
description: Feature-by-feature comparison of Kida and Jinja2
weight: 25
type: doc
draft: false
lang: en
tags:
- reference
- kida
- comparison
category: reference
---

# Kida vs Jinja2 Comparison

Kida parses Jinja2 syntax, so existing templates work without changes. This page compares features and syntax for migration planning.

## Quick Reference

| Feature | Kida | Jinja2 |
|---------|------|--------|
| Block endings | `{% end %}` | `{% endif %}`, `{% endfor %}`, etc. |
| Template variables | `{% let %}` (template-scoped) | `{% set %}` (block-scoped) |
| Pattern matching | `{% match %}...{% case %}` | `{% if %}...{% elif %}` |
| Pipeline operator | `\|>` | Not available |
| Optional chaining | `?.` | Not available |
| Null coalescing | `??` | `\| default()` |
| Fragment caching | `{% cache %}` | Extension required |
| Functions | `{% def %}` (lexical scope) | `{% macro %}` (no closure) |
| Range literals | `1..10` | `range(1, 11)` |
| Loop control | `{% break %}`, `{% continue %}` | Limited |

## Performance

| Metric | Kida | Jinja2 |
|--------|------|--------|
| Render speed | 5.6x faster | Baseline |
| Compilation | AST-to-AST | String-based |
| Free-threading | GIL-independent | GIL-bound |
| Block caching | Automatic | Manual/None |
| HTML escaping | O(n) | O(5n) |

## Detailed Comparisons

For detailed comparisons, see the [Kida vs Jinja2 Comparison (Legacy)](./kida-vs-jinja-comparison.md) page, which includes comprehensive side-by-side examples of:

- **Syntax**: Block endings, variables, expressions
- **Control Flow**: Conditionals, loops, pattern matching
- **Variables**: Scoping, `let` vs `set`, exports
- **Functions**: `def` vs `macro`, lexical scope
- **Filters**: Pipeline operator, filter names
- **Caching**: Fragment caching, automatic blocks

## Filter Name Mapping

| Jinja2 | Kida | Description |
|--------|------|-------------|
| `selectattr('key')` | `where('key', true)` | Boolean filter |
| `selectattr('key', 'eq', val)` | `where('key', val)` | Equality filter |
| `rejectattr('key')` | `where_not('key', true)` | Inverse boolean |
| `sort(attribute='key')` | `sort_by('key')` | Sort by attribute |
| `batch(n) \| first` | `take(n)` | First n items |
| `groupby('key')` | `group_by('key')` | Group by attribute |

## When to Use Which

**Kida:**
- Sites with 100+ pages (automatic caching)
- Free-threaded Python (3.14t+)
- You want modern syntax
- Cold start matters (serverless)

**Jinja2:**
- 100% extension compatibility required
- Small sites (<50 pages)
- Committed to Jinja2 ecosystem

## Migration

1. Enable Kida (default in Bengal)
2. Existing templates work as-is
3. Convert to Kida syntax as you edit files

See [Migration Guide](./migrate-jinja-to-kida.md) for step-by-step instructions.

:::{seealso}
- [Migration Guide](./migrate-jinja-to-kida.md) — Step-by-step conversion
- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax
:::
