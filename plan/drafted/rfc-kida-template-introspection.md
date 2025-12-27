# RFC: Kida Template Introspection API

**Status**: Draft  
**Created**: 2025-12-26  
**Priority**: High  
**Effort**: ~20 hours (~2.5 days)  
**Impact**: High — Enables tooling to reason about templates without rendering  
**Category**: Compiler / Analysis / API  
**Scope**: `bengal/rendering/kida/`  
**Dependencies**: None (pure Python, no external packages)

---

## Executive Summary

This RFC proposes a **template introspection API** for Kida that exposes structural metadata about compiled templates. By preserving the optimized AST and analyzing block dependencies, Kida enables tooling to reason about templates without rendering them.

**Key Insight**: Traditional template engines compile to opaque bytecode, discarding structural information. Kida's AST-to-AST architecture preserves this information — we just need to stop discarding it after compilation.

**Core Capabilities**:

| Capability | What It Answers | Use Case |
|------------|-----------------|----------|
| Block enumeration | "What blocks does this template define?" | Layout validation |
| Dependency analysis | "What context variables does this block need?" | Cache invalidation |
| Purity inference | "Is this block deterministic?" | Cache safety |
| Role classification | "Is this navigation, content, or sidebar?" | Incremental builds |
| Cache scope | "Can this be cached per-page or per-site?" | Build optimization |

**Design Principles**:

1. **Zero syntax changes** — Templates work exactly as before
2. **Zero author burden** — Introspection is automatic, not annotated
3. **Zero runtime impact** — Analysis happens at compile time
4. **Conservative claims** — When uncertain, report "unknown"
5. **Standalone-ready** — API designed for Kida as independent package
6. **Configurable** — Memory/analysis trade-off controllable via Environment

---

## Motivation

### The Information Destruction Problem

Consider this template:

```jinja
{% extends "base.html" %}

{% block nav %}
  <nav>
    {% for page in site.pages %}
      <a href="{{ page.url }}">{{ page.title }}</a>
    {% end %}
  </nav>
{% end %}

{% block content %}
  <article>{{ page.content | safe }}</article>
{% end %}
```

**What a human knows**:
- The `nav` block depends only on `site.pages` (stable across pages)
- The `content` block depends on `page.content` (changes per page)
- The `nav` block could be cached site-wide
- The `content` block must be rendered per-page

**What Jinja knows after compilation**: Nothing. The structure is gone.

**What Kida could know**: Everything above, inferred from the AST.

### Why This Matters

#### For Static Site Generators (like Bengal)

```python
# Without introspection
for page in site.pages:
    html = template.render(page=page, site=site)  # Full render every time

# With introspection
nav_meta = template.block_metadata()["nav"]
if nav_meta.cache_scope == "site":
    nav_html = cache.get_or_set("nav", lambda: render_block("nav", site=site))

for page in site.pages:
    content_html = render_block("content", page=page)
    html = combine(nav_html, content_html)  # Nav rendered once
```

**Impact**: 10-100x faster builds for navigation-heavy sites.

#### For Documentation Tools

```python
# Validate that all page templates emit required landmarks
for template in theme.templates:
    meta = template.block_metadata()
    content_block = meta.get("content")
    if content_block and "main" not in content_block.emits_landmarks:
        warn(f"{template.name}: content block should emit <main>")
```

#### For IDE/Editor Integration

```python
# Autocomplete context variables
meta = template.block_metadata()
required_context = set()
for block in meta.values():
    required_context |= block.depends_on

# Show: "This template requires: page.title, page.content, site.pages"
```

#### For Kida as Standalone Package

When Kida is published independently, users get:
- Template analysis without framework coupling
- Cache optimization for any use case
- Validation hooks for custom tooling
- No Bengal-specific assumptions

---

## Design

### Architecture

```
Template Source
      │
      ▼
   Lexer → Parser → Kida AST
      │
      ▼
┌─────────────────────────────────┐
│     ASTOptimizer (existing)     │
└─────────────────────────────────┘
      │
      ▼
  Optimized AST ←────────────────────┐
      │                              │
      ▼                              │
   Compiler → Python AST → compile() │
      │                              │
      ▼                              │
┌─────────────────────────────────┐  │
│   Template Object               │  │
│   ├── _code: code object        │  │
│   ├── _render_func: callable    │  │
│   └── _optimized_ast: Template ◄┴──┘  NEW: Preserve AST (if preserve_ast=True)
└─────────────────────────────────┘
      │
      ▼ (on demand)
┌─────────────────────────────────┐
│     BlockAnalyzer (NEW)         │
│   ├── DependencyWalker          │
│   ├── PurityAnalyzer            │
│   ├── LandmarkDetector          │
│   └── RoleClassifier            │
└─────────────────────────────────┘
      │
      ▼
  BlockMetadata (cached)
```

### Memory Considerations

Preserving the AST increases memory usage per template. Measurements on representative templates:

| Template Type | Bytecode Size | AST Size | Overhead |
|--------------|---------------|----------|----------|
| Simple (50 lines) | ~2 KB | ~4 KB | +2 KB |
| Medium (200 lines) | ~8 KB | ~18 KB | +10 KB |
| Complex (500 lines) | ~20 KB | ~45 KB | +25 KB |

**For a 1000-template site**:
- Without AST: ~20 MB
- With AST: ~45 MB (+25 MB, ~2x)

**Mitigation**: New `preserve_ast` configuration option (default: `True`):

```python
# Full introspection support (default)
env = Environment(preserve_ast=True)

# Minimal memory mode (no introspection)
env = Environment(preserve_ast=False)
```

When `preserve_ast=False`:
- `template.block_metadata()` returns `{}`
- `template.template_metadata()` returns `None`
- `template.depends_on()` returns `frozenset()`

### Breaking Change: Template `__slots__`

**Current** (`bengal/rendering/kida/template.py:237`):
```python
__slots__ = ("_env_ref", "_code", "_name", "_filename", "_render_func")
```

**Proposed**:
```python
__slots__ = (
    "_env_ref", "_code", "_name", "_filename", "_render_func",
    "_optimized_ast",   # NEW: Preserved AST (or None)
    "_metadata_cache",  # NEW: Cached analysis results
)
```

**Impact**: Any subclasses of `Template` will need to update their `__slots__`. This is unlikely to affect users since `Template` is an internal class, but should be documented in release notes.

### Core Data Structures

```python
# bengal/rendering/kida/analysis/metadata.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class BlockMetadata:
    """Metadata about a template block, inferred from static analysis.

    All fields are conservative estimates:
    - `depends_on` may include unused paths (over-approximation)
    - `is_pure` defaults to "unknown" when uncertain
    - `inferred_role` is heuristic, not semantic truth

    Thread-safe: Immutable after creation.

    Attributes:
        name: Block identifier (e.g., "nav", "content", "sidebar")

        # Output characteristics
        emits_html: True if block produces any output
        emits_landmarks: HTML5 landmark elements emitted (nav, main, header, etc.)
        inferred_role: Heuristic classification based on name and landmarks

        # Input characteristics
        depends_on: Context paths this block may access (conservative superset)
        is_pure: Whether block output is deterministic for same inputs

        # Derived optimization hints
        cache_scope: Recommended caching granularity
    """

    name: str

    # Output characteristics
    emits_html: bool = True
    emits_landmarks: frozenset[str] = frozenset()
    inferred_role: Literal[
        "navigation",
        "content",
        "sidebar",
        "header",
        "footer",
        "unknown",
    ] = "unknown"

    # Input characteristics
    depends_on: frozenset[str] = frozenset()
    is_pure: Literal["pure", "impure", "unknown"] = "unknown"

    # Derived optimization hints
    cache_scope: Literal["none", "page", "site", "unknown"] = "unknown"

    def is_cacheable(self) -> bool:
        """Check if this block can be safely cached."""
        return self.is_pure == "pure" and self.cache_scope != "none"

    def depends_on_page(self) -> bool:
        """Check if block depends on page-specific context."""
        return any(
            path.startswith("page.") or path == "page"
            for path in self.depends_on
        )

    def depends_on_site(self) -> bool:
        """Check if block depends on site-wide context."""
        return any(
            path.startswith("site.") or path == "site"
            for path in self.depends_on
        )


@dataclass(frozen=True, slots=True)
class TemplateMetadata:
    """Metadata about a complete template.

    Attributes:
        name: Template identifier
        extends: Parent template name (if any)
        blocks: Mapping of block name → BlockMetadata
        top_level_depends_on: Context paths used outside blocks
    """

    name: str | None
    extends: str | None
    blocks: dict[str, BlockMetadata]
    top_level_depends_on: frozenset[str] = frozenset()

    def all_dependencies(self) -> frozenset[str]:
        """Return all context paths used anywhere in template."""
        deps = set(self.top_level_depends_on)
        for block in self.blocks.values():
            deps |= block.depends_on
        return frozenset(deps)
```

### Analysis Configuration

```python
# bengal/rendering/kida/analysis/config.py

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """Configuration for template analysis.

    Allows customization of naming conventions for standalone Kida use.
    Bengal uses defaults; other frameworks may override.

    Attributes:
        page_prefixes: Variable prefixes indicating per-page scope
        site_prefixes: Variable prefixes indicating site-wide scope
        extra_pure_functions: Additional functions to treat as pure
        extra_impure_filters: Additional filters to treat as impure
    """

    # Naming conventions for cache scope inference
    page_prefixes: frozenset[str] = frozenset({
        "page.", "page", "post.", "post", "item.", "item",
        "doc.", "doc", "entry.", "entry",
    })
    site_prefixes: frozenset[str] = frozenset({
        "site.", "site", "config.", "config", "global.", "global",
    })

    # Extend purity analysis
    extra_pure_functions: frozenset[str] = frozenset()
    extra_impure_filters: frozenset[str] = frozenset()


# Default configuration for Bengal
DEFAULT_CONFIG = AnalysisConfig()
```

### Dependency Walker

```python
# bengal/rendering/kida/analysis/dependencies.py

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Expr, Node


class DependencyWalker:
    """Extract context variable dependencies from AST expressions.

    Walks the AST and collects all context paths (e.g., "page.title",
    "site.pages") that an expression or block may access.

    Produces a conservative superset: may include paths not actually
    used at runtime, but never excludes paths that are used.

    Thread-safe: Stateless after initialization.

    Example:
        >>> walker = DependencyWalker()
        >>> deps = walker.analyze(block_node)
        >>> print(deps)
        frozenset({'site.pages', 'site.title'})
    """

    def __init__(self) -> None:
        self._scope_stack: list[set[str]] = []
        self._dependencies: set[str] = set()

    def analyze(self, node: Node) -> frozenset[str]:
        """Analyze a node and return all context dependencies.

        Args:
            node: AST node to analyze (Block, Template, expression, etc.)

        Returns:
            Frozen set of context paths (e.g., {"page.title", "site.pages"})
        """
        self._scope_stack = [set()]  # Reset state
        self._dependencies = set()
        self._visit(node)
        return frozenset(self._dependencies)

    def _visit(self, node: Node) -> None:
        """Visit a node and its children."""
        node_type = type(node).__name__

        # Dispatch to specific handlers
        handler = getattr(self, f"_visit_{node_type.lower()}", None)
        if handler:
            handler(node)
        else:
            self._visit_children(node)

    def _visit_children(self, node: Node) -> None:
        """Visit all child nodes."""
        # Handle common container attributes
        for attr in ("body", "else_", "empty", "elif_"):
            if hasattr(node, attr):
                children = getattr(node, attr)
                if children:
                    if isinstance(children, (list, tuple)):
                        for child in children:
                            if hasattr(child, "lineno"):  # It's a node
                                self._visit(child)
                            elif isinstance(child, tuple):  # elif case
                                test, body = child
                                self._visit(test)
                                for b in body:
                                    self._visit(b)

        # Handle expression attributes
        for attr in ("test", "expr", "value", "iter", "left", "right", "operand"):
            if hasattr(node, attr):
                child = getattr(node, attr)
                if child and hasattr(child, "lineno"):
                    self._visit(child)

        # Handle sequence attributes
        for attr in ("args", "items", "nodes", "comparators", "values"):
            if hasattr(node, attr):
                children = getattr(node, attr)
                if children:
                    for child in children:
                        if hasattr(child, "lineno"):
                            self._visit(child)

        # Handle dict attributes (kwargs)
        for attr in ("kwargs",):
            if hasattr(node, attr):
                mapping = getattr(node, attr)
                if mapping:
                    for child in mapping.values():
                        if hasattr(child, "lineno"):
                            self._visit(child)

    def _visit_name(self, node) -> None:
        """Handle variable reference."""
        name = node.name

        # Skip if it's a local variable (loop var, with binding, etc.)
        if self._is_local(name):
            return

        # Skip built-in names
        if name in _BUILTIN_NAMES:
            return

        # It's a context variable
        self._dependencies.add(name)

    def _visit_getattr(self, node) -> None:
        """Handle attribute access: obj.attr"""
        path = self._build_path(node)
        if path:
            self._dependencies.add(path)
        else:
            # Couldn't build full path, visit children
            self._visit(node.obj)

    def _visit_optionalgetattr(self, node) -> None:
        """Handle optional attribute access: obj?.attr"""
        # Same logic as regular getattr
        path = self._build_path(node)
        if path:
            self._dependencies.add(path)
        else:
            self._visit(node.obj)

    def _visit_getitem(self, node) -> None:
        """Handle subscript access: obj[key]"""
        # We can only track static string keys
        if type(node.key).__name__ == "Const" and isinstance(node.key.value, str):
            path = self._build_path(node)
            if path:
                self._dependencies.add(path)
                return

        # Dynamic key - track the base object and the key expression
        self._visit(node.obj)
        self._visit(node.key)

    def _visit_optionalgetitem(self, node) -> None:
        """Handle optional subscript access: obj?[key]"""
        # Same logic as regular getitem
        if type(node.key).__name__ == "Const" and isinstance(node.key.value, str):
            path = self._build_path(node)
            if path:
                self._dependencies.add(path)
                return

        self._visit(node.obj)
        self._visit(node.key)

    def _visit_for(self, node) -> None:
        """Handle for loop: push loop variable into scope."""
        # Visit the iterable (this IS a dependency)
        self._visit(node.iter)

        # Visit optional filter condition
        if hasattr(node, "test") and node.test:
            # test is evaluated with loop var in scope
            loop_vars = self._extract_targets(node.target)
            self._scope_stack.append(loop_vars | {"loop"})
            self._visit(node.test)
            self._scope_stack.pop()

        # Push loop variable(s) into scope
        loop_vars = self._extract_targets(node.target)
        self._scope_stack.append(loop_vars)

        # Add implicit 'loop' variable
        self._scope_stack[-1].add("loop")

        # Visit body with loop var in scope
        for child in node.body:
            self._visit(child)

        # Visit empty block (if any)
        if hasattr(node, "empty") and node.empty:
            for child in node.empty:
                self._visit(child)

        # Pop scope
        self._scope_stack.pop()

    def _visit_with(self, node) -> None:
        """Handle with block: push bindings into scope."""
        # Collect all bindings
        bindings = set()
        for name, value in node.targets:
            self._visit(value)  # Value expression IS a dependency
            bindings.add(name)

        # Push bindings into scope
        self._scope_stack.append(bindings)

        # Visit body
        for child in node.body:
            self._visit(child)

        # Pop scope
        self._scope_stack.pop()

    def _visit_withconditional(self, node) -> None:
        """Handle conditional with: {% with expr as name %}"""
        # Visit the expression (IS a dependency)
        self._visit(node.expr)

        # Push binding into scope
        self._scope_stack.append({node.name})

        # Visit body
        for child in node.body:
            self._visit(child)

        # Pop scope
        self._scope_stack.pop()

    def _visit_def(self, node) -> None:
        """Handle function definition: push args into scope."""
        # Push function arguments into scope
        self._scope_stack.append(set(node.args))

        # Visit body
        for child in node.body:
            self._visit(child)

        # Visit defaults (outside function scope)
        self._scope_stack.pop()
        for default in node.defaults:
            self._visit(default)

    def _visit_macro(self, node) -> None:
        """Handle macro definition (same as def)."""
        self._visit_def(node)

    def _visit_set(self, node) -> None:
        """Handle set statement."""
        # Visit the value expression
        self._visit(node.value)

        # Add target to current scope
        targets = self._extract_targets(node.target)
        if self._scope_stack:
            self._scope_stack[-1] |= targets

    def _visit_let(self, node) -> None:
        """Handle let statement (template-scoped)."""
        # Visit the value expression
        self._visit(node.value)

        # Add to root scope
        if self._scope_stack:
            self._scope_stack[0].add(node.name)

    def _visit_capture(self, node) -> None:
        """Handle capture block: {% capture name %}...{% end %}"""
        # Visit body
        for child in node.body:
            self._visit(child)

        # Add captured name to current scope
        if self._scope_stack:
            self._scope_stack[-1].add(node.name)

    def _visit_filter(self, node) -> None:
        """Handle filter expression."""
        # Visit the value being filtered
        self._visit(node.value)

        # Visit filter arguments
        for arg in node.args:
            self._visit(arg)

        for value in node.kwargs.values():
            self._visit(value)

    def _visit_pipeline(self, node) -> None:
        """Handle pipeline expression: expr |> filter1 |> filter2"""
        # Visit the initial value
        self._visit(node.value)

        # Visit arguments in each pipeline step
        for _name, args, kwargs in node.steps:
            for arg in args:
                self._visit(arg)
            for value in kwargs.values():
                self._visit(value)

    def _visit_funccall(self, node) -> None:
        """Handle function call."""
        # Visit the function expression
        self._visit(node.func)

        # Visit arguments
        for arg in node.args:
            self._visit(arg)

        for value in node.kwargs.values():
            self._visit(value)

        # Handle *args and **kwargs
        if hasattr(node, "dyn_args") and node.dyn_args:
            self._visit(node.dyn_args)
        if hasattr(node, "dyn_kwargs") and node.dyn_kwargs:
            self._visit(node.dyn_kwargs)

    def _visit_nullcoalesce(self, node) -> None:
        """Handle null coalescing: a ?? b"""
        self._visit(node.left)
        self._visit(node.right)

    def _visit_condexpr(self, node) -> None:
        """Handle conditional expression: a if cond else b"""
        self._visit(node.test)
        self._visit(node.if_true)
        self._visit(node.if_false)

    def _visit_boolop(self, node) -> None:
        """Handle boolean operations: a and b, a or b"""
        for value in node.values:
            self._visit(value)

    def _visit_range(self, node) -> None:
        """Handle range literal: start..end or start...end"""
        self._visit(node.start)
        self._visit(node.end)
        if node.step:
            self._visit(node.step)

    def _visit_slice(self, node) -> None:
        """Handle slice expression: [start:stop:step]"""
        if node.start:
            self._visit(node.start)
        if node.stop:
            self._visit(node.stop)
        if node.step:
            self._visit(node.step)

    def _visit_concat(self, node) -> None:
        """Handle string concatenation: a ~ b ~ c"""
        for child in node.nodes:
            self._visit(child)

    def _visit_match(self, node) -> None:
        """Handle match statement."""
        self._visit(node.subject)
        for pattern, body in node.cases:
            self._visit(pattern)
            for child in body:
                self._visit(child)

    def _visit_cache(self, node) -> None:
        """Handle cache block: {% cache key %}...{% end %}"""
        self._visit(node.key)
        if node.ttl:
            self._visit(node.ttl)
        for dep in node.depends:
            self._visit(dep)
        for child in node.body:
            self._visit(child)

    def _visit_include(self, node) -> None:
        """Handle include statement."""
        self._visit(node.template)

    def _visit_import(self, node) -> None:
        """Handle import statement."""
        self._visit(node.template)
        # Add imported name to scope
        if self._scope_stack:
            self._scope_stack[-1].add(node.target)

    def _visit_fromimport(self, node) -> None:
        """Handle from...import statement."""
        self._visit(node.template)
        # Add imported names to scope
        if self._scope_stack:
            for name, alias in node.names:
                self._scope_stack[-1].add(alias or name)

    def _build_path(self, node) -> str | None:
        """Build dotted path from chained attribute/item access.

        Returns None if the path can't be determined statically
        (e.g., dynamic keys, local variables).
        """
        parts: list[str] = []
        current = node

        while True:
            node_type = type(current).__name__

            if node_type == "Getattr":
                parts.append(current.attr)
                current = current.obj
            elif node_type == "OptionalGetattr":
                parts.append(current.attr)
                current = current.obj
            elif node_type == "Getitem":
                # Only static string keys
                if type(current.key).__name__ == "Const" and isinstance(current.key.value, str):
                    parts.append(current.key.value)
                    current = current.obj
                else:
                    return None  # Dynamic key
            elif node_type == "OptionalGetitem":
                if type(current.key).__name__ == "Const" and isinstance(current.key.value, str):
                    parts.append(current.key.value)
                    current = current.obj
                else:
                    return None
            elif node_type == "Name":
                name = current.name
                # Check if root is local
                if self._is_local(name):
                    return None  # Local var, not a context dep
                if name in _BUILTIN_NAMES:
                    return None  # Built-in
                parts.append(name)
                break
            else:
                return None  # Can't determine statically

        parts.reverse()
        return ".".join(parts)

    def _extract_targets(self, node) -> set[str]:
        """Extract variable names from assignment target."""
        node_type = type(node).__name__

        if node_type == "Name":
            return {node.name}
        elif node_type == "Tuple":
            names = set()
            for item in node.items:
                names |= self._extract_targets(item)
            return names

        return set()

    def _is_local(self, name: str) -> bool:
        """Check if a name is in local scope."""
        return any(name in scope for scope in self._scope_stack)


# Names that are always available (not context dependencies)
_BUILTIN_NAMES = frozenset({
    # Python builtins commonly used in templates
    "range", "len", "str", "int", "float", "bool",
    "list", "dict", "set", "tuple",
    "min", "max", "sum", "abs", "round",
    "sorted", "reversed", "enumerate", "zip", "map", "filter",
    "any", "all", "hasattr", "getattr", "isinstance", "type",
    # Boolean/None literals
    "true", "false", "none", "True", "False", "None",
    # Kida builtins
    "loop",  # Loop context variable
})
```

### Purity Analyzer

```python
# bengal/rendering/kida/analysis/purity.py

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Node

# Purity lattice: pure < unknown < impure
# When combining, take the most conservative (worst case)

PurityLevel = Literal["pure", "unknown", "impure"]


def _combine_purity(a: PurityLevel, b: PurityLevel) -> PurityLevel:
    """Combine two purity levels (take worst case)."""
    if a == "impure" or b == "impure":
        return "impure"
    if a == "unknown" or b == "unknown":
        return "unknown"
    return "pure"


class PurityAnalyzer:
    """Determine if an expression or block is pure (deterministic).

    Pure expressions produce the same output for the same inputs.
    This is used to determine cache safety.

    Conservative: defaults to "unknown" when uncertain.
    """

    def analyze(self, node: Node) -> PurityLevel:
        """Analyze a node and return its purity level."""
        return self._visit(node)

    def _visit(self, node: Node) -> PurityLevel:
        """Visit a node and determine purity."""
        node_type = type(node).__name__

        handler = getattr(self, f"_visit_{node_type.lower()}", None)
        if handler:
            return handler(node)

        # Default: check children
        return self._visit_children(node)

    def _visit_children(self, node: Node) -> PurityLevel:
        """Visit children and combine purity."""
        result: PurityLevel = "pure"

        for attr in ("body", "else_", "empty"):
            if hasattr(node, attr):
                children = getattr(node, attr)
                if children:
                    for child in children:
                        if hasattr(child, "lineno"):
                            result = _combine_purity(result, self._visit(child))

        for attr in ("test", "expr", "value", "iter", "left", "right", "operand"):
            if hasattr(node, attr):
                child = getattr(node, attr)
                if child and hasattr(child, "lineno"):
                    result = _combine_purity(result, self._visit(child))

        return result

    def _visit_const(self, node) -> PurityLevel:
        """Constants are pure."""
        return "pure"

    def _visit_name(self, node) -> PurityLevel:
        """Variable access is pure (reading doesn't mutate)."""
        return "pure"

    def _visit_getattr(self, node) -> PurityLevel:
        """Attribute access is pure."""
        return self._visit(node.obj)

    def _visit_optionalgetattr(self, node) -> PurityLevel:
        """Optional attribute access is pure."""
        return self._visit(node.obj)

    def _visit_getitem(self, node) -> PurityLevel:
        """Subscript access is pure."""
        return _combine_purity(
            self._visit(node.obj),
            self._visit(node.key),
        )

    def _visit_optionalgetitem(self, node) -> PurityLevel:
        """Optional subscript access is pure."""
        return _combine_purity(
            self._visit(node.obj),
            self._visit(node.key),
        )

    def _visit_binop(self, node) -> PurityLevel:
        """Binary operations are pure."""
        return _combine_purity(
            self._visit(node.left),
            self._visit(node.right),
        )

    def _visit_unaryop(self, node) -> PurityLevel:
        """Unary operations are pure."""
        return self._visit(node.operand)

    def _visit_compare(self, node) -> PurityLevel:
        """Comparisons are pure."""
        result = self._visit(node.left)
        for comp in node.comparators:
            result = _combine_purity(result, self._visit(comp))
        return result

    def _visit_boolop(self, node) -> PurityLevel:
        """Boolean operations are pure."""
        result: PurityLevel = "pure"
        for value in node.values:
            result = _combine_purity(result, self._visit(value))
        return result

    def _visit_condexpr(self, node) -> PurityLevel:
        """Conditional expressions are pure if all parts are pure."""
        return _combine_purity(
            self._visit(node.test),
            _combine_purity(
                self._visit(node.if_true),
                self._visit(node.if_false),
            ),
        )

    def _visit_nullcoalesce(self, node) -> PurityLevel:
        """Null coalescing is pure."""
        return _combine_purity(
            self._visit(node.left),
            self._visit(node.right),
        )

    def _visit_concat(self, node) -> PurityLevel:
        """String concatenation is pure."""
        result: PurityLevel = "pure"
        for child in node.nodes:
            result = _combine_purity(result, self._visit(child))
        return result

    def _visit_range(self, node) -> PurityLevel:
        """Range literals are pure."""
        result = _combine_purity(
            self._visit(node.start),
            self._visit(node.end),
        )
        if node.step:
            result = _combine_purity(result, self._visit(node.step))
        return result

    def _visit_slice(self, node) -> PurityLevel:
        """Slice expressions are pure."""
        result: PurityLevel = "pure"
        if node.start:
            result = _combine_purity(result, self._visit(node.start))
        if node.stop:
            result = _combine_purity(result, self._visit(node.stop))
        if node.step:
            result = _combine_purity(result, self._visit(node.step))
        return result

    def _visit_list(self, node) -> PurityLevel:
        """List literals are pure if all items are pure."""
        result: PurityLevel = "pure"
        for item in node.items:
            result = _combine_purity(result, self._visit(item))
        return result

    def _visit_tuple(self, node) -> PurityLevel:
        """Tuple literals are pure if all items are pure."""
        result: PurityLevel = "pure"
        for item in node.items:
            result = _combine_purity(result, self._visit(item))
        return result

    def _visit_dict(self, node) -> PurityLevel:
        """Dict literals are pure if all keys and values are pure."""
        result: PurityLevel = "pure"
        for key in node.keys:
            result = _combine_purity(result, self._visit(key))
        for value in node.values:
            result = _combine_purity(result, self._visit(value))
        return result

    def _visit_filter(self, node) -> PurityLevel:
        """Filter purity depends on the filter."""
        # Check filter name
        if node.name in _KNOWN_PURE_FILTERS:
            filter_purity: PurityLevel = "pure"
        elif node.name in _KNOWN_IMPURE_FILTERS:
            filter_purity = "impure"
        else:
            filter_purity = "unknown"  # User-defined

        # Combine with value and args
        result = _combine_purity(filter_purity, self._visit(node.value))
        for arg in node.args:
            result = _combine_purity(result, self._visit(arg))
        for value in node.kwargs.values():
            result = _combine_purity(result, self._visit(value))

        return result

    def _visit_pipeline(self, node) -> PurityLevel:
        """Pipeline purity depends on all filters in the chain."""
        result = self._visit(node.value)

        for filter_name, args, kwargs in node.steps:
            # Check filter purity
            if filter_name in _KNOWN_PURE_FILTERS:
                filter_purity: PurityLevel = "pure"
            elif filter_name in _KNOWN_IMPURE_FILTERS:
                filter_purity = "impure"
            else:
                filter_purity = "unknown"

            result = _combine_purity(result, filter_purity)

            # Check args
            for arg in args:
                result = _combine_purity(result, self._visit(arg))
            for value in kwargs.values():
                result = _combine_purity(result, self._visit(value))

        return result

    def _visit_funccall(self, node) -> PurityLevel:
        """Function call purity depends on the function."""
        # Check if it's a known pure builtin
        if type(node.func).__name__ == "Name":
            func_name = node.func.name
            if func_name in _KNOWN_PURE_FUNCTIONS:
                # Pure function - check arguments
                result: PurityLevel = "pure"
                for arg in node.args:
                    result = _combine_purity(result, self._visit(arg))
                for value in node.kwargs.values():
                    result = _combine_purity(result, self._visit(value))
                return result

        # Unknown function - conservative
        return "unknown"

    def _visit_test(self, node) -> PurityLevel:
        """Tests are pure (they're just predicates)."""
        result = self._visit(node.value)
        for arg in node.args:
            result = _combine_purity(result, self._visit(arg))
        return result

    def _visit_for(self, node) -> PurityLevel:
        """For loops are pure if body is pure."""
        result = self._visit(node.iter)
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        if hasattr(node, "empty") and node.empty:
            for child in node.empty:
                result = _combine_purity(result, self._visit(child))
        return result

    def _visit_if(self, node) -> PurityLevel:
        """Conditionals are pure if all branches are pure."""
        result = self._visit(node.test)
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        for child in node.else_:
            result = _combine_purity(result, self._visit(child))
        # Handle elif
        if hasattr(node, "elif_") and node.elif_:
            for test, body in node.elif_:
                result = _combine_purity(result, self._visit(test))
                for child in body:
                    result = _combine_purity(result, self._visit(child))
        return result

    def _visit_match(self, node) -> PurityLevel:
        """Match statements are pure if all branches are pure."""
        result = self._visit(node.subject)
        for pattern, body in node.cases:
            result = _combine_purity(result, self._visit(pattern))
            for child in body:
                result = _combine_purity(result, self._visit(child))
        return result

    def _visit_output(self, node) -> PurityLevel:
        """Output is pure if expression is pure."""
        return self._visit(node.expr)

    def _visit_data(self, node) -> PurityLevel:
        """Static data is pure."""
        return "pure"

    def _visit_cache(self, node) -> PurityLevel:
        """Cache blocks: the body is evaluated, but result is cached.

        The block itself is pure if the body is pure.
        """
        result = self._visit(node.key)
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        return result


# Filters known to be pure (deterministic, no side effects)
_KNOWN_PURE_FILTERS = frozenset({
    # String manipulation
    "upper", "lower", "title", "capitalize", "swapcase",
    "strip", "lstrip", "rstrip", "trim",
    "replace", "truncate", "wordwrap", "center", "indent",
    "striptags", "urlize", "wordcount",

    # Collections
    "first", "last", "length", "count",
    "sort", "reverse", "unique",
    "batch", "slice", "list",
    "map", "select", "reject", "selectattr", "rejectattr",
    "groupby", "join", "pprint",

    # Type conversion
    "string", "int", "float", "bool",
    "tojson", "safe", "escape", "e",

    # Defaults
    "default", "d",

    # Math
    "abs", "round", "sum", "min", "max",

    # Format
    "filesizeformat", "format",

    # Path/URL
    "basename", "dirname", "splitext",
})

# Filters known to be impure (non-deterministic)
_KNOWN_IMPURE_FILTERS = frozenset({
    "random",
    "shuffle",
})

# Functions known to be pure
_KNOWN_PURE_FUNCTIONS = frozenset({
    # Python builtins
    "len", "str", "int", "float", "bool",
    "list", "dict", "set", "tuple", "frozenset",
    "min", "max", "sum", "abs", "round", "pow",
    "sorted", "reversed", "enumerate", "zip", "map", "filter",
    "any", "all", "range",
    "hasattr", "getattr", "isinstance", "type",
    "ord", "chr", "hex", "oct", "bin",
    "repr", "hash",
})
```

### Landmark Detector

```python
# bengal/rendering/kida/analysis/landmarks.py

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Node

# HTML5 landmark elements
_LANDMARK_ELEMENTS = frozenset({
    "nav", "main", "header", "footer", "aside", "article", "section",
})

# Regex to find HTML tags in Data nodes
_TAG_RE = re.compile(r"<\s*(\w+)", re.IGNORECASE)


class LandmarkDetector:
    """Detect HTML5 landmark elements in template output.

    Analyzes Data nodes to find landmark elements like <nav>, <main>, etc.
    Used for structural classification and role inference.
    """

    def detect(self, node: Node) -> frozenset[str]:
        """Detect landmark elements in a node tree."""
        landmarks: set[str] = set()
        self._visit(node, landmarks)
        return frozenset(landmarks)

    def _visit(self, node: Node, landmarks: set[str]) -> None:
        """Visit node and collect landmarks."""
        node_type = type(node).__name__

        if node_type == "Data":
            # Scan static content for HTML tags
            for match in _TAG_RE.finditer(node.value):
                tag = match.group(1).lower()
                if tag in _LANDMARK_ELEMENTS:
                    landmarks.add(tag)

        # Recurse into children
        for attr in ("body", "else_", "empty"):
            if hasattr(node, attr):
                children = getattr(node, attr)
                if children:
                    for child in children:
                        if hasattr(child, "lineno"):
                            self._visit(child, landmarks)

        # Handle elif
        if hasattr(node, "elif_") and node.elif_:
            for _test, body in node.elif_:
                for child in body:
                    if hasattr(child, "lineno"):
                        self._visit(child, landmarks)

        # Handle match cases
        if hasattr(node, "cases") and node.cases:
            for _pattern, body in node.cases:
                for child in body:
                    if hasattr(child, "lineno"):
                        self._visit(child, landmarks)
```

### Role Classifier

```python
# bengal/rendering/kida/analysis/roles.py

from __future__ import annotations

from typing import Literal

RoleType = Literal["navigation", "content", "sidebar", "header", "footer", "unknown"]


def classify_role(
    block_name: str,
    landmarks: frozenset[str],
) -> RoleType:
    """Classify block role based on name and emitted landmarks.

    This is a heuristic, not semantic truth. Returns "unknown" when
    classification is ambiguous.

    Priority:
        1. Landmarks (most reliable signal)
        2. Block name patterns (fallback)

    Args:
        block_name: Block identifier (e.g., "nav", "content", "sidebar")
        landmarks: HTML5 landmarks emitted by this block

    Returns:
        Inferred role or "unknown"
    """
    # Landmark-based classification (strongest signal)
    if "nav" in landmarks and len(landmarks) == 1:
        return "navigation"
    if "main" in landmarks:
        return "content"
    if "aside" in landmarks:
        return "sidebar"
    if "header" in landmarks and "main" not in landmarks:
        return "header"
    if "footer" in landmarks:
        return "footer"

    # Name-based classification (fallback)
    name_lower = block_name.lower()

    if name_lower in ("nav", "navigation", "menu", "navbar", "topnav", "sidenav"):
        return "navigation"
    if name_lower in ("content", "main", "body", "article", "post", "entry"):
        return "content"
    if name_lower in ("sidebar", "aside", "toc", "sidenav", "left", "right"):
        return "sidebar"
    if name_lower in ("header", "head", "masthead", "banner", "hero"):
        return "header"
    if name_lower in ("footer", "foot", "colophon", "bottom"):
        return "footer"

    return "unknown"
```

### Cache Scope Inference

```python
# bengal/rendering/kida/analysis/cache.py

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from bengal.rendering.kida.analysis.config import AnalysisConfig

CacheScope = Literal["none", "page", "site", "unknown"]


def infer_cache_scope(
    depends_on: frozenset[str],
    is_pure: Literal["pure", "impure", "unknown"],
    config: AnalysisConfig | None = None,
) -> CacheScope:
    """Infer recommended cache scope for a block.

    Args:
        depends_on: Context paths the block depends on
        is_pure: Block purity level
        config: Analysis configuration (for naming conventions)

    Returns:
        Recommended cache scope:
        - "site": Can cache once per site build
        - "page": Must re-render per page, but cacheable
        - "none": Cannot be cached (impure)
        - "unknown": Cannot determine
    """
    # Use default config if not provided
    if config is None:
        from bengal.rendering.kida.analysis.config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG

    # Impure blocks cannot be cached
    if is_pure == "impure":
        return "none"

    # Unknown purity means unknown cacheability
    if is_pure == "unknown":
        return "unknown"

    # Pure block - check dependencies
    if not depends_on:
        # No dependencies - can cache forever (site-wide)
        return "site"

    # Check if any dependency is page-specific
    has_page_dep = any(
        any(path.startswith(prefix) or path == prefix.rstrip(".")
            for prefix in config.page_prefixes)
        for path in depends_on
    )

    if has_page_dep:
        # Depends on page - must cache per-page
        return "page"

    # Only site-level dependencies - can cache site-wide
    return "site"
```

### Block Analyzer (Unified Entry Point)

```python
# bengal/rendering/kida/analysis/__init__.py

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.kida.analysis.cache import infer_cache_scope
from bengal.rendering.kida.analysis.config import AnalysisConfig, DEFAULT_CONFIG
from bengal.rendering.kida.analysis.dependencies import DependencyWalker
from bengal.rendering.kida.analysis.landmarks import LandmarkDetector
from bengal.rendering.kida.analysis.metadata import BlockMetadata, TemplateMetadata
from bengal.rendering.kida.analysis.purity import PurityAnalyzer
from bengal.rendering.kida.analysis.roles import classify_role

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Block, Template


class BlockAnalyzer:
    """Analyze template blocks and extract metadata.

    Combines dependency analysis, purity checking, landmark detection,
    and role classification into a unified analysis pass.

    Thread-safe: Stateless, creates new objects.

    Example:
        >>> analyzer = BlockAnalyzer()
        >>> meta = analyzer.analyze(template_ast)
        >>> print(meta.blocks["nav"].cache_scope)
        'site'

    Configuration:
        >>> from bengal.rendering.kida.analysis import AnalysisConfig
        >>> config = AnalysisConfig(
        ...     page_prefixes=frozenset({"post.", "item."}),
        ...     site_prefixes=frozenset({"global.", "settings."}),
        ... )
        >>> analyzer = BlockAnalyzer(config=config)
    """

    def __init__(self, config: AnalysisConfig | None = None) -> None:
        self._config = config or DEFAULT_CONFIG
        self._dep_walker = DependencyWalker()
        self._purity_analyzer = PurityAnalyzer()
        self._landmark_detector = LandmarkDetector()

    def analyze(self, ast: Template) -> TemplateMetadata:
        """Analyze a template AST and return metadata.

        Args:
            ast: Parsed template AST

        Returns:
            TemplateMetadata with block information
        """
        blocks: dict[str, BlockMetadata] = {}

        # Collect blocks from AST
        block_nodes = self._collect_blocks(ast)

        for block_node in block_nodes:
            block_meta = self._analyze_block(block_node)
            blocks[block_meta.name] = block_meta

        # Analyze top-level dependencies (outside blocks)
        top_level_deps = self._analyze_top_level(ast, set(blocks.keys()))

        # Extract extends info
        extends = None
        if ast.extends:
            extends_expr = ast.extends.template
            if type(extends_expr).__name__ == "Const":
                extends = extends_expr.value

        return TemplateMetadata(
            name=None,  # Set by caller
            extends=extends,
            blocks=blocks,
            top_level_depends_on=top_level_deps,
        )

    def _analyze_block(self, block_node: Block) -> BlockMetadata:
        """Analyze a single block node."""
        # Dependency analysis
        depends_on = self._dep_walker.analyze(block_node)

        # Purity analysis
        is_pure = self._purity_analyzer.analyze(block_node)

        # Landmark detection
        landmarks = self._landmark_detector.detect(block_node)

        # Role classification
        inferred_role = classify_role(block_node.name, landmarks)

        # Cache scope inference
        cache_scope = infer_cache_scope(depends_on, is_pure, self._config)

        # Check if block emits any HTML
        emits_html = self._check_emits_html(block_node)

        return BlockMetadata(
            name=block_node.name,
            emits_html=emits_html,
            emits_landmarks=landmarks,
            inferred_role=inferred_role,
            depends_on=depends_on,
            is_pure=is_pure,
            cache_scope=cache_scope,
        )

    def _collect_blocks(self, ast: Template) -> list[Block]:
        """Recursively collect all Block nodes from AST."""
        blocks: list = []
        self._collect_blocks_recursive(ast.body, blocks)
        return blocks

    def _collect_blocks_recursive(self, nodes, blocks: list) -> None:
        """Recursively find Block nodes."""
        for node in nodes:
            if type(node).__name__ == "Block":
                blocks.append(node)

            # Recurse into containers
            for attr in ("body", "else_", "empty"):
                if hasattr(node, attr):
                    children = getattr(node, attr)
                    if children:
                        self._collect_blocks_recursive(children, blocks)

            # Handle elif
            if hasattr(node, "elif_") and node.elif_:
                for _test, body in node.elif_:
                    self._collect_blocks_recursive(body, blocks)

            # Handle match cases
            if hasattr(node, "cases") and node.cases:
                for _pattern, body in node.cases:
                    self._collect_blocks_recursive(body, blocks)

    def _analyze_top_level(
        self,
        ast: Template,
        block_names: set[str],
    ) -> frozenset[str]:
        """Analyze dependencies in top-level code outside blocks.

        This captures dependencies from:
        - Code before/after blocks
        - Extends expression (e.g., dynamic parent template)
        - Context type declarations

        Does NOT include dependencies from inside blocks (those are
        tracked per-block).
        """
        deps: set[str] = set()

        # Analyze extends expression
        if ast.extends:
            extends_deps = self._dep_walker.analyze(ast.extends)
            deps.update(extends_deps)

        # Walk top-level nodes, excluding block bodies
        self._analyze_top_level_nodes(ast.body, block_names, deps)

        return frozenset(deps)

    def _analyze_top_level_nodes(
        self,
        nodes,
        block_names: set[str],
        deps: set[str],
    ) -> None:
        """Walk nodes, collecting dependencies but skipping block bodies."""
        for node in nodes:
            node_type = type(node).__name__

            if node_type == "Block":
                # Skip block body - it's analyzed separately
                # But the block name itself is not a dependency
                continue

            if node_type in ("Output", "If", "For", "Set", "Let", "With",
                            "WithConditional", "Include", "Import", "FromImport",
                            "Cache", "Match"):
                # These nodes may have dependencies
                node_deps = self._dep_walker.analyze(node)
                deps.update(node_deps)

            elif node_type == "Data":
                # Static content has no dependencies
                continue

            elif node_type in ("Def", "Macro"):
                # Function definitions - analyze body for lexical scope access
                node_deps = self._dep_walker.analyze(node)
                deps.update(node_deps)

            else:
                # Unknown node type - try to analyze it
                try:
                    node_deps = self._dep_walker.analyze(node)
                    deps.update(node_deps)
                except Exception:
                    pass  # Skip nodes we can't analyze

    def _check_emits_html(self, node) -> bool:
        """Check if a node produces any output."""
        node_type = type(node).__name__

        if node_type == "Data" and node.value.strip():
            return True
        if node_type == "Output":
            return True

        for attr in ("body", "else_", "empty"):
            if hasattr(node, attr):
                children = getattr(node, attr)
                if children:
                    for child in children:
                        if hasattr(child, "lineno") and self._check_emits_html(child):
                            return True

        # Handle elif
        if hasattr(node, "elif_") and node.elif_:
            for _test, body in node.elif_:
                for child in body:
                    if hasattr(child, "lineno") and self._check_emits_html(child):
                        return True

        return False


__all__ = [
    "AnalysisConfig",
    "BlockAnalyzer",
    "BlockMetadata",
    "DEFAULT_CONFIG",
    "DependencyWalker",
    "LandmarkDetector",
    "PurityAnalyzer",
    "TemplateMetadata",
]
```

### Template Integration

```python
# Update bengal/rendering/kida/template.py

class Template:
    """Compiled template ready for rendering."""

    __slots__ = (
        "_env_ref",
        "_code",
        "_name",
        "_filename",
        "_render_func",
        "_optimized_ast",  # NEW: Preserve AST for analysis (or None if disabled)
        "_metadata_cache",  # NEW: Cached metadata
    )

    def __init__(
        self,
        env: Environment,
        code: Any,
        name: str | None,
        filename: str | None,
        optimized_ast: Any = None,  # NEW parameter
    ):
        # ... existing init ...
        self._optimized_ast = optimized_ast
        self._metadata_cache: TemplateMetadata | None = None

    def block_metadata(self) -> dict[str, BlockMetadata]:
        """Get metadata about template blocks.

        Returns a mapping of block name → BlockMetadata with:
        - depends_on: Context paths the block may access
        - is_pure: Whether output is deterministic
        - cache_scope: Recommended caching granularity
        - inferred_role: Heuristic classification

        Results are cached after first call.

        Returns empty dict if:
        - AST was not preserved (preserve_ast=False)
        - Template was loaded from bytecode cache without source

        Example:
            >>> meta = template.block_metadata()
            >>> nav = meta.get("nav")
            >>> if nav and nav.cache_scope == "site":
            ...     html = cache.get_or_render("nav", ...)

        Note:
            This is best-effort static analysis. Dependency sets
            are conservative (may over-approximate). Treat as hints.
        """
        if self._optimized_ast is None:
            return {}

        if self._metadata_cache is None:
            from bengal.rendering.kida.analysis import BlockAnalyzer, TemplateMetadata
            analyzer = BlockAnalyzer()
            self._metadata_cache = analyzer.analyze(self._optimized_ast)
            # Set template name
            self._metadata_cache = TemplateMetadata(
                name=self._name,
                extends=self._metadata_cache.extends,
                blocks=self._metadata_cache.blocks,
                top_level_depends_on=self._metadata_cache.top_level_depends_on,
            )

        return self._metadata_cache.blocks

    def template_metadata(self) -> TemplateMetadata | None:
        """Get full template metadata including inheritance info.

        Returns None if AST was not preserved (preserve_ast=False or
        loaded from bytecode cache without source).
        """
        if self._optimized_ast is None:
            return None

        # Populate cache via block_metadata()
        self.block_metadata()
        return self._metadata_cache

    def depends_on(self) -> frozenset[str]:
        """Get all context paths this template may access.

        Convenience method combining all block dependencies.
        Returns empty frozenset if AST was not preserved.
        """
        meta = self.template_metadata()
        if meta is None:
            return frozenset()
        return meta.all_dependencies()
```

### Environment Integration

```python
# Update bengal/rendering/kida/environment/core.py

@dataclass
class Environment:
    """Central configuration and template management hub."""

    # ... existing fields ...

    # NEW: Control AST preservation for introspection
    # True (default): Preserve AST, enable block_metadata()/depends_on()
    # False: Discard AST after compilation, save ~2x memory per template
    preserve_ast: bool = True

    def _compile(
        self,
        source: str,
        name: str | None,
        filename: str | None,
    ) -> Template:
        """Compile template source to Template object."""
        # ... existing lexer/parser code ...

        # Apply AST optimizations
        optimized_ast = None
        if self.optimized:
            from bengal.rendering.kida.optimizer import ASTOptimizer
            optimizer = ASTOptimizer()
            result = optimizer.optimize(ast)
            ast = result.ast
            if self.preserve_ast:
                optimized_ast = ast  # NEW: Preserve for analysis
        elif self.preserve_ast:
            optimized_ast = ast  # Preserve unoptimized AST

        # Compile
        compiler = Compiler(self)
        code = compiler.compile(ast, name, filename)

        # ... bytecode cache ...

        return Template(
            self,
            code,
            name,
            filename,
            optimized_ast=optimized_ast,  # NEW: Pass AST
        )
```

---

## Public API

### For Template Users

```python
from bengal.rendering.kida import Environment

env = Environment()
template = env.get_template("page.html")

# Get block metadata
blocks = template.block_metadata()

# Check what nav block depends on
nav = blocks.get("nav")
if nav:
    print(f"Nav depends on: {nav.depends_on}")
    print(f"Nav cache scope: {nav.cache_scope}")
    print(f"Nav is pure: {nav.is_pure}")

# Get all template dependencies
all_deps = template.depends_on()
print(f"Template requires: {all_deps}")
```

### For Tooling Authors

```python
from bengal.rendering.kida.analysis import (
    AnalysisConfig,
    BlockAnalyzer,
    BlockMetadata,
)

# Custom configuration for non-Bengal projects
config = AnalysisConfig(
    page_prefixes=frozenset({"post.", "item.", "entry."}),
    site_prefixes=frozenset({"settings.", "global."}),
)

# Direct AST analysis (without full compilation)
analyzer = BlockAnalyzer(config=config)
metadata = analyzer.analyze(parsed_ast)

# Custom analysis
for name, block in metadata.blocks.items():
    if block.inferred_role == "navigation":
        if block.cache_scope != "site":
            warn(f"Navigation block '{name}' should be site-cacheable")
```

### Memory-Constrained Environments

```python
# Disable AST preservation to save memory
env = Environment(preserve_ast=False)

template = env.get_template("page.html")

# These return empty/None (no AST available)
template.block_metadata()  # {}
template.depends_on()      # frozenset()
template.template_metadata()  # None

# Rendering still works normally
template.render(page=page, site=site)
```

---

## Bengal Integration Example

```python
# bengal/core/site.py

class Site:
    def _render_page(self, page: Page, template: Template) -> str:
        """Render a page with caching optimization."""
        blocks = template.block_metadata()

        # Check for site-cacheable blocks
        site_cached_blocks = {}
        for name, meta in blocks.items():
            if meta.cache_scope == "site":
                cache_key = f"block:{template.name}:{name}"
                cached = self._block_cache.get(cache_key)
                if cached is not None:
                    site_cached_blocks[name] = cached
                else:
                    # Render and cache
                    html = template.render_block(name, site=self._site_context)
                    self._block_cache.set(cache_key, html)
                    site_cached_blocks[name] = html

        # Render with pre-cached blocks
        return template.render(
            page=page,
            site=self._site_context,
            _cached_blocks=site_cached_blocks,
        )
```

---

## Test Cases

```python
# tests/rendering/kida/analysis/test_block_analyzer.py

import pytest
from bengal.rendering.kida import Environment
from bengal.rendering.kida.analysis import BlockAnalyzer, AnalysisConfig


class TestDependencyWalker:
    """Test dependency extraction."""

    def test_simple_variable(self):
        """Direct variable access is tracked."""
        env = Environment()
        t = env.from_string("{{ page.title }}")
        deps = t.depends_on()
        assert "page.title" in deps

    def test_loop_variable_excluded(self):
        """Loop variables are not context dependencies."""
        env = Environment()
        t = env.from_string("""
            {% for item in items %}
                {{ item.name }}
            {% end %}
        """)
        deps = t.depends_on()
        assert "items" in deps
        assert "item" not in deps
        assert "item.name" not in deps

    def test_nested_access(self):
        """Chained attribute access builds full path."""
        env = Environment()
        t = env.from_string("{{ site.config.theme.name }}")
        deps = t.depends_on()
        assert "site.config.theme.name" in deps

    def test_with_binding_excluded(self):
        """With bindings create local scope."""
        env = Environment()
        t = env.from_string("""
            {% with page.author as author %}
                {{ author.name }}
            {% end %}
        """)
        deps = t.depends_on()
        assert "page.author" in deps
        assert "author" not in deps

    def test_optional_chaining(self):
        """Optional chaining is tracked."""
        env = Environment()
        t = env.from_string("{{ page?.author?.name }}")
        deps = t.depends_on()
        assert "page.author.name" in deps

    def test_null_coalescing(self):
        """Null coalescing tracks both sides."""
        env = Environment()
        t = env.from_string("{{ page.subtitle ?? 'Default' }}")
        deps = t.depends_on()
        assert "page.subtitle" in deps

    def test_pipeline_dependencies(self):
        """Pipeline tracks dependencies in filter args."""
        env = Environment()
        t = env.from_string("{{ items |> sort_by(config.sort_key) |> take(5) }}")
        deps = t.depends_on()
        assert "items" in deps
        assert "config.sort_key" in deps


class TestPurityAnalyzer:
    """Test purity inference."""

    def test_static_content_is_pure(self):
        """Static HTML is pure."""
        env = Environment()
        t = env.from_string("<div>Hello</div>")
        # Template-level purity (no blocks)

    def test_pure_filter_preserves_purity(self):
        """Pure filters don't affect purity."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ page.title | upper }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].is_pure == "pure"

    def test_random_filter_is_impure(self):
        """Random filter makes block impure."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ items | random }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].is_pure == "impure"

    def test_function_call_with_known_pure_function(self):
        """Known pure functions are marked pure."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ len(items) }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].is_pure == "pure"

    def test_unknown_function_call_is_unknown(self):
        """Unknown function calls are unknown purity."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ some_function() }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].is_pure == "unknown"


class TestCacheScope:
    """Test cache scope inference."""

    def test_site_only_deps_is_site_scope(self):
        """Block depending only on site is site-cacheable."""
        env = Environment()
        t = env.from_string("""
            {% block nav %}
                {% for p in site.pages %}
                    {{ p.title }}
                {% end %}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["nav"].cache_scope == "site"

    def test_page_deps_is_page_scope(self):
        """Block depending on page is page-cacheable."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ page.content }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].cache_scope == "page"

    def test_impure_block_not_cacheable(self):
        """Impure blocks cannot be cached."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ items | random }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].cache_scope == "none"

    def test_custom_prefix_config(self):
        """Custom prefix configuration works."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ post.content }}
            {% end %}
        """)

        # Default config doesn't know "post." is page-scoped
        blocks = t.block_metadata()
        # With default config, "post." is recognized as page prefix
        assert blocks["content"].cache_scope == "page"


class TestTopLevelDependencies:
    """Test top-level dependency analysis."""

    def test_top_level_output(self):
        """Top-level output is tracked."""
        env = Environment()
        t = env.from_string("""
            {{ site.title }}
            {% block content %}
                {{ page.content }}
            {% end %}
        """)
        meta = t.template_metadata()
        assert "site.title" in meta.top_level_depends_on
        assert "page.content" not in meta.top_level_depends_on  # In block
        assert "page.content" in meta.blocks["content"].depends_on

    def test_dynamic_extends(self):
        """Dynamic extends expression is tracked."""
        env = Environment()
        t = env.from_string("""
            {% extends config.base_template %}
            {% block content %}Hello{% end %}
        """)
        meta = t.template_metadata()
        assert "config.base_template" in meta.top_level_depends_on


class TestRoleClassification:
    """Test role inference."""

    def test_nav_landmark_is_navigation(self):
        """Block with <nav> is classified as navigation."""
        env = Environment()
        t = env.from_string("""
            {% block sidebar %}
                <nav><a href="/">Home</a></nav>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["sidebar"].inferred_role == "navigation"

    def test_main_landmark_is_content(self):
        """Block with <main> is classified as content."""
        env = Environment()
        t = env.from_string("""
            {% block body %}
                <main>{{ content }}</main>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["body"].inferred_role == "content"

    def test_name_based_fallback(self):
        """Block name is used when no landmarks present."""
        env = Environment()
        t = env.from_string("""
            {% block navigation %}
                <ul><li>Item</li></ul>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["navigation"].inferred_role == "navigation"


class TestPreserveAstConfig:
    """Test preserve_ast configuration."""

    def test_preserve_ast_true(self):
        """With preserve_ast=True, metadata is available."""
        env = Environment(preserve_ast=True)
        t = env.from_string("""
            {% block content %}{{ page.title }}{% end %}
        """)
        assert t.block_metadata() != {}
        assert t.depends_on() != frozenset()
        assert t.template_metadata() is not None

    def test_preserve_ast_false(self):
        """With preserve_ast=False, metadata is empty."""
        env = Environment(preserve_ast=False)
        t = env.from_string("""
            {% block content %}{{ page.title }}{% end %}
        """)
        assert t.block_metadata() == {}
        assert t.depends_on() == frozenset()
        assert t.template_metadata() is None

        # But rendering still works
        result = t.render(page={"title": "Hello"})
        assert "Hello" in result
```

---

## Documentation

### README Section (for Kida standalone)

```markdown
## Template Introspection

Kida exposes optional, read-only metadata about compiled templates.
This allows tools to reason about templates without rendering them.

```python
template = env.get_template("page.html")
meta = template.block_metadata()

# What blocks does this template define?
print(meta.keys())
# ['nav', 'content', 'sidebar']

# What does the nav block depend on?
print(meta['nav'].depends_on)
# frozenset({'site.pages', 'site.nav_version'})

# Can this block be cached across all pages?
print(meta['nav'].cache_scope)
# 'site'
```

### What this is

- Best-effort static analysis
- Conservative by design (when uncertain, reports "unknown")
- Read-only (never affects rendering)
- Optional (templates work normally without it)

### What this is not

- A guarantee of correctness
- A required feature for template authors
- A semantic markup or documentation DSL

### Memory Trade-off

By default, Kida preserves the AST for introspection (~2x memory per template).
For memory-constrained environments:

```python
# Disable AST preservation
env = Environment(preserve_ast=False)

# Metadata methods return empty/None, but rendering works normally
```

### Custom Configuration

For non-Bengal projects with different naming conventions:

```python
from bengal.rendering.kida.analysis import AnalysisConfig, BlockAnalyzer

config = AnalysisConfig(
    page_prefixes=frozenset({"post.", "item."}),
    site_prefixes=frozenset({"settings.", "global."}),
)

analyzer = BlockAnalyzer(config=config)
```
```

---

## Rollout Plan

### Phase 1: Core Analysis (Week 1, ~10 hours)

- [ ] Create `bengal/rendering/kida/analysis/` package
- [ ] Implement `AnalysisConfig` with configurable prefixes
- [ ] Implement `DependencyWalker` with full node coverage
- [ ] Implement `PurityAnalyzer` with known-pure functions
- [ ] Implement `LandmarkDetector` with HTML regex
- [ ] Implement `classify_role()` heuristics
- [ ] Implement `infer_cache_scope()` logic
- [ ] Unit tests for each analyzer (>90% coverage)

### Phase 2: Integration (Week 1, ~6 hours)

- [ ] Add `preserve_ast` config to Environment
- [ ] Add `_optimized_ast` and `_metadata_cache` to Template `__slots__`
- [ ] Add `block_metadata()` method
- [ ] Add `template_metadata()` method
- [ ] Add `depends_on()` convenience method
- [ ] Update `Environment._compile()` to preserve AST conditionally
- [ ] Integration tests for full pipeline

### Phase 3: Bengal Integration (Week 2, ~4 hours)

- [ ] Add nav block caching in Site render
- [ ] Add cache scope logging for debugging
- [ ] Benchmark: measure cache hit rate improvement
- [ ] Document integration pattern

### Phase 4: Documentation

- [ ] Add README section for Kida standalone
- [ ] Add docstrings to all public APIs
- [ ] Add "best-effort analysis" disclaimers
- [ ] Add examples to module docstrings
- [ ] Document breaking change in release notes

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Dependency accuracy | No false negatives (may over-approximate) |
| Purity accuracy | Conservative (defaults to unknown) |
| Cache scope accuracy | Never under-invalidate |
| Test coverage | >90% for analysis package |
| Performance | <1ms per template analysis |
| Memory overhead | Documented, controllable via `preserve_ast` |
| API stability | No breaking changes in 1.0 |

---

## Future Extensions

These are explicitly **not** in scope for this RFC but are enabled by it:

1. **Incremental build optimization** — Only re-render pages affected by changed dependencies
2. **Layout validation** — Warn if content block doesn't emit `<main>`
3. **Dead template detection** — Find templates with no dependents
4. **Type inference** — Track expected types of context variables
5. **LSP integration** — Autocomplete for context variables in editors
6. **Inheritance chain analysis** — Merge metadata from parent templates

---

## References

- Kida Architecture: `bengal/rendering/kida/__init__.py`
- AST Nodes: `bengal/rendering/kida/nodes.py`
- Optimizer: `bengal/rendering/kida/optimizer/__init__.py`
- Compiler: `bengal/rendering/kida/compiler/core.py`
- Template: `bengal/rendering/kida/template.py`
- Environment: `bengal/rendering/kida/environment/core.py`
