---
title: Kida vs Jinja2 Comparison
nav_title: Comparison
description: Feature-by-feature comparison of Kida and Jinja2 template engines
weight: 25
type: doc
draft: false
lang: en
tags:
- reference
- kida
- jinja
- comparison
keywords:
- kida vs jinja
- template comparison
- migration
category: reference
---

# Kida vs Jinja2 Comparison

Side-by-side comparison of Kida and Jinja2 template engines. Use this reference when migrating templates or evaluating Kida for your project.

:::{tip}
**Kida is Jinja2-compatible**: Your existing Jinja2 templates work without changes. Kida can parse Jinja2 syntax automatically, so you can migrate incrementally.
:::

## Quick Reference

| Feature | Kida | Jinja2 |
|---------|------|--------|
| **Performance** | 5.6x faster | Baseline |
| **Block endings** | `{% end %}` (unified) | `{% endif %}`, `{% endfor %}`, etc. |
| **Template variables** | `{% let %}` (template-scoped) | `{% set %}` (block-scoped) |
| **Pattern matching** | `{% match %}...{% case %}` | `{% if %}...{% elif %}` chains |
| **Pipeline operator** | `\|>` (left-to-right) | `\|` (filter chain) |
| **Optional chaining** | `?.` | Not available |
| **Null coalescing** | `??` or `\| default()` | `\| default()` |
| **Fragment caching** | `{% cache %}` (built-in) | Requires extension |
| **Functions** | `{% def %}` (lexical scope) | `{% macro %}` (no closure) |
| **Range literals** | `1..10`, `1...11`, `1..10 by 2` | `range(1, 11)` |
| **Loop control** | `{% break %}`, `{% continue %}` | Limited support |
| **Free-threading** | Optimized | GIL-bound |
| **Compilation** | AST-to-AST | String-based |
| **Automatic caching** | Site-scoped blocks | Manual/None |

## Detailed Comparisons

:::{cards}
:columns: 2
:gap: medium

:::{card} Syntax Comparison
:icon: code
:link: ./comparison/syntax
:description: Side-by-side syntax comparison for common template patterns
:color: blue
:::{/card}

:::{card} Control Flow
:icon: code-branch
:link: ./comparison/control-flow
:description: Conditionals, loops, and pattern matching comparison
:color: purple
:::{/card}

:::{card} Variables and Scoping
:icon: variables
:link: ./comparison/variables
:description: Variable scoping, template variables, and exports
:color: green
:::{/card}

:::{card} Functions and Macros
:icon: function
:link: ./comparison/functions
:description: Functions vs macros, lexical scoping, and component patterns
:color: orange
:::{/card}

:::{card} Filters and Pipelines
:icon: filter
:link: ./comparison/filters
:description: Filter syntax, pipeline operator, and collection operations
:color: teal
:::{/card}

:::{card} Caching
:icon: zap
:link: ./comparison/caching
:description: Fragment caching, automatic block caching, and optimization
:color: indigo
:::{/card}

:::{card} Modern Features
:icon: sparkles
:link: ./comparison/modern-features
:description: Optional chaining, null coalescing, range literals, and more
:color: cyan
:::{/card}

:::{card} Performance
:icon: tachometer-alt
:link: ./comparison/performance
:description: Benchmarks, optimization strategies, and real-world performance
:color: red
:::{/card}

:::{/cards}

## When to Use Kida

**Use Kida when**:
- ✅ You need maximum performance (5.6x faster)
- ✅ You're building large sites (100+ pages)
- ✅ You're using free-threaded Python (3.14t+)
- ✅ You want modern syntax features
- ✅ You need automatic caching
- ✅ You want better error messages

**Use Jinja2 when**:
- ✅ You need 100% Jinja2 compatibility (Kida is mostly compatible)
- ✅ You're using extensions that require Jinja2 internals
- ✅ You have a small site (<50 pages) where performance doesn't matter
- ✅ You're already heavily invested in Jinja2 ecosystem

## Migration Path

Kida is **Jinja2-compatible**, so you can migrate incrementally:

1. **Start using Kida**: Enable Kida in `bengal.yaml` (it's the default)
2. **Existing templates work**: Kida can parse Jinja2 syntax automatically
3. **Migrate incrementally**: Convert templates to Kida syntax as you touch them
4. **Unlock performance**: Automatic caching and modern features available immediately

See the [Migration Guide](/docs/theming/templating/kida/migrate-jinja-to-kida/) for step-by-step instructions.

## Key Differences Summary

### Performance

- **Kida**: 5.6x faster rendering, automatic block caching, bytecode caching
- **Jinja2**: Baseline performance, manual caching required

### Syntax

- **Kida**: Modern syntax (`{% end %}`, `{% match %}`, `|>`), Jinja2-compatible
- **Jinja2**: Traditional syntax (`{% endif %}`, `{% endfor %}`, `|`)

### Architecture

- **Kida**: AST-to-AST compilation, StringBuilder rendering, free-threading ready
- **Jinja2**: String-based compilation, generator rendering, GIL-bound

### Features

- **Kida**: Built-in caching, pattern matching, pipeline operator, optional chaining
- **Jinja2**: Extensions required for caching, no pattern matching, traditional filters

## Next Steps

- **Migrate from Jinja2**: [Migration Guide](/docs/theming/templating/kida/migrate-jinja-to-kida/)
- **Learn Kida syntax**: [Syntax Reference](/docs/reference/kida-syntax/)
- **See performance benchmarks**: [Performance Guide](/docs/theming/templating/kida/performance/)

:::{seealso}
- [Kida Overview](/docs/theming/templating/kida/overview/) — Why Kida is production-ready
- [Kida Architecture](/docs/theming/templating/kida/architecture/) — How Kida works
- [Kida Performance](/docs/theming/templating/kida/performance/) — Benchmarks and optimization
:::
