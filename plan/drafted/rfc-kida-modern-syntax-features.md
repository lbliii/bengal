# RFC: Kida Modern Syntax Features

**Status**: Draft  
**Created**: 2025-12-26  
**Priority**: Medium-High  
**Effort**: ~33 hours (~4 days)  
**Impact**: High - Developer experience, modern feel, reduced boilerplate  
**Category**: Parser / Syntax / DX  
**Scope**: `bengal/rendering/kida/`

---

## Executive Summary

This RFC proposes a collection of modern syntax features inspired by JavaScript, Ruby, and other template engines that developers love. These features reduce boilerplate, improve readability, and give Kida a contemporary feel.

**Proposed Features**:

| Feature | Syntax | Effort | Impact |
|---------|--------|--------|--------|
| Optional Chaining | `user?.profile?.avatar` | 4h | ⭐⭐⭐ |
| Null Coalescing | `value ?? 'default'` | 3h | ⭐⭐⭐ |
| Break/Continue | `{% break %}`, `{% continue %}` | 5h | ⭐⭐⭐ |
| Inline If in For | `{% for x in items if x.visible %}` | 2h | ⭐⭐⭐ |
| Unless Block | `{% unless condition %}` | 2h | ⭐⭐ |
| Range Literals | `1..10`, `1...11` | 5h | ⭐⭐ |
| Spaceless Block | `{% spaceless %}...{% end %}` | 4h | ⭐⭐ |
| Embed Block | `{% embed 'card.html' %}...{% end %}` | 8h | ⭐⭐ |

**Total Effort**: ~33 hours (~4 days)

---

## Feature 1: Optional Chaining `?.`

### Problem

Accessing nested properties requires verbose defensive coding:

```jinja
{# Current: verbose and error-prone #}
{% if user and user.profile and user.profile.settings %}
    {{ user.profile.settings.theme }}
{% end %}

{# Or with multiple defaults #}
{{ (user.profile.settings.theme if user.profile.settings else 'light') if user.profile else 'light' if user else 'light' }}
```

### Solution

JavaScript-style optional chaining:

```jinja
{# Proposed: clean and readable #}
{{ user?.profile?.settings?.theme ?? 'light' }}

{# Works with method calls too #}
{{ user?.get_preferences()?.theme }}

{# And with subscripts #}
{{ data?.items?[0]?.name }}
```

### Semantics

- `a?.b` returns `None` if `a` is `None` or `undefined`, otherwise `a.b`
- Short-circuits: `None?.anything` returns `None` without evaluating `anything`
- Works with: attribute access (`.`), subscript (`[]`), and method calls (`()`)

### Implementation

**Lexer**: Add `OPTIONAL_DOT` token (`?.`)

```python
# In lexer token patterns
TokenType.OPTIONAL_DOT: r'\?\.',
```

**Parser**: Modify `_parse_postfix` to handle `?.`

```python
def _parse_postfix(self, node: Expr) -> Expr:
    while True:
        if self._match(TokenType.DOT):
            # Regular attribute access
            node = Getattr(obj=node, attr=self._expect_name())
        elif self._match(TokenType.OPTIONAL_DOT):
            # Optional chaining
            node = OptionalGetattr(obj=node, attr=self._expect_name())
        elif self._match(TokenType.LBRACKET):
            # Subscript (handle ?[ for optional)
            ...
        else:
            break
    return node
```

**AST Node**:

```python
@dataclass(frozen=True, slots=True)
class OptionalGetattr(Expr):
    """Optional attribute access: obj?.attr

    Returns None if obj is None/undefined, otherwise obj.attr.
    """
    obj: Expr
    attr: str


@dataclass(frozen=True, slots=True)
class OptionalGetitem(Expr):
    """Optional subscript access: obj?[key]

    Returns None if obj is None/undefined, otherwise obj[key].
    """
    obj: Expr
    key: Expr
```

**Compiler**:

```python
def _compile_optional_getattr(self, node: OptionalGetattr) -> ast.expr:
    """Compile obj?.attr using walrus operator to avoid double evaluation.

    obj?.attr compiles to:
        (_tmp := obj).attr if _tmp is not None else None
    """
    obj = self._compile_expr(node.obj)
    tmp_name = self._gensym("_oc")  # Generate unique temp name

    # Use walrus operator to cache obj and avoid double evaluation
    return ast.IfExp(
        test=ast.Compare(
            left=ast.NamedExpr(
                target=ast.Name(id=tmp_name, ctx=ast.Store()),
                value=obj,
            ),
            ops=[ast.IsNot()],
            comparators=[ast.Constant(value=None)],
        ),
        body=ast.Attribute(
            value=ast.Name(id=tmp_name, ctx=ast.Load()),
            attr=node.attr,
            ctx=ast.Load(),
        ),
        orelse=ast.Constant(value=None),
    )
```

**Chained Expressions**: For `user?.profile?.name`, each level uses its own temp:

```python
# user?.profile?.name compiles to:
# ((_t1 := user) is not None and
#  (_t2 := _t1.profile) is not None and
#  _t2.name) or None
```

### Tests

```python
class TestOptionalChaining:
    def test_none_short_circuit(self, env):
        tmpl = env.from_string("{{ user?.name }}")
        assert tmpl.render(user=None) == ""
        assert tmpl.render(user={"name": "Alice"}) == "Alice"

    def test_nested_optional(self, env):
        tmpl = env.from_string("{{ user?.profile?.avatar }}")
        assert tmpl.render(user=None) == ""
        assert tmpl.render(user={"profile": None}) == ""
        assert tmpl.render(user={"profile": {"avatar": "pic.png"}}) == "pic.png"

    def test_with_null_coalescing(self, env):
        tmpl = env.from_string("{{ user?.name ?? 'Anonymous' }}")
        assert tmpl.render(user=None) == "Anonymous"
        assert tmpl.render(user={"name": "Bob"}) == "Bob"

    def test_optional_subscript(self, env):
        tmpl = env.from_string("{{ items?[0]?.name }}")
        assert tmpl.render(items=None) == ""
        assert tmpl.render(items=[]) == ""
        assert tmpl.render(items=[{"name": "First"}]) == "First"
```

---

## Feature 2: Null Coalescing `??`

### Problem

The `default` filter is verbose for simple fallbacks:

```jinja
{# Current #}
{{ user.name | default('Anonymous') }}
{{ config.timeout | default(30) }}
{{ items | default([]) | length }}
```

### Solution

JavaScript/PHP-style null coalescing operator:

```jinja
{# Proposed #}
{{ user.name ?? 'Anonymous' }}
{{ config.timeout ?? 30 }}
{{ (items ?? []) | length }}

{# Chainable #}
{{ primary ?? secondary ?? tertiary ?? 'fallback' }}
```

### Semantics

- `a ?? b` returns `b` if `a` is `None` or `undefined`, otherwise `a`
- Unlike `or`, doesn't treat falsy values (0, '', False, []) as missing
- Right-associative: `a ?? b ?? c` = `a ?? (b ?? c)`

### Undefined Behavior

In Kida's strict mode, undefined variables raise `UndefinedError`. The `??` operator catches this:

```jinja
{# Strict mode: missing raises UndefinedError normally #}
{{ missing }}  {# Raises UndefinedError #}

{# But ?? catches undefined and uses fallback #}
{{ missing ?? 'default' }}  {# → 'default' #}

{# Chain with optional chaining #}
{{ user?.profile?.theme ?? settings?.default_theme ?? 'light' }}
```

**Implementation Note**: The compiler wraps the left operand in a try/except for `UndefinedError`:

```python
# a ?? b compiles to:
try:
    _nc_tmp = a
except UndefinedError:
    _nc_tmp = None
result = _nc_tmp if _nc_tmp is not None else b
```

### Comparison with `or` and `default`

```jinja
{# These behave DIFFERENTLY #}
{{ count ?? 0 }}       {# Returns 0 only if count is None #}
{{ count or 0 }}       {# Returns 0 if count is 0, None, '', False, [] #}
{{ count | default(0) }}  {# Same as ?? for None #}

{# Example: count = 0 #}
{{ count ?? 100 }}     {# → 0 (count exists) #}
{{ count or 100 }}     {# → 100 (0 is falsy) #}
```

### Implementation

**Lexer**: Add `NULLISH_COALESCE` token (`??`)

```python
TokenType.NULLISH_COALESCE: r'\?\?',
```

**Parser**: Add to binary operator precedence (lower than `or`)

```python
# Precedence table update in _types.py:
# Current: OR: 1 (lowest)
# New:     NULLISH_COALESCE: 0, OR: 1, AND: 2, ...

# In PRECEDENCE dict:
TokenType.NULLISH_COALESCE: 0,  # Lowest precedence

def _parse_nullish_coalesce(self) -> Expr:
    left = self._parse_or()
    while self._match(TokenType.NULLISH_COALESCE):
        right = self._parse_or()
        left = NullCoalesce(left=left, right=right, ...)
    return left
```

**Precedence Rationale**: `??` binds looser than `or` so that:
```jinja
{{ a or b ?? 'fallback' }}  {# Parsed as: (a or b) ?? 'fallback' #}
```

**AST Node**:

```python
@dataclass(frozen=True, slots=True)
class NullCoalesce(Expr):
    """Null coalescing: a ?? b

    Returns b if a is None/undefined, otherwise a.
    Unlike 'or', doesn't treat falsy values as missing.
    """
    left: Expr
    right: Expr
```

**Compiler**:

```python
def _compile_null_coalesce(self, node: NullCoalesce) -> ast.expr:
    """Compile a ?? b to: a if a is not None else b"""
    left = self._compile_expr(node.left)
    right = self._compile_expr(node.right)

    # Use walrus to avoid double evaluation
    # (_tmp := a) if _tmp is not None else b
    return ast.IfExp(
        test=ast.Compare(
            left=ast.NamedExpr(
                target=ast.Name(id="_nc_tmp", ctx=ast.Store()),
                value=left,
            ),
            ops=[ast.IsNot()],
            comparators=[ast.Constant(value=None)],
        ),
        body=ast.Name(id="_nc_tmp", ctx=ast.Load()),
        orelse=right,
    )
```

### Tests

```python
class TestNullCoalescing:
    def test_none_fallback(self, env):
        tmpl = env.from_string("{{ x ?? 'default' }}")
        assert tmpl.render(x=None) == "default"
        assert tmpl.render(x="value") == "value"

    def test_preserves_falsy(self, env):
        """Unlike 'or', ?? preserves falsy values."""
        tmpl = env.from_string("{{ x ?? 'default' }}")
        assert tmpl.render(x=0) == "0"
        assert tmpl.render(x="") == ""
        assert tmpl.render(x=False) == "False"
        assert tmpl.render(x=[]) == "[]"

    def test_chained(self, env):
        tmpl = env.from_string("{{ a ?? b ?? c ?? 'last' }}")
        assert tmpl.render(a=None, b=None, c=None) == "last"
        assert tmpl.render(a=None, b=None, c="found") == "found"
        assert tmpl.render(a="first", b="second", c="third") == "first"

    def test_with_optional_chaining(self, env):
        tmpl = env.from_string("{{ user?.name ?? 'Anonymous' }}")
        assert tmpl.render(user=None) == "Anonymous"
        assert tmpl.render(user={"name": None}) == "Anonymous"
        assert tmpl.render(user={"name": "Alice"}) == "Alice"

    def test_undefined_fallback(self, env):
        """Undefined (not just None) should trigger fallback in strict mode."""
        tmpl = env.from_string("{{ missing ?? 'default' }}")
        assert tmpl.render() == "default"  # missing is undefined

    def test_undefined_vs_none(self, env):
        """Distinguish between undefined and explicitly None."""
        tmpl = env.from_string("{{ x ?? 'was undefined or none' }}")
        assert tmpl.render() == "was undefined or none"  # undefined
        assert tmpl.render(x=None) == "was undefined or none"  # None
        assert tmpl.render(x="value") == "value"  # defined
```

---

## Feature 3: Break and Continue

### Problem

Kida loops cannot be exited early or skipped:

```jinja
{# Current: no way to break early #}
{% for item in expensive_items %}
    {% if found %}
        {# Still iterates through remaining items #}
    {% else %}
        {% if item.matches %}
            {{ item }}
            {% set found = true %}
        {% end %}
    {% end %}
{% end %}
```

### Solution

Standard loop control:

```jinja
{# Proposed: clean and efficient #}
{% for item in items %}
    {% if item.skip %}{% continue %}{% end %}
    {% if item.stop %}{% break %}{% end %}
    {{ item.name }}
{% end %}

{# Find first match #}
{% for item in items %}
    {% if item.matches %}
        {{ item }}
        {% break %}
    {% end %}
{% end %}
```

### Implementation

**AST Nodes**:

```python
@dataclass(frozen=True, slots=True)
class Break(Node):
    """Break out of loop: {% break %}"""
    pass


@dataclass(frozen=True, slots=True)
class Continue(Node):
    """Skip to next iteration: {% continue %}"""
    pass
```

**Parser**: Add to statement keywords

```python
def _parse_statement(self) -> Node:
    keyword = self._current.value

    if keyword == "break":
        return self._parse_break()
    elif keyword == "continue":
        return self._parse_continue()
    # ...

def _parse_break(self) -> Break:
    start = self._advance()  # consume 'break'
    self._expect(TokenType.BLOCK_END)
    return Break(lineno=start.lineno, col_offset=start.col_offset)

def _parse_continue(self) -> Continue:
    start = self._advance()  # consume 'continue'
    self._expect(TokenType.BLOCK_END)
    return Continue(lineno=start.lineno, col_offset=start.col_offset)
```

**Compiler**:

```python
def _compile_break(self, node: Break) -> list[ast.stmt]:
    return [ast.Break()]

def _compile_continue(self, node: Continue) -> list[ast.stmt]:
    return [ast.Continue()]
```

**Validation**: Add compile-time check that break/continue are inside loops.

The existing `BlockStackMixin` tracks nested blocks. Extend it to check for loop context:

```python
# In BlockStackMixin (parser/blocks/core.py):
LOOP_BLOCKS = frozenset({"for", "while"})

def _in_loop(self) -> bool:
    """Check if currently inside a loop block."""
    return any(block_type in self.LOOP_BLOCKS for block_type, _ in self._block_stack)

# In parser when encountering break/continue:
def _parse_break(self) -> Break:
    start = self._advance()  # consume 'break'

    if not self._in_loop():
        raise self._error(
            "'break' outside loop",
            suggestion="Use 'break' only inside {% for %} or {% while %} loops",
        )

    self._expect(TokenType.BLOCK_END)
    return Break(lineno=start.lineno, col_offset=start.col_offset)
```

**Note**: Validation happens at parse time, not compile time, for better error messages with source location.

### Tests

```python
class TestBreakContinue:
    def test_break(self, env):
        tmpl = env.from_string("""
            {% for i in range(10) %}
                {{ i }}
                {% if i == 3 %}{% break %}{% end %}
            {% end %}
        """)
        assert tmpl.render().split() == ["0", "1", "2", "3"]

    def test_continue(self, env):
        tmpl = env.from_string("""
            {% for i in range(5) %}
                {% if i == 2 %}{% continue %}{% end %}
                {{ i }}
            {% end %}
        """)
        assert tmpl.render().split() == ["0", "1", "3", "4"]

    def test_break_in_nested(self, env):
        """Break only exits innermost loop."""
        tmpl = env.from_string("""
            {% for i in range(3) %}
                {% for j in range(3) %}
                    {% if j == 1 %}{% break %}{% end %}
                    {{ i }}-{{ j }}
                {% end %}
            {% end %}
        """)
        result = tmpl.render().split()
        assert result == ["0-0", "1-0", "2-0"]

    def test_break_outside_loop_error(self, env):
        with pytest.raises(TemplateSyntaxError, match="outside loop"):
            env.from_string("{% break %}")

    def test_continue_outside_loop_error(self, env):
        with pytest.raises(TemplateSyntaxError, match="outside loop"):
            env.from_string("{% continue %}")
```

---

## Feature 4: Inline If in For Loops

### Problem

Filtering in loops requires nested if blocks:

```jinja
{# Current: nested and verbose #}
{% for item in items %}
    {% if item.published and item.visible %}
        {{ item.title }}
    {% end %}
{% end %}
```

### Solution

Python-style inline filtering:

```jinja
{# Proposed: clean and readable #}
{% for item in items if item.published and item.visible %}
    {{ item.title }}
{% end %}

{# Multiple conditions #}
{% for post in posts if post.status == 'published' if post.category == 'tech' %}
    {{ post.title }}
{% end %}
```

### Status

The `For` AST node already has a `test` field for this! Just needs parser support.

```python
@dataclass(frozen=True, slots=True)
class For(Node):
    target: Expr
    iter: Expr
    body: Sequence[Node]
    empty: Sequence[Node] = ()
    recursive: bool = False
    test: Expr | None = None  # ← Already exists!
```

### Implementation

**Parser**: Modify `_parse_for` to check for `if` before `%}`

```python
def _parse_for(self) -> For:
    start = self._advance()  # consume 'for'

    target = self._parse_tuple_or_name()
    self._expect_keyword("in")
    iter_expr = self._parse_expression()

    # Check for inline filter: {% for x in items if condition %}
    test = None
    if self._match_keyword("if"):
        test = self._parse_expression()

    self._expect(TokenType.BLOCK_END)

    body = self._parse_body({"end", "empty", "else"})
    empty = self._parse_empty_clause()

    return For(
        lineno=start.lineno,
        col_offset=start.col_offset,
        target=target,
        iter=iter_expr,
        body=body,
        empty=empty,
        test=test,
    )
```

**Compiler**: Already handles `For.test`:

```python
def _compile_for(self, node: For) -> list[ast.stmt]:
    # ... existing code ...

    if node.test:
        # Wrap body in if statement
        body_stmts = [
            ast.If(
                test=self._compile_expr(node.test),
                body=compiled_body,
                orelse=[],
            )
        ]
    else:
        body_stmts = compiled_body
```

### Tests

```python
class TestInlineIfFor:
    def test_simple_filter(self, env):
        tmpl = env.from_string("""
            {% for x in items if x.visible %}{{ x.name }}{% end %}
        """)
        items = [
            {"name": "a", "visible": True},
            {"name": "b", "visible": False},
            {"name": "c", "visible": True},
        ]
        assert tmpl.render(items=items).strip() == "ac"

    def test_complex_condition(self, env):
        tmpl = env.from_string("""
            {% for x in items if x.count > 0 and x.active %}{{ x.name }}{% end %}
        """)
        items = [
            {"name": "a", "count": 5, "active": True},
            {"name": "b", "count": 0, "active": True},
            {"name": "c", "count": 3, "active": False},
            {"name": "d", "count": 1, "active": True},
        ]
        assert tmpl.render(items=items).strip() == "ad"

    def test_with_empty_clause(self, env):
        tmpl = env.from_string("""
            {% for x in items if x.visible %}{{ x.name }}{% empty %}None{% end %}
        """)
        items = [{"name": "a", "visible": False}]
        assert tmpl.render(items=items).strip() == "None"
```

---

## Feature 5: Unless Block

### Problem

Negated conditions are common but verbose:

```jinja
{# Current #}
{% if not user.admin %}
    Access denied
{% end %}

{% if not items %}
    No items found
{% end %}
```

### Solution

Ruby/Liquid-style `unless`:

```jinja
{# Proposed #}
{% unless user.admin %}
    Access denied
{% end %}

{% unless items %}
    No items found
{% end %}

{# With else #}
{% unless user.banned %}
    Welcome!
{% else %}
    You are banned.
{% end %}
```

### Implementation

**Parser**: Add `unless` as keyword that creates `If` with negated test

```python
def _parse_unless(self) -> If:
    """Parse {% unless cond %} as {% if not cond %}."""
    start = self._advance()  # consume 'unless'

    condition = self._parse_expression()
    self._expect(TokenType.BLOCK_END)

    body = self._parse_body({"end", "else"})
    else_body = self._parse_else_clause()

    # Create If with negated condition
    return If(
        lineno=start.lineno,
        col_offset=start.col_offset,
        test=UnaryOp(op="not", operand=condition, ...),
        body=body,
        elif_=(),
        else_=else_body,
    )
```

**Note**: No AST changes needed - `unless` desugars to `If(not condition)`.

### Tests

```python
class TestUnless:
    def test_basic_unless(self, env):
        tmpl = env.from_string("{% unless x %}yes{% end %}")
        assert tmpl.render(x=False) == "yes"
        assert tmpl.render(x=True) == ""

    def test_unless_with_else(self, env):
        tmpl = env.from_string("{% unless x %}no{% else %}yes{% end %}")
        assert tmpl.render(x=False) == "no"
        assert tmpl.render(x=True) == "yes"

    def test_unless_complex_condition(self, env):
        tmpl = env.from_string("{% unless user.admin or user.moderator %}denied{% end %}")
        assert tmpl.render(user={"admin": False, "moderator": False}) == "denied"
        assert tmpl.render(user={"admin": True, "moderator": False}) == ""
```

---

## Feature 6: Range Literals

### Problem

Range expressions require function calls:

```jinja
{# Current #}
{% for i in range(1, 11) %}
{% for i in range(0, 100, 10) %}
```

### Solution

Ruby-style range literals:

```jinja
{# Proposed: inclusive end #}
{% for i in 1..10 %}     {# 1, 2, 3, ..., 10 #}

{# Exclusive end (like Python range) #}
{% for i in 1...11 %}    {# 1, 2, 3, ..., 10 #}

{# Variables work too #}
{% for i in start..end %}

{# Step syntax (optional enhancement) #}
{% for i in 0..100 by 10 %}  {# 0, 10, 20, ..., 100 #}
```

### Implementation

**Lexer**: Add range tokens with disambiguation

```python
# In TokenType enum:
RANGE_INCLUSIVE = "range_inclusive"  # ..
RANGE_EXCLUSIVE = "range_exclusive"  # ...

# In lexer operator lookup (check 3-char before 2-char):
_OPERATORS_3CHAR: dict[str, TokenType] = {
    "...": TokenType.RANGE_EXCLUSIVE,
}
_OPERATORS_2CHAR: dict[str, TokenType] = {
    "..": TokenType.RANGE_INCLUSIVE,
    # ... existing operators ...
}
```

**Disambiguation**: The lexer checks longest match first (`...` before `..`). The parser validates that ranges have numeric/variable operands:

```python
def _parse_range(self, left: Expr) -> Expr:
    # Range literals only valid after numeric literals or names
    # This prevents confusion with attribute access typos
    if not isinstance(left, (Const, Name)):
        raise self._error(
            "Range literal requires numeric or variable start",
            suggestion="Use range(start, end) for complex expressions",
        )
    # ... rest of parsing
```

**AST Node**:

```python
@dataclass(frozen=True, slots=True)
class Range(Expr):
    """Range literal: start..end or start...end

    Attributes:
        start: Start value (inclusive)
        end: End value (inclusive if inclusive=True)
        inclusive: True for .., False for ...
        step: Optional step value
    """
    start: Expr
    end: Expr
    inclusive: bool = True
    step: Expr | None = None
```

**Parser**:

```python
def _parse_range(self, left: Expr) -> Expr:
    """Parse a..b or a...b after seeing left operand."""
    if self._match(TokenType.RANGE_INCLUSIVE):
        inclusive = True
    elif self._match(TokenType.RANGE_EXCLUSIVE):
        inclusive = False
    else:
        return left

    right = self._parse_additive()  # Parse end value

    # Optional: parse 'by step'
    step = None
    if self._match_keyword("by"):
        step = self._parse_expression()

    return Range(
        start=left,
        end=right,
        inclusive=inclusive,
        step=step,
        lineno=left.lineno,
        col_offset=left.col_offset,
    )
```

**Compiler**:

```python
def _compile_range(self, node: Range) -> ast.expr:
    """Compile range literal to range() call."""
    start = self._compile_expr(node.start)
    end = self._compile_expr(node.end)

    if node.inclusive:
        # 1..10 → range(1, 11)
        end = ast.BinOp(left=end, op=ast.Add(), right=ast.Constant(1))

    args = [start, end]
    if node.step:
        args.append(self._compile_expr(node.step))

    return ast.Call(
        func=ast.Name(id="range", ctx=ast.Load()),
        args=args,
        keywords=[],
    )
```

### Tests

```python
class TestRangeLiterals:
    def test_inclusive_range(self, env):
        tmpl = env.from_string("{% for i in 1..5 %}{{ i }}{% end %}")
        assert tmpl.render() == "12345"

    def test_exclusive_range(self, env):
        tmpl = env.from_string("{% for i in 1...5 %}{{ i }}{% end %}")
        assert tmpl.render() == "1234"

    def test_with_variables(self, env):
        tmpl = env.from_string("{% for i in start..end %}{{ i }}{% end %}")
        assert tmpl.render(start=3, end=6) == "3456"

    def test_with_step(self, env):
        tmpl = env.from_string("{% for i in 0..10 by 2 %}{{ i }}{% end %}")
        assert tmpl.render() == "0246810"

    def test_in_expression(self, env):
        tmpl = env.from_string("{{ 1..5 | list }}")
        assert tmpl.render() == "[1, 2, 3, 4, 5]"

    def test_negative_range(self, env):
        tmpl = env.from_string("{% for i in -3..3 %}{{ i }}{% end %}")
        assert tmpl.render() == "-3-2-10123"

    def test_reverse_range(self, env):
        """Reverse ranges produce empty results (like Python range)."""
        tmpl = env.from_string("{% for i in 5..1 %}{{ i }}{% end %}")
        assert tmpl.render() == ""  # Empty - use 5..1 by -1 for reverse

    def test_negative_step(self, env):
        tmpl = env.from_string("{% for i in 10..0 by -2 %}{{ i }}{% end %}")
        assert tmpl.render() == "108642"
```

---

## Feature 7: Spaceless Block

### Problem

HTML output often has unwanted whitespace:

```jinja
{# Current output has unwanted whitespace #}
<ul>
    {% for item in items %}
    <li>{{ item }}</li>
    {% end %}
</ul>

{# Actual output:
<ul>

    <li>a</li>

    <li>b</li>

</ul>
#}
```

### Solution

Django/Twig-style spaceless block:

```jinja
{% spaceless %}
<ul>
    {% for item in items %}
    <li>{{ item }}</li>
    {% end %}
</ul>
{% end %}

{# Output: <ul><li>a</li><li>b</li></ul> #}
```

### Semantics

- Removes whitespace between HTML tags
- Preserves whitespace inside tags and text content
- Only affects direct children (not recursively)

### Implementation

**AST Node**:

```python
@dataclass(frozen=True, slots=True)
class Spaceless(Node):
    """Remove whitespace between HTML tags: {% spaceless %}...{% end %}

    Removes whitespace between > and <, preserving content whitespace.
    """
    body: Sequence[Node]
```

**Parser**:

```python
def _parse_spaceless(self) -> Spaceless:
    start = self._advance()  # consume 'spaceless'
    self._expect(TokenType.BLOCK_END)

    body = self._parse_body({"end"})
    self._consume_end()

    return Spaceless(
        lineno=start.lineno,
        col_offset=start.col_offset,
        body=body,
    )
```

**Compiler**:

The key challenge is redirecting output to a temporary buffer. The compiler tracks the current buffer name:

```python
import re

def _compile_spaceless(self, node: Spaceless) -> list[ast.stmt]:
    """Compile spaceless block with buffer context switching.

    Steps:
    1. Create temporary buffer
    2. Switch compiler's buffer context
    3. Compile body (writes to temp buffer)
    4. Restore original buffer context
    5. Apply _spaceless() and append to main buffer
    """
    tmp_buf = self._gensym("_buf_spaceless")

    # Save current buffer name and switch to temp
    old_buf = self._buf_name
    self._buf_name = tmp_buf

    # Compile body - all appends now go to tmp_buf
    body_stmts = self._compile_body(node.body)

    # Restore original buffer
    self._buf_name = old_buf

    return [
        # Create temp buffer: _buf_spaceless_0 = []
        ast.Assign(
            targets=[ast.Name(id=tmp_buf, ctx=ast.Store())],
            value=ast.List(elts=[], ctx=ast.Load()),
        ),
        # Compiled body (appends to tmp_buf)
        *body_stmts,
        # Apply spaceless and append to main buffer:
        # buf.append(_spaceless(''.join(_buf_spaceless_0)))
        ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=old_buf, ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
                args=[
                    ast.Call(
                        func=ast.Name(id="_spaceless", ctx=ast.Load()),
                        args=[
                            ast.Call(
                                func=ast.Attribute(
                                    value=ast.Constant(value=""),
                                    attr="join",
                                    ctx=ast.Load(),
                                ),
                                args=[ast.Name(id=tmp_buf, ctx=ast.Load())],
                                keywords=[],
                            )
                        ],
                        keywords=[],
                    )
                ],
                keywords=[],
            )
        ),
    ]
```

**Runtime Helper**:

```python
_SPACELESS_RE = re.compile(r'>\s+<')

def _spaceless(html: str) -> str:
    """Remove whitespace between HTML tags."""
    return _SPACELESS_RE.sub('><', html).strip()
```

### Tests

```python
class TestSpaceless:
    def test_removes_whitespace(self, env):
        tmpl = env.from_string("""
            {% spaceless %}
            <div>
                <p>Hello</p>
            </div>
            {% end %}
        """)
        assert tmpl.render().strip() == "<div><p>Hello</p></div>"

    def test_preserves_content_whitespace(self, env):
        tmpl = env.from_string("""
            {% spaceless %}
            <p>Hello   World</p>
            {% end %}
        """)
        assert "Hello   World" in tmpl.render()

    def test_with_loop(self, env):
        tmpl = env.from_string("""
            {% spaceless %}
            <ul>
                {% for i in items %}
                <li>{{ i }}</li>
                {% end %}
            </ul>
            {% end %}
        """)
        result = tmpl.render(items=["a", "b"])
        assert result.strip() == "<ul><li>a</li><li>b</li></ul>"
```

---

## Feature 8: Embed Block

### Problem

Including a partial and overriding parts requires complex workarounds:

```jinja
{# Current: can't override included template's blocks #}
{% include 'card.html' %}  {# No way to customize title/body #}

{# Workaround: pass everything as variables #}
{% include 'card.html' with title='Custom', body='<p>Content</p>' %}
```

### Solution

Twig-style embed (include + block override):

```jinja
{# card.html #}
<div class="card">
    <h3>{% block title %}Default Title{% end %}</h3>
    <div class="body">{% block body %}Default body{% end %}</div>
</div>

{# Usage: embed and override blocks #}
{% embed 'card.html' %}
    {% block title %}My Custom Title{% end %}
    {% block body %}
        <p>My custom content goes here!</p>
    {% end %}
{% end %}

{# Output:
<div class="card">
    <h3>My Custom Title</h3>
    <div class="body">
        <p>My custom content goes here!</p>
    </div>
</div>
#}
```

### Semantics

- `embed` is like `include` but allows block overrides
- Block overrides only affect the embedded template (scoped, not global)
- Can pass variables like `include`
- Can embed the same template multiple times with different overrides
- Nested embeds are supported (embed within embed)
- Circular embed detection: runtime error if A embeds B embeds A

### Edge Cases

```jinja
{# Embed within embed #}
{% embed 'outer.html' %}
    {% block content %}
        {% embed 'inner.html' %}
            {% block title %}Nested{% end %}
        {% end %}
    {% end %}
{% end %}

{# Embed same template twice with different overrides #}
{% embed 'card.html' %}{% block title %}Card A{% end %}{% end %}
{% embed 'card.html' %}{% block title %}Card B{% end %}{% end %}

{# Embed doesn't affect outer template's blocks #}
{% block sidebar %}Original{% end %}
{% embed 'partial.html' %}
    {% block sidebar %}Override{% end %}  {# Only affects partial.html #}
{% end %}
{# sidebar block in current template still shows "Original" #}
```

### Implementation

**AST Node**:

```python
@dataclass(frozen=True, slots=True)
class Embed(Node):
    """Embed template with block overrides: {% embed 'card.html' %}...{% end %}

    Like include, but allows overriding blocks in the embedded template.

    Attributes:
        template: Template path expression
        blocks: Block overrides defined in embed body
        with_context: Pass current context to embedded template
    """
    template: Expr
    blocks: dict[str, Block]
    with_context: bool = True
```

**Parser**:

```python
def _parse_embed(self) -> Embed:
    start = self._advance()  # consume 'embed'

    template = self._parse_expression()

    # Check for 'with context' or 'without context'
    with_context = True
    if self._match_keyword("without"):
        self._expect_keyword("context")
        with_context = False
    elif self._match_keyword("with"):
        self._expect_keyword("context")
        with_context = True

    self._expect(TokenType.BLOCK_END)

    # Parse block overrides
    blocks = {}
    while not self._at_end_keyword({"end"}):
        if self._current.value == "block":
            block = self._parse_block()
            blocks[block.name] = block
        else:
            # Skip whitespace/text between blocks
            self._advance()

    self._consume_end()

    return Embed(
        lineno=start.lineno,
        col_offset=start.col_offset,
        template=template,
        blocks=blocks,
        with_context=with_context,
    )
```

**Compiler**:

```python
def _compile_embed(self, node: Embed) -> list[ast.stmt]:
    """Compile embed as include with temporary block overrides."""
    stmts = []

    # Save current blocks
    stmts.append(
        ast.Assign(
            targets=[ast.Name(id="_saved_blocks", ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="_blocks", ctx=ast.Load()),
                    attr="copy",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            ),
        )
    )

    # Add override blocks
    for name, block in node.blocks.items():
        block_func = self._make_block_function(name, block)
        stmts.append(block_func)
        stmts.append(
            ast.Assign(
                targets=[
                    ast.Subscript(
                        value=ast.Name(id="_blocks", ctx=ast.Load()),
                        slice=ast.Constant(value=name),
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Name(id=f"_block_{name}", ctx=ast.Load()),
            )
        )

    # Include template
    stmts.extend(self._compile_include(
        Include(template=node.template, with_context=node.with_context, ...)
    ))

    # Restore blocks
    stmts.append(
        ast.Assign(
            targets=[ast.Name(id="_blocks", ctx=ast.Store())],
            value=ast.Name(id="_saved_blocks", ctx=ast.Load()),
        )
    )

    return stmts
```

### Tests

```python
class TestEmbed:
    @pytest.fixture
    def env_with_card(self):
        env = Environment(loader=DictLoader({
            "card.html": """
                <div class="card">
                    <h3>{% block title %}Default{% end %}</h3>
                    <div>{% block body %}Empty{% end %}</div>
                </div>
            """,
        }))
        return env

    def test_basic_embed(self, env_with_card):
        tmpl = env_with_card.from_string("""
            {% embed 'card.html' %}
                {% block title %}Custom Title{% end %}
            {% end %}
        """)
        result = tmpl.render()
        assert "Custom Title" in result
        assert "Empty" in result  # Body uses default

    def test_multiple_block_overrides(self, env_with_card):
        tmpl = env_with_card.from_string("""
            {% embed 'card.html' %}
                {% block title %}My Title{% end %}
                {% block body %}My Content{% end %}
            {% end %}
        """)
        result = tmpl.render()
        assert "My Title" in result
        assert "My Content" in result

    def test_multiple_embeds(self, env_with_card):
        tmpl = env_with_card.from_string("""
            {% embed 'card.html' %}
                {% block title %}Card 1{% end %}
            {% end %}
            {% embed 'card.html' %}
                {% block title %}Card 2{% end %}
            {% end %}
        """)
        result = tmpl.render()
        assert "Card 1" in result
        assert "Card 2" in result

    def test_with_variables(self, env_with_card):
        env_with_card.loader.mapping["card.html"] = """
            <div class="card">
                <h3>{% block title %}{{ default_title }}{% end %}</h3>
            </div>
        """
        tmpl = env_with_card.from_string("""
            {% embed 'card.html' %}
                {% block title %}{{ custom_title }}{% end %}
            {% end %}
        """)
        result = tmpl.render(custom_title="From Variable")
        assert "From Variable" in result

    def test_embed_doesnt_affect_outer_blocks(self, env_with_card):
        """Embed block overrides are scoped, not global."""
        env_with_card.loader.mapping["partial.html"] = """
            {% block sidebar %}Partial Sidebar{% end %}
        """
        tmpl = env_with_card.from_string("""
            {% block sidebar %}Main Sidebar{% end %}
            {% embed 'partial.html' %}
                {% block sidebar %}Overridden{% end %}
            {% end %}
            {% block sidebar %}Still Main{% end %}
        """)
        result = tmpl.render()
        assert "Main Sidebar" in result
        assert "Overridden" in result
        assert "Still Main" in result

    def test_nested_embed(self, env_with_card):
        """Embed within embed works correctly."""
        env_with_card.loader.mapping["outer.html"] = """
            <div class="outer">{% block content %}Default{% end %}</div>
        """
        env_with_card.loader.mapping["inner.html"] = """
            <span class="inner">{% block label %}Label{% end %}</span>
        """
        tmpl = env_with_card.from_string("""
            {% embed 'outer.html' %}
                {% block content %}
                    {% embed 'inner.html' %}
                        {% block label %}Nested Label{% end %}
                    {% end %}
                {% end %}
            {% end %}
        """)
        result = tmpl.render()
        assert "Nested Label" in result
        assert "outer" in result
        assert "inner" in result
```

---

## Implementation Order

Ordered by risk/dependencies, starting with lowest risk:

### Phase 1: Quick Wins (~6 hours)

1. **Inline If in For** (2h) - Lowest risk; AST already exists, parser-only change
2. **Unless** (2h) - Simple desugaring to `If(not condition)`
3. **Null Coalescing `??`** (2h lexer/parser) - High value, no dependencies

### Phase 2: Core Features (~9 hours)

4. **Break/Continue** (5h) - Needs loop context tracking in `BlockStackMixin`
5. **Optional Chaining `?.`** (4h) - Can reuse patterns from `??`

### Phase 3: Syntax Sugar (~9 hours)

6. **Range Literals** (5h) - Lexer disambiguation + parser validation
7. **Spaceless Block** (4h) - Buffer context switching pattern

### Phase 4: Advanced (~8 hours)

8. **Embed Block** (8h) - Most complex; block resolution + include integration

### Dependency Graph

```
                    ┌─────────────┐
                    │ Inline If   │  (no deps)
                    └─────────────┘
                    ┌─────────────┐
                    │   Unless    │  (no deps)
                    └─────────────┘
┌─────────────┐     ┌─────────────┐
│    ??       │────▶│     ?.      │  (reuse patterns)
└─────────────┘     └─────────────┘
┌─────────────┐
│ Break/Cont  │  (needs BlockStackMixin)
└─────────────┘
┌─────────────┐
│   Range     │  (needs lexer 3-char support)
└─────────────┘
┌─────────────┐     ┌─────────────┐
│  Spaceless  │────▶│    Embed    │  (similar buffer patterns)
└─────────────┘     └─────────────┘
```

---

## Pre-Implementation Checklist

Before starting implementation, complete these infrastructure changes:

### 1. Update `_types.py` Keywords

Add new keywords to `KEYWORDS` frozenset:

```python
KEYWORDS = frozenset({
    # ... existing keywords ...

    # New keywords (this RFC)
    "unless",
    "break",
    "continue",
    "spaceless",
    "embed",
    "by",  # For range step syntax
})
```

### 2. Update `_types.py` TokenType

Add new token types:

```python
class TokenType(Enum):
    # ... existing tokens ...

    # Optional chaining (Feature 1)
    OPTIONAL_DOT = "optional_dot"     # ?.
    OPTIONAL_BRACKET = "optional_bracket"  # ?[

    # Null coalescing (Feature 2)
    NULLISH_COALESCE = "nullish_coalesce"  # ??

    # Range literals (Feature 6)
    RANGE_INCLUSIVE = "range_inclusive"  # ..
    RANGE_EXCLUSIVE = "range_exclusive"  # ...
```

### 3. Update `_types.py` Precedence

Add precedence for new operators:

```python
PRECEDENCE = {
    TokenType.NULLISH_COALESCE: 0,  # Lowest - below OR
    TokenType.OR: 1,
    # ... rest unchanged ...
}
```

### 4. Update `lexer.py` Operator Lookup

Add 3-char operator support (check longest first):

```python
_OPERATORS_3CHAR: dict[str, TokenType] = {
    "...": TokenType.RANGE_EXCLUSIVE,
}
_OPERATORS_2CHAR: dict[str, TokenType] = {
    "?.": TokenType.OPTIONAL_DOT,
    "??": TokenType.NULLISH_COALESCE,
    "..": TokenType.RANGE_INCLUSIVE,
    # ... existing operators ...
}
```

### 5. Add AST Nodes to `nodes.py`

```python
# Optional chaining
@dataclass(frozen=True, slots=True)
class OptionalGetattr(Expr): ...

@dataclass(frozen=True, slots=True)
class OptionalGetitem(Expr): ...

# Null coalescing
@dataclass(frozen=True, slots=True)
class NullCoalesce(Expr): ...

# Loop control
@dataclass(frozen=True, slots=True)
class Break(Node): ...

@dataclass(frozen=True, slots=True)
class Continue(Node): ...

# Range
@dataclass(frozen=True, slots=True)
class Range(Expr): ...

# Spaceless
@dataclass(frozen=True, slots=True)
class Spaceless(Node): ...

# Embed
@dataclass(frozen=True, slots=True)
class Embed(Node): ...
```

### 6. Extend BlockStackMixin

Add loop detection for break/continue validation:

```python
# In parser/blocks/core.py
LOOP_BLOCKS = frozenset({"for", "while"})

def _in_loop(self) -> bool:
    return any(bt in self.LOOP_BLOCKS for bt, _ in self._block_stack)
```

---

## Migration & Compatibility

All features are **additive**:
- No breaking changes to existing templates
- New syntax is opt-in
- Existing code continues to work unchanged

---

## Success Criteria

| Feature | Metric |
|---------|--------|
| All features | 100% test coverage |
| All features | No new linter warnings |
| Optional chaining | Chain depth ≤ 10 without stack overflow |
| Optional chaining | Works with method calls and subscripts |
| Null coalescing | Preserves all falsy values (0, '', False, []) |
| Null coalescing | Catches `UndefinedError` in strict mode |
| Null coalescing | Right-associative chaining works |
| Break/Continue | Works in nested loops (exits innermost only) |
| Break/Continue | Error at parse time if outside loop |
| Inline If For | Empty clause triggers when all items filtered |
| Range literals | Works with negative values and steps |
| Range literals | Lexer correctly distinguishes `..` vs `...` |
| Spaceless | Preserves content whitespace (inside tags) |
| Spaceless | Works with nested loops and conditionals |
| Embed | Works with nested embeds |
| Embed | Block overrides don't affect outer template |

---

## Open Questions

### 1. `??` and Method Calls

Should `??` work with method calls that might raise exceptions?

```jinja
{{ obj.risky_method() ?? 'fallback' }}
```

**Options**:
- A) Only catch `UndefinedError` and `None` (proposed)
- B) Catch all exceptions (too broad, hides bugs)
- C) Catch `UndefinedError`, `None`, and `AttributeError` (compromise)

**Recommendation**: Option A - keep it simple, only handle null/undefined.

### 2. `?.` with `?[]`

The syntax `?[` for optional subscript requires lexer look-ahead or a separate token:

```jinja
{{ items?[0] }}   {# Optional subscript #}
{{ items ? [0] }} {# Ternary with list literal? #}
```

**Options**:
- A) `?[` as single token `OPTIONAL_BRACKET` (proposed)
- B) Require whitespace for ternary: `items ? [0]` is ternary, `items?[0]` is optional
- C) Don't support optional subscript initially

**Recommendation**: Option A - `?[` is unambiguous.

### 3. Range with Expressions

Should range support complex expressions on either side?

```jinja
{{ (start + 1)..(end - 1) }}  {# Complex expressions #}
{{ 1..items|length }}          {# Filter on end #}
```

**Current proposal**: Allow, but parser validates at parse time.

### 4. Spaceless and Inline Content

How should spaceless handle inline content mixed with tags?

```jinja
{% spaceless %}
Text before<span>content</span>Text after
{% end %}
```

**Current behavior**: Only removes whitespace between `>` and `<`, not around text.

---

## References

- [JavaScript Optional Chaining](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Optional_chaining)
- [JavaScript Nullish Coalescing](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Nullish_coalescing)
- [Ruby Range Literals](https://ruby-doc.org/core/Range.html)
- [Liquid Unless](https://shopify.github.io/liquid/tags/control-flow/#unless)
- [Twig Spaceless](https://twig.symfony.com/doc/3.x/tags/spaceless.html)
- [Twig Embed](https://twig.symfony.com/doc/3.x/tags/embed.html)
