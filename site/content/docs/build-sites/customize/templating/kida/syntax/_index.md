---


title: Syntax
description: Kida template syntax reference
weight: 10
icon: code
tags:
- persona-themer
aliases:
  - /docs/theming/templating/kida/syntax/
aliases:
  - /docs/build-sites/customize/templating/kida/syntax/
  - /docs/theming/templating/kida/syntax/
---

Kida extends Jinja2 with pattern matching, pipeline operators, and unified block endings. Your existing Jinja2 templates work without changes—Kida parses both syntaxes.

:::{note}
**Do I need this?** Use for Kida-specific syntax topics (operators, variables,
control flow). For a single-page overview, see [[docs/reference/kida-syntax|Kida Syntax]].
:::

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
| Functions | `{% def %}` (sees outer variables) | `{% def %}` (isolated) |
| Range literals | `1..10` | `range(1, 11)` |

## Topics

:::{child-cards}
:columns: 2
:::

:::{seealso}
- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Template Functions](/docs/reference/template-functions/) — Available filters and functions
:::
