"""Kida AST node definitions.

Immutable, frozen dataclass nodes representing the Kida template AST.
All nodes track source location (lineno, col_offset) for error reporting.

Kida-Native Features:
    - **Unified endings**: `{% end %}` closes any block (like Go templates)
    - **Functions**: `{% def %}` with true lexical scoping (not Jinja macros)
    - **Pipeline**: `|>` for readable filter chains
    - **Pattern matching**: `{% match %}...{% case %}...{% end %}`
    - **Caching**: `{% cache key %}...{% end %}` with TTL support
    - **Explicit scoping**: `{% let %}` (template), `{% set %}` (block), `{% export %}`

Node Categories:
    **Template Structure**:
        - `Template`: Root node containing body
        - `Extends`, `Block`, `Include`: Inheritance and composition
        - `Import`, `FromImport`: Macro/function imports

    **Control Flow**:
        - `If`, `For`, `While`: Standard control flow
        - `AsyncFor`: Native async iteration
        - `Match`: Pattern matching

    **Variables**:
        - `Set`: Block-scoped assignment
        - `Let`: Template-scoped assignment
        - `Export`: Export from inner scope to enclosing scope
        - `Capture`: Capture block output to variable

    **Functions**:
        - `Def`/`Macro`: Function definition
        - `CallBlock`: Call function with body content
        - `Slot`: Content placeholder in components

    **Expressions**:
        - `Const`, `Name`: Literals and identifiers
        - `Getattr`, `Getitem`: Attribute and subscript access
        - `FuncCall`, `Filter`, `Pipeline`: Function calls and filters
        - `BinOp`, `UnaryOp`, `Compare`, `BoolOp`: Operators
        - `CondExpr`: Ternary conditional
        - `Test`: `is` test expressions

    **Output**:
        - `Output`: Expression output `{{ expr }}`
        - `Data`: Raw text between template constructs

Thread-Safety:
    All nodes are frozen dataclasses, making the AST immutable and safe
    for concurrent access. The Parser produces a new AST on each call.

Jinja Compatibility:
    For existing Jinja2 templates, use `kida.compat.jinja.JinjaParser` which
    produces Kida AST from Jinja2 syntax (translates `{% endif %}` → `{% end %}`, etc.).
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
        context_type: Optional type declaration from {% template %}
    """

    body: Sequence[Node]
    extends: Extends | None = None
    context_type: TemplateContext | None = None


@dataclass(frozen=True, slots=True)
class TemplateContext(Node):
    """Type declaration: {% template page: Page, site: Site %}

    Kida-native feature for type-aware validation.
    """

    declarations: Sequence[tuple[str, str]]  # (name, type_name)


@dataclass(frozen=True, slots=True)
class Extends(Node):
    """Template inheritance: {% extends "base.html" %}"""

    template: Expr


@dataclass(frozen=True, slots=True)
class Block(Node):
    """Named block for inheritance: {% block name %}...{% end %}

    Kida uses unified {% end %} for all block closings.

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
    """Import functions from template: {% import "funcs.html" as f %}"""

    template: Expr
    target: str
    with_context: bool = False


@dataclass(frozen=True, slots=True)
class FromImport(Node):
    """Import specific functions: {% from "funcs.html" import button, card %}"""

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
    """Conditional: {% if cond %}...{% elif cond %}...{% else %}...{% end %}

    Kida uses unified {% end %} instead of {% endif %}.

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
    """For loop: {% for x in items %}...{% empty %}...{% end %}

    Kida uses {% empty %} (not {% else %}) and {% end %} (not {% endfor %}).

    Attributes:
        target: Loop variable(s) - can be tuple for unpacking
        iter: Iterable expression
        body: Loop body
        empty: Rendered if iterable is empty (Kida uses 'empty' not 'else')
        recursive: Enable recursive loop calls
        test: Optional filter condition (like Python's if in comprehensions)
    """

    target: Expr
    iter: Expr
    body: Sequence[Node]
    empty: Sequence[Node] = ()  # Kida: 'empty' not 'else_'
    recursive: bool = False
    test: Expr | None = None


@dataclass(frozen=True, slots=True)
class AsyncFor(Node):
    """Async for loop: {% async for x in async_items %}...{% end %}

    Native async iteration without wrapper adapters.
    """

    target: Expr
    iter: Expr
    body: Sequence[Node]
    empty: Sequence[Node] = ()


@dataclass(frozen=True, slots=True)
class While(Node):
    """While loop: {% while cond %}...{% end %}

    Kida-native feature.
    """

    test: Expr
    body: Sequence[Node]


@dataclass(frozen=True, slots=True)
class Match(Node):
    """Pattern matching: {% match expr %}{% case pattern %}...{% end %}

    Kida-native feature for cleaner branching than if/elif chains.

    Example:
        {% match page.type %}
            {% case "post" %}<i class="icon-pen"></i>
            {% case "gallery" %}<i class="icon-image"></i>
            {% case _ %}<i class="icon-file"></i>
        {% end %}
    """

    subject: Expr
    cases: Sequence[tuple[Expr, Sequence[Node]]]  # (pattern, body)


# =============================================================================
# Variable Statements (Kida's explicit scoping)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Let(Node):
    """Template-scoped variable: {% let x = expr %}

    Variables declared with 'let' persist across the template
    and can be modified within inner scopes.

    Kida-native replacement for Jinja's confusing namespace() workaround.
    """

    name: str
    value: Expr


@dataclass(frozen=True, slots=True)
class Set(Node):
    """Block-scoped variable: {% set x = expr %} or {% set a, b = 1, 2 %}

    Variable is scoped to current block. Use 'let' for template-wide scope.
    Supports tuple unpacking on the left-hand side.

    Attributes:
        target: Assignment target - can be a Name or Tuple of Names
        value: Value expression to assign
    """

    target: Expr  # Name or Tuple for unpacking
    value: Expr


@dataclass(frozen=True, slots=True)
class Export(Node):
    """Export variable from inner scope: {% export x = expr %}

    Explicitly exports a variable from an inner scope (like a for loop)
    to the enclosing scope. Makes scope behavior explicit and predictable.

    Example:
        {% for item in items %}
            {% export last = item %}
        {% end %}
        {{ last }}
    """

    name: str
    value: Expr


@dataclass(frozen=True, slots=True)
class Capture(Node):
    """Capture block content: {% capture x %}...{% end %}

    Kida-native name (clearer than Jinja's {% set x %}...{% endset %}).
    """

    name: str
    body: Sequence[Node]
    filter: Filter | None = None


# =============================================================================
# Functions (Kida-native, replaces macros)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Def(Node):
    """Function definition: {% def name(args) %}...{% end %}

    Kida uses functions with true lexical scoping instead of macros.
    Functions can access variables from their enclosing scope.

    Example:
        {% def card(item) %}
            <div>{{ item.title }}</div>
            <span>From: {{ site.title }}</span>  {# Can access outer scope #}
        {% end %}

        {{ card(page) }}

    Attributes:
        name: Function name
        args: Argument names
        body: Function body
        defaults: Default argument values
    """

    name: str
    args: Sequence[str]
    body: Sequence[Node]
    defaults: Sequence[Expr] = ()


@dataclass(frozen=True, slots=True)
class Slot(Node):
    """Slot for component content: {% slot %}

    Used inside {% def %} to mark where caller content goes.

    Example:
        {% def card(title) %}
            <div class="card">
                <h3>{{ title }}</h3>
                <div class="body">{% slot %}</div>
            </div>
        {% end %}

        {% call card("My Title") %}
            <p>This goes in the slot!</p>
        {% end %}
    """

    name: str = "default"


@dataclass(frozen=True, slots=True)
class CallBlock(Node):
    """Call function with body content: {% call name(args) %}body{% end %}

    The body content fills the {% slot %} in the function.
    """

    call: Expr
    body: Sequence[Node]
    args: Sequence[Expr] = ()


# Legacy compatibility - kept for Jinja compat layer
@dataclass(frozen=True, slots=True)
class Macro(Node):
    """Macro definition (Jinja compatibility).

    Prefer {% def %} for new Kida templates.
    """

    name: str
    args: Sequence[str]
    body: Sequence[Node]
    defaults: Sequence[Expr] = ()


@dataclass(frozen=True, slots=True)
class Call(Node):
    """Macro call with body (Jinja compatibility)."""

    call: Expr
    body: Sequence[Node]
    args: Sequence[Expr] = ()


# =============================================================================
# Caching (Kida-native)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Cache(Node):
    """Fragment caching: {% cache key %}...{% end %}

    Kida-native built-in caching. No external dependencies required.

    Example:
        {% cache "sidebar-" + site.nav_version %}
            {{ build_nav_tree(site.pages) }}
        {% end %}

        {% cache "weather", ttl="5m" %}
            {{ fetch_weather() }}
        {% end %}

    Attributes:
        key: Cache key expression
        body: Content to cache
        ttl: Optional time-to-live expression
        depends: Optional dependency expressions for invalidation
    """

    key: Expr
    body: Sequence[Node]
    ttl: Expr | None = None
    depends: Sequence[Expr] = ()


# =============================================================================
# Misc Statements
# =============================================================================


@dataclass(frozen=True, slots=True)
class With(Node):
    """Context manager: {% with x = expr %}...{% end %}"""

    targets: Sequence[tuple[str, Expr]]
    body: Sequence[Node]


@dataclass(frozen=True, slots=True)
class FilterBlock(Node):
    """Apply filter to block: {% filter upper %}...{% end %}"""

    filter: Filter
    body: Sequence[Node]


@dataclass(frozen=True, slots=True)
class Autoescape(Node):
    """Control autoescaping: {% autoescape true %}...{% end %}"""

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
    """Raw block (no template processing): {% raw %}...{% end %}"""

    value: str


@dataclass(frozen=True, slots=True)
class Trim(Node):
    """Whitespace control block: {% trim %}...{% end %}

    Kida-native replacement for Jinja's {%- -%} modifiers.
    Content inside is trimmed of leading/trailing whitespace.
    """

    body: Sequence[Node]


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
class FuncCall(Expr):
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
class Pipeline(Expr):
    """Pipeline operator: expr |> filter1 |> filter2

    Kida-native syntax for readable filter chains.
    More readable than deeply nested Jinja filters.

    Example:
        {{ items |> where(published=true) |> sort_by("date") |> take(5) }}

    vs Jinja:
        {{ items | selectattr("published") | sort(attribute="date") | first }}
    """

    value: Expr
    steps: Sequence[tuple[str, Sequence[Expr], dict[str, Expr]]]  # (name, args, kwargs)


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
class LoopVar(Expr):
    """Loop variable access: {{ loop.index }}

    Provides access to loop iteration state.
    """

    attr: str  # 'index', 'index0', 'first', 'last', 'length', etc.


# =============================================================================
# Type Aliases
# =============================================================================

AnyExpr = Union[
    Const,
    Name,
    Tuple,
    List,
    Dict,
    Getattr,
    Getitem,
    Slice,
    FuncCall,
    Filter,
    Pipeline,
    Test,
    BinOp,
    UnaryOp,
    Compare,
    BoolOp,
    CondExpr,
    Await,
    Concat,
    MarkSafe,
    LoopVar,
]
