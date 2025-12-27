---
title: Kida Architecture
nav_title: Architecture
description: Deep dive into Kida's AST-to-AST compilation pipeline and performance optimizations
weight: 15
type: doc
draft: false
lang: en
tags:
- explanation
- kida
- architecture
- compilation
keywords:
- kida architecture
- ast compilation
- template engine internals
- performance optimization
category: explanation
---

# Kida Architecture

Kida's architecture is designed for **performance, maintainability, and thread-safety**. Unlike traditional template engines that generate Python source strings, Kida uses **AST-to-AST compilation** to produce optimized, thread-safe template code.

## Compilation Pipeline

Kida transforms templates through a multi-stage pipeline:

```
Template Source
      │
      ▼
┌─────────────┐
│   Lexer     │  O(n) single-pass tokenization
│             │  • O(1) dict-based operator lookup
│             │  • Compiled regex patterns (class-level)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│   Parser    │  Recursive descent, no backtracking
│             │  • Immutable AST nodes (dataclasses)
│             │  • Source location tracking
└─────┬───────┘
      │
      ▼
┌─────────────┐
│ Optimizer   │  Pure-Python AST transformations
│ (optional)  │  • Constant folding
│             │  • Dead code elimination
│             │  • Data node coalescing
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  Compiler   │  O(1) dispatch → Python AST
│             │  • LOAD_FAST caching
│             │  • Line markers for errors
└─────┬───────┘
      │
      ▼
┌─────────────┐
│ Bytecode    │  Optional persistent cache
│   Cache     │  • 90%+ cold-start reduction
│             │  • Version-aware invalidation
└─────┬───────┘
      │
      ▼
   Template    Immutable, thread-safe render()
```

## Stage 1: Lexer

The lexer tokenizes template source into a stream of tokens.

**Key optimizations**:

- **O(n) single-pass**: Tokenizes the entire template in one pass
- **O(1) operator lookup**: Dict-based lookup for operators (`{{`, `}}`, `{%`, `%}`, etc.)
- **Compiled regex**: Regex patterns compiled at class level (immutable, shared)

**Example**:

```kida
Hello, {{ name }}!
```

**Tokens**:
```
Data("Hello, ")
OutputStart
Name("name")
OutputEnd
Data("!")
```

## Stage 2: Parser

The parser builds an immutable Kida AST from tokens using recursive descent parsing.

**Key features**:

- **No backtracking**: Predictive parsing based on token lookahead
- **Immutable AST**: All nodes are frozen dataclasses (thread-safe)
- **Source location**: Every node tracks `lineno` and `col_offset` for error reporting

**AST Node Types**:

- **Template Structure**: `Template`, `Extends`, `Block`, `Include`
- **Control Flow**: `If`, `For`, `While`, `Match`
- **Variables**: `Set`, `Let`, `Export`, `Capture`
- **Functions**: `Def`, `CallBlock`, `Slot`
- **Expressions**: `Const`, `Name`, `Getattr`, `FuncCall`, `Filter`, `Pipeline`
- **Output**: `Output`, `Data`

**Example AST**:

```python
Template(
    body=[
        Data(value="Hello, ", lineno=1, col_offset=0),
        Output(
            expr=Name(name="name", lineno=1, col_offset=9),
            lineno=1,
            col_offset=7
        ),
        Data(value="!", lineno=1, col_offset=16)
    ]
)
```

## Stage 3: Optimizer (Optional)

The optimizer performs compile-time optimizations on the Kida AST.

**Optimizations**:

- **Constant folding**: `{{ 2 + 3 }}` → `{{ 5 }}`
- **Dead code elimination**: Remove unreachable code paths
- **Data node coalescing**: Merge adjacent `Data` nodes
- **Buffer size estimation**: Pre-allocate buffer for known output size

**Example**:

```kida
{% if false %}
  This will never render
{% end %}
{{ 2 + 3 }}
```

**After optimization**:
- `if false` block removed (dead code elimination)
- `{{ 2 + 3 }}` → `{{ 5 }}` (constant folding)

## Stage 4: Compiler

The compiler transforms Kida AST into Python AST (`ast.Module`).

### AST-to-AST Compilation

**Jinja2 approach** (string-based):
```
Kida AST → Python source string → Code object
```

**Kida approach** (AST-to-AST):
```
Kida AST → Python AST → Code object
```

**Advantages**:
- **Structured manipulation**: No regex, no string parsing
- **Compile-time optimization**: Transform AST before compilation
- **Precise error mapping**: Source location preserved through compilation
- **No eval() security concerns**: Direct AST compilation

### Generated Code Pattern

Kida generates code using the **StringBuilder pattern**:

```python
def render(ctx, _blocks=None):
    if _blocks is None: _blocks = {}
    _e = _escape          # Cache for LOAD_FAST
    _s = _str
    buf = []
    _append = buf.append  # Cached method lookup

    # Template body...
    _append("Hello, ")
    _append(_e(_s(ctx.get("name", ""))))
    _append("!")

    return ''.join(buf)
```

**Performance optimizations**:

1. **LOAD_FAST caching**: `_e`, `_s`, `_append` cached as local variables (faster than `LOAD_GLOBAL`)
2. **Method lookup caching**: `_append = buf.append` cached once (avoids repeated attribute lookup)
3. **O(n) join**: Single `''.join(buf)` at return (vs O(n²) string concatenation)
4. **Line markers**: Injected only for error-prone nodes (Output, For, If, etc.)

### O(1) Dispatch

The compiler uses O(1) dict-based dispatch:

```python
dispatch = {
    "Data": self._compile_data,
    "Output": self._compile_output,
    "If": self._compile_if,
    "For": self._compile_for,
    ...
}

handler = dispatch[type(node).__name__]
handler(node)
```

### Mixin Architecture

The compiler uses mixins for maintainability:

- **OperatorUtilsMixin**: Binary/unary operator AST generation
- **ExpressionCompilationMixin**: Expressions, filters, tests, function calls
- **StatementCompilationMixin**: Control flow, blocks, macros, includes

## Stage 5: Bytecode Cache

Kida optionally caches compiled bytecode to disk for near-instant cold starts.

**Benefits**:
- **90%+ cold-start reduction**: Compiled templates cached, no recompilation needed
- **Version-aware invalidation**: Cache invalidated when Kida version changes
- **Serverless-friendly**: Critical for serverless applications

**Cache format**: Python's `marshal` format (fast, built-in)

## Rendering: StringBuilder Pattern

Kida uses the **StringBuilder pattern** for rendering, which is **25-40% faster** than Jinja2's generator-based approach.

### Jinja2 Approach (Generator)

```python
def render():
    yield "Hello, "
    yield escape(name)
    yield "!"
    # Concat all at end
```

**Overhead**:
- Generator suspension/resumption
- Final concatenation step

### Kida Approach (StringBuilder)

```python
def render(ctx):
    buf = []
    _append = buf.append  # Cached method lookup
    _e = _escape           # Cached function
    _append("Hello, ")
    _append(_e(ctx["name"]))
    _append("!")
    return ''.join(buf)
```

**Advantages**:
- **No generator overhead**: Direct list append
- **O(n) final join**: Single `''.join(buf)` operation
- **Cached lookups**: `_append`, `_e` cached as locals (LOAD_FAST vs LOAD_GLOBAL)

## HTML Escaping: O(n) Single-Pass

Kida uses `str.translate()` for O(n) HTML escaping, vs Jinja2's O(5n) chained `.replace()` calls.

### Jinja2 Approach

```python
def escape(s):
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    s = s.replace('"', "&quot;")
    s = s.replace("'", "&#39;")
    return s
```

**Complexity**: O(5n) - 5 passes over the string

### Kida Approach

```python
_ESCAPE_TABLE = str.maketrans({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;",
})

def escape(s):
    # Fast path: skip if no escapable chars
    if not _ESCAPE_CHECK.search(s):
        return s
    return s.translate(_ESCAPE_TABLE)
```

**Complexity**: O(n) - single pass with `str.translate()`

**Fast path**: Regex check to skip translation if no escapable characters found

## Thread Safety

Kida is **thread-safe by design**:

### Immutable AST

All AST nodes are frozen dataclasses:

```python
@dataclass(frozen=True)
class Template:
    body: list[Node]
    lineno: int
    col_offset: int
```

**Benefits**:
- No shared mutable state
- Safe for concurrent access
- Enables concurrent compilation

### Thread-Safe Rendering

Rendering uses only local state:

```python
def render(ctx, _blocks=None):
    buf = []  # Local to render call
    _append = buf.append  # Local variable
    # ... rendering code ...
    return ''.join(buf)
```

**No shared state**: Each render call has its own buffer, no locks needed

### Free-Threading Ready

Kida declares GIL independence via PEP 703:

```python
# In compiled template code
_Py_mod_gil = 0  # Declares GIL independence
```

**Result**: In Python 3.14t+, Kida templates can render concurrently without GIL contention

## Error Reporting

Kida provides **precise error reporting** with source location tracking.

### Source Location Tracking

Every AST node tracks its source location:

```python
@dataclass(frozen=True)
class Output:
    expr: Expression
    lineno: int      # Source line number
    col_offset: int   # Column offset
```

### Line Markers

The compiler injects line markers for error-prone nodes:

```python
# Generated code
ctx['_line'] = 5  # Set before Output node
_append(_e(ctx["name"]))  # If error occurs, we know it's line 5
```

**Result**: Errors include precise source location:

```
UndefinedError: 'name' is undefined
  File "template.html", line 5, column 9
    {{ name }}
         ^^^^
```

## Comparison with Jinja2

| Feature | Kida | Jinja2 |
|---------|------|--------|
| **Compilation** | AST-to-AST | String-based |
| **Rendering** | StringBuilder | Generator |
| **HTML Escape** | O(n) `str.translate()` | O(5n) chained `.replace()` |
| **Thread Safety** | Immutable AST, local state | Thread-safe (with GIL) |
| **Free-Threading** | GIL-independent | GIL-bound |
| **Error Reporting** | Precise source location | Line numbers |
| **Optimization** | Compile-time AST transforms | Limited |

## Next Steps

- **See performance benchmarks**: [Performance Guide](/docs/theming/templating/kida/performance/)
- **Learn the syntax**: [Syntax Reference](/docs/reference/kida-syntax/)
- **Try it hands-on**: [Tutorial](/docs/tutorials/getting-started-with-kida/)

:::{seealso}
- [Kida Overview](/docs/theming/templating/kida/overview/) — Why Kida is production-ready
- [Kida Performance](/docs/theming/templating/kida/performance/) — Benchmarks and optimization strategies
- [Kida Comparison](/docs/theming/templating/kida/comparison/) — Feature-by-feature comparison with Jinja2
:::
