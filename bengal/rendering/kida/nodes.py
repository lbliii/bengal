"""Kida AST node definitions.

All nodes are immutable dataclasses with __slots__ for memory efficiency.
This design enables:
- Thread-safe AST traversal
- Pattern matching with match/case
- Easy serialization and debugging

Node Categories:
    - Template: Root node and structural elements
    - Statements: Control flow, assignments, blocks
    - Expressions: Values, operations, filters
    - Helpers: Loop context, macro calls
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Union

# =============================================================================
# Base Node
# =============================================================================


@dataclass(frozen=True, slots=True)
class Node:
    """Base class for all AST nodes.

    All nodes track their source location for error reporting.
    Nodes are immutable for thread-safety.
    """

    lineno: int
    col_offset: int


# =============================================================================
# Template Structure
# =============================================================================


@dataclass(frozen=True, slots=True)
class Template(Node):
    """Root node representing a complete template.

    Attributes:
        body: Sequence of top-level nodes
        extends: Optional parent template path
    """

    body: Sequence[Node]
    extends: Extends | None = None


@dataclass(frozen=True, slots=True)
class Extends(Node):
    """Template inheritance: {% extends "base.html" %}"""

    template: Expr


@dataclass(frozen=True, slots=True)
class Block(Node):
    """Named block for inheritance: {% block name %}...{% endblock %}

    Attributes:
        name: Block identifier
        body: Block content
        scoped: If True, block has its own variable scope
        required: If True, child templates must override this block
    """

    name: str
    body: Sequence[Node]
    scoped: bool = False
    required: bool = False


@dataclass(frozen=True, slots=True)
class Include(Node):
    """Include another template: {% include "partial.html" %}

    Attributes:
        template: Template path expression
        with_context: If True, pass current context to included template
        ignore_missing: If True, silently skip if template doesn't exist
    """

    template: Expr
    with_context: bool = True
    ignore_missing: bool = False


@dataclass(frozen=True, slots=True)
class Import(Node):
    """Import macros from template: {% import "macros.html" as m %}"""

    template: Expr
    target: str
    with_context: bool = False


@dataclass(frozen=True, slots=True)
class FromImport(Node):
    """Import specific macros: {% from "macros.html" import button, card %}"""

    template: Expr
    names: Sequence[tuple[str, str | None]]  # (name, alias)
    with_context: bool = False


# =============================================================================
# Statements
# =============================================================================


@dataclass(frozen=True, slots=True)
class Output(Node):
    """Output expression: {{ expr }}

    Attributes:
        expr: Expression to output
        escape: If True, HTML-escape the result
    """

    expr: Expr
    escape: bool = True


@dataclass(frozen=True, slots=True)
class Data(Node):
    """Raw text data between template constructs."""

    value: str


@dataclass(frozen=True, slots=True)
class If(Node):
    """Conditional: {% if cond %}...{% elif cond %}...{% else %}...{% endif %}

    Attributes:
        test: Condition expression
        body: Nodes to render if condition is true
        elif_: Sequence of (condition, body) pairs
        else_: Nodes to render if all conditions are false
    """

    test: Expr
    body: Sequence[Node]
    elif_: Sequence[tuple[Expr, Sequence[Node]]] = ()
    else_: Sequence[Node] = ()


@dataclass(frozen=True, slots=True)
class For(Node):
    """For loop: {% for x in items %}...{% else %}...{% endfor %}

    Attributes:
        target: Loop variable(s) - can be tuple for unpacking
        iter: Iterable expression
        body: Loop body
        else_: Rendered if iterable is empty
        recursive: Enable recursive loop calls
        test: Optional filter condition (like Python's if in comprehensions)
    """

    target: Expr
    iter: Expr
    body: Sequence[Node]
    else_: Sequence[Node] = ()
    recursive: bool = False
    test: Expr | None = None


@dataclass(frozen=True, slots=True)
class AsyncFor(Node):
    """Async for loop: {% async for x in async_items %}...{% endfor %}

    Native async iteration without wrapper adapters.
    """

    target: Expr
    iter: Expr
    body: Sequence[Node]
    else_: Sequence[Node] = ()


@dataclass(frozen=True, slots=True)
class While(Node):
    """While loop: {% while cond %}...{% endwhile %}

    Kida addition - not in Jinja2.
    """

    test: Expr
    body: Sequence[Node]


# =============================================================================
# Variable Statements (Kida's improved scoping)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Let(Node):
    """Template-scoped variable: {% let x = expr %}

    Variables declared with 'let' persist across the template
    and can be modified within inner scopes.

    This replaces Jinja2's confusing namespace() workaround.
    """

    name: str
    value: Expr


@dataclass(frozen=True, slots=True)
class Set(Node):
    """Block-scoped variable: {% set x = expr %}

    Traditional Jinja2 behavior - variable is scoped to current block.
    Use 'let' if you need the variable to persist.
    """

    name: str
    value: Expr


@dataclass(frozen=True, slots=True)
class Export(Node):
    """Export variable from inner scope: {% export x = expr %}

    Explicitly exports a variable from an inner scope (like a for loop)
    to the enclosing scope. Makes scope behavior explicit and predictable.

    Example:
        {% for item in items %}
            {% export last = item %}
        {% endfor %}
        {{ last }}  {# Works! #}
    """

    name: str
    value: Expr


@dataclass(frozen=True, slots=True)
class SetBlock(Node):
    """Capture block content: {% set x %}...{% endset %}"""

    name: str
    body: Sequence[Node]
    filter: Filter | None = None


# =============================================================================
# Macros
# =============================================================================


@dataclass(frozen=True, slots=True)
class Macro(Node):
    """Macro definition: {% macro name(args) %}...{% endmacro %}

    Attributes:
        name: Macro identifier
        args: Argument definitions
        body: Macro body
        defaults: Default argument values
    """

    name: str
    args: Sequence[str]
    body: Sequence[Node]
    defaults: Sequence[Expr] = ()


@dataclass(frozen=True, slots=True)
class Call(Node):
    """Macro call with body: {% call name(args) %}body{% endcall %}"""

    call: Expr
    body: Sequence[Node]
    args: Sequence[Expr] = ()


# =============================================================================
# Misc Statements
# =============================================================================


@dataclass(frozen=True, slots=True)
class With(Node):
    """Context manager: {% with x = expr %}...{% endwith %}"""

    targets: Sequence[tuple[str, Expr]]
    body: Sequence[Node]


@dataclass(frozen=True, slots=True)
class FilterBlock(Node):
    """Apply filter to block: {% filter upper %}...{% endfilter %}"""

    filter: Filter
    body: Sequence[Node]


@dataclass(frozen=True, slots=True)
class Autoescape(Node):
    """Control autoescaping: {% autoescape true %}...{% endautoescape %}"""

    enabled: bool
    body: Sequence[Node]


@dataclass(frozen=True, slots=True)
class Do(Node):
    """Expression statement: {% do expr %}

    Evaluate expression for side effects, discard result.
    """

    expr: Expr


@dataclass(frozen=True, slots=True)
class Raw(Node):
    """Raw block (no template processing): {% raw %}...{% endraw %}"""

    value: str


# =============================================================================
# Expressions
# =============================================================================


@dataclass(frozen=True, slots=True)
class Expr(Node):
    """Base class for expressions."""

    pass


@dataclass(frozen=True, slots=True)
class Const(Expr):
    """Constant value: string, number, boolean, None."""

    value: str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class Name(Expr):
    """Variable reference: {{ user }}"""

    name: str
    ctx: Literal["load", "store", "del"] = "load"


@dataclass(frozen=True, slots=True)
class Tuple(Expr):
    """Tuple expression: (a, b, c)"""

    items: Sequence[Expr]
    ctx: Literal["load", "store"] = "load"


@dataclass(frozen=True, slots=True)
class List(Expr):
    """List expression: [a, b, c]"""

    items: Sequence[Expr]


@dataclass(frozen=True, slots=True)
class Dict(Expr):
    """Dict expression: {a: b, c: d}"""

    keys: Sequence[Expr]
    values: Sequence[Expr]


@dataclass(frozen=True, slots=True)
class Getattr(Expr):
    """Attribute access: obj.attr"""

    obj: Expr
    attr: str


@dataclass(frozen=True, slots=True)
class Getitem(Expr):
    """Subscript access: obj[key]"""

    obj: Expr
    key: Expr


@dataclass(frozen=True, slots=True)
class Slice(Expr):
    """Slice expression: [start:stop:step]"""

    start: Expr | None
    stop: Expr | None
    step: Expr | None


@dataclass(frozen=True, slots=True)
class Call(Expr):
    """Function call: func(args, **kwargs)"""

    func: Expr
    args: Sequence[Expr] = ()
    kwargs: dict[str, Expr] = field(default_factory=dict)
    dyn_args: Expr | None = None  # *args
    dyn_kwargs: Expr | None = None  # **kwargs


@dataclass(frozen=True, slots=True)
class Filter(Expr):
    """Filter application: expr | filter(args)"""

    value: Expr
    name: str
    args: Sequence[Expr] = ()
    kwargs: dict[str, Expr] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Test(Expr):
    """Test application: expr is test(args) or expr is not test(args)"""

    value: Expr
    name: str
    args: Sequence[Expr] = ()
    kwargs: dict[str, Expr] = field(default_factory=dict)
    negated: bool = False  # True for "is not"


# =============================================================================
# Operators
# =============================================================================


@dataclass(frozen=True, slots=True)
class BinOp(Expr):
    """Binary operation: left op right"""

    op: str  # '+', '-', '*', '/', '//', '%', '**', '~'
    left: Expr
    right: Expr


@dataclass(frozen=True, slots=True)
class UnaryOp(Expr):
    """Unary operation: op operand"""

    op: str  # '-', '+', 'not'
    operand: Expr


@dataclass(frozen=True, slots=True)
class Compare(Expr):
    """Comparison: left op1 right1 op2 right2 ...

    Supports chained comparisons like: 1 < x < 10
    """

    left: Expr
    ops: Sequence[str]  # '<', '<=', '>', '>=', '==', '!=', 'in', 'not in', 'is', 'is not'
    comparators: Sequence[Expr]


@dataclass(frozen=True, slots=True)
class BoolOp(Expr):
    """Boolean operation: expr1 and/or expr2"""

    op: Literal["and", "or"]
    values: Sequence[Expr]


@dataclass(frozen=True, slots=True)
class CondExpr(Expr):
    """Conditional expression: a if cond else b"""

    test: Expr
    if_true: Expr
    if_false: Expr


# =============================================================================
# Async Expressions (Kida native)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Await(Expr):
    """Await expression: await expr

    Native async support without auto_await() wrappers.
    """

    value: Expr


# =============================================================================
# Special
# =============================================================================


@dataclass(frozen=True, slots=True)
class Concat(Expr):
    """String concatenation: a ~ b ~ c

    Multiple ~ operators are collapsed into a single Concat node
    for efficient string building.
    """

    nodes: Sequence[Expr]


@dataclass(frozen=True, slots=True)
class MarkSafe(Expr):
    """Mark expression as safe (no escaping): {{ expr | safe }}"""

    value: Expr


@dataclass(frozen=True, slots=True)
class EnvironmentAttribute(Expr):
    """Access to environment: {{ loop.index }}"""

    name: str


@dataclass(frozen=True, slots=True)
class ExtensionAttribute(Expr):
    """Access to extension-defined value."""

    name: str
    identifier: str


# Type alias for any expression
AnyExpr = Union[
    Const,
    Name,
    Tuple,
    List,
    Dict,
    Getattr,
    Getitem,
    Slice,
    Call,
    Filter,
    Test,
    BinOp,
    UnaryOp,
    Compare,
    BoolOp,
    CondExpr,
    Await,
    Concat,
    MarkSafe,
    EnvironmentAttribute,
    ExtensionAttribute,
]
