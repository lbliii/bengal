# RFC: Kida Match and Pipeline Implementation

**Status**: Draft  
**Created**: 2025-12-26  
**Priority**: High (Prerequisite for template refactor)  
**Scope**: `bengal/rendering/kida/`

---

## Executive Summary

Two Kida-native features are defined as AST nodes but not yet implemented:

| Feature | AST Node | Parser | Compiler | Status |
|---------|----------|--------|----------|--------|
| `{% match %}` | ✅ `Match` | ❌ Missing | ❌ Missing | **Not usable** |
| `\|>` pipeline | ✅ `Pipeline` | ❌ Missing | ❌ Missing | **Not usable** |

This RFC provides implementation details for both features. They are prerequisites for the Kida-native template architecture refactor (RFC: Kida-Native Template Architecture).

---

## Problem Statement

### Current State

The Kida AST defines `Match` and `Pipeline` nodes (`bengal/rendering/kida/nodes.py`), but:

1. **No lexer support**: `|>` is not tokenized
2. **No parser support**: `{% match %}` and `|>` are not parsed
3. **No compiler support**: No Python AST generation

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

```python
@dataclass(frozen=True, slots=True)
class Match(Node):
    """Pattern matching: {% match expr %}{% case pattern %}...{% end %}"""
    subject: Expr
    cases: Sequence[tuple[Expr, Sequence[Node]]]  # (pattern, body)
```

### Implementation Plan

#### 1. Lexer: No Changes Needed

Keywords `match` and `case` are recognized as `TokenType.NAME`. The underscore `_` is also valid as a name. No lexer changes required.

#### 2. Parser: Add `_parse_match()` Method

**File**: `bengal/rendering/kida/parser/statements.py`

Add to the keyword dispatch:

```python
# In _parse_block_content():
elif keyword == "match":
    return self._parse_match()
```

**File**: `bengal/rendering/kida/parser/blocks/control_flow.py`

New method:

```python
def _parse_match(self) -> Match:
    """Parse {% match expr %}{% case pattern %}...{% end %}.
    
    Pattern matching for cleaner branching than if/elif chains.
    
    Syntax:
        {% match page.type %}
            {% case "post" %}...
            {% case "gallery" %}...
            {% case _ %}...
        {% end %}
    
    The underscore (_) is the wildcard/default case.
    """
    from bengal.rendering.kida.nodes import Match
    
    start = self._advance()  # consume 'match'
    self._push_block("match", start)
    
    # Parse subject expression
    subject = self._parse_expression()
    self._expect(TokenType.BLOCK_END)
    
    cases: list[tuple[Expr, Sequence[Node]]] = []
    
    # Parse case clauses
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
            
            # Parse case body - stop at next case or end
            body = self._parse_match_body()
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

def _parse_match_body(self) -> list[Node]:
    """Parse match case body until next case or end."""
    nodes: list[Node] = []
    
    while self._current.type != TokenType.EOF:
        if self._current.type == TokenType.BLOCK_BEGIN:
            next_tok = self._peek(1)
            if next_tok.type == TokenType.NAME:
                # Stop on case, end, or endmatch
                if next_tok.value in ("case", "end", "endmatch"):
                    break
        
        if self._current.type == TokenType.BLOCK_BEGIN:
            node = self._parse_block()
            if node is not None:
                nodes.append(node)
        elif self._current.type == TokenType.DATA:
            nodes.append(self._parse_data())
        elif self._current.type == TokenType.VARIABLE_BEGIN:
            nodes.append(self._parse_output())
        elif self._current.type == TokenType.COMMENT_BEGIN:
            self._skip_comment()
        else:
            self._advance()
    
    return nodes
```

**Update Keywords/End Tags**:

```python
# In statements.py, add to _parse_block_content():
elif keyword == "match":
    return self._parse_match()

# In statements.py, add "endmatch" to end tag list:
elif keyword in (
    "endif", "endfor", "endblock", "endmacro", "endwith",
    "endraw", "end", "enddef", "endcall", "endcapture",
    "endcache", "endfilter", "endmatch",  # <-- Add this
):
```

#### 3. Compiler: Add `_compile_match()` Method

**File**: `bengal/rendering/kida/compiler/statements/control_flow.py`

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
    """
    from bengal.rendering.kida.nodes import Name as KidaName
    
    stmts: list[ast.stmt] = []
    
    # _match_subject = expr
    subject_var = "_match_subject"
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
            # Wildcard: always True
            test = ast.Constant(value=True)
        else:
            # Equality comparison: _match_subject == pattern
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

**Register in Compiler**:

```python
# In bengal/rendering/kida/compiler/core.py, add to _NODE_COMPILERS:
"Match": self._compile_match,
```

---

## Feature 2: `|>` Pipeline Operator

### Syntax

```jinja2
{# Filter chain with pipeline operator #}
{{ items |> where(published=true) |> sort_by('date') |> take(5) }}

{# Equivalent to nested filters (harder to read) #}
{{ items | where(published=true) | sort_by('date') | take(5) }}
```

### AST Node (Already Defined)

```python
@dataclass(frozen=True, slots=True)
class Pipeline(Expr):
    """Pipeline operator: expr |> filter1 |> filter2"""
    value: Expr
    steps: Sequence[tuple[str, Sequence[Expr], dict[str, Expr]]]  # (name, args, kwargs)
```

### Implementation Plan

#### 1. Lexer: Add `|>` Token

**File**: `bengal/rendering/kida/_types.py`

Add new token type:

```python
class TokenType(Enum):
    # ... existing tokens ...
    
    # Pipeline operator (Kida-native)
    PIPELINE = "pipeline"  # |>
```

**File**: `bengal/rendering/kida/lexer.py`

Add to operator lookup (2-char operators are checked first):

```python
# In Lexer class, add to _OPERATORS_2CHAR dict:
_OPERATORS_2CHAR: ClassVar[dict[str, TokenType]] = {
    "**": TokenType.POW,
    "//": TokenType.FLOORDIV,
    "==": TokenType.EQ,
    "!=": TokenType.NE,
    "<=": TokenType.LE,
    ">=": TokenType.GE,
    "|>": TokenType.PIPELINE,  # <-- Add this
}
```

#### 2. Parser: Add Pipeline Parsing

**File**: `bengal/rendering/kida/parser/expressions.py`

Modify `_parse_filter_chain` to also handle `|>`:

```python
def _parse_filter_chain(self, expr: Expr) -> Expr:
    """Parse filter chain: expr | filter1 | filter2(arg).
    
    Also handles pipeline operator: expr |> filter1 |> filter2(arg).
    
    The difference is syntactic only - both produce the same result.
    Pipeline uses |> which is visually clearer for chained operations.
    """
    from bengal.rendering.kida.nodes import Pipeline
    
    # Check for pipeline operator first
    if self._match(TokenType.PIPELINE):
        return self._parse_pipeline(expr)
    
    # Standard filter chain
    while self._match(TokenType.PIPE):
        self._advance()
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
    """
    from bengal.rendering.kida.nodes import Pipeline
    
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
    
    if not steps:
        return expr
    
    return Pipeline(
        lineno=expr.lineno,
        col_offset=expr.col_offset,
        value=expr,
        steps=tuple(steps),
    )
```

**Update imports** in expressions.py:

```python
from bengal.rendering.kida.nodes import (
    # ... existing imports ...
    Pipeline,
)
```

#### 3. Compiler: Add Pipeline Compilation

**File**: `bengal/rendering/kida/compiler/expressions.py`

Add method:

```python
def _compile_pipeline(self, node: Any) -> ast.expr:
    """Compile pipeline: expr |> filter1 |> filter2.
    
    Pipelines compile to nested filter calls, just like regular
    filter chains. The difference is purely syntactic.
    
    expr |> a |> b(x)  →  _filter_b(_filter_a(expr), x)
    
    For now, we expand to nested filter calls. Future optimization
    could potentially fuse adjacent filters.
    """
    result = self._compile_expr(node.value)
    
    for filter_name, args, kwargs in node.steps:
        # Compile filter arguments
        compiled_args = [self._compile_expr(arg) for arg in args]
        compiled_kwargs = [
            ast.keyword(arg=k, value=self._compile_expr(v))
            for k, v in kwargs.items()
        ]
        
        # Look up filter in registry
        filter_func = f"_filter_{filter_name}"
        
        # Call: _filter_name(prev_result, *args, **kwargs)
        result = ast.Call(
            func=ast.Name(id=filter_func, ctx=ast.Load()),
            args=[result] + compiled_args,
            keywords=compiled_kwargs,
        )
    
    return result
```

**Register in Compiler**:

```python
# In expression compilation dispatch, add:
elif isinstance(node, Pipeline):
    return self._compile_pipeline(node)
```

---

## Implementation Order

### Phase 1: `|>` Pipeline Operator (Day 1)

1. **Lexer** (`_types.py`, `lexer.py`):
   - Add `TokenType.PIPELINE`
   - Add `"|>": TokenType.PIPELINE` to 2-char operators

2. **Parser** (`expressions.py`):
   - Import `Pipeline` node
   - Add `_parse_pipeline()` method
   - Modify `_parse_filter_chain()` to check for `|>`

3. **Compiler** (`expressions.py`):
   - Add `_compile_pipeline()` method
   - Register in expression dispatch

4. **Tests**:
   - `tests/rendering/kida/test_kida_pipeline.py`

### Phase 2: `{% match %}` Pattern Matching (Day 2)

1. **Parser** (`statements.py`, `blocks/control_flow.py`):
   - Add `_parse_match()` method
   - Add `_parse_match_body()` helper
   - Register "match" keyword
   - Add "endmatch" to end tags

2. **Compiler** (`statements/control_flow.py`, `core.py`):
   - Add `_compile_match()` method
   - Register in node compiler dispatch

3. **Tests**:
   - `tests/rendering/kida/test_kida_match.py`

### Phase 3: Integration & Documentation (Day 3)

1. Update `bengal/rendering/kida/__init__.py` docstring
2. Update `TEMPLATE-CONTEXT.md` with new syntax
3. Add examples to existing test templates
4. Run full test suite

---

## Test Cases

### Pipeline Tests

```python
# tests/rendering/kida/test_kida_pipeline.py

class TestPipelineOperator:
    def test_single_pipeline(self, env):
        template = env.from_string("{{ 'hello' |> upper }}")
        assert template.render() == "HELLO"
    
    def test_chained_pipeline(self, env):
        template = env.from_string("{{ 'hello world' |> upper |> title }}")
        assert template.render() == "Hello World"
    
    def test_pipeline_with_args(self, env):
        template = env.from_string("{{ items |> take(3) }}")
        result = template.render(items=[1, 2, 3, 4, 5])
        assert result == "[1, 2, 3]"
    
    def test_pipeline_with_kwargs(self, env):
        template = env.from_string("{{ items |> sort_by('name', reverse=true) }}")
        # ... test implementation
    
    def test_mixed_pipe_and_pipeline_error(self, env):
        """Cannot mix | and |> in same expression."""
        with pytest.raises(TemplateSyntaxError):
            env.from_string("{{ x | a |> b }}")
    
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
```

### Match Tests

```python
# tests/rendering/kida/test_kida_match.py

class TestMatchStatement:
    def test_simple_match(self, env):
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
    
    def test_match_without_default(self, env):
        template = env.from_string("""
        {% match x %}
            {% case "a" %}A
            {% case "b" %}B
        {% end %}
        """)
        assert "A" in template.render(x="a")
        assert "" == template.render(x="z").strip()
    
    def test_match_with_expressions(self, env):
        template = env.from_string("""
        {% match page.type %}
            {% case "post" %}📝 Post
            {% case "gallery" %}🖼️ Gallery
            {% case _ %}📄 Page
        {% end %}
        """)
        # ... test implementation
    
    def test_match_nested_content(self, env):
        """Match cases can contain complex content."""
        template = env.from_string("""
        {% match item.type %}
            {% case "user" %}
                <div class="user">
                    {{ item.name }}
                </div>
            {% case "group" %}
                <div class="group">
                    {% for member in item.members %}
                        {{ member }}
                    {% end %}
                </div>
        {% end %}
        """)
        # ... test implementation
    
    def test_match_error_no_cases(self, env):
        """Match must have at least one case."""
        with pytest.raises(TemplateSyntaxError):
            env.from_string("{% match x %}{% end %}")
    
    def test_match_with_endmatch(self, env):
        """Both {% end %} and {% endmatch %} work."""
        template1 = env.from_string("""
        {% match x %}{% case "a" %}A{% end %}
        """)
        template2 = env.from_string("""
        {% match x %}{% case "a" %}A{% endmatch %}
        """)
        assert template1.render(x="a") == template2.render(x="a")
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing templates | New syntax only; no changes to existing constructs |
| Performance impact | Pipeline compiles to same code as filter chain |
| Complexity in compiler | Follow existing patterns for if/for compilation |
| Mixing `\|` and `\|>` | Either: allow mixing, or error on mixed usage |

---

## Success Criteria

- [ ] `|>` tokenized by lexer
- [ ] `|>` parsed into `Pipeline` AST node
- [ ] `Pipeline` compiled to filter calls
- [ ] `{% match %}` parsed into `Match` AST node
- [ ] `Match` compiled to if/elif chain
- [ ] All tests pass
- [ ] Existing templates unaffected
- [ ] Documentation updated

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
```

### Pipeline Optimization

Future compiler optimization could fuse adjacent pipelines:

```python
# Before (current): nested calls
_filter_c(_filter_b(_filter_a(x)))

# After (optimized): single fused call
_pipeline_abc(x)
```

---

## References

- AST Nodes: `bengal/rendering/kida/nodes.py:261-276` (Match), `620-635` (Pipeline)
- Parser examples: `bengal/rendering/kida/parser/blocks/control_flow.py`
- Compiler examples: `bengal/rendering/kida/compiler/statements/control_flow.py`
- Related RFC: `plan/drafted/rfc-kida-native-template-architecture.md`

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-26 | Initial draft |

