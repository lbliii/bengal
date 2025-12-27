# RFC: Kida Match and Pipeline Implementation

**Status**: Draft  
**Created**: 2025-12-26  
**Updated**: 2025-12-26  
**Priority**: High (Prerequisite for template refactor)  
**Scope**: `bengal/rendering/kida/`

---

## Executive Summary

Two Kida-native features have AST nodes and partial infrastructure but are not yet usable:

| Feature | AST Node | Lexer | Types | Parser | Compiler | Status |
|---------|----------|-------|-------|--------|----------|--------|
| `{% match %}` | ✅ `Match` | ✅ N/A | ✅ Keywords | ❌ Missing | ❌ Missing | **Not usable** |
| `\|>` pipeline | ✅ `Pipeline` | ✅ Implemented | ✅ Precedence | ❌ Missing | ❌ Missing | **Not usable** |

**Good news**: The lexer and type infrastructure is already complete. We only need parser and compiler work.

This RFC provides implementation details for both features. They are prerequisites for the Kida-native template architecture refactor (RFC: Kida-Native Template Architecture).

---

## Problem Statement

### Current State

The Kida AST defines `Match` and `Pipeline` nodes with partial infrastructure:

**✅ Already Implemented**:

| Component | Location | Status |
|-----------|----------|--------|
| `Match` AST node | `nodes.py:261-276` | ✅ Defined |
| `Pipeline` AST node | `nodes.py:620-635` | ✅ Defined |
| `TokenType.PIPELINE` | `_types.py:105` | ✅ Defined |
| `\|>` lexer recognition | `lexer.py:220` | ✅ In `_OPERATORS_2CHAR` |
| `PIPELINE` precedence | `_types.py:231` | ✅ Same as `PIPE` (6) |
| `match`, `case`, `endmatch` keywords | `_types.py:201-203` | ✅ In `KEYWORDS` |

**❌ Not Yet Implemented**:

| Component | Location | What's Missing |
|-----------|----------|----------------|
| `_END_KEYWORDS` | `blocks/core.py:29-44` | Missing `"endmatch"` |
| `_CONTINUATION_KEYWORDS` | `blocks/core.py:47-53` | Missing `"case"` |
| `_parse_block_content()` | `statements.py:105-203` | No `"match"` case |
| End tag list | `statements.py:163-176` | Missing `"endmatch"` |
| `_parse_match()` | `blocks/control_flow.py` | Method doesn't exist |
| `_parse_filter_chain()` | `expressions.py:333-363` | Doesn't check for `\|>` |
| `_parse_pipeline()` | `expressions.py` | Method doesn't exist |
| Node dispatch | `compiler/core.py:481-506` | Missing `"Match"` |
| `_compile_match()` | `compiler/statements/` | Method doesn't exist |
| `_compile_pipeline()` | `compiler/expressions.py` | Method doesn't exist |

### Why These Features Matter

**`{% match %}` Pattern Matching**:
- Replaces verbose `{% if %}{% elif %}{% elif %}{% else %}{% end %}` chains
- Cleaner type/value dispatching in templates
- Familiar syntax for Python developers (inspired by PEP 634)

**`|>` Pipeline Operator**:
- Readable left-to-right filter chains
- Alternative to deeply nested `{{ a | b | c | d }}` patterns
- Explicit data flow visualization

---

## Feature 1: `{% match %}` Pattern Matching

### Syntax

```jinja2
{% match expression %}
  {% case "value1" %}
    ... content for value1 ...
  {% case "value2" %}
    ... content for value2 ...
  {% case _ %}
    ... default fallback ...
{% end %}
```

### AST Node (Already Defined)

**File**: `bengal/rendering/kida/nodes.py:261-276`

```python
@dataclass(frozen=True, slots=True)
class Match(Node):
    """Pattern matching: {% match expr %}{% case pattern %}...{% end %}"""
    subject: Expr
    cases: Sequence[tuple[Expr, Sequence[Node]]]  # (pattern, body)
```

### Implementation Plan

#### 1. Parser: Update Block Keyword Sets

**File**: `bengal/rendering/kida/parser/blocks/core.py`

Add `"endmatch"` to `_END_KEYWORDS` (line 29-44):

```python
_END_KEYWORDS: frozenset[str] = frozenset(
    {
        "end",
        "endif",
        "endfor",
        "endblock",
        "endmacro",
        "endwith",
        "enddef",
        "endcall",
        "endcapture",
        "endcache",
        "endfilter",
        "endraw",
        "endmatch",  # <-- Add this
    }
)
```

Add `"case"` to `_CONTINUATION_KEYWORDS` (line 46-53):

```python
_CONTINUATION_KEYWORDS: frozenset[str] = frozenset(
    {
        "else",
        "elif",
        "empty",
        "case",  # <-- Add this
    }
)
```

#### 2. Parser: Add Keyword Dispatch

**File**: `bengal/rendering/kida/parser/statements.py`

Add to `_parse_block_content()` (after line 156, before the elif/else error):

```python
elif keyword == "match":
    return self._parse_match()
```

Update end tag list (line 163-176) to include `"endmatch"`:

```python
elif keyword in (
    "endif", "endfor", "endblock", "endmacro", "endwith",
    "endraw", "end", "enddef", "endcall", "endcapture",
    "endcache", "endfilter", "endmatch",  # <-- Add endmatch
):
```

Also add `"case"` to the continuation keyword error handling (after line 157):

```python
elif keyword in ("elif", "else", "empty", "case"):  # <-- Add case
    # Continuation tags outside of their block context
    raise self._error(
        f"Unexpected '{keyword}' - not inside a matching block",
        suggestion=f"'{keyword}' can only appear inside an 'if', 'for', or 'match' block",
    )
```

Update the suggestion in the unknown keyword error (line 202) to include `match`:

```python
suggestion="Valid keywords: if, for, set, let, block, extends, include, macro, from, with, do, raw, def, call, capture, cache, filter, slot, match",
```

#### 3. Parser: Add `_parse_match()` Method

**File**: `bengal/rendering/kida/parser/blocks/control_flow.py`

Update import at top to include `Match`:

```python
from bengal.rendering.kida.nodes import For, If, Match, While
```

Add method after `_parse_while()` (or `_parse_for()` if while isn't there):

```python
def _parse_match(self) -> Match:
    """Parse {% match expr %}{% case pattern %}...{% end %}.

    Pattern matching for cleaner branching than if/elif chains.
    Reuses the existing _parse_body infrastructure for case bodies.

    Syntax:
        {% match page.type %}
            {% case "post" %}...
            {% case "gallery" %}...
            {% case _ %}...
        {% end %}

    The underscore (_) is the wildcard/default case.
    """
    start = self._advance()  # consume 'match'
    self._push_block("match", start)

    # Parse subject expression
    subject = self._parse_expression()
    self._expect(TokenType.BLOCK_END)

    cases: list[tuple[Expr, Sequence[Node]]] = []

    # Parse case clauses using existing body parsing infrastructure
    # _parse_body(stop_on_continuation=True) stops at "case" keywords
    while self._current.type == TokenType.BLOCK_BEGIN:
        next_tok = self._peek(1)
        if next_tok.type != TokenType.NAME:
            break

        keyword = next_tok.value

        if keyword == "case":
            self._advance()  # consume {%
            self._advance()  # consume 'case'

            # Parse pattern expression
            pattern = self._parse_expression()
            self._expect(TokenType.BLOCK_END)

            # Parse case body - reuse existing _parse_body
            # stop_on_continuation=True stops at next "case" or end keywords
            body = self._parse_body(stop_on_continuation=True)
            cases.append((pattern, tuple(body)))

        elif keyword in ("end", "endmatch"):
            self._consume_end_tag("match")
            break
        else:
            # Unknown keyword - error
            raise self._error(
                f"Expected 'case' or 'end' in match block, got '{keyword}'",
                suggestion="Match blocks contain {% case pattern %} clauses",
            )

    if not cases:
        raise self._error(
            "Match block must have at least one {% case %} clause",
            suggestion="Add {% case value %}...{% end %} inside the match block",
        )

    return Match(
        lineno=start.lineno,
        col_offset=start.col_offset,
        subject=subject,
        cases=tuple(cases),
    )
```

#### 4. Compiler: Add `_compile_match()` Method

**File**: `bengal/rendering/kida/compiler/statements/control_flow.py`

Add import at top (if not already present):

```python
import ast
from typing import Any
```

Add method after `_compile_for()` (or at end of control flow compilation methods):

```python
def _compile_match(self, node: Any) -> list[ast.stmt]:
    """Compile {% match expr %}{% case pattern %}...{% end %}.

    Generates chained if/elif comparisons:
        _match_subject = expr
        if _match_subject == pattern1:
            ...body1...
        elif _match_subject == pattern2:
            ...body2...
        elif True:  # Wildcard case (_)
            ...default...

    The wildcard pattern (_) compiles to `True` (always matches).

    Uses unique variable name with block counter to support nested match blocks.
    """
    from bengal.rendering.kida.nodes import Name as KidaName

    stmts: list[ast.stmt] = []

    # Use unique variable name to support nested match blocks
    self._block_counter += 1
    subject_var = f"_match_subject_{self._block_counter}"

    # _match_subject_N = expr
    stmts.append(
        ast.Assign(
            targets=[ast.Name(id=subject_var, ctx=ast.Store())],
            value=self._compile_expr(node.subject),
        )
    )

    if not node.cases:
        return stmts

    # Build if/elif chain from cases
    # Process cases in reverse to build the orelse chain
    orelse: list[ast.stmt] = []

    for pattern_expr, case_body in reversed(node.cases):
        # Compile case body
        body_stmts: list[ast.stmt] = []
        for child in case_body:
            body_stmts.extend(self._compile_node(child))
        if not body_stmts:
            body_stmts = [ast.Pass()]

        # Check for wildcard pattern (_)
        is_wildcard = (
            isinstance(pattern_expr, KidaName)
            and pattern_expr.name == "_"
        )

        if is_wildcard:
            # Wildcard: always True (becomes else clause effectively)
            test = ast.Constant(value=True)
        else:
            # Equality comparison: _match_subject_N == pattern
            test = ast.Compare(
                left=ast.Name(id=subject_var, ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[self._compile_expr(pattern_expr)],
            )

        # Build if node
        if_node = ast.If(
            test=test,
            body=body_stmts,
            orelse=orelse,
        )
        orelse = [if_node]

    # The first case becomes the outermost if
    if orelse:
        stmts.extend(orelse)

    return stmts
```

#### 5. Compiler: Register Node Handler

**File**: `bengal/rendering/kida/compiler/core.py`

Add to `_get_node_dispatch()` method (line 484-506):

```python
def _get_node_dispatch(self) -> dict[str, Callable]:
    """Get node type dispatch table (cached on first call)."""
    if not hasattr(self, "_node_dispatch"):
        self._node_dispatch = {
            # ... existing entries ...
            "Match": self._compile_match,  # <-- Add this
        }
    return self._node_dispatch
```

---

## Feature 2: `|>` Pipeline Operator

### Syntax

```jinja2
{# Filter chain with pipeline operator #}
{{ items |> where(published=true) |> sort_by('date') |> take(5) }}

{# Equivalent to standard filter chain #}
{{ items | where(published=true) | sort_by('date') | take(5) }}
```

**Design Decision**: Mixing `|` and `|>` in the same expression is **not allowed**.
Choose one style per expression. This prevents ambiguity and encourages consistent code.

### AST Node (Already Defined)

**File**: `bengal/rendering/kida/nodes.py:620-635`

```python
@dataclass(frozen=True, slots=True)
class Pipeline(Expr):
    """Pipeline operator: expr |> filter1 |> filter2"""
    value: Expr
    steps: Sequence[tuple[str, Sequence[Expr], dict[str, Expr]]]  # (name, args, kwargs)
```

### Implementation Plan

> **Note**: Lexer and type infrastructure is already complete. The `TokenType.PIPELINE`
> enum value exists at `_types.py:105`, the `|>` operator is recognized by the lexer at
> `lexer.py:220`, and precedence is set at `_types.py:231`. We only need parser and compiler work.

#### 1. Parser: Add Pipeline Import

**File**: `bengal/rendering/kida/parser/expressions.py`

Update imports (around line 11-28) to include `Pipeline`:

```python
from bengal.rendering.kida.nodes import (
    BinOp,
    BoolOp,
    Compare,
    CondExpr,
    Const,
    Dict,
    Filter,
    FuncCall,
    Getattr,
    Getitem,
    List,
    Name,
    Pipeline,  # <-- Add this
    Slice,
    Test,
    Tuple,
    UnaryOp,
)
```

#### 2. Parser: Modify Filter Chain Parsing

**File**: `bengal/rendering/kida/parser/expressions.py`

Replace `_parse_filter_chain()` method (line 333-363) with version that detects `|>`:

```python
def _parse_filter_chain(self, expr: Expr) -> Expr:
    """Parse filter chain: expr | filter1 | filter2(arg).

    Also handles pipeline operator: expr |> filter1 |> filter2(arg).

    Design: Mixing | and |> in the same expression is not allowed.
    The first operator encountered determines the style for the expression.
    """
    # Check for pipeline operator first
    if self._match(TokenType.PIPELINE):
        return self._parse_pipeline(expr)

    # Standard filter chain with |
    while self._match(TokenType.PIPE):
        self._advance()

        # Error if switching from | to |> mid-expression
        if self._match(TokenType.GT):
            raise self._error(
                "Cannot mix '|' and '|>' operators in the same expression",
                suggestion="Use either '|' or '|>' consistently: {{ x | a | b }} or {{ x |> a |> b }}",
            )

        if self._current.type != TokenType.NAME:
            raise self._error("Expected filter name")
        filter_name = self._advance().value

        args: list[Expr] = []
        kwargs: dict[str, Expr] = {}

        # Optional arguments
        if self._match(TokenType.LPAREN):
            self._advance()
            args, kwargs = self._parse_call_args()
            self._expect(TokenType.RPAREN)

        expr = Filter(
            lineno=expr.lineno,
            col_offset=expr.col_offset,
            value=expr,
            name=filter_name,
            args=tuple(args),
            kwargs=kwargs,
        )

    return expr

def _parse_pipeline(self, expr: Expr) -> Expr:
    """Parse pipeline chain: expr |> filter1 |> filter2(arg).

    Pipelines are left-associative: a |> b |> c == (a |> b) |> c

    Each step is a filter application. The pipeline collects all
    steps into a single Pipeline node for potential optimization.

    Design: Mixing | and |> is not allowed. Error on | after |>.
    """
    steps: list[tuple[str, Sequence[Expr], dict[str, Expr]]] = []

    while self._match(TokenType.PIPELINE):
        self._advance()  # consume |>

        if self._current.type != TokenType.NAME:
            raise self._error(
                "Expected filter name after |>",
                suggestion="Pipeline syntax: expr |> filter_name or expr |> filter_name(args)",
            )

        filter_name = self._advance().value

        args: list[Expr] = []
        kwargs: dict[str, Expr] = {}

        # Optional arguments
        if self._match(TokenType.LPAREN):
            self._advance()
            args, kwargs = self._parse_call_args()
            self._expect(TokenType.RPAREN)

        steps.append((filter_name, tuple(args), kwargs))

    # Error if switching from |> to | mid-expression
    if self._match(TokenType.PIPE):
        raise self._error(
            "Cannot mix '|>' and '|' operators in the same expression",
            suggestion="Use either '|>' or '|' consistently: {{ x |> a |> b }} or {{ x | a | b }}",
        )

    if not steps:
        return expr

    return Pipeline(
        lineno=expr.lineno,
        col_offset=expr.col_offset,
        value=expr,
        steps=tuple(steps),
    )
```

#### 3. Compiler: Add Pipeline Compilation

**File**: `bengal/rendering/kida/compiler/expressions.py`

Add `Pipeline` to the imports from nodes (if not already present).

Add method to `ExpressionCompilationMixin` class (after the `Filter` handling around line 277):

```python
def _compile_pipeline(self, node: Pipeline) -> ast.expr:
    """Compile pipeline: expr |> filter1 |> filter2.

    Pipelines compile to nested filter calls using the _filters dict,
    exactly like regular filter chains. The difference is purely syntactic.

    expr |> a |> b(x)  →  _filters['b'](_filters['a'](expr), x)

    Validates filter existence at compile time (same as Filter nodes).
    """
    result = self._compile_expr(node.value)

    for filter_name, args, kwargs in node.steps:
        # Validate filter exists at compile time
        if filter_name not in self._env._filters:
            suggestion = self._get_filter_suggestion(filter_name)
            msg = f"Unknown filter '{filter_name}'"
            if suggestion:
                msg += f". Did you mean '{suggestion}'?"
            raise TemplateSyntaxError(msg, lineno=getattr(node, "lineno", None))

        # Compile filter arguments
        compiled_args = [self._compile_expr(arg) for arg in args]
        compiled_kwargs = [
            ast.keyword(arg=k, value=self._compile_expr(v))
            for k, v in kwargs.items()
        ]

        # Call: _filters['filter_name'](prev_result, *args, **kwargs)
        result = ast.Call(
            func=ast.Subscript(
                value=ast.Name(id="_filters", ctx=ast.Load()),
                slice=ast.Constant(value=filter_name),
                ctx=ast.Load(),
            ),
            args=[result] + compiled_args,
            keywords=compiled_kwargs,
        )

    return result
```

Update `_compile_expr()` method (add after the `Filter` handling, before `BinOp`):

```python
if node_type == "Pipeline":
    return self._compile_pipeline(node)
```

The placement should be around line 278, after the Filter block and before BinOp.

---

## Implementation Order

### Phase 1: `|>` Pipeline Operator (Half Day)

> Lexer and types already complete. Only parser and compiler needed.

**Parser Changes** (3 tasks):
1. `expressions.py`: Import `Pipeline` node
2. `expressions.py`: Replace `_parse_filter_chain()` with version that detects `|>`
3. `expressions.py`: Add `_parse_pipeline()` method

**Compiler Changes** (2 tasks):
4. `expressions.py`: Add `_compile_pipeline()` method
5. `expressions.py`: Add `"Pipeline"` case to `_compile_expr()`

**Tests** (1 task):
6. Create `tests/rendering/kida/test_kida_pipeline.py`

### Phase 2: `{% match %}` Pattern Matching (Half Day)

> Keywords already in `KEYWORDS`. Need parser infrastructure and compiler.

**Parser Infrastructure** (2 tasks):
1. `blocks/core.py`: Add `"endmatch"` to `_END_KEYWORDS`
2. `blocks/core.py`: Add `"case"` to `_CONTINUATION_KEYWORDS`

**Parser Statement Dispatch** (3 tasks):
3. `statements.py`: Add `"match"` case to `_parse_block_content()`
4. `statements.py`: Add `"endmatch"` to end tag list
5. `statements.py`: Add `"case"` to continuation error handling

**Parser Implementation** (2 tasks):
6. `blocks/control_flow.py`: Import `Match` node
7. `blocks/control_flow.py`: Add `_parse_match()` method

**Compiler Changes** (2 tasks):
8. `statements/control_flow.py`: Add `_compile_match()` method
9. `core.py`: Add `"Match": self._compile_match` to `_get_node_dispatch()`

**Tests** (1 task):
10. Create `tests/rendering/kida/test_kida_match.py`

### Phase 3: Integration & Documentation (Day 3)

1. Update `bengal/rendering/kida/__init__.py` docstring
2. Update template syntax documentation
3. Add examples to existing test templates
4. Run full test suite

---

## Test Cases

### Pipeline Tests

```python
# tests/rendering/kida/test_kida_pipeline.py

import pytest
from bengal.rendering.kida.environment.exceptions import TemplateSyntaxError


class TestPipelineOperator:
    """Tests for |> pipeline operator."""

    def test_single_pipeline(self, env):
        """Single pipeline step works."""
        template = env.from_string("{{ 'hello' |> upper }}")
        assert template.render() == "HELLO"

    def test_chained_pipeline(self, env):
        """Multiple pipeline steps chain correctly."""
        template = env.from_string("{{ 'hello world' |> upper |> replace('O', '0') }}")
        assert template.render() == "HELL0 W0RLD"

    def test_pipeline_with_args(self, env):
        """Pipeline with positional arguments."""
        template = env.from_string("{{ items |> batch(2) |> list }}")
        result = template.render(items=[1, 2, 3, 4])
        assert "[[1, 2], [3, 4]]" in result

    def test_pipeline_with_kwargs(self, env):
        """Pipeline with keyword arguments."""
        template = env.from_string("{{ items |> sort(reverse=true) |> first }}")
        result = template.render(items=[1, 3, 2])
        assert result.strip() == "3"

    def test_pipeline_in_expression(self, env):
        """Pipeline within larger expression."""
        template = env.from_string("{{ (items |> length) + 10 }}")
        assert template.render(items=[1, 2, 3]) == "13"

    def test_mixed_pipe_and_pipeline_error(self, env):
        """Cannot mix | and |> in same expression."""
        with pytest.raises(TemplateSyntaxError, match="Cannot mix"):
            env.from_string("{{ x | upper |> lower }}")

    def test_mixed_pipeline_and_pipe_error(self, env):
        """Cannot mix |> and | in same expression."""
        with pytest.raises(TemplateSyntaxError, match="Cannot mix"):
            env.from_string("{{ x |> upper | lower }}")

    def test_pipeline_preserves_filter_semantics(self, env):
        """Pipeline should behave identically to filter chain."""
        items = [{"name": "b"}, {"name": "a"}]

        filter_result = env.from_string(
            "{{ items | sort(attribute='name') | first }}"
        ).render(items=items)

        pipeline_result = env.from_string(
            "{{ items |> sort(attribute='name') |> first }}"
        ).render(items=items)

        assert filter_result == pipeline_result

    def test_pipeline_unknown_filter_error(self, env):
        """Unknown filter in pipeline raises error at compile time."""
        with pytest.raises(TemplateSyntaxError, match="Unknown filter"):
            env.from_string("{{ x |> nonexistent_filter }}")

    def test_pipeline_filter_typo_suggestion(self, env):
        """Typo in filter name suggests correction."""
        with pytest.raises(TemplateSyntaxError, match="Did you mean"):
            env.from_string("{{ x |> uper }}")  # typo for 'upper'


class TestPipelineEdgeCases:
    """Edge cases for pipeline operator."""

    def test_empty_pipeline(self, env):
        """Expression without pipeline returns value unchanged."""
        template = env.from_string("{{ x }}")
        assert template.render(x="hello") == "hello"

    def test_pipeline_with_none(self, env):
        """Pipeline handles None values correctly."""
        template = env.from_string("{{ x |> default('fallback') }}")
        assert template.render(x=None) == "fallback"

    def test_nested_pipelines_in_ternary(self, env):
        """Pipelines work in ternary expressions."""
        template = env.from_string(
            "{{ (a |> upper) if condition else (b |> lower) }}"
        )
        assert template.render(a="hi", b="BYE", condition=True) == "HI"
        assert template.render(a="hi", b="BYE", condition=False) == "bye"
```

### Match Tests

```python
# tests/rendering/kida/test_kida_match.py

import pytest
from bengal.rendering.kida.environment.exceptions import TemplateSyntaxError


class TestMatchStatement:
    """Tests for {% match %} pattern matching."""

    def test_simple_match_string(self, env):
        """Match with string literals."""
        template = env.from_string("""
        {% match x %}
            {% case "a" %}A
            {% case "b" %}B
            {% case _ %}default
        {% end %}
        """)
        assert "A" in template.render(x="a")
        assert "B" in template.render(x="b")
        assert "default" in template.render(x="z")

    def test_match_integer(self, env):
        """Match with integer values."""
        template = env.from_string("""
        {% match status %}
            {% case 200 %}OK
            {% case 404 %}Not Found
            {% case 500 %}Error
            {% case _ %}Unknown
        {% end %}
        """)
        assert "OK" in template.render(status=200)
        assert "Not Found" in template.render(status=404)
        assert "Unknown" in template.render(status=999)

    def test_match_without_default(self, env):
        """Match without wildcard produces no output for unmatched values."""
        template = env.from_string("""
        {% match x %}
            {% case "a" %}A
            {% case "b" %}B
        {% end %}
        """)
        assert "A" in template.render(x="a")
        assert template.render(x="z").strip() == ""

    def test_match_with_expression(self, env):
        """Match subject can be any expression."""
        template = env.from_string("""
        {% match page.type %}
            {% case "post" %}📝 Post
            {% case "gallery" %}🖼️ Gallery
            {% case _ %}📄 Page
        {% end %}
        """)
        assert "📝 Post" in template.render(page={"type": "post"})
        assert "📄 Page" in template.render(page={"type": "other"})

    def test_match_case_with_expression(self, env):
        """Case patterns can be expressions."""
        template = env.from_string("""
        {% match value %}
            {% case expected %}Matched expected
            {% case _ %}No match
        {% end %}
        """)
        assert "Matched expected" in template.render(value=42, expected=42)
        assert "No match" in template.render(value=42, expected=99)

    def test_match_nested_content(self, env):
        """Match cases can contain complex nested content."""
        template = env.from_string("""
        {% match item.type %}
            {% case "user" %}
                <div class="user">
                    {{ item.name }}
                </div>
            {% case "group" %}
                <div class="group">
                    {% for member in item.members %}
                        <span>{{ member }}</span>
                    {% end %}
                </div>
        {% end %}
        """)
        result = template.render(item={"type": "user", "name": "Alice"})
        assert "Alice" in result
        assert "user" in result

    def test_match_with_endmatch(self, env):
        """Both {% end %} and {% endmatch %} work."""
        template1 = env.from_string("""
        {% match x %}{% case "a" %}A{% end %}
        """)
        template2 = env.from_string("""
        {% match x %}{% case "a" %}A{% endmatch %}
        """)
        assert template1.render(x="a").strip() == template2.render(x="a").strip()

    def test_match_error_no_cases(self, env):
        """Match must have at least one case."""
        with pytest.raises(TemplateSyntaxError, match="at least one"):
            env.from_string("{% match x %}{% end %}")

    def test_match_error_invalid_block_inside(self, env):
        """Invalid keywords inside match block raise errors."""
        with pytest.raises(TemplateSyntaxError, match="Expected 'case' or 'end'"):
            env.from_string("{% match x %}{% for i in items %}{% end %}{% end %}")


class TestMatchEdgeCases:
    """Edge cases for match statement."""

    def test_nested_match(self, env):
        """Match blocks can be nested."""
        template = env.from_string("""
        {% match outer %}
            {% case "a" %}
                {% match inner %}
                    {% case 1 %}A1
                    {% case 2 %}A2
                {% end %}
            {% case "b" %}B
        {% end %}
        """)
        assert "A1" in template.render(outer="a", inner=1)
        assert "A2" in template.render(outer="a", inner=2)
        assert "B" in template.render(outer="b", inner=999)

    def test_match_with_filters(self, env):
        """Match subject can include filters."""
        template = env.from_string("""
        {% match name | lower %}
            {% case "alice" %}Found Alice
            {% case _ %}Unknown
        {% end %}
        """)
        assert "Found Alice" in template.render(name="ALICE")
        assert "Found Alice" in template.render(name="Alice")

    def test_match_boolean(self, env):
        """Match works with boolean values."""
        template = env.from_string("""
        {% match flag %}
            {% case true %}Enabled
            {% case false %}Disabled
        {% end %}
        """)
        assert "Enabled" in template.render(flag=True)
        assert "Disabled" in template.render(flag=False)

    def test_match_none(self, env):
        """Match works with None value."""
        template = env.from_string("""
        {% match value %}
            {% case none %}No value
            {% case _ %}Has value: {{ value }}
        {% end %}
        """)
        assert "No value" in template.render(value=None)
        assert "Has value: 42" in template.render(value=42)

    def test_first_match_wins(self, env):
        """First matching case is used (no fall-through)."""
        template = env.from_string("""
        {% match x %}
            {% case "a" %}First
            {% case "a" %}Second
        {% end %}
        """)
        assert "First" in template.render(x="a")
        assert "Second" not in template.render(x="a")
```

---

## Design Decisions

### 1. No Mixing of `|` and `|>`

**Decision**: Raise an error if `|` and `|>` are mixed in the same expression.

**Rationale**:
- Prevents ambiguous parsing: `x | a |> b` could mean `(x | a) |> b` or `x | (a |> b)`
- Encourages consistent code style
- Simplifies parser implementation

**Alternative considered**: Allow mixing with left-to-right precedence. Rejected due to cognitive overhead and potential confusion.

### 2. Pipeline Compiles to Same Code as Filter Chain

**Decision**: Pipeline `|>` produces identical compiled output to filter `|`.

**Rationale**:
- Zero runtime overhead
- Same semantics, different syntax
- Future optimization (filter fusion) can apply to both

### 3. Match Uses Equality Comparison

**Decision**: `{% case pattern %}` uses `==` comparison, not pattern matching.

**Rationale**:
- Simple and predictable behavior
- Matches user expectations from other languages
- Type patterns and guards can be added later (see Future Considerations)

### 4. Case is a Continuation Keyword

**Decision**: Add `"case"` to `_CONTINUATION_KEYWORDS` to reuse existing `_parse_body()`.

**Rationale**:
- Consistent with existing `elif`/`else` handling
- Reuses tested infrastructure
- Reduces code duplication

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing templates | High | New syntax only; no changes to existing constructs |
| Performance impact | Low | Pipeline compiles to same code as filter chain |
| Parser complexity | Medium | Follow existing patterns for if/for compilation |
| Nested match variable collision | Low | Use unique `_match_subject_N` with block counter |

---

## Success Criteria

**Already Complete** ✅:
- [x] `|>` tokenized by lexer as `TokenType.PIPELINE`
- [x] `PIPELINE` added to `PRECEDENCE` dict (same as `PIPE`)
- [x] `"match"`, `"case"`, `"endmatch"` added to `KEYWORDS`

**Pipeline Implementation**:
- [ ] `|>` parsed into `Pipeline` AST node
- [ ] Mixed `|`/`|>` produces clear error message
- [ ] `Pipeline` compiled to filter calls using `_filters` dict
- [ ] Pipeline filter typos suggest corrections

**Match Implementation**:
- [ ] `"endmatch"` added to `_END_KEYWORDS`
- [ ] `"case"` added to `_CONTINUATION_KEYWORDS`
- [ ] `{% match %}` parsed into `Match` AST node
- [ ] `Match` compiled to if/elif chain with unique subject variable
- [ ] Nested match blocks work correctly (no variable collision)
- [ ] Wildcard `_` pattern compiles to `True` (always matches)

**Quality Gates**:
- [ ] All new tests pass
- [ ] Existing template tests unaffected
- [ ] Documentation updated in `bengal/rendering/kida/__init__.py`

---

## Future Considerations

### Advanced Match Patterns

The current implementation uses simple equality matching. Future versions could add:

```jinja2
{# Type patterns (like Python's match) #}
{% match value %}
    {% case str as s %}String: {{ s }}
    {% case int as n %}Number: {{ n }}
    {% case list as items %}List with {{ items | length }} items
{% end %}

{# Guard clauses #}
{% match value %}
    {% case n if n > 0 %}Positive
    {% case n if n < 0 %}Negative
    {% case _ %}Zero
{% end %}

{# Tuple unpacking #}
{% match point %}
    {% case (0, 0) %}Origin
    {% case (x, 0) %}On X-axis at {{ x }}
    {% case (0, y) %}On Y-axis at {{ y }}
    {% case (x, y) %}Point at ({{ x }}, {{ y }})
{% end %}
```

### Pipeline Optimization

Future compiler optimization could fuse adjacent pipelines:

```python
# Before (current): nested calls
_filters['c'](_filters['b'](_filters['a'](x)))

# After (optimized): single fused call if filters are composable
_pipeline_abc(x)
```

---

## References

**AST Nodes** (already defined):
- `Match`: `bengal/rendering/kida/nodes.py:261-276`
- `Pipeline`: `bengal/rendering/kida/nodes.py:620-635`

**Type Infrastructure** (already complete):
- `TokenType.PIPELINE`: `bengal/rendering/kida/_types.py:105`
- `PRECEDENCE[PIPELINE]`: `bengal/rendering/kida/_types.py:231`
- `KEYWORDS` (match/case/endmatch): `bengal/rendering/kida/_types.py:201-203`
- `_OPERATORS_2CHAR["|>"]`: `bengal/rendering/kida/lexer.py:220`

**Parser** (needs modification):
- `_END_KEYWORDS`: `bengal/rendering/kida/parser/blocks/core.py:29-44`
- `_CONTINUATION_KEYWORDS`: `bengal/rendering/kida/parser/blocks/core.py:47-53`
- `_parse_block_content()`: `bengal/rendering/kida/parser/statements.py:105-203`
- `_parse_filter_chain()`: `bengal/rendering/kida/parser/expressions.py:333-363`

**Compiler** (needs modification):
- `_get_node_dispatch()`: `bengal/rendering/kida/compiler/core.py:481-506`
- Filter compilation pattern: `bengal/rendering/kida/compiler/expressions.py:229-277`

**Related**:
- RFC: `plan/drafted/rfc-kida-native-template-architecture.md`
- Template impact analysis: 84 `elif` occurrences, potential `{% match %}` candidates

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-26 | Initial draft |
| 2025-12-26 | Added KEYWORDS/PRECEDENCE updates, fixed compiler dispatch reference, added filter validation, improved test cases, added design decisions section, fixed filter compilation to use `_filters` dict pattern |
