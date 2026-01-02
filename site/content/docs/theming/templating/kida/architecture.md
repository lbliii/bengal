---
title: Kida Architecture
nav_title: Architecture
description: Compilation pipeline, AST structure, and rendering implementation
weight: 15
type: doc
draft: false
lang: en
tags:
- explanation
- kida
- architecture
category: explanation
---

# Kida Architecture

Kida compiles templates through a multi-stage pipeline: Lexer → Parser → Compiler → Bytecode Cache. Each stage produces immutable data structures, enabling thread-safe compilation and rendering.

## Compilation Pipeline

```
Template Source
      │
      ▼
┌─────────────┐
│   Lexer     │  O(n) single-pass tokenization
│             │  Dict-based operator lookup
└─────┬───────┘
      │
      ▼
┌─────────────┐
│   Parser    │  Recursive descent, no backtracking
│             │  Immutable AST nodes (frozen dataclasses)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  Compiler   │  O(1) dispatch → Python ast.Module
│             │  LOAD_FAST caching, line markers
└─────┬───────┘
      │
      ▼
┌─────────────┐
│ Bytecode    │  Persistent cache, version-aware
│   Cache     │  invalidation
└─────┬───────┘
      │
      ▼
   Template    Immutable, thread-safe render()
```

## Stage 1: Lexer

Tokenizes template source in a single pass.

**Input:**
```kida
Hello, {{ name }}!
```

**Output tokens:**
```
Data("Hello, ")
OutputStart
Name("name")
OutputEnd
Data("!")
```

**Implementation:**
- Compiled regex patterns at class level (shared, immutable)
- Dict-based operator lookup: `{{`, `}}`, `{%`, `%}` → O(1)

Source: `bengal/rendering/kida/lexer.py`

## Stage 2: Parser

Builds an immutable Kida AST using recursive descent.

**AST node types:**

| Category | Nodes |
|----------|-------|
| Structure | `Template`, `Extends`, `Block`, `Include` |
| Control | `If`, `For`, `While`, `Match`, `Case` |
| Variables | `Set`, `Let`, `Export`, `Capture` |
| Functions | `Def`, `CallBlock`, `Slot` |
| Expressions | `Const`, `Name`, `Getattr`, `FuncCall`, `Filter`, `Pipeline` |
| Output | `Output`, `Data` |

**Example AST:**

```python
Template(
    body=[
        Data(value="Hello, ", lineno=1, col_offset=0),
        Output(
            expr=Name(name="name", lineno=1, col_offset=9),
            lineno=1, col_offset=7
        ),
        Data(value="!", lineno=1, col_offset=16)
    ]
)
```

All nodes are frozen dataclasses with `lineno` and `col_offset` for error reporting.

Source: `bengal/rendering/kida/parser/core.py`

## Stage 3: Compiler

Transforms Kida AST to Python `ast.Module`.

### AST-to-AST vs String-Based

```
Jinja2: Kida AST → Python source string → compile() → Code object
Kida:   Kida AST → Python ast.Module → compile() → Code object
```

Direct AST generation eliminates string manipulation overhead and preserves source locations for precise error reporting.

### Generated Code Pattern

```python
def render(ctx, _blocks=None):
    if _blocks is None: _blocks = {}
    _e = _escape          # LOAD_FAST (cached)
    _s = _str
    buf = []
    _append = buf.append  # Method lookup cached

    _append("Hello, ")
    _append(_e(_s(ctx.get("name", ""))))
    _append("!")

    return ''.join(buf)   # O(n) join
```

**Optimizations:**
- `_e`, `_s`, `_append` cached as locals (LOAD_FAST vs LOAD_GLOBAL)
- Single `''.join(buf)` at return (O(n) vs O(n²) concatenation)
- Line markers injected only for error-prone nodes

Source: `bengal/rendering/kida/compiler/core.py`

## Stage 4: Bytecode Cache

Caches compiled bytecode to disk using Python's `marshal` format.

- Cache key: Template path + content hash + Kida version
- Location: `.bengal/cache/kida/`
- Invalidation: Automatic on template change or Kida upgrade

Cold start reduction: ~90% (no recompilation on subsequent builds)

## HTML Escaping

Kida escapes HTML in O(n) using `str.translate()`:

```python
_ESCAPE_TABLE = str.maketrans({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;",
})

def escape(s):
    if not _ESCAPE_CHECK.search(s):  # Fast path
        return s
    return s.translate(_ESCAPE_TABLE)
```

Compare to Jinja2's O(5n) approach (5 chained `.replace()` calls).

Source: `bengal/rendering/kida/utils/html.py`

## Thread Safety

Kida is thread-safe by design:

| Component | Thread Safety Mechanism |
|-----------|------------------------|
| AST nodes | Frozen dataclasses (immutable) |
| Rendering | Local state only (`buf = []`) |
| Bytecode cache | File-based, no shared state |

Kida is designed for thread-safe operation. All AST nodes are immutable, rendering uses only local state, and the bytecode cache uses atomic file operations.

:::{seealso}
- [Performance](/docs/theming/templating/kida/performance/) — Benchmarks and optimization strategies
- [Overview](/docs/theming/templating/kida/) — Why Kida exists
:::
