# RFC: Kida Modern Syntax Features

**Status**: Draft  
**Created**: 2025-12-26  
**Priority**: Medium-High  
**Effort**: ~3-4 days total  
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
| Null Coalescing | `value ?? 'default'` | 2h | ⭐⭐⭐ |
| Break/Continue | `{% break %}`, `{% continue %}` | 4h | ⭐⭐⭐ |
| Inline If in For | `{% for x in items if x.visible %}` | 4h | ⭐⭐⭐ |
| Unless Block | `{% unless condition %}` | 2h | ⭐⭐ |
| Range Literals | `1..10`, `1...11` | 3h | ⭐⭐ |
| Spaceless Block | `{% spaceless %}...{% end %}` | 3h | ⭐⭐ |
| Embed Block | `{% embed 'card.html' %}...{% end %}` | 8h | ⭐⭐ |

**Total Effort**: ~30 hours (~3-4 days)

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
    """Compile obj?.attr to: (obj.attr if obj is not None else None)"""
    obj = self._compile_expr(node.obj)

    # Generate: (_tmp := obj) and _tmp.attr
    # Or: obj.attr if obj is not None else None
    return ast.IfExp(
        test=ast.Compare(
            left=obj,
            ops=[ast.IsNot()],
            comparators=[ast.Constant(value=None)],
        ),
        body=ast.Attribute(
            value=obj,  # Note: need to cache obj to avoid double evaluation
            attr=node.attr,
            ctx=ast.Load(),
        ),
        orelse=ast.Constant(value=None),
    )
```

**Optimization**: For chained `?.` expressions, use walrus operator to cache intermediate values:

```python
# user?.profile?.name compiles to:
# (_t1 := user) is not None and (_t2 := _t1.profile) is not None and _t2.name
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
# Precedence: ?? < or < and < not < comparisons < ...
def _parse_nullish_coalesce(self) -> Expr:
    left = self._parse_or()
    while self._match(TokenType.NULLISH_COALESCE):
        right = self._parse_or()
        left = NullCoalesce(left=left, right=right, ...)
    return left
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

**Validation**: Add compile-time check that break/continue are inside loops:

```python
def _validate_loop_control(self, node: Break | Continue) -> None:
    """Ensure break/continue are inside a loop."""
    if not self._in_loop:
        raise TemplateSyntaxError(
            f"'{type(node).__name__.lower()}' outside loop",
            lineno=node.lineno,
        )
```

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

**Lexer**: Add range tokens

```python
TokenType.RANGE_INCLUSIVE: r'\.\.',   # ..
TokenType.RANGE_EXCLUSIVE: r'\.\.\.',  # ...
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

```python
import re

def _compile_spaceless(self, node: Spaceless) -> list[ast.stmt]:
    """Compile spaceless block.

    Wraps body output in _spaceless() helper that removes
    whitespace between HTML tags.
    """
    # Compile body to a capture
    body_stmts = self._compile_body(node.body)

    # Wrap in spaceless helper
    # _spaceless(''.join(buf))
    return [
        # _buf_spaceless = []
        ast.Assign(
            targets=[ast.Name(id="_buf_spaceless", ctx=ast.Store())],
            value=ast.List(elts=[], ctx=ast.Load()),
        ),
        # ... compile body to _buf_spaceless ...
        *body_stmts,
        # buf.append(_spaceless(''.join(_buf_spaceless)))
        ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="buf", ctx=ast.Load()),
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
                                args=[ast.Name(id="_buf_spaceless", ctx=ast.Load())],
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
- Block overrides only affect the embedded template
- Can pass variables like `include`
- Can embed the same template multiple times with different overrides

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
```

---

## Implementation Order

### Phase 1: Quick Wins (~8 hours)

1. **Break/Continue** (4h) - Universal expectation
2. **Unless** (2h) - Simple parser alias
3. **Inline if in for** (2h) - AST already exists

### Phase 2: Modern Operators (~8 hours)

4. **Null Coalescing `??`** (3h) - High impact, simple
5. **Optional Chaining `?.`** (5h) - Requires more compiler work

### Phase 3: Syntax Sugar (~8 hours)

6. **Range Literals** (4h) - Nice syntax improvement
7. **Spaceless Block** (4h) - HTML optimization

### Phase 4: Advanced (~8 hours)

8. **Embed Block** (8h) - Powerful but complex

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
| Optional chaining | Chain depth ≤ 10 without stack overflow |
| Null coalescing | Preserves all falsy values |
| Break/Continue | Works in nested loops |
| Range literals | Works with negative values |
| Spaceless | Preserves content whitespace |
| Embed | Works with nested embeds |

---

## References

- [JavaScript Optional Chaining](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Optional_chaining)
- [JavaScript Nullish Coalescing](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Nullish_coalescing)
- [Ruby Range Literals](https://ruby-doc.org/core/Range.html)
- [Liquid Unless](https://shopify.github.io/liquid/tags/control-flow/#unless)
- [Twig Spaceless](https://twig.symfony.com/doc/3.x/tags/spaceless.html)
- [Twig Embed](https://twig.symfony.com/doc/3.x/tags/embed.html)
