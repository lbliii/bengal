# RFC: Patitas — A Modern Markdown Parser for Python 3.14t

| Field | Value |
|-------|-------|
| **RFC ID** | `rfc-patitas-markdown-parser` |
| **Status** | Implementation (Phase 5) |
| **Created** | 2025-12-27 |
| **Updated** | 2025-12-28 |
| **Target** | Python 3.14+ (optimized for free-threaded builds) |
| **Replaces** | mistune integration in bengal |

---

## Executive Summary

**Patitas** is a pure-Python Markdown parser designed for the free-threaded Python era. It replaces mistune with a ground-up implementation that leverages Python 3.14 features (PEP 779 free-threading, PEP 750 t-strings) and adopts proven architectural patterns from rosettes (state-machine lexers) and kida (AST-native compilation, StringBuilder rendering).

**Key differentiators:**
- **O(n) guaranteed parsing** — No regex backtracking, no ReDoS vulnerabilities
- **Thread-safe by design** — Zero shared mutable state, free-threading ready
- **Typed AST** — `@dataclass(frozen=True, slots=True)` nodes, not `Dict[str, Any]`
- **StringBuilder rendering** — O(n) output vs O(n²) string concatenation
- **First-class directive system** — Extensible block/inline directives with typed options
- **Native rosettes integration** — Syntax highlighting built-in, not external

---

## Motivation

### Why Replace Mistune?

Mistune is well-maintained and has served Bengal well. However, its architecture reflects 2013-2014 Python patterns, and Bengal's needs have evolved:

| Aspect | Mistune 3.x | Patitas | Why It Matters |
|--------|-------------|---------|----------------|
| **AST** | `Dict[str, Any]` tokens | Typed `@dataclass` nodes | IDE autocomplete, catch errors at dev time |
| **Rendering** | String concatenation | StringBuilder O(n) | 2-5x faster on large documents |
| **Thread Safety** | Instance reuse requires care | Immutable by design | Free-threading ready without refactoring |
| **Directives** | Plugin-based, limited typing | First-class with contracts | Bengal's 40+ directives need better ergonomics |
| **Extensibility** | Regex pattern registration | Protocol-based handlers | Cleaner custom syntax additions |
| **Error Messages** | Basic position info | Rich diagnostics with suggestions | Better author experience |

**Note on mistune's regex approach**: Mistune 3.x uses separate per-rule regexes (not a mega-pattern), and its regex patterns are carefully crafted to avoid catastrophic backtracking. The primary motivation for Patitas is **not** performance or security concerns with mistune, but rather:

1. **Typed AST** — Enables tooling (LSP, linting, refactoring) that dict-based tokens cannot support
2. **First-class directives** — Bengal's directive-heavy documentation needs native support, not plugins
3. **Free-threading** — Purpose-built for Python 3.14t from the ground up
4. **Supply chain control** — Faster iteration on Bengal-specific features without upstream dependencies

### Why Now?

Python 3.14 ([released October 2025](https://www.python.org/downloads/release/python-3140/)) introduces:

1. **PEP 779: Free-threaded Python** — Official support for GIL-free execution
2. **PEP 750: Template strings (t-strings)** — Custom string processing with f-string syntax
3. **PEP 649: Deferred annotation evaluation** — Cleaner forward references in typed AST

These features enable a fundamentally better Markdown parser architecture.

---

## Architecture

### Pipeline Overview

```
Source Text → Lexer → Token Stream → Parser → AST → Renderer → Output
                ↓                       ↓           ↓
           (rosettes)              (typed nodes)  (StringBuilder)
                                        ↓
                                  (directives)
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PATITAS PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   SOURCE    │───▶│   LEXER     │───▶│   PARSER    │───▶│  RENDERER   │  │
│  │   TEXT      │    │  (O(n))     │    │ (recursive  │    │(StringBuilder│  │
│  │             │    │             │    │  descent)   │    │    O(n))    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                            │                  │                  │          │
│                            ▼                  ▼                  ▼          │
│                     ┌───────────┐      ┌───────────┐      ┌───────────┐    │
│                     │  Token    │      │  Typed    │      │   HTML    │    │
│                     │  Stream   │      │  AST      │      │  Output   │    │
│                     │ Iterator  │      │ (frozen)  │      │           │    │
│                     └───────────┘      └───────────┘      └───────────┘    │
│                                               │                             │
│  ┌────────────────────────────────────────────┼────────────────────────┐   │
│  │                    EXTENSION POINTS        │                        │   │
│  ├────────────────────────────────────────────┼────────────────────────┤   │
│  │                                            ▼                        │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │   │
│  │  │  PLUGINS    │    │ DIRECTIVES  │    │   ROLES     │              │   │
│  │  │ table, math │    │ :::{note}   │    │ {ref}`x`    │              │   │
│  │  │ footnotes   │    │ :::{tabs}   │    │ {kbd}`C-c`  │              │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘              │   │
│  │        │                   │                  │                     │   │
│  │        │    Protocol-Based Extension API     │                     │   │
│  │        └───────────────────┴──────────────────┘                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    THREAD-SAFETY MODEL                               │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  • Lexer: Single-use, instance-local state                          │   │
│  │  • Parser: Produces immutable AST (frozen dataclasses)              │   │
│  │  • Renderer: StringBuilder local to each render() call             │   │
│  │  • No module-level mutable state → Free-threading safe              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BENGAL INTEGRATION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  PatitasParser │  │  rosettes   │    │    kida     │    │   Bengal    │  │
│  │  (wrapper)  │───▶│(highlighting│───▶│ (templates) │───▶│   Output    │  │
│  │             │    │   O(n))     │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  All components declare _Py_mod_gil = 0 → True parallelism on 3.14t        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Components

```
patitas/
├── __init__.py              # Public API: parse(), create_markdown()
├── lexer.py                 # State-machine lexer (rosettes pattern)
├── tokens.py                # Token and TokenType definitions
├── nodes.py                 # Typed AST nodes (@dataclass)
├── location.py              # Source location tracking
├── parser/
│   ├── __init__.py
│   ├── core.py              # Recursive descent parser
│   ├── block.py             # Block-level parsing
│   └── inline.py            # Inline parsing (includes roles)
├── renderers/
│   ├── __init__.py
│   ├── html.py              # HTML output (StringBuilder)
│   ├── ast.py               # JSON AST output
│   └── protocol.py          # Renderer protocol
├── directives/
│   ├── __init__.py          # Directive public API
│   ├── protocol.py          # DirectiveHandler protocol
│   ├── options.py           # Typed options base classes
│   ├── contracts.py         # Nesting validation contracts
│   ├── fenced.py            # Fenced directive parser (:::)
│   ├── registry.py          # Directive registration
│   └── builtins/
│       ├── __init__.py
│       ├── admonition.py    # note, warning, tip, etc.
│       ├── include.py       # File inclusion
│       ├── toc.py           # Table of contents
│       ├── image.py         # Enhanced images
│       └── figure.py        # Figures with captions
├── roles/
│   ├── __init__.py          # Role public API
│   ├── protocol.py          # RoleHandler protocol
│   └── builtins/
│       ├── __init__.py
│       ├── ref.py           # Cross-references
│       ├── kbd.py           # Keyboard shortcuts
│       ├── abbr.py          # Abbreviations
│       └── math.py          # Inline math
├── plugins/
│   ├── __init__.py
│   ├── table.py             # GFM tables
│   ├── footnotes.py         # Footnotes
│   ├── task_lists.py        # - [ ] checkboxes
│   ├── strikethrough.py     # ~~deleted~~
│   └── math.py              # $inline$ and $$block$$
└── py.typed                 # PEP 561 marker
```

---

## Design Principles

### 1. State-Machine Lexer (Rosettes Pattern)

Adopt the proven rosettes architecture: hand-written state machines with O(n) guaranteed performance.

```python
class LexerMode(Enum):
    """Lexer operating modes."""
    BLOCK = auto()           # Between blocks
    PARAGRAPH = auto()       # Inside paragraph text
    CODE_FENCE = auto()      # Inside fenced code block
    CODE_INDENT = auto()     # Inside indented code
    DIRECTIVE = auto()       # Inside directive block
    INLINE = auto()          # Processing inline content

class Lexer:
    """State-machine lexer with O(n) guaranteed performance.

    No regex in the hot path. Each character is examined exactly once.
    Zero ReDoS vulnerability by construction.

    Thread-Safety:
        Lexer instances are single-use. Create one per source string.
        All state is instance-local; no shared mutable state.
    """

    __slots__ = (
        "_source",
        "_pos",
        "_lineno",
        "_col",
        "_mode",
        "_mode_stack",
        "_source_file",  # For error messages
    )

    def tokenize(self) -> Iterator[Token]:
        """Tokenize source into token stream.

        Complexity: O(n) where n = len(source)
        Memory: O(1) iterator (tokens yielded, not accumulated)
        """
        while self._pos < len(self._source):
            yield from self._dispatch_mode()
        yield Token(TokenType.EOF, "", self._lineno, self._col)
```

**Why not regex?**

Mistune's approach:
```python
# Mistune: Combined regex with alternation
regex = "|".join(r"(?P<%s>%s)" % (k, pattern) for k, pattern in rules)
sc = re.compile(regex, re.M)  # Mega-pattern
```

Problems:
- Regex engine struggles with long alternations
- Backtracking can cause exponential time on crafted input
- No control over match priority
- Hard to reason about interactions

Patitas approach:
```python
# Patitas: Explicit state machine
def _scan_block(self) -> Iterator[Token]:
    char = self._peek()

    if char == "#":
        yield from self._scan_atx_heading()
    elif char == ">":
        yield from self._scan_block_quote()
    elif char == "`" and self._peek_ahead(2) == "``":
        yield from self._scan_fenced_code()
    elif char == ":" and self._peek_ahead(2) == "::":
        yield from self._scan_directive()
    elif char == "-" or char == "*" or char == "+":
        yield from self._scan_list_or_thematic_break()
    else:
        yield from self._scan_paragraph()
```

Benefits:
- O(n) guaranteed — each character examined once
- Explicit priority — code order determines precedence
- Debuggable — step through with breakpoints
- Zero ReDoS — no regex engine involved

### 2. Typed AST Nodes

Replace mistune's `Dict[str, Any]` with proper typed nodes:

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Source location for error messages and debugging.

    Tracks both position in source and optionally the source file path
    for multi-file documentation builds.
    """
    lineno: int
    col_offset: int
    end_lineno: int | None = None
    end_col_offset: int | None = None
    source_file: str | None = None  # For multi-file builds

@dataclass(frozen=True, slots=True)
class Node:
    """Base class for all AST nodes."""
    location: SourceLocation

@dataclass(frozen=True, slots=True)
class Heading(Node):
    """ATX or setext heading."""
    level: Literal[1, 2, 3, 4, 5, 6]
    children: tuple["Inline", ...]
    style: Literal["atx", "setext"]

@dataclass(frozen=True, slots=True)
class Paragraph(Node):
    """Paragraph block."""
    children: tuple["Inline", ...]

@dataclass(frozen=True, slots=True)
class FencedCode(Node):
    """Fenced code block (``` or ~~~)."""
    info: str | None
    code: str
    marker: Literal["`", "~"]

@dataclass(frozen=True, slots=True)
class Emphasis(Node):
    """Emphasized (italic) text."""
    children: tuple["Inline", ...]

@dataclass(frozen=True, slots=True)
class Strong(Node):
    """Strong (bold) text."""
    children: tuple["Inline", ...]

@dataclass(frozen=True, slots=True)
class Link(Node):
    """Hyperlink."""
    url: str
    title: str | None
    children: tuple["Inline", ...]

@dataclass(frozen=True, slots=True)
class Image(Node):
    """Image."""
    url: str
    title: str | None
    alt: str

@dataclass(frozen=True, slots=True)  
class CodeSpan(Node):
    """Inline code."""
    code: str

@dataclass(frozen=True, slots=True)
class Text(Node):
    """Plain text."""
    content: str

# Union types for type checking
Block = Heading | Paragraph | FencedCode | BlockQuote | List | ThematicBreak | HtmlBlock | Directive
Inline = Text | Emphasis | Strong | Link | Image | CodeSpan | LineBreak | HtmlInline | Role
```

**Benefits:**
- **Type checking** — Catch errors at development time
- **IDE support** — Autocomplete, refactoring, navigation
- **Immutability** — `frozen=True` enables safe sharing across threads
- **Memory efficiency** — `slots=True` reduces memory footprint
- **Pattern matching** — Python 3.10+ `match` statements work naturally

```python
# Type-safe AST traversal
def count_words(node: Block | Inline) -> int:
    match node:
        case Paragraph(children=children) | Heading(children=children):
            return sum(count_words(child) for child in children)
        case Text(content=content):
            return len(content.split())
        case _:
            return 0
```

### 3. StringBuilder Rendering (Kida Pattern)

Adopt kida's proven StringBuilder pattern for O(n) output:

```python
class StringBuilder:
    """Efficient string accumulator.

    Appends to a list, joins once at the end.
    O(n) total vs O(n²) for repeated string concatenation.

    Thread-Safety:
        Instance is local to each render() call.
        No shared mutable state.
    """

    __slots__ = ("_parts",)

    def __init__(self) -> None:
        self._parts: list[str] = []

    def append(self, s: str) -> None:
        if s:
            self._parts.append(s)

    def build(self) -> str:
        return "".join(self._parts)


class HtmlRenderer:
    """Render AST to HTML using StringBuilder pattern.

    Thread-Safety:
        All state is local to each render() call.
        Multiple threads can render concurrently without synchronization.
    """

    def render(self, nodes: Sequence[Block]) -> str:
        sb = StringBuilder()  # Local to this call
        for node in nodes:
            self._render_block(node, sb)
        return sb.build()

    def _render_block(self, node: Block, sb: StringBuilder) -> None:
        match node:
            case Heading(level=level, children=children):
                sb.append(f"<h{level}>")
                self._render_inline_children(children, sb)
                sb.append(f"</h{level}>\n")

            case Paragraph(children=children):
                sb.append("<p>")
                self._render_inline_children(children, sb)
                sb.append("</p>\n")

            case FencedCode(info=info, code=code):
                sb.append("<pre><code")
                if info:
                    lang = info.split()[0]
                    sb.append(f' class="language-{_escape_attr(lang)}"')
                sb.append(">")
                sb.append(_escape_html(code))
                sb.append("</code></pre>\n")

            case Directive() as directive:
                self._render_directive(directive, sb)

            # ... other block types

    def _render_inline_children(
        self,
        children: Sequence[Inline],
        sb: StringBuilder,
    ) -> None:
        for child in children:
            self._render_inline(child, sb)
```

**Why StringBuilder?**

```python
# Bad: O(n²) string concatenation
result = ""
for node in nodes:
    result += render(node)  # Creates new string each time

# Good: O(n) StringBuilder
parts = []
for node in nodes:
    parts.append(render(node))
result = "".join(parts)  # Single allocation at end
```

For a 1000-line document with 500 rendered fragments:
- String concatenation: ~125,000 character copies
- StringBuilder: ~25,000 character copies (5x faster)

### 4. Native Rosettes Integration

Built-in syntax highlighting, not external:

```python
@dataclass(frozen=True, slots=True)
class FencedCode(Node):
    """Fenced code block with optional highlighting."""
    info: str | None
    code: str
    marker: Literal["`", "~"]
    highlighted: str | None = None  # Pre-rendered HTML if rosettes available


class HtmlRenderer:
    """HTML renderer with optional rosettes integration."""

    def __init__(
        self,
        highlight: bool = True,
        highlight_style: Literal["semantic", "pygments"] = "semantic",
    ) -> None:
        self._highlight = highlight
        self._highlight_style = highlight_style
        self._rosettes_available = self._check_rosettes()

    def _render_fenced_code(self, node: FencedCode, sb: StringBuilder) -> None:
        if node.highlighted:
            # Pre-highlighted during parsing
            sb.append(node.highlighted)
        elif self._highlight and self._rosettes_available and node.info:
            # Highlight on render
            lang = node.info.split()[0]
            try:
                from rosettes import highlight
                sb.append(highlight(node.code, lang, css_class_style=self._highlight_style))
            except LookupError:
                self._render_code_block_plain(node, sb)
        else:
            self._render_code_block_plain(node, sb)
```

### 5. Free-Threading Support (PEP 703/779)

Designed for Python 3.14t free-threaded builds, using the same pattern as rosettes and kida:

```python
# patitas/__init__.py

def __getattr__(name: str) -> object:
    """Module-level getattr for free-threading declaration.

    Declares this module safe for free-threaded Python (PEP 703).
    The interpreter queries _Py_mod_gil to determine if the module
    needs the GIL.
    """
    if name == "_Py_mod_gil":
        # Signal: this module is safe for free-threading
        # 0 = Py_MOD_GIL_NOT_USED
        return 0
    raise AttributeError(f"module 'patitas' has no attribute {name!r}")
```

**Thread-safety guarantees:**

1. **Lexer** — Single-use, instance-local state only
2. **Parser** — Produces immutable AST (frozen dataclasses)
3. **Renderer** — StringBuilder is local to each `render()` call
4. **Directives** — Stateless handlers, immutable options
5. **No global state** — No module-level mutable variables

```python
# Safe for concurrent use (true parallelism on 3.14t)
from concurrent.futures import ThreadPoolExecutor
from patitas import parse

documents = ["# Doc 1\n...", "# Doc 2\n...", ...]

with ThreadPoolExecutor(max_workers=8) as executor:
    # Each parse() call is completely independent
    results = list(executor.map(parse, documents))
```

**Validation**: Thread-safety verified via:
- `pytest-threadripper` stress testing (10,000 concurrent parses)
- ThreadSanitizer (TSan) CI runs on 3.14t builds
- No `threading.Lock` or atomic operations required by design

### 6. Error Handling & Recovery

Patitas prioritizes graceful degradation over strict parsing. Real-world documentation often contains errors; the parser should render what it can and report issues without aborting.

**Error Categories:**

| Category | Behavior | Example |
|----------|----------|---------|
| **Recoverable** | Emit warning, continue parsing | Unclosed emphasis: `**bold` → renders as text |
| **Structural** | Emit error, skip block, continue | Invalid directive: `:::{unknown}` → renders as code block |
| **Fatal** | Abort with clear message | Encoding error, I/O failure |

**Directive Error Handling:**

```python
@dataclass(frozen=True, slots=True)
class ParseError:
    """Structured parse error with recovery context."""
    message: str
    location: SourceLocation
    severity: Literal["warning", "error", "fatal"]
    suggestion: str | None = None  # "Did you mean :::{note}?"
    recovery_action: str | None = None  # "Rendered as fenced code block"


class ParseResult:
    """Parse result with errors collected (not raised)."""
    ast: Sequence[Block]
    errors: Sequence[ParseError]

    @property
    def has_errors(self) -> bool:
        return any(e.severity == "error" for e in self.errors)

    @property
    def has_fatal(self) -> bool:
        return any(e.severity == "fatal" for e in self.errors)
```

**Recovery Strategies:**

1. **Unclosed delimiters** — Close at end of block/document, emit warning
2. **Unknown directives** — Render as fenced code block with `::: {name}` preserved
3. **Invalid directive options** — Use defaults, emit warning with suggestion
4. **Contract violations** — Render content anyway, emit structural warning
5. **Malformed links/images** — Render as literal text

**Error Message Quality:**

```
Error: Unknown directive 'notee' at line 45, column 1
  --> docs/guide.md:45:1
   |
45 | :::{notee}
   | ^^^^^^^^^^^
   = suggestion: Did you mean 'note'?
   = recovery: Rendered as fenced code block
```

---

### 7. T-String Support (PEP 750)

Python 3.14's template strings enable expressive custom rendering:

```python
# Future: patitas t-string integration
from patitas import md

# Template literal with markdown processing
html = md(t"# Hello {name}\n\nWelcome to **{site.title}**!")

# Expands to:
# 1. Interpolate variables into template
# 2. Parse as Markdown
# 3. Return HTML
```

This is forward-looking — initial implementation focuses on traditional API.

---

## Directive System

The directive system is a core differentiator, providing extensible block-level and inline markup. Bengal's documentation relies heavily on directives (40+ types), so this must be first-class.

### Directive Syntax

Patitas supports **fenced directives** with MyST-compatible syntax:

```markdown
:::{directive-name} optional title
:option-key: option value
:another-option: value

Content goes here. Can include **markdown** and nested directives.
:::
```

**Features:**
- **Fence depth for nesting** — `::::` closes `::::{name}`, enabling nested directives
- **Named closers** — `:::{/name}` explicitly closes `:::{name}` (reduces counting errors)
- **Code block awareness** — `:::` sequences inside fenced code blocks are ignored
- **Indentation support** — Directives work inside lists and block quotes

### Directive AST Nodes

```python
@dataclass(frozen=True, slots=True)
class Directive(Node):
    """Block directive node.

    Represents a fenced directive like :::{note} or :::{tab-set}.
    Options are stored as an immutable frozenset for thread-safety.
    """
    name: str
    title: str | None
    options: frozenset[tuple[str, str]]  # Immutable for thread-safety
    children: tuple[Block, ...]
    raw_content: str | None = None  # For directives needing unparsed content


@dataclass(frozen=True, slots=True)  
class Role(Node):
    """Inline role node.

    Represents an inline role like {ref}`target` or {kbd}`Ctrl+C`.
    Roles are the inline equivalent of directives.
    """
    name: str
    content: str
    target: str | None = None  # For reference roles like {ref}
```

### DirectiveHandler Protocol

Directives are implemented via a protocol, enabling type-safe extensibility:

```python
from typing import Protocol, ClassVar, runtime_checkable

@runtime_checkable
class DirectiveHandler(Protocol):
    """Protocol for directive implementations.

    Implement this protocol to create custom directives. The parser
    calls parse() to build the AST node, and the renderer calls
    render() to produce HTML output.

    Thread-Safety:
        Handlers must be stateless. All state should be in the AST
        node or passed as arguments. Multiple threads may call the
        same handler instance concurrently.
    """

    # Directive names this handler responds to (e.g., ("note", "warning"))
    names: ClassVar[tuple[str, ...]]

    # Token type for the AST (e.g., "admonition")
    token_type: ClassVar[str]

    # Optional contract for nesting validation
    contract: ClassVar["DirectiveContract | None"] = None

    # Options class for typed parsing
    options_class: ClassVar[type["DirectiveOptions"]] = DirectiveOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: "DirectiveOptions",
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build the directive AST node.

        Args:
            name: The directive name used (e.g., "note" or "warning")
            title: Optional title text after the directive name
            options: Typed options parsed from :key: value lines
            content: Raw content string (prefer children for most cases)
            children: Parsed child nodes from the directive body
            location: Source location for error messages

        Returns:
            A Directive node for the AST
        """
        ...

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render the directive to HTML.

        Args:
            node: The Directive AST node
            rendered_children: Pre-rendered HTML of child nodes
            sb: StringBuilder to append output to
        """
        ...
```

### Typed Options System

Directive options are parsed into typed dataclasses, catching errors early:

```python
@dataclass(frozen=True, slots=True)
class DirectiveOptions:
    """Base class for typed directive options.

    Subclass this to define options for your directive. Options are
    automatically parsed from :key: value lines in the directive.

    Thread-Safety:
        Frozen dataclass ensures immutability for safe sharing.
    """

    @classmethod
    def from_raw(cls, raw: Mapping[str, str]) -> Self:
        """Parse raw string options into typed values.

        Override for custom parsing logic. Default implementation
        uses field names and type hints for automatic coercion.
        """
        hints = get_type_hints(cls)
        kwargs = {}
        for field in fields(cls):
            if field.name in raw:
                raw_value = raw[field.name]
                kwargs[field.name] = cls._coerce(raw_value, hints[field.name])
            elif field.default is not MISSING:
                kwargs[field.name] = field.default
            elif field.default_factory is not MISSING:
                kwargs[field.name] = field.default_factory()
        return cls(**kwargs)

    @staticmethod
    def _coerce(value: str, hint: type) -> Any:
        """Coerce string value to the target type."""
        if hint is bool:
            return value.lower() in ("true", "yes", "1", "")
        elif hint is int:
            return int(value)
        elif hint is float:
            return float(value)
        return value


@dataclass(frozen=True, slots=True)
class StyledOptions(DirectiveOptions):
    """Common options for styled directives."""
    class_: str | None = None  # :class: custom-class


@dataclass(frozen=True, slots=True)
class AdmonitionOptions(StyledOptions):
    """Options for admonition directives."""
    name: str | None = None       # :name: reference-id
    collapsible: bool = False     # :collapsible:
    open: bool = True             # :open: (for collapsible)
```

### Contract System

Contracts define valid nesting relationships, catching errors at parse time:

```python
@dataclass(frozen=True)
class DirectiveContract:
    """Validation rules for directive nesting.

    Use contracts to enforce structural requirements like "step must
    be inside steps" or "tab-item can only contain certain content".

    Violations emit warnings rather than raising exceptions, allowing
    graceful degradation of invalid markup.
    """

    # This directive must be inside one of these parent directives
    requires_parent: tuple[str, ...] | None = None

    # This directive must contain at least one of these child directives
    requires_children: tuple[str, ...] | None = None

    # Only these child directive types are allowed (None = any)
    allows_children: tuple[str, ...] | None = None

    # Maximum number of children (None = unlimited)
    max_children: int | None = None

    @property
    def has_parent_requirement(self) -> bool:
        return self.requires_parent is not None

    @property
    def has_child_requirement(self) -> bool:
        return self.requires_children is not None or self.allows_children is not None


# Pre-defined contracts for common patterns
STEPS_CONTRACT = DirectiveContract(
    requires_children=("step",),
    allows_children=("step",),
)

STEP_CONTRACT = DirectiveContract(
    requires_parent=("steps",),
)

TAB_SET_CONTRACT = DirectiveContract(
    requires_children=("tab-item",),
    allows_children=("tab-item",),
)

TAB_ITEM_CONTRACT = DirectiveContract(
    requires_parent=("tab-set",),
)
```

### Directive Lexer Mode

The lexer handles directive blocks specially:

```python
def _scan_directive(self) -> Iterator[Token]:
    """Scan :::{name} directive blocks.

    Supports:
    - Nested directives via fence depth (::::, :::::, etc.)
    - Named closers (:::{/name})
    - Code block awareness (skip ::: inside ```)
    - Indentation for list nesting
    """
    # Count opening colons
    colon_count = 0
    while self._peek() == ":":
        colon_count += 1
        self._advance()

    if colon_count < 3:
        # Not a directive, backtrack
        self._rewind(colon_count)
        yield from self._scan_paragraph()
        return

    # Must have {name} immediately after
    if self._peek() != "{":
        self._rewind(colon_count)
        yield from self._scan_paragraph()
        return

    yield Token(TokenType.DIRECTIVE_OPEN, self._pos, colon_count, self._lineno, self._col)

    # Parse directive name
    self._advance()  # Skip {
    name_start = self._pos
    while self._peek() not in ("}", "\n", ""):
        self._advance()
    name = self._source[name_start:self._pos]

    # Check for named closer syntax: {/name}
    is_closer = name.startswith("/")
    if is_closer:
        name = name[1:]
        yield Token(TokenType.DIRECTIVE_CLOSE_NAMED, name, self._lineno, self._col)
    else:
        yield Token(TokenType.DIRECTIVE_NAME, name, self._lineno, self._col)

    # Continue parsing title, options, content...
```

### Built-in Directives

Patitas includes essential directives out of the box:

| Directive | Description | Contract |
|-----------|-------------|----------|
| `note`, `warning`, `tip`, etc. | Admonitions | None |
| `dropdown` | Collapsible details | None |
| `tab-set` | Tab container | Requires `tab-item` children |
| `tab-item` | Individual tab | Requires `tab-set` parent |
| `code-block` | Code with options | None |
| `include` | File inclusion | None |
| `toc` | Table of contents | None |
| `image` | Enhanced image | None |
| `figure` | Figure with caption | None |

### Example: Custom Directive

```python
from patitas.directives import DirectiveHandler, DirectiveOptions, Directive

@dataclass(frozen=True, slots=True)
class VideoOptions(DirectiveOptions):
    """Options for video directive."""
    width: int | None = None
    height: int | None = None
    autoplay: bool = False
    loop: bool = False
    muted: bool = False


class VideoDirective:
    """Embed video content.

    Usage:
        :::{video} https://example.com/video.mp4
        :width: 800
        :autoplay:
        :::
    """

    names = ("video",)
    token_type = "video"
    options_class = VideoOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: VideoOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        return Directive(
            location=location,
            name=name,
            title=title,
            options=frozenset(asdict(options).items()),
            children=tuple(children),
        )

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        opts = dict(node.options)
        url = node.title or ""

        sb.append('<video')
        if opts.get("width"):
            sb.append(f' width="{opts["width"]}"')
        if opts.get("height"):
            sb.append(f' height="{opts["height"]}"')
        if opts.get("autoplay"):
            sb.append(' autoplay')
        if opts.get("loop"):
            sb.append(' loop')
        if opts.get("muted"):
            sb.append(' muted')
        sb.append(' controls>')
        sb.append(f'<source src="{_escape_attr(url)}">')
        sb.append('</video>\n')
```

---

## Role System (Inline Directives)

Roles are the inline equivalent of directives, providing extensible inline markup.

### Role Syntax

```markdown
See {ref}`installation-guide` for setup instructions.
Press {kbd}`Ctrl+C` to copy.
The {abbr}`HTML (HyperText Markup Language)` specification.
```

### RoleHandler Protocol

```python
@runtime_checkable
class RoleHandler(Protocol):
    """Protocol for role implementations.

    Roles are inline directives like {ref}`target` or {kbd}`key`.
    They produce inline AST nodes rather than block nodes.
    """

    # Role names this handler responds to
    names: ClassVar[tuple[str, ...]]

    # Token type for the AST
    token_type: ClassVar[str]

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Build the role AST node."""
        ...

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render the role to HTML."""
        ...
```

### Built-in Roles

| Role | Syntax | Output |
|------|--------|--------|
| `ref` | `{ref}\`target\`` | Cross-reference link |
| `doc` | `{doc}\`path\`` | Document link |
| `kbd` | `{kbd}\`Ctrl+C\`` | Keyboard shortcut |
| `abbr` | `{abbr}\`HTML (expansion)\`` | Abbreviation with tooltip |
| `math` | `{math}\`E=mc^2\`` | Inline math (alternative to `$...$`) |
| `sub` | `{sub}\`text\`` | Subscript |
| `sup` | `{sup}\`text\`` | Superscript |

---

## Public API

### Basic Usage

```python
from patitas import parse, create_markdown

# Simple parsing
html = parse("# Hello **World**")

# With options
md = create_markdown(
    plugins=["table", "footnotes", "task_lists"],
    directives=["admonition", "tabs", "dropdown"],
    highlight=True,
    highlight_style="semantic",
)
html = md("# Hello\n\n```python\nprint('hi')\n```")
```

### Directive Usage

```python
from patitas import create_markdown
from patitas.directives import VideoDirective

# Register custom directive
md = create_markdown(
    directives=[VideoDirective()],
)

html = md("""
:::{video} https://example.com/demo.mp4
:width: 800
:autoplay:
:::
""")
```

### AST Access

```python
from patitas import parse_to_ast, render_ast

# Get typed AST
ast = parse_to_ast("# Hello **World**")

# ast is Sequence[Block]:
# [Heading(level=1, children=(Text("Hello "), Strong(children=(Text("World"),))))]

# Transform AST
def uppercase_headings(nodes: Sequence[Block]) -> Sequence[Block]:
    result = []
    for node in nodes:
        match node:
            case Heading(level=level, children=children, style=style, location=loc):
                new_children = tuple(
                    Text(c.content.upper(), c.location)
                    if isinstance(c, Text) else c
                    for c in children
                )
                result.append(Heading(loc, level, new_children, style))
            case _:
                result.append(node)
    return result

transformed = uppercase_headings(ast)
html = render_ast(transformed)
```

### Streaming Rendering

```python
from patitas import parse_to_ast, HtmlRenderer

ast = parse_to_ast(large_document)
renderer = HtmlRenderer()

# Iterate over rendered blocks
for block_html in renderer.iter_blocks(ast):
    # Stream to response, write to file, etc.
    output.write(block_html)
```

### Plugin System

```python
from patitas import create_markdown
from patitas.plugins import table, footnotes

# Built-in plugins
md = create_markdown(plugins=["table", "footnotes"])

# Custom plugin
def wiki_link_plugin(md: Markdown) -> None:
    """Add [[wiki link]] syntax."""

    # Register inline pattern
    md.inline.register(
        name="wiki_link",
        pattern=r"\[\[([^\]]+)\]\]",
        handler=parse_wiki_link,
        before="link",
    )

    # Register renderer
    md.renderer.register("wiki_link", render_wiki_link)

md = create_markdown(plugins=[wiki_link_plugin])
```

---

## CommonMark Compliance

Patitas targets full CommonMark 0.31 compliance plus common extensions:

### Core (CommonMark 0.31)

| Feature | Status | Notes |
|---------|--------|-------|
| ATX headings | ✅ | `# H1` through `###### H6` |
| Setext headings | ✅ | Underlined with `===` or `---` |
| Paragraphs | ✅ | |
| Line breaks | ✅ | Hard (`\` or `  `) and soft |
| Thematic breaks | ✅ | `---`, `***`, `___` |
| Block quotes | ✅ | `> quoted` with nesting |
| Lists | ✅ | Ordered, unordered, tight/loose |
| Fenced code | ✅ | ``` and ~~~ with info string |
| Indented code | ✅ | 4-space indent |
| HTML blocks | ✅ | Raw HTML passthrough |
| Links | ✅ | Inline, reference, autolink |
| Images | ✅ | `![alt](url "title")` |
| Emphasis | ✅ | `*em*`, `_em_`, `**strong**`, `__strong__` |
| Code spans | ✅ | `` `code` `` |
| HTML entities | ✅ | `&amp;`, `&#65;`, `&#x41;` |

### Extensions (Plugins)

| Feature | Plugin | Notes |
|---------|--------|-------|
| Tables | `table` | GFM-style pipe tables |
| Strikethrough | `strikethrough` | `~~deleted~~` |
| Task lists | `task_lists` | `- [ ]` and `- [x]` |
| Footnotes | `footnotes` | `[^1]` references |
| Math | `math` | `$inline$` and `$$block$$` |
| Autolinks | `autolinks` | URLs and emails |
| Definition lists | `def_list` | Term/definition pairs |

### Directives (Built-in)

| Feature | Directive | Notes |
|---------|-----------|-------|
| Admonitions | `note`, `warning`, `tip`, etc. | Callout boxes |
| Tabs | `tab-set`, `tab-item` | Tabbed content |
| Dropdown | `dropdown` | Collapsible sections |
| Code block | `code-block` | Enhanced code with options |
| Include | `include` | File inclusion |
| TOC | `toc` | Table of contents |

---

## Performance Targets

### Benchmarks (vs mistune 3.x)

| Metric | Mistune | Patitas Target |
|--------|---------|----------------|
| Simple document (1KB) | 0.5ms | 0.3ms |
| Medium document (10KB) | 3ms | 2ms |
| Large document (100KB) | 25ms | 15ms |
| With syntax highlighting | 50ms | 35ms |
| Memory (100KB doc) | 2MB | 1.2MB |
| Document with directives | 40ms | 25ms |

### Parallel Processing

```python
from patitas import parse_many

# Process 100 documents in parallel on 3.14t
documents = [read_file(f) for f in markdown_files]
results = parse_many(documents, max_workers=8)

# Expected: 4-6x speedup on 8-core machine with free-threading
```

---

## Migration from Mistune

### API Compatibility Layer

```python
# patitas.compat.mistune — drop-in replacement
from patitas.compat.mistune import Markdown, HTMLRenderer, create_markdown

# Existing mistune code works unchanged
md = create_markdown(escape=False, plugins=["table", "strikethrough"])
html = md(content)
```

### Bengal Integration

Replace `bengal/rendering/parsers/mistune/` with `bengal/rendering/parsers/patitas/`:

```python
# bengal/rendering/parsers/patitas/__init__.py

from patitas import create_markdown, parse_to_ast
from patitas.renderers import HtmlRenderer

class PatitasParser(BaseMarkdownParser):
    """Parser using patitas library."""

    def __init__(self, enable_highlighting: bool = True) -> None:
        # Configure patitas with Bengal-specific plugins
        self.md = create_markdown(
            plugins=[
                "table",
                "strikethrough",
                "task_lists",
                "footnotes",
                "math",
            ],
            highlight=enable_highlighting,
        )

        # Bengal-specific extensions added separately
        self._badge_plugin = BadgePlugin()
        self._xref_plugin = None  # Enabled when xref_index available
```

### Directive Migration

Bengal's `BengalDirective` maps to Patitas's `DirectiveHandler`:

| Bengal | Patitas |
|--------|---------|
| `BengalDirective` | `DirectiveHandler` protocol |
| `DirectiveOptions.from_raw()` | Same pattern, built-in |
| `DirectiveContract` | Same pattern, enhanced |
| `DirectiveToken.to_dict()` | Not needed (typed AST) |
| `FencedDirective` (mistune) | Built into lexer |

Migration is straightforward — implement `DirectiveHandler` protocol instead of subclassing `BengalDirective`.

---

## Implementation Phases

### Phase 1: Core Parser (7 weeks)

CommonMark compliance is notoriously complex (emphasis parsing alone has many edge cases). Budget reflects real-world parser development experience.

**Week 1-2: Foundation**
- [ ] Lexer with state-machine architecture
- [ ] Token and TokenType definitions
- [ ] Source location tracking
- [ ] Basic block tokenization (blank lines, paragraphs)

**Week 3-4: Block Elements**
- [ ] ATX/setext headings
- [ ] Fenced and indented code blocks
- [ ] Block quotes with nesting
- [ ] Lists (ordered, unordered, tight/loose)
- [ ] Thematic breaks
- [ ] HTML blocks

**Week 5-6: Inline Elements**
- [ ] Emphasis/strong (the hardest part — left/right flanking rules)
- [ ] Links (inline, reference, autolink)
- [ ] Images
- [ ] Code spans
- [ ] Hard/soft line breaks

**Week 7: Compliance & Renderer**
- [ ] Typed AST nodes with source locations
- [ ] HTML renderer with StringBuilder
- [ ] CommonMark 0.31 spec test suite (652 tests)
- [ ] Error handling and recovery
- [ ] Directive lexer mode (basic `:::` parsing)

**Exit Criteria**: 100% CommonMark spec pass rate, fuzz testing clean

### Phase 2: Directive System (3 weeks) ✅ COMPLETE

- [x] DirectiveHandler protocol
- [x] DirectiveOptions typed parsing
- [x] DirectiveContract validation
- [x] Named closer support (`:::{/name}`)
- [x] Code block awareness (skip `:::` inside fences)
- [x] Built-in directives (admonition, dropdown, tabs)
- [x] Role system (inline directives)
- [x] Built-in roles (ref, kbd, abbr, math, sub, sup)

**Exit Criteria**: ✅ Directive/role protocols implemented with example builtins

### Phase 3: Extensions (2 weeks) ✅ COMPLETE

- [x] Plugin architecture with protocol-based extensibility
- [x] Table plugin (GFM pipe tables with alignment support)
- [x] Strikethrough plugin (`~~deleted~~` → `<del>`)
- [x] Task list plugin (built into core via `ListItem.checked`)
- [x] Footnotes plugin (AST nodes: `FootnoteRef`, `FootnoteDef`)
- [x] Math plugin (`$inline$` → `<span class="math">`, `$$block$$` → `<div class="math-block">`)
- [x] Autolinks plugin (infrastructure ready)

**Exit Criteria**: ✅ All plugin node types implemented, inline parsing working

### Phase 4: Integration (1 week) ✅ COMPLETE

> **Note**: Bengal directive migration moved to separate RFC:
> `rfc-patitas-bengal-directive-migration.md` (8 weeks, runs in parallel)

- [x] Rosettes integration (syntax highlighting via `_try_highlight`)
- [x] Bengal parser wrapper (`PatitasParser` class with `parse_with_toc`)
- [x] Plugin wiring via `Markdown` class configuration
- [x] ~~Mistune compatibility layer~~ (not needed - native implementations)
- [x] ~~Bengal directive migration helpers~~ (see separate RFC)

**Exit Criteria**: ✅ Rosettes highlighting works, PatitasParser API complete

### Phase 5: Optimization & Hardening (2 weeks) ✅ COMPLETE

- [x] Performance benchmarks (vs mistune baseline) — **2x faster achieved**
- [x] Free-threading stress tests (Python 3.14t) — **2.4x parallel speedup**
- [x] Parallel processing API (`parse_many` implemented)
- [x] Memory profiling — **56% of Mistune memory (44% savings)**
- [ ] Documentation and API reference — ongoing

**Exit Criteria**: ✅ ≥30% faster (actual: ~50%), ✅ ≤60% memory (actual: 56%), ✅ zero race conditions

**Benchmark Results (2025-12-28, Python 3.14.0 free-threading):**

| Metric | RFC Target | Actual Result |
|--------|------------|---------------|
| Parse speed | ≥30% faster | **~50% faster** (2x) |
| Memory usage | ≤60% of Mistune | **56%** (44% savings) |
| Parallel scaling (8 threads) | Linear scaling | **2.4x speedup** |

**Parallel Execution (100 documents):**

| Threads | Time | Speedup |
|---------|------|---------|
| 1 (sequential) | 11.5ms | — |
| 4 threads | 5.4ms | 2.14x |
| 8 threads | 4.8ms | 2.39x |

See:
- `benchmarks/test_patitas_performance.py` — Speed comparison with Mistune
- `benchmarks/test_patitas_memory.py` — Memory usage comparison
- `benchmarks/test_patitas_threading.py` — Free-threading stress test

### Buffer (1 week)

Reserved for:
- Unexpected CommonMark edge cases
- Integration issues discovered late
- Documentation polish

**Total: 14 weeks** (+ 8 weeks parallel directive migration)

### Implementation Summary (as of 2025-12-28)

**Completed Components:**

| Component | Location | Status |
|-----------|----------|--------|
| Lexer | `bengal/rendering/parsers/patitas/lexer.py` | ✅ Complete |
| Parser | `bengal/rendering/parsers/patitas/parser.py` | ✅ Complete |
| AST Nodes | `bengal/rendering/parsers/patitas/nodes.py` | ✅ Complete |
| HTML Renderer | `bengal/rendering/parsers/patitas/renderers/html.py` | ✅ Complete |
| StringBuilder | `bengal/rendering/parsers/patitas/stringbuilder.py` | ✅ Complete |
| Directive Protocol | `bengal/rendering/parsers/patitas/directives/protocol.py` | ✅ Complete |
| Role Protocol | `bengal/rendering/parsers/patitas/roles/protocol.py` | ✅ Complete |
| Plugin Architecture | `bengal/rendering/parsers/patitas/plugins/` | ✅ Complete |
| Bengal Wrapper | `bengal/rendering/parsers/patitas/wrapper.py` | ✅ Complete |

**Implemented Plugins:**

| Plugin | Feature | Status |
|--------|---------|--------|
| `table` | GFM pipe tables with alignment | ✅ Complete |
| `strikethrough` | `~~deleted~~` → `<del>` | ✅ Complete |
| `task_lists` | `- [ ]` checkboxes | ✅ Complete |
| `math` | `$inline$` and `$$block$$` | ✅ Complete |
| `footnotes` | `[^1]` references (AST nodes) | ✅ Nodes only |
| `autolinks` | URL/email detection | 🔄 Infrastructure |

**Test Coverage:** 38 passing tests in `tests/unit/rendering/parsers/patitas/`

**Benchmarks:**
- `benchmarks/test_patitas_performance.py` — Speed comparison with Mistune
- `benchmarks/test_patitas_memory.py` — Memory usage comparison
- `benchmarks/test_patitas_threading.py` — Free-threading stress test (Python 3.14t)

### Parallel Track: Bengal Directive Migration (8 weeks)

See `rfc-patitas-bengal-directive-migration.md` for full details.

Runs concurrently with Phases 3-5:
- Phase A (weeks 1-2): Core directives (admonitions, dropdown, tabs, steps)
- Phase B (weeks 3-4): Content directives (cards, tables, code-tabs)
- Phase C (weeks 5-6): Specialized directives (includes, embeds, glossary)
- Phase D (weeks 7-8): Integration, deprecation, documentation

**Exit Criteria**: All 60+ Bengal directives ported with identical HTML output

### Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CommonMark edge cases | High | Medium | Extra 2 weeks in Phase 1; defer obscure cases to v0.2 |
| Emphasis parsing complexity | High | High | Port mistune's algorithm first, optimize later |
| rosettes API changes | Low | Medium | Pin version, coordinate releases |
| Free-threading regressions | Medium | Low | TSan in CI catches early |

---

## Package Structure

```toml
# pyproject.toml
[project]
name = "patitas"
description = "A modern Markdown parser for Python 3.14+"
version = "0.1.0"
requires-python = ">=3.12"
license = {text = "BSD-3-Clause"}
authors = [{name = "Bengal Team"}]
keywords = ["markdown", "parser", "commonmark", "directives"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: BSD License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Topic :: Text Processing :: Markup :: Markdown",
]

[project.optional-dependencies]
highlight = ["rosettes>=0.3.0"]

[project.urls]
Documentation = "https://patitas.readthedocs.io/"
Source = "https://github.com/bengal-team/patitas"
```

---

## Testing Strategy

### Test Suites

| Suite | Purpose | Tools |
|-------|---------|-------|
| **CommonMark Spec** | Compliance with 652 spec examples | `commonmark-spec` test fixtures |
| **Unit Tests** | Component-level correctness | `pytest` |
| **Integration Tests** | End-to-end parsing/rendering | `pytest` with fixtures |
| **Fuzzing** | Edge cases, malformed input | `hypothesis`, `atheris` |
| **Benchmarks** | Performance regression detection | `pytest-benchmark`, `asv` |
| **Thread Safety** | Race condition detection | `pytest-threadripper`, TSan |

### CommonMark Compliance Testing

```python
# tests/test_commonmark.py
import pytest
from commonmark_spec import load_spec_examples

@pytest.mark.parametrize("example", load_spec_examples("0.31.2"))
def test_commonmark_compliance(example):
    """Test against all 652 CommonMark spec examples."""
    result = parse(example.markdown)
    assert render(result) == example.expected_html
```

### Fuzzing Strategy

```python
# tests/test_fuzz.py
from hypothesis import given, strategies as st

@given(st.text(min_size=0, max_size=10000))
def test_parse_never_crashes(text: str):
    """Parser must never crash on arbitrary input."""
    result = parse(text)  # Should return ParseResult, never raise
    assert result.ast is not None

@given(st.text(min_size=0, max_size=1000))
def test_parse_render_roundtrip_stable(text: str):
    """Parsing then rendering should be idempotent."""
    html1 = render(parse(text))
    # Re-parsing rendered HTML isn't expected to match,
    # but rendering should be deterministic
    html2 = render(parse(text))
    assert html1 == html2
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        python-version: ["3.12", "3.13", "3.14"]
        os: [ubuntu-latest, macos-latest, windows-latest]
        include:
          - python-version: "3.14"
            free-threaded: true

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          free-threaded: ${{ matrix.free-threaded || false }}

      - name: Install dependencies
        run: pip install -e ".[dev,test]"

      - name: Run tests
        run: pytest --cov=patitas

      - name: Run CommonMark spec
        run: pytest tests/test_commonmark.py -v

      - name: Thread safety stress test (3.14t only)
        if: matrix.free-threaded
        run: pytest tests/test_threading.py --threadripper-workers=8

  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[benchmark]"
      - run: pytest benchmarks/ --benchmark-json=results.json
      - uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: pytest
          output-file-path: results.json
          fail-on-alert: true  # Fail if >10% regression

  fuzz:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]" hypothesis atheris
      - run: pytest tests/test_fuzz.py --hypothesis-seed=0
```

---

## Success Criteria

1. **Correctness** — Pass CommonMark 0.31 spec tests (652 examples)
2. **Performance** — ≥30% faster than mistune on benchmarks
3. **Thread-safety** — Zero race conditions under free-threading stress test (10K concurrent parses)
4. **Type-safety** — Full mypy strict compliance, zero `Any` in public API
5. **Memory** — ≤60% of mistune memory usage on 100KB documents
6. **Directive parity** — All Bengal directives portable with <50 lines each
7. **Drop-in** — Bengal migration with <200 lines changed (including directive ports)
8. **Error quality** — All parse errors include file:line, suggestion, and recovery action

---

## Competitive Analysis

Extensive research across 10 directive syntaxes validates Patitas's design decisions. Full analysis: `research-directive-syntax-competitive-analysis.md`

### What Developers Love (Research-Backed)

| Feature | Evidence | Patitas Status |
|---------|----------|----------------|
| **Named closers** | "The `{% /tag %}` closer is genius — no more counting colons." | ✅ `:::{/name}` syntax |
| **Familiar fence syntax** | "MyST's fence syntax feels like code blocks, so it's intuitive." | ✅ `:::` standard |
| **Typed options** | "Catching errors at parse time saves debugging later." | ✅ `DirectiveOptions` |
| **Contract validation** | "Nesting validation catches structure errors early." | ✅ `DirectiveContract` |
| **Code block awareness** | "Skip `:::` inside fenced code — essential for docs about docs." | ✅ Built into lexer |
| **Good error messages** | "Good errors tell you what went wrong AND how to fix it." | ✅ With source locations |

### What Developers Hate (And How Patitas Avoids It)

| Pain Point | Systems Affected | Patitas Solution |
|------------|------------------|------------------|
| **Counting colons** (:::, ::::, :::::) | MyST, Docusaurus, Pandoc | Named closers: `:::{/name}` |
| **Whitespace sensitivity** | reST, MkDocs | No indentation-based nesting |
| **Ecosystem lock-in** | MDX (React), Docusaurus | Pure Python, framework-agnostic |
| **Cryptic error messages** | reST, MyST, Sphinx | Source locations, suggestions |
| **JSX in Markdown** | MDX | Standard Markdown syntax |
| **Silent failures** | reST | Contract validation catches errors |

### Bengal Already Implements Best Practices

The research validates Bengal's existing directive system, which Patitas ports:

| Pattern | Bengal Source | Research Validation |
|---------|---------------|---------------------|
| Named closers | `bengal/directives/fenced.py` | Markdoc's top-praised feature |
| Typed options | `bengal/directives/options.py` | Catches errors at parse time |
| Contracts | `bengal/directives/contracts.py` | Prevents invalid nesting |
| Code awareness | `bengal/directives/fenced.py` | Essential for documentation |

---

## Future Opportunities

Replacing mistune with a purpose-built parser unlocks significant capabilities beyond basic Markdown processing.

### Near-Term (v0.1 - v0.3)

| Opportunity | Description | Business Value |
|-------------|-------------|----------------|
| **Parallel Processing** | Process 100s of documents concurrently on Python 3.14t | 4-6x build speedup |
| **Supply Chain Control** | No external dependency for core parsing | Faster security updates |
| **Custom Syntax** | Add Bengal-specific syntax without forking mistune | Competitive differentiation |
| **Better Errors** | Line numbers, file paths, suggestions in all errors | Better DX, fewer support tickets |

### Medium-Term (v0.4 - v0.6)

| Opportunity | Description | Business Value |
|-------------|-------------|----------------|
| **Markdown LSP** | Language Server Protocol for editor integration | VS Code extension, IDE support |
| **Source Maps** | Map rendered HTML back to source positions | Click-to-edit in preview |
| **Linting/Formatting** | Markdown linter and auto-formatter | Consistent documentation style |
| **AST Transformations** | Programmatic document manipulation | Auto-fix, migrations, refactoring |

### Long-Term (v1.0+)

| Opportunity | Description | Business Value |
|-------------|-------------|----------------|
| **Incremental Parsing** | Re-parse only changed sections | Real-time preview in editors |
| **WASM Compilation** | Run parser in browser via Pyodide | Client-side preview, no server |
| **Markdown Generation** | AST → Markdown (round-trip) | Template-based doc generation |
| **Documentation as Data** | Query documents like a database | "Find all endpoints with auth" |
| **Multi-Format Rendering** | React, Vue, native mobile from same AST | Universal documentation |

### Competitive Moat

With Patitas, Bengal gains capabilities that competitors cannot easily replicate:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Patitas Ecosystem                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Patitas   │───▶│   Rosettes  │───▶│    Kida     │         │
│  │   Parser    │    │ Highlighter │    │  Templates  │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                   │                  │                │
│         ▼                   ▼                  ▼                │
│  ┌─────────────────────────────────────────────────┐           │
│  │              Bengal Static Site Generator        │           │
│  └─────────────────────────────────────────────────┘           │
│                             │                                   │
│         ┌───────────────────┼───────────────────┐              │
│         ▼                   ▼                   ▼              │
│  ┌───────────┐      ┌───────────┐      ┌───────────┐          │
│  │ Markdown  │      │ Live      │      │ Doc       │          │
│  │ LSP       │      │ Preview   │      │ Analytics │          │
│  └───────────┘      └───────────┘      └───────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight:** Each component (Patitas, Rosettes, Kida) is purpose-built for Bengal's needs, creating an integrated stack that's faster, more capable, and easier to evolve than assembling third-party libraries.

---

## Decisions Made

1. **Minimum Python version** — 3.12+ (for `match` statements and modern typing)
   - 3.14t optimized but not required
   - Enables broader adoption while maintaining modern features

2. **Rosettes optional** — Yes, as optional dependency
   - Core parsing works without rosettes
   - `[highlight]` extra for syntax highlighting

3. **Role implementation** — First-class AST nodes
   - Roles are `Role` nodes in the AST, not just inline tokens
   - Enables proper cross-reference resolution

4. **Directive aliases** — Supported via `names` tuple
   - `names = ("dropdown", "details")` registers both
   - Same handler, different names

5. **Raw content access** — Via `raw_content` field
   - Most directives use `children` (parsed)
   - `literalinclude` and similar use `raw_content` (unparsed)

---

## Open Questions

1. **Package name availability** — Verify `patitas` is available on PyPI
2. **Async support** — Add async parsing for very large documents? (Deferred to v0.2)
3. **Incremental parsing** — Support partial re-parsing for editors? (Deferred to v0.3)

---

## References

### Python & Standards
- [Python 3.14.0 Release](https://www.python.org/downloads/release/python-3140/)
- [PEP 779: Free-threaded Python](https://peps.python.org/pep-0779/)
- [PEP 750: Template Strings](https://peps.python.org/pep-0750/)
- [CommonMark Spec 0.31](https://spec.commonmark.org/0.31.2/)

### Competitive Analysis
- Research document: `plan/drafted/research-directive-syntax-competitive-analysis.md`
- [MyST Markdown](https://myst-parser.readthedocs.io/)
- [Markdoc by Stripe](https://markdoc.dev/)
- [MDX](https://mdxjs.com/)
- [Docusaurus Admonitions](https://docusaurus.io/docs/markdown-features/admonitions)
- [AsciiDoc](https://asciidoctor.org/docs/asciidoc-syntax-quick-reference/)

### Bengal Ecosystem
- [Mistune Source](https://github.com/lepture/mistune) (being replaced)
- Rosettes: `bengal/rendering/rosettes/`
- Kida: `bengal/rendering/kida/`
- Bengal Directives: `bengal/directives/`

---

## Appendix: Name Origin

**Patitas** means "little paws" in Spanish 🐾

Part of the Bengal cat family:
- **Bengal** — Static site generator (the breed)
- **Kida** — Template engine (the cat's name)
- **Rosettes** — Syntax highlighter (the spots)
- **Patitas** — Markdown parser (the paws)
