# Rosettes 🌹

**Modern, lock-free syntax highlighting for Python 3.14t**

Rosettes is a pure-Python syntax highlighter designed from the ground up for free-threaded Python. Zero global mutable state, immutable configuration, lazy loading.

## Features

- ✅ **Zero global mutable state** — free-threading native
- ✅ **Immutable configuration** — thread-safe by design
- ✅ **Lazy loading** — fast cold start (<5ms target)
- ✅ **Streaming output** — low memory footprint
- ✅ **Pygments CSS compatible** — drop-in themes

## Installation

```bash
pip install rosettes
```

**Requires Python 3.14t** (free-threaded build). Run with `PYTHON_GIL=0` for lock-free operation.

## Quick Start

```python
from rosettes import highlight

# Basic usage
html = highlight("def foo(): pass", "python")
print(html)

# With line highlighting
html = highlight(
    "x = 1\ny = 2\nz = 3",
    "python",
    hl_lines={2},
)

# Tokenization only
from rosettes import tokenize

tokens = tokenize("print('hello')", "python")
for token in tokens:
    print(f"{token.type}: {token.value!r}")
```

## Supported Languages

MVP includes 10 essential languages:

1. **Python** — Full Python 3.x syntax including f-strings, type hints, walrus operator
2. **JavaScript** — ES6+ syntax
3. **TypeScript** — TypeScript with type annotations
4. **JSON** — JSON with number and string detection
5. **YAML** — YAML configuration files
6. **TOML** — TOML configuration (pyproject.toml, etc.)
7. **Bash** — Shell scripts and commands
8. **HTML** — HTML markup
9. **CSS** — CSS stylesheets
10. **Diff** — Unified diff/patch format

## Thread Safety

Rosettes is designed for free-threaded Python (PEP 703):

```python
from concurrent.futures import ThreadPoolExecutor
from rosettes import highlight

def highlight_code(code: str) -> str:
    return highlight(code, "python")

# Safe to use from multiple threads simultaneously
with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(highlight_code, codes))
```

### How It Works

- **Immutable lexers**: Rules are frozen at class definition time
- **No shared mutable state**: All tokenization uses local variables
- **functools.cache**: Thread-safe memoization for lexer registry
- **Free-threading declaration**: Module declares `_Py_mod_gil = 0`

## Pygments Compatibility

Rosettes uses the same CSS class names as Pygments:

| Token Type | CSS Class |
|------------|-----------|
| Keyword | `.k` |
| String | `.s` |
| Comment | `.c` |
| Number | `.m` |
| Name.Function | `.nf` |
| Name.Class | `.nc` |

Existing Pygments themes work out of the box.

## Configuration

```python
from rosettes import highlight, HighlightConfig, HtmlFormatter

# Custom highlight configuration
html = highlight(
    code,
    "python",
    hl_lines={1, 3, 5},      # Lines to highlight
    show_linenos=True,        # Show line numbers (future)
    css_class="code-block",   # Custom CSS class
)

# Advanced: direct formatter access
from rosettes import tokenize

config = HighlightConfig(
    hl_lines=frozenset({1, 2}),
    hl_line_class="highlighted",
    css_class="my-code",
)
formatter = HtmlFormatter(config=config)
tokens = iter(tokenize(code, "python"))
html = formatter.format_string(tokens)
```

## API Reference

### High-Level Functions

```python
def highlight(
    code: str,
    language: str,
    *,
    hl_lines: set[int] | None = None,
    show_linenos: bool = False,
    css_class: str = "highlight",
) -> str:
    """Highlight code and return HTML string."""

def tokenize(code: str, language: str) -> list[Token]:
    """Tokenize code without formatting."""
```

### Registry Functions

```python
def get_lexer(name: str) -> Lexer:
    """Get a cached lexer instance."""

def list_languages() -> list[str]:
    """List supported language names."""

def supports_language(name: str) -> bool:
    """Check if a language is supported."""
```

### Types

```python
class Token(NamedTuple):
    type: TokenType
    value: str
    line: int = 1
    column: int = 1

class TokenType(StrEnum):
    KEYWORD = "k"
    STRING = "s"
    # ... (Pygments-compatible values)
```

## Performance

Targets compared to Pygments:

| Metric | Pygments | Rosettes Target |
|--------|----------|-----------------|
| Import time | ~50ms | <5ms |
| Cold lexer | ~30ms | <5ms |
| Memory/block | ~2KB | <200 bytes |

Run benchmarks:

```bash
pip install rosettes[benchmark]
python -m pytest tests/benchmarks/ -v
```

## Development

```bash
# Clone and install
git clone https://github.com/bengal/rosettes
cd rosettes
pip install -e ".[dev]"

# Run tests
pytest

# Run with GIL disabled (Python 3.14t)
PYTHON_GIL=0 pytest

# Type check
mypy rosettes

# Lint
ruff check rosettes tests
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

- Inspired by [Pygments](https://pygments.org/)
- Part of the [Bengal](https://github.com/bengal/bengal) project
- Designed for [PEP 703](https://peps.python.org/pep-0703/) (free-threading)
