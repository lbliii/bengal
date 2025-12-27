# Kida: A Next-Generation Template Engine for Python

## Executive Summary

**Kida** is a pure-Python template engine designed from the ground up for **free-threaded Python (3.14t+)** and optimized for performance. It serves as the native templating layer within the Bengal static site generator, achieving **5.6x faster rendering than Jinja2** (arithmetic mean) with zero external C dependencies.

**Key differentiators:**

- **AST-to-AST compilation**: Generates Python `ast.Module` objects directly (no string manipulation)
- **StringBuilder pattern**: O(n) output construction vs O(n²) string concatenation
- **Free-threading ready**: Declares GIL independence via PEP 703's `_Py_mod_gil = 0`
- **Compile-time optimizations**: Constant folding, dead code elimination, filter inlining
- **Bytecode caching**: Near-instant cold starts for serverless environments

---

## Architecture Overview

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
│             │  • Frozenset for type matching
│             │  • Immutable AST nodes (dataclasses)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│ Optimizer   │  Pure-Python AST transformations
│ (optional)  │  • Constant folding
│             │  • Dead code elimination
│             │  • Data node coalescing
│             │  • Buffer size estimation
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  Compiler   │  O(1) dispatch table → Python AST
│             │  • LOAD_FAST caching (_e, _s, _append)
│             │  • Line markers for error context
└─────┬───────┘
      │
      ▼
┌─────────────┐
│ Bytecode    │  Optional persistent cache (marshal)
│   Cache     │  • 90%+ cold-start reduction
│             │  • Version-aware invalidation
└─────┬───────┘
      │
      ▼
   Template    Immutable, thread-safe render()
```

---

## Performance Benchmarks

**Test conditions**: Both engines with `autoescape=True`, Python 3.12

| Template Type | Kida | Jinja2 | Speedup |
|--------------|------|--------|---------|
| Simple `{{ name }}` | 0.005s | 0.045s | **8.9x** |
| Filter chain | 0.006s | 0.050s | **8.9x** |
| Conditionals `{% if %}` | 0.004s | 0.039s | **11.2x** |
| For loop (100 items) | 0.014s | 0.028s | **2.1x** |
| For loop (1000 items) | 0.013s | 0.024s | **1.8x** |
| Dict attr `{{ item.name }}` | 0.006s | 0.026s | **4.3x** |
| HTML escape heavy | 0.019s | 0.044s | **2.3x** |

**Summary**: Arithmetic mean **5.6x faster**, geometric mean **4.4x faster**, wins **7/7 benchmarks**.

---

## Key Differentiators from Jinja2

### 1. AST-to-AST Compilation

**Jinja2**: Template → Tokens → AST → Python source string → Code object

**Kida**: Template → Tokens → AST → Python `ast.Module` → Code object

This enables structured manipulation, compile-time optimization, and precise error source mapping without regex-based string manipulation.

### 2. StringBuilder Rendering Pattern

**Jinja2** (generator yields):

```python
def render():
    yield "Hello, "
    yield escape(name)
    yield "!"
    # Concat all at end
```

**Kida** (list append + join):

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

StringBuilder is **25-40% faster** due to no generator suspension overhead and O(n) final join.

### 3. O(n) HTML Escaping

**Jinja2**: 5 chained `.replace()` calls = O(5n)

**Kida**: Single-pass `str.translate()` = O(n)

```python
_ESCAPE_TABLE = str.maketrans({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;",
})

# Fast path: skip if no escapable chars
if not _ESCAPE_CHECK.search(s):
    return s
return s.translate(_ESCAPE_TABLE)
```

### 4. Unified Block Syntax

Kida uses `{% end %}` for all block closings (like Go templates), eliminating mismatched tag errors:

```jinja
{% if condition %}
    {% for item in items %}
        {{ item }}
    {% end %}  {# Not {% endfor %} #}
{% end %}      {# Not {% endif %} #}
```

### 5. Explicit Variable Scoping

| Keyword | Scope | Jinja2 Equivalent |
|---------|-------|-------------------|
| `{% set x = val %}` | Block-scoped | `{% set x = val %}` |
| `{% let x = val %}` | Template-wide | `namespace()` workaround |
| `{% export x = val %}` | Escape inner scope | No equivalent |

### 6. Native Pipeline Operator

```jinja
{# Kida - readable left-to-right flow #}
{{ items |> where(published=true) |> sort_by("date") |> take(5) }}

{# Jinja2 - deeply nested, read inside-out #}
{{ items | selectattr("published") | sort(attribute="date") | first }}
```

---

## Kida-Native Features

### Pattern Matching

```jinja
{% match page.type %}
    {% case "post" %}<i class="icon-pen"></i>
    {% case "gallery" %}<i class="icon-image"></i>
    {% case _ %}<i class="icon-file"></i>
{% end %}
```

### Built-in Fragment Caching

```jinja
{% cache "sidebar-" ~ site.nav_version %}
    {{ build_nav_tree(site.pages) }}
{% end %}

{% cache "weather", ttl="5m" %}
    {{ fetch_weather() }}
{% end %}
```

### True Functions (Not Macros)

```jinja
{% def card(item) %}
    <div>{{ item.title }}</div>
    <span>From: {{ site.title }}</span>  {# Lexical scope access #}
{% end %}

{{ card(page) }}
```

### Modern Syntax (RFC: kida-modern-syntax-features)

| Feature | Syntax | Purpose |
|---------|--------|---------|
| Optional chaining | `obj?.attr` | Safe attribute access |
| Null coalescing | `a ?? b` | Fallback for None |
| Range literals | `1..10`, `1...11` | Inclusive/exclusive ranges |
| Break/Continue | `{% break %}` | Loop control |
| Spaceless | `{% spaceless %}` | Remove HTML whitespace |
| Embed | `{% embed 'card.html' %}` | Include with block overrides |

---

## Optimizer Pipeline

The `ASTOptimizer` applies pure-Python transformations before compilation:

### 1. Constant Folding

```jinja
{# Before #}
{{ 60 * 60 * 24 }}
{{ "Hello" ~ " " ~ "World" }}

{# After (compile-time) #}
{{ 86400 }}
{{ "Hello World" }}
```

**Impact**: 5-15% speedup on math-heavy templates

### 2. Dead Code Elimination

```jinja
{# Before #}
{% if false %}
    <div class="debug">{{ dump(context) }}</div>
{% end %}

{# After: completely removed #}
```

**Impact**: 10-30% speedup when debug blocks are present

### 3. Data Node Coalescing

Adjacent static text nodes are merged to reduce `_append()` calls:

```python
# Before: 3 calls
_append('<div class="card">\n    <h2>Title</h2>\n')
_append('</div>\n')

# After: 1 call  
_append('<div class="card">\n    <h2>Title</h2>\n</div>\n')
```

**Impact**: 5-10% reduction in function calls

### 4. Filter Inlining (Optional)

Simple pure filters become direct method calls:

```python
# Before: filter dispatch
_filters['upper'](ctx["name"])

# After: direct call
str(ctx["name"]).upper()
```

**Impact**: 5-10% speedup for filter-heavy templates

---

## Bytecode Cache

Eliminates cold-start compilation penalty (critical for serverless):

```python
from pathlib import Path
from bengal.rendering.kida import Environment
from bengal.rendering.kida.bytecode_cache import BytecodeCache

env = Environment(
    bytecode_cache=BytecodeCache(Path(".bengal-cache/kida"))
)

# First request: compile + cache (~10-50ms per template)
# Subsequent: marshal.load (~0.5ms per template)
# Warm cache: instant (~0.01ms)
```

**Features**:

- Python version tagging prevents cross-version bytecode errors
- SHA-256 source hashing for automatic invalidation
- Atomic file writes (temp + rename pattern)
- Multi-process safe

---

## Thread-Safety & Free-Threading

Kida declares GIL independence for Python 3.14t+:

```python
# In __init__.py
def __getattr__(name: str) -> object:
    if name == "_Py_mod_gil":
        return 0  # Py_MOD_GIL_NOT_USED
    raise AttributeError(...)
```

**Thread-safety characteristics**:

| Component | Strategy |
|-----------|----------|
| Template compilation | Immutable AST, new objects per parse |
| Filter/test registration | Copy-on-write dicts |
| Template cache | Lock-free LRU with atomic operations |
| Render execution | Local-only state (buf list) |
| Environment config | Immutable after `__post_init__` |

---

## AST Node System

50+ immutable frozen dataclass nodes covering:

**Template Structure**: `Template`, `Extends`, `Block`, `Include`, `Import`

**Control Flow**: `If`, `For`, `While`, `AsyncFor`, `Match`

**Variables**: `Set` (block-scoped), `Let` (template-scoped), `Export`, `Capture`

**Functions**: `Def`, `Slot`, `CallBlock`, `Macro` (Jinja compat)

**Expressions**: `Const`, `Name`, `BinOp`, `UnaryOp`, `Compare`, `Filter`, `Pipeline`, `CondExpr`, `NullCoalesce`

**Special**: `Cache`, `Raw`, `Trim`, `Spaceless`, `Break`, `Continue`

All nodes are frozen for thread-safety:

```python
@dataclass(frozen=True, slots=True)
class If(Node):
    test: Expr
    body: Sequence[Node]
    elif_: Sequence[tuple[Expr, Sequence[Node]]] = ()
    else_: Sequence[Node] = ()
```

---

## Error Handling

Runtime errors are enhanced with template context:

```
TemplateRuntimeError: 'NoneType' has no attribute 'title'
  Location: article.html:15
  Expression: {{ post.title }}
  Values:
    post = None (NoneType)
  Suggestion: Check if 'post' is defined before accessing .title
```

**Strict mode** (default): Undefined variables raise `UndefinedError` instead of silently returning empty string:

```python
env = Environment()  # strict=True by default

env.from_string("{{ typo_var }}").render()
# UndefinedError: Undefined variable 'typo_var' in <template>:1

env.from_string("{{ optional | default('N/A') }}").render()
# 'N/A'
```

---

## Built-in Filters

**70+ filters** organized by category:

| Category | Examples |
|----------|----------|
| String | `capitalize`, `lower`, `upper`, `truncate`, `trim`, `replace` |
| HTML/Security | `escape`/`e`, `safe`, `striptags` |
| Collections | `first`, `last`, `sort`, `reverse`, `unique`, `groupby`, `join` |
| Functional | `map`, `select`, `reject`, `selectattr`, `rejectattr` |
| Numbers | `abs`, `round`, `int`, `float`, `filesizeformat` |
| Type Conversion | `string`, `list`, `tojson` |
| Validation | `default`/`d`, `require` |

All filters are None-resilient (like Hugo):

```jinja
{{ none | default('N/A') }}  {# → 'N/A' #}
{{ none | length }}          {# → 0 #}
```

---

## Jinja2 Compatibility

The `kida.compat.jinja` module provides a `JinjaParser` that translates Jinja2 syntax to Kida AST:

```python
from bengal.rendering.kida.compat.jinja import JinjaParser

parser = JinjaParser(tokens, source=source)
kida_ast = parser.parse()  # Translates {% endif %} → {% end %}, etc.
```

---

## Usage Examples

### Basic Usage

```python
from bengal.rendering.kida import Environment

env = Environment()
template = env.from_string("Hello, {{ name }}!")
template.render(name="World")  # 'Hello, World!'
```

### File-based Templates

```python
from bengal.rendering.kida import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates/"))
template = env.get_template("index.html")
template.render(page=page, site=site)
```

### Custom Filters

```python
env.add_filter("money", lambda x, currency="$": f"{currency}{x:,.2f}")

# Or with decorator
@env.filter()
def double(value):
    return value * 2
```

### Optimization Debugging

```python
from bengal.rendering.kida.optimizer import ASTOptimizer

optimizer = ASTOptimizer()
result = optimizer.optimize(ast)

print(result.stats.summary())
# "3 constants folded; 1 dead blocks removed; 5 data nodes merged"
```

---

## Configuration

```python
env = Environment(
    # Template loading
    loader=FileSystemLoader("templates/"),

    # Security
    autoescape=True,           # HTML escape by default
    strict=True,               # Raise on undefined variables

    # Performance
    optimized=True,            # Enable AST optimizations
    cache_size=400,            # LRU template cache
    bytecode_cache=BytecodeCache(Path(".cache/kida")),

    # Syntax customization
    block_start="{%", block_end="%}",
    variable_start="{{", variable_end="}}",
    trim_blocks=True, lstrip_blocks=True,

    # Caching
    fragment_cache_size=1000,  # {% cache %} entries
    fragment_ttl=300.0,        # Fragment TTL (5 min)
)
```

---

## Complexity Analysis

All operations are designed for **O(n)** template processing where n = template size.

| Stage | Complexity | Notes |
|-------|------------|-------|
| Lexer | O(n) | Single-pass, O(1) operator lookup |
| Parser | O(t) | t = tokens ≈ O(n) |
| Compiler | O(a) | a = AST nodes ≈ O(n) |
| Render | O(n) | n = output size |
| Escape | O(n) | Single-pass translate |

**Space Complexity**: O(n) where n = max(source, output)

---

## Summary

Kida represents a ground-up rethinking of Python templating, optimized for:

1. **Performance**: 5.6x faster than Jinja2 through AST-to-AST compilation, StringBuilder rendering, and compile-time optimizations
2. **Modern Python**: Ready for free-threaded Python 3.14t with lock-free concurrent rendering
3. **Developer Experience**: Unified syntax, explicit scoping, pattern matching, and rich error messages
4. **Zero Dependencies**: Pure Python with optional bytecode caching—no C extensions or binary wheels

**Location**: `bengal/rendering/kida/` (~220 Python files covering lexer, parser, compiler, optimizer, environment, and template runtime)
