# RFC: Rosettes — Modern Syntax Highlighting for Python 3.14t

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-0002 |
| **Title** | Rosettes: Pure Python 3.14t Syntax Highlighter |
| **Status** | Draft |
| **Created** | 2025-12-24 |
| **Revised** | 2025-12-24 |
| **Author** | Bengal Core Team |
| **Depends On** | RFC-0001 (HighlightBackend Protocol) |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Build a new syntax highlighter from scratch, optimized for Python 3.14t |
| **Why** | Pygments re-enables GIL; we need a free-threading-native solution |
| **Effort** | 2-3 weeks for MVP (10 languages, HTML formatter) |
| **Risk** | Low — Pygments fallback via existing HighlightBackend protocol |
| **Dependencies** | None (pure Python 3.12+) |

**Key Design Goals:**
1. ✅ Zero global mutable state (free-threading native)
2. ✅ Immutable configuration objects (thread-safe by design)
3. ✅ Lazy loading (fast cold start)
4. ✅ Streaming output (low memory)
5. ✅ Pygments CSS compatibility (drop-in themes)

---

## Motivation

### Problem: Pygments Re-enables the GIL

When running Bengal on Python 3.14t (free-threaded), Pygments triggers:

```
RuntimeWarning: The global interpreter lock (GIL) has been enabled to load
module 'pygments'... which has not declared that it can run safely without the GIL.
```

**Root causes in Pygments:**
1. Mutable global state (`_lexer_cache`, `_formatter_cache`)
2. Non-thread-safe plugin discovery
3. Mutable formatter instances shared across calls
4. No `Py_mod_gil` slot declaring free-threading safety

### Why Not Fix Pygments?

| Approach | Effort | Outcome |
|----------|--------|---------|
| Contribute to Pygments | High (15-year codebase) | Months/years to merge |
| Fork Pygments | Medium | Maintenance burden |
| Build new (Rosettes) | Medium | Clean slate, modern Python |

**Decision**: Build Rosettes as a modern alternative, keep Pygments as fallback.

---

## Design Goals

### 1. Free-Threading Native

```python
# ❌ Pygments pattern (unsafe)
_cache = {}  # Global mutable state
def get_lexer(name):
    with _lock:  # Requires locking
        if name not in _cache:
            _cache[name] = load_lexer(name)
        return _cache[name]

# ✅ Rosettes pattern (safe)
@cache  # functools.cache is thread-safe in 3.14t
def get_lexer(name: str) -> Lexer:
    return _load_lexer(name)  # Returns immutable lexer
```

### 2. Immutable by Default

```python
# Configuration is frozen
@dataclass(frozen=True, slots=True)
class HighlightConfig:
    hl_lines: frozenset[int] = frozenset()
    show_linenos: bool = False
    css_class: str = "highlight"

# Tokens are immutable
class Token(NamedTuple):
    type: TokenType
    value: str
    line: int
    column: int
```

### 3. Lazy Loading

```python
# Registry is static, lexers load on demand
_LEXER_SPECS = {
    "python": LexerSpec("rosettes.lexers.python", "PythonLexer"),
    "javascript": LexerSpec("rosettes.lexers.javascript", "JSLexer"),
}

@cache
def get_lexer(name: str) -> Lexer:
    spec = _LEXER_SPECS[_normalize(name)]
    module = import_module(spec.module)  # Lazy import
    return getattr(module, spec.class_name)()
```

### 4. Streaming Output

```python
# Memory-efficient for large files
def format(tokens: Iterator[Token]) -> Iterator[str]:
    yield '<pre><code>'
    for token in tokens:
        yield format_token(token)
    yield '</code></pre>'

# Usage: stream to file
for chunk in formatter.format(lexer.tokenize(large_code)):
    file.write(chunk)
```

### 5. Pygments CSS Compatibility

```python
# Same CSS class names as Pygments
_CSS_CLASSES = {
    TokenType.KEYWORD: "k",      # .k { color: green; }
    TokenType.STRING: "s",       # .s { color: red; }
    TokenType.COMMENT: "c",      # .c { color: gray; }
    TokenType.NAME_FUNCTION: "nf",
    TokenType.NAME_CLASS: "nc",
    # ... matches Pygments exactly
}
```

---

## Architecture

### Package Structure

```
rosettes/
├── pyproject.toml
├── rosettes/
│   ├── __init__.py           # Public API
│   ├── _types.py             # Token, TokenType (StrEnum)
│   ├── _config.py            # Frozen dataclass configs
│   ├── _protocol.py          # Lexer, Formatter protocols
│   ├── _registry.py          # Lazy lexer registry
│   ├── _escape.py            # HTML escaping utilities
│   ├── lexers/
│   │   ├── __init__.py
│   │   ├── _base.py          # PatternLexer base class
│   │   ├── python.py
│   │   ├── javascript.py
│   │   ├── typescript.py
│   │   ├── rust.py
│   │   ├── go.py
│   │   ├── html.py
│   │   ├── css.py
│   │   ├── json.py
│   │   ├── yaml.py
│   │   ├── toml.py
│   │   ├── markdown.py
│   │   ├── bash.py
│   │   └── sql.py
│   ├── formatters/
│   │   ├── __init__.py
│   │   ├── html.py           # Primary formatter
│   │   └── terminal.py       # ANSI colors (future)
│   └── themes/
│       ├── __init__.py
│       └── css.py            # CSS generation
└── tests/
    ├── test_lexers.py
    ├── test_formatters.py
    └── benchmarks/
        └── bench_vs_pygments.py
```

### Core Types

```python
# rosettes/_types.py

from enum import StrEnum, auto
from typing import NamedTuple


class TokenType(StrEnum):
    """Semantic token types with Pygments-compatible naming."""

    # Keywords
    KEYWORD = "k"
    KEYWORD_CONSTANT = "kc"
    KEYWORD_DECLARATION = "kd"
    KEYWORD_NAMESPACE = "kn"
    KEYWORD_PSEUDO = "kp"
    KEYWORD_RESERVED = "kr"
    KEYWORD_TYPE = "kt"

    # Names
    NAME = "n"
    NAME_ATTRIBUTE = "na"
    NAME_BUILTIN = "nb"
    NAME_BUILTIN_PSEUDO = "bp"
    NAME_CLASS = "nc"
    NAME_CONSTANT = "no"
    NAME_DECORATOR = "nd"
    NAME_ENTITY = "ni"
    NAME_EXCEPTION = "ne"
    NAME_FUNCTION = "nf"
    NAME_FUNCTION_MAGIC = "fm"
    NAME_LABEL = "nl"
    NAME_NAMESPACE = "nn"
    NAME_OTHER = "nx"
    NAME_PROPERTY = "py"
    NAME_TAG = "nt"
    NAME_VARIABLE = "nv"
    NAME_VARIABLE_CLASS = "vc"
    NAME_VARIABLE_GLOBAL = "vg"
    NAME_VARIABLE_INSTANCE = "vi"
    NAME_VARIABLE_MAGIC = "vm"

    # Literals
    LITERAL = "l"
    LITERAL_DATE = "ld"
    STRING = "s"
    STRING_AFFIX = "sa"
    STRING_BACKTICK = "sb"
    STRING_CHAR = "sc"
    STRING_DELIMITER = "dl"
    STRING_DOC = "sd"
    STRING_DOUBLE = "s2"
    STRING_ESCAPE = "se"
    STRING_HEREDOC = "sh"
    STRING_INTERPOL = "si"
    STRING_OTHER = "sx"
    STRING_REGEX = "sr"
    STRING_SINGLE = "s1"
    STRING_SYMBOL = "ss"
    NUMBER = "m"
    NUMBER_BIN = "mb"
    NUMBER_FLOAT = "mf"
    NUMBER_HEX = "mh"
    NUMBER_INTEGER = "mi"
    NUMBER_INTEGER_LONG = "il"
    NUMBER_OCT = "mo"

    # Operators
    OPERATOR = "o"
    OPERATOR_WORD = "ow"

    # Punctuation
    PUNCTUATION = "p"
    PUNCTUATION_MARKER = "pm"

    # Comments
    COMMENT = "c"
    COMMENT_HASHBANG = "ch"
    COMMENT_MULTILINE = "cm"
    COMMENT_PREPROC = "cp"
    COMMENT_PREPROCFILE = "cpf"
    COMMENT_SINGLE = "c1"
    COMMENT_SPECIAL = "cs"

    # Generic
    GENERIC = "g"
    GENERIC_DELETED = "gd"
    GENERIC_EMPH = "ge"
    GENERIC_ERROR = "gr"
    GENERIC_HEADING = "gh"
    GENERIC_INSERTED = "gi"
    GENERIC_OUTPUT = "go"
    GENERIC_PROMPT = "gp"
    GENERIC_STRONG = "gs"
    GENERIC_SUBHEADING = "gu"
    GENERIC_TRACEBACK = "gt"

    # Special
    TEXT = ""
    WHITESPACE = "w"
    ERROR = "err"
    OTHER = "x"


class Token(NamedTuple):
    """Immutable token — thread-safe, minimal memory."""
    type: TokenType
    value: str
    line: int = 1
    column: int = 1
```

### Protocols

```python
# rosettes/_protocol.py

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from ._types import Token
from ._config import LexerConfig, FormatConfig


@runtime_checkable
class Lexer(Protocol):
    """Tokenizer protocol — must be thread-safe."""

    @property
    def name(self) -> str: ...

    @property
    def aliases(self) -> tuple[str, ...]: ...

    def tokenize(
        self,
        code: str,
        config: LexerConfig = ...,
    ) -> Iterator[Token]: ...


@runtime_checkable  
class Formatter(Protocol):
    """Output formatter protocol — must be thread-safe."""

    @property
    def name(self) -> str: ...

    def format(
        self,
        tokens: Iterator[Token],
        config: FormatConfig = ...,
    ) -> Iterator[str]: ...
```

### Base Lexer

```python
# rosettes/lexers/_base.py

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Callable

from .._types import Token, TokenType
from .._config import LexerConfig


@dataclass(frozen=True, slots=True)
class Rule:
    """Immutable lexer rule."""
    pattern: re.Pattern[str]
    token_type: TokenType | Callable[[re.Match[str]], TokenType]


class PatternLexer:
    """
    Base class for pattern-based lexers.

    Thread-safe: all instance state is immutable.
    Tokenize uses only local variables.
    """

    name: str = "base"
    aliases: tuple[str, ...] = ()

    # Subclasses define rules as class variable (immutable tuple)
    rules: tuple[Rule, ...] = ()

    # Combined pattern for fast matching (built once at class definition)
    _combined_pattern: re.Pattern[str] | None = None

    def __init_subclass__(cls, **kwargs):
        """Pre-compile combined regex pattern for the lexer."""
        super().__init_subclass__(**kwargs)
        if cls.rules:
            # Build combined pattern with named groups
            parts = []
            cls._rule_map = {}
            for i, rule in enumerate(cls.rules):
                group_name = f"r{i}"
                parts.append(f"(?P<{group_name}>{rule.pattern.pattern})")
                cls._rule_map[group_name] = rule
            cls._combined_pattern = re.compile("|".join(parts), re.MULTILINE)

    def tokenize(
        self,
        code: str,
        config: LexerConfig = LexerConfig(),
    ) -> Iterator[Token]:
        """
        Tokenize source code. Thread-safe (no shared mutable state).
        """
        if not self._combined_pattern:
            return

        line = 1
        line_start = 0

        for match in self._combined_pattern.finditer(code):
            # Find which rule matched
            for group_name, rule in self._rule_map.items():
                value = match.group(group_name)
                if value is not None:
                    # Compute token type
                    token_type = (
                        rule.token_type(match)
                        if callable(rule.token_type)
                        else rule.token_type
                    )

                    # Yield token
                    yield Token(
                        type=token_type,
                        value=value,
                        line=line,
                        column=match.start() - line_start + 1,
                    )

                    # Track line numbers
                    newlines = value.count('\n')
                    if newlines:
                        line += newlines
                        line_start = match.end() - len(value.rsplit('\n', 1)[-1])

                    break
```

---

## Performance Expectations

### Benchmarks to Validate

| Metric | Pygments | Rosettes Target | Validation |
|--------|----------|-----------------|------------|
| Import time | ~50ms | <5ms | `python -c "import rosettes"` |
| Cold lexer | ~30ms | <5ms | First `get_lexer("python")` |
| Tokenization | 0.05ms/100 chars | <0.02ms | Benchmark suite |
| Formatting | 0.05ms/100 chars | <0.02ms | Benchmark suite |
| Memory/block | ~2KB | <200 bytes | `tracemalloc` |
| GIL re-enable | Yes | No | `PYTHON_GIL=0` test |

### Expected Site-Wide Impact

| Site Size | Pygments | Rosettes | Speedup |
|-----------|----------|----------|---------|
| 100 blocks | 60ms | 10ms | 6x |
| 500 blocks | 100ms | 30ms | 3.3x |
| 1000 blocks | 150ms | 50ms | 3x |

### Free-Threading Scaling

| Cores | Pygments (lock contention) | Rosettes (lock-free) |
|-------|---------------------------|----------------------|
| 1 | 1.0x | 1.0x |
| 4 | 2.5x | 3.8x |
| 8 | 4.0x | 7.2x |

---

## Implementation Plan

### Phase 0: Project Setup (Day 1)

- [ ] Create `rosettes/` package structure
- [ ] Set up `pyproject.toml` with Python 3.12+ requirement
- [ ] Define core types (`Token`, `TokenType`)
- [ ] Define protocols (`Lexer`, `Formatter`)
- [ ] Create frozen config dataclasses
- [ ] Add to Bengal workspace

### Phase 1: Core Infrastructure (Days 2-3)

- [ ] Implement `PatternLexer` base class
- [ ] Implement lazy lexer registry
- [ ] Implement `HtmlFormatter`
- [ ] Write comprehensive tests
- [ ] Verify thread-safety with `PYTHON_GIL=0`

### Phase 2: Essential Lexers (Days 4-7)

Priority order (by usage frequency):

1. [ ] Python (most common in Bengal docs)
2. [ ] JavaScript/TypeScript
3. [ ] JSON/YAML/TOML (config files)
4. [ ] Bash/Shell
5. [ ] HTML/CSS
6. [ ] Markdown
7. [ ] Rust
8. [ ] Go
9. [ ] SQL
10. [ ] Diff/Patch

### Phase 3: Bengal Integration (Days 8-9)

- [ ] Create `RosettesBackend` implementing `HighlightBackend`
- [ ] Add to Bengal's highlighting registry
- [ ] Add `backend: rosettes` config option
- [ ] Implement Pygments fallback for unsupported languages

### Phase 4: Benchmarking & Validation (Days 10-12)

- [ ] Create benchmark suite (`bench_vs_pygments.py`)
- [ ] Measure import time
- [ ] Measure per-block performance
- [ ] Measure memory usage
- [ ] Validate thread scaling
- [ ] Verify no GIL re-enablement
- [ ] Document results

### Phase 5: Polish & Documentation (Days 13-14)

- [ ] Write README with performance results
- [ ] Add docstrings
- [ ] Create migration guide from Pygments
- [ ] Consider PyPI publication (future)

---

## Bengal Integration

### Backend Implementation

```python
# bengal/rendering/highlighting/rosettes.py

from rosettes import highlight as rosettes_highlight, get_lexer, list_languages
from bengal.rendering.highlighting.protocol import HighlightBackend


class RosettesBackend(HighlightBackend):
    """Rosettes-based syntax highlighting backend."""

    @property
    def name(self) -> str:
        return "rosettes"

    def supports_language(self, language: str) -> bool:
        try:
            get_lexer(language)
            return True
        except LookupError:
            return False

    def highlight(
        self,
        code: str,
        language: str,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        # Check if Rosettes supports this language
        if not self.supports_language(language):
            # Fall back to Pygments for unsupported languages
            from bengal.rendering.highlighting.pygments import PygmentsBackend
            return PygmentsBackend().highlight(code, language, hl_lines, show_linenos)

        return rosettes_highlight(
            code,
            language,
            hl_lines=set(hl_lines) if hl_lines else None,
            show_linenos=show_linenos,
        )
```

### Configuration

```yaml
# bengal.yaml
rendering:
  syntax_highlighting:
    backend: rosettes  # or "pygments" or "auto"
```

### Auto Mode Logic

```python
def get_highlighter(name: str | None = None) -> HighlightBackend:
    name = (name or "auto").lower()

    if name == "auto":
        # Prefer Rosettes on free-threaded Python
        if _is_free_threaded_python() and "rosettes" in _HIGHLIGHT_BACKENDS:
            name = "rosettes"
        else:
            name = "pygments"

    return _HIGHLIGHT_BACKENDS[name]()
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_lexers.py

import pytest
from rosettes import tokenize, TokenType


class TestPythonLexer:
    def test_keywords(self):
        tokens = list(tokenize("def foo():", "python"))
        assert tokens[0].type == TokenType.KEYWORD
        assert tokens[0].value == "def"

    def test_strings(self):
        tokens = list(tokenize('"hello"', "python"))
        assert tokens[0].type == TokenType.STRING

    def test_thread_safety(self):
        """Verify no crashes under concurrent access."""
        from concurrent.futures import ThreadPoolExecutor

        def highlight_many():
            for _ in range(100):
                list(tokenize("def foo(): pass", "python"))

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(highlight_many) for _ in range(8)]
            for f in futures:
                f.result()  # Should not raise
```

### GIL Test

```python
# tests/test_no_gil.py

import subprocess
import sys


def test_no_gil_warning():
    """Verify Rosettes doesn't re-enable GIL."""
    result = subprocess.run(
        [sys.executable, "-c", "import rosettes; rosettes.highlight('x=1', 'python')"],
        env={"PYTHON_GIL": "0"},
        capture_output=True,
        text=True,
    )
    assert "GIL has been enabled" not in result.stderr
```

### Benchmark Suite

```python
# tests/benchmarks/bench_vs_pygments.py

import time
from rosettes import highlight as rosettes_highlight
from pygments import highlight as pygments_highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter


CODE = '''
def fibonacci(n):
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


class Calculator:
    def __init__(self):
        self.history = []

    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
'''


def bench_rosettes(iterations=1000):
    start = time.perf_counter()
    for _ in range(iterations):
        rosettes_highlight(CODE, "python")
    return time.perf_counter() - start


def bench_pygments(iterations=1000):
    lexer = PythonLexer()
    formatter = HtmlFormatter()
    start = time.perf_counter()
    for _ in range(iterations):
        pygments_highlight(CODE, lexer, formatter)
    return time.perf_counter() - start


if __name__ == "__main__":
    print("Warming up...")
    bench_rosettes(10)
    bench_pygments(10)

    print("\nBenchmarking...")
    r_time = bench_rosettes()
    p_time = bench_pygments()

    print(f"Rosettes: {r_time*1000:.1f}ms ({r_time/1000*1000:.3f}ms/call)")
    print(f"Pygments: {p_time*1000:.1f}ms ({p_time/1000*1000:.3f}ms/call)")
    print(f"Speedup: {p_time/r_time:.2f}x")
```

---

## Success Criteria

### Must Have (MVP)

- [ ] No GIL re-enablement on Python 3.14t
- [ ] 10 languages supported (Python, JS, JSON, YAML, etc.)
- [ ] HTML formatter with Pygments CSS compatibility
- [ ] 2x faster than Pygments per-block
- [ ] Works as Bengal `HighlightBackend`

### Should Have

- [ ] 5x faster cold start than Pygments
- [ ] Linear thread scaling (vs Pygments sublinear)
- [ ] <200 bytes memory per code block
- [ ] All Bengal site examples render correctly

### Nice to Have

- [ ] Terminal formatter (ANSI colors)
- [ ] 20+ languages
- [ ] PyPI publication
- [ ] MkDocs plugin

---

## Alternatives Considered

### 1. Fix Pygments Upstream

**Rejected**: 15-year codebase, months to merge changes, uncertain free-threading support timeline.

### 2. Fork Pygments

**Rejected**: Inherit legacy patterns, maintenance burden, still need significant refactoring.

### 3. Use tree-sitter Only

**Rejected**: Grammar packages not compatible with Python 3.14t free-threading yet.

### 4. Wait for Pygments Free-Threading Support

**Rejected**: No timeline, blocks Bengal's free-threading story.

---

## Open Questions

1. **Package name**: `rosettes` or `rosettes-highlight` or `lumina`?
2. **PyPI publication**: Keep internal or open-source from start?
3. **Minimum Python version**: 3.12+ or 3.13+ or 3.14+?
4. **Language priority**: Which 10 languages for MVP?

---

## References

- [PEP 703: Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [Pygments Documentation](https://pygments.org/docs/)
- [Bengal HighlightBackend Protocol](../bengal/rendering/highlighting/protocol.py)
- [RFC-0001: Tree-sitter Integration](./rfc-tree-sitter-universal-autodoc.md)

---

## Appendix: Pygments CSS Class Mapping

Rosettes uses identical CSS class names to Pygments for theme compatibility:

| Token Type | CSS Class | Example |
|------------|-----------|---------|
| Keyword | `.k` | `def`, `class`, `if` |
| Keyword.Declaration | `.kd` | `def`, `class` |
| Name.Function | `.nf` | Function names |
| Name.Class | `.nc` | Class names |
| Name.Builtin | `.nb` | `print`, `len` |
| String | `.s` | `"hello"` |
| String.Doc | `.sd` | `"""docstring"""` |
| Number | `.m` | `42`, `3.14` |
| Comment | `.c` | `# comment` |
| Operator | `.o` | `+`, `-`, `*` |
| Punctuation | `.p` | `(`, `)`, `:` |

This ensures existing Pygments CSS themes work with Rosettes out of the box.
