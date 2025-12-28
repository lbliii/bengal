# RFC: Patitas — A Modern Markdown Parser for Python 3.14t

| Field | Value |
|-------|-------|
| **RFC ID** | `rfc-patitas-markdown-parser` |
| **Status** | Draft |
| **Created** | 2025-12-27 |
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
- **Native rosettes integration** — Syntax highlighting built-in, not external

---

## Motivation

### Why Replace Mistune?

Mistune is well-maintained but architecturally dated (2013-2014 patterns):

| Aspect | Mistune | Patitas |
|--------|---------|---------|
| **Parsing** | Combined mega-regex with `\|` alternation | Hand-written state-machine lexer |
| **AST** | `Dict[str, Any]` everywhere | Typed `@dataclass` nodes |
| **Rendering** | String concatenation O(n²) | StringBuilder O(n) |
| **Thread Safety** | Mutable cursor state, shared env | Immutable state, local-only rendering |
| **Regex Risk** | ReDoS possible on crafted input | Zero regex in hot path |
| **Performance** | "speedup" plugin as workaround | Fast by default |

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
```

### Core Components

```
patitas/
├── __init__.py          # Public API: parse(), create_markdown()
├── lexer.py             # State-machine lexer (rosettes pattern)
├── tokens.py            # Token and TokenType definitions
├── parser/
│   ├── __init__.py
│   ├── core.py          # Recursive descent parser
│   ├── block.py         # Block-level parsing
│   └── inline.py        # Inline parsing
├── nodes.py             # Typed AST nodes (@dataclass)
├── renderers/
│   ├── __init__.py
│   ├── html.py          # HTML output (StringBuilder)
│   ├── ast.py           # JSON AST output
│   └── protocol.py      # Renderer protocol
├── plugins/
│   ├── __init__.py
│   ├── table.py         # GFM tables
│   ├── footnotes.py     # Footnotes
│   ├── task_lists.py    # - [ ] checkboxes
│   ├── strikethrough.py # ~~deleted~~
│   └── math.py          # $inline$ and $$block$$
└── py.typed             # PEP 561 marker
```

---

## Design Principles

### 1. State-Machine Lexer (Rosettes Pattern)

Adopt the proven rosettes architecture: hand-written state machines with O(n) guaranteed performance.

```python
class LexerMode(Enum):
    """Lexer operating modes."""
    BLOCK = auto()      # Between blocks
    PARAGRAPH = auto()  # Inside paragraph text
    CODE_FENCE = auto() # Inside fenced code block
    CODE_INDENT = auto() # Inside indented code
    INLINE = auto()     # Processing inline content

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
class Node:
    """Base class for all AST nodes."""
    lineno: int
    col_offset: int

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
Block = Heading | Paragraph | FencedCode | BlockQuote | List | ThematicBreak | HtmlBlock
Inline = Text | Emphasis | Strong | Link | Image | CodeSpan | LineBreak | HtmlInline
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

### 5. Free-Threading Support (PEP 779)

Designed for Python 3.14t free-threaded builds:

```python
# patitas/__init__.py

def __getattr__(name: str) -> object:
    """Module-level getattr for free-threading declaration."""
    if name == "_Py_mod_gil":
        # Signal: this module is safe for free-threading
        # 0 = Py_MOD_GIL_NOT_USED (PEP 703)
        return 0
    raise AttributeError(f"module 'patitas' has no attribute {name!r}")
```

**Thread-safety guarantees:**

1. **Lexer** — Single-use, instance-local state only
2. **Parser** — Produces immutable AST (frozen dataclasses)
3. **Renderer** — StringBuilder is local to each `render()` call
4. **No global state** — No module-level mutable variables

```python
# Safe for concurrent use
from concurrent.futures import ThreadPoolExecutor
from patitas import parse

documents = ["# Doc 1\n...", "# Doc 2\n...", ...]

with ThreadPoolExecutor(max_workers=8) as executor:
    # Each parse() call is completely independent
    results = list(executor.map(parse, documents))
```

### 6. T-String Support (PEP 750)

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

## Public API

### Basic Usage

```python
from patitas import parse, create_markdown

# Simple parsing
html = parse("# Hello **World**")

# With options
md = create_markdown(
    plugins=["table", "footnotes", "task_lists"],
    highlight=True,
    highlight_style="semantic",
)
html = md("# Hello\n\n```python\nprint('hi')\n```")
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
            case Heading(level=level, children=children, style=style, lineno=ln, col_offset=col):
                new_children = tuple(
                    Text(c.content.upper(), c.lineno, c.col_offset)
                    if isinstance(c, Text) else c
                    for c in children
                )
                result.append(Heading(level, new_children, style, ln, col))
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

---

## Implementation Phases

### Phase 1: Core Parser (4 weeks)

- [ ] Lexer with state-machine architecture
- [ ] Block parser (headings, paragraphs, code, quotes, lists)
- [ ] Inline parser (emphasis, links, images, code spans)
- [ ] Typed AST nodes
- [ ] HTML renderer with StringBuilder
- [ ] CommonMark 0.31 compliance tests

### Phase 2: Extensions (2 weeks)

- [ ] Table plugin (GFM)
- [ ] Strikethrough plugin
- [ ] Task list plugin
- [ ] Footnotes plugin
- [ ] Math plugin
- [ ] Autolinks plugin

### Phase 3: Integration (2 weeks)

- [ ] Rosettes integration (syntax highlighting)
- [ ] Bengal parser wrapper
- [ ] Mistune compatibility layer
- [ ] Migration guide

### Phase 4: Optimization (2 weeks)

- [ ] Performance benchmarks
- [ ] Free-threading validation
- [ ] Parallel processing API
- [ ] Memory profiling

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
keywords = ["markdown", "parser", "commonmark"]
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

## Success Criteria

1. **Correctness** — Pass CommonMark 0.31 spec tests (652 examples)
2. **Performance** — ≥30% faster than mistune on benchmarks
3. **Thread-safety** — Zero race conditions under free-threading stress test
4. **Type-safety** — Full mypy strict compliance
5. **Memory** — ≤60% of mistune memory usage
6. **Drop-in** — Bengal migration with <100 lines changed

---

## Open Questions

1. **Package name availability** — Verify `patitas` is available on PyPI
2. **Minimum Python version** — 3.12+ (for `match` statements) or 3.14+ only?
3. **Rosettes optional** — Should rosettes be optional or bundled?
4. **Async support** — Add async parsing for very large documents?

---

## References

- [Python 3.14.0 Release](https://www.python.org/downloads/release/python-3140/)
- [PEP 779: Free-threaded Python](https://peps.python.org/pep-0779/)
- [PEP 750: Template Strings](https://peps.python.org/pep-0750/)
- [CommonMark Spec 0.31](https://spec.commonmark.org/0.31.2/)
- [Mistune Source](https://github.com/lepture/mistune)
- Rosettes: `bengal/rendering/rosettes/`
- Kida: `bengal/rendering/kida/`

---

## Appendix: Name Origin

**Patitas** means "little paws" in Spanish 🐾

Part of the Bengal cat family:
- **Bengal** — Static site generator (the breed)
- **Kida** — Template engine (the cat's name)
- **Rosettes** — Syntax highlighter (the spots)
- **Patitas** — Markdown parser (the paws)
