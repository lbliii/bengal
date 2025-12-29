---
title: Syntax
description: Kida template syntax reference
weight: 10
icon: code
---

Kida extends Jinja2 with pattern matching, pipeline operators, and unified block endings. Your existing Jinja2 templates work without changes—Kida parses both syntaxes.

## Quick Reference

| Feature | Kida | Jinja2 |
|---------|------|--------|
| Block endings | `{% end %}` | `{% endif %}`, `{% endfor %}`, etc. |
| Template variables | `{% let x = ... %}` | `{% set x = ... %}` |
| Pattern matching | `{% match %}...{% case %}` | `{% if %}...{% elif %}` |
| While loops | `{% while cond %}` | Not available |
| Pipeline operator | `\|>` | Not available |
| Optional chaining | `?.` | Not available |
| Null coalescing | `??` | `\| default()` |
| Fragment caching | `{% cache %}` | Extension required |
| Functions | `{% def %}` (lexical scope) | `{% macro %}` (no closure) |
| Range literals | `1..10` | `range(1, 11)` |

## Topics

:::{child-cards}
:columns: 2
:::

:::{seealso}
- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Template Functions](/docs/reference/template-functions/) — Available filters and functions
:::
