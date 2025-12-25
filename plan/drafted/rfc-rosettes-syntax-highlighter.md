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
| **Package Name** | `rosettes` (decided: short, memorable, unique on PyPI) |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Build a new syntax highlighter from scratch, optimized for Python 3.14t |
| **Why** | Modern, lock-free alternative to Pygments for free-threaded Python |
| **Effort** | 2-3 weeks for MVP (10 languages, HTML formatter) |
| **Risk** | Low — Pygments fallback via existing HighlightBackend protocol |
| **Dependencies** | None (pure Python 3.12+) |
| **Min Python** | 3.12+ (StrEnum, slots, modern typing; works on 3.13t/3.14t) |

**Key Design Goals:**
1. ✅ Zero global mutable state (free-threading native)
2. ✅ Immutable configuration objects (thread-safe by design)
3. ✅ Lazy loading (fast cold start)
4. ✅ Streaming output (low memory)
5. ✅ Pygments CSS compatibility (drop-in themes)

---

## Motivation

### Problem: Pygments Wasn't Designed for Modern Python

Pygments was created in 2006 (Python 2.4 era). While it works, it has architectural patterns that don't align with modern Python:

| Pygments Pattern | Modern Alternative |
|------------------|-------------------|
| Mutable global state | Immutable + `@cache` |
| `**options` dicts | Frozen dataclasses |
| No type hints | Full typing |
| Eager plugin discovery | Lazy loading |
| In-memory string building | Generator streaming |
| Lock-based thread safety | Lock-free immutability |

**Pygments doesn't trigger GIL warnings** (it's pure Python), but its mutable shared state requires locking for thread safety, which limits parallelism.

### Why Build Rosettes?

| Reason | Details |
|--------|---------|
| **Modern API** | Type hints, protocols, dataclasses |
| **Free-threading optimized** | Immutable by default, no locks needed |
| **Performance** | Lazy loading, streaming, less overhead |
| **Clean codebase** | Easy to understand and contribute |
| **Learning project** | Fun to build modern Python! |

### Why Not Just Use Pygments?

| Aspect | Pygments | Rosettes |
|--------|----------|----------|
| API style | 2006 Python | 2024 Python |
| Thread model | Locks required | Lock-free |
| Cold start | ~50ms (plugin scan) | <5ms (lazy) |
| Memory per block | ~2KB | <200 bytes |
| Languages | 500+ | 10-20 (quality > quantity) |

**Decision**: Build Rosettes for fun, benchmark it, keep Pygments as fallback for unsupported languages.

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

### 6. Free-Threading Declaration

```python
# rosettes/__init__.py

# Declare free-threading safety (PEP 703)
# This prevents Python from re-enabling the GIL when importing this module.
def __getattr__(name: str):
    """Module-level getattr for lazy loading and free-threading declaration."""
    if name == "_Py_mod_gil":
        # Signal: this module is safe for free-threading
        return 0  # Py_MOD_GIL_NOT_USED
    raise AttributeError(f"module 'rosettes' has no attribute {name!r}")
```

---

## Known Limitations (MVP)

The MVP prioritizes correctness and thread-safety over completeness. These limitations are acceptable because Pygments fallback handles edge cases.

| Limitation | Description | Mitigation |
|------------|-------------|------------|
| **No nested languages** | Can't highlight JS inside HTML, SQL inside Python strings | Falls back to Pygments |
| **No heredoc interpolation** | Basic heredoc support, no variable highlighting inside | Outer syntax correct |
| **Complex escape sequences** | Triple-quoted strings with mixed escapes may mis-tokenize | Rare in practice |
| **No lexer plugins** | Static lexer registry, no runtime extension | Add lexers to codebase |
| **No custom themes** | CSS generation matches Pygments only | Use Pygments themes |

**Trade-off**: Simplicity and thread-safety over Pygments feature parity. The fallback strategy makes this low-risk.

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

    Complexity Guards:
        - MAX_RULES: Prevents regex explosion from too many alternations
        - MAX_PATTERN_LENGTH: Caps combined pattern size
        - These are validated at class definition time (fail-fast)
    """

    name: str = "base"
    aliases: tuple[str, ...] = ()

    # Subclasses define rules as class variable (immutable tuple)
    rules: tuple[Rule, ...] = ()

    # Combined pattern for fast matching (built once at class definition)
    _combined_pattern: re.Pattern[str] | None = None

    # Complexity guards to prevent regex pathology
    MAX_RULES = 50  # Prevent alternation explosion
    MAX_PATTERN_LENGTH = 8000  # Cap combined pattern size

    def __init_subclass__(cls, **kwargs):
        """Pre-compile combined regex pattern for the lexer."""
        super().__init_subclass__(**kwargs)
        if cls.rules:
            # Validate complexity bounds
            if len(cls.rules) > cls.MAX_RULES:
                raise ValueError(
                    f"Lexer {cls.name!r} has {len(cls.rules)} rules, "
                    f"exceeds MAX_RULES={cls.MAX_RULES}. Split into sublexers."
                )

            # Build combined pattern with named groups
            parts = []
            cls._rule_map = {}
            for i, rule in enumerate(cls.rules):
                group_name = f"r{i}"
                parts.append(f"(?P<{group_name}>{rule.pattern.pattern})")
                cls._rule_map[group_name] = rule

            combined = "|".join(parts)

            # Validate pattern length
            if len(combined) > cls.MAX_PATTERN_LENGTH:
                raise ValueError(
                    f"Lexer {cls.name!r} combined pattern is {len(combined)} chars, "
                    f"exceeds MAX_PATTERN_LENGTH={cls.MAX_PATTERN_LENGTH}."
                )

            cls._combined_pattern = re.compile(combined, re.MULTILINE)

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

## Performance Targets

> **Note**: These are **targets**, not validated claims. All will be benchmarked in Phase 4 before MVP release.

### Target Metrics

| Metric | Pygments Baseline | Rosettes Target | Acceptable | Validation Method |
|--------|-------------------|-----------------|------------|-------------------|
| Import time | ~50ms | <5ms | <15ms | `python -c "import rosettes"` |
| Cold lexer | ~30ms | <5ms | <10ms | First `get_lexer("python")` |
| Tokenization | 0.05ms/100 chars | <0.02ms | <0.05ms | Benchmark suite |
| Formatting | 0.05ms/100 chars | <0.02ms | <0.05ms | Benchmark suite |
| Memory/block | ~2KB | <200 bytes | <1KB | `tracemalloc` |
| GIL re-enable | Yes | **No** | **No** | `PYTHON_GIL=0` CI test |

**Acceptance Criteria**:
- 🔴 **Hard requirement**: No GIL re-enablement (blocks MVP if failed)
- 🟡 **Soft target**: Performance within "Acceptable" column (document if missed)
- 🟢 **Stretch goal**: Hit "Target" column

### Projected Site-Wide Impact

| Site Size | Pygments (est.) | Rosettes Target | Minimum Speedup |
|-----------|-----------------|-----------------|-----------------|
| 100 blocks | 60ms | 10ms | 2x |
| 500 blocks | 100ms | 30ms | 2x |
| 1000 blocks | 150ms | 50ms | 2x |

### Free-Threading Scaling (Projected)

| Cores | Pygments (lock contention) | Rosettes Target (lock-free) |
|-------|---------------------------|----------------------------|
| 1 | 1.0x | 1.0x |
| 4 | 2.5x (estimated) | 3.5x+ |
| 8 | 4.0x (estimated) | 6.0x+ |

**Validation**: Run `bench_vs_pygments.py` on 8-core machine with `PYTHON_GIL=0`.

---

## Implementation Plan

### Phase 0: Project Setup (Day 1)

- [ ] Create `rosettes/` package structure
- [ ] Set up `pyproject.toml` with Python 3.12+ requirement
- [ ] Define core types (`Token`, `TokenType`)
- [ ] Define protocols (`Lexer`, `Formatter`)
- [ ] Create frozen config dataclasses
- [ ] Add free-threading declaration (`__getattr__` for `_Py_mod_gil`)
- [ ] Add to Bengal workspace
- [ ] **Set up CI**: Add `PYTHON_GIL=0` test job (GitHub Actions)
- [ ] **Baseline**: Record Pygments performance before starting

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
            # Fall back to Pygments via registry (avoids import cycle)
            from bengal.rendering.highlighting import get_highlighter
            return get_highlighter("pygments").highlight(
                code, language, hl_lines, show_linenos
            )

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
import os


def test_no_gil_warning():
    """Verify Rosettes doesn't re-enable GIL."""
    env = os.environ.copy()
    env["PYTHON_GIL"] = "0"

    result = subprocess.run(
        [sys.executable, "-c", "import rosettes; rosettes.highlight('x=1', 'python')"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert "GIL has been enabled" not in result.stderr, (
        f"GIL was re-enabled! stderr: {result.stderr}"
    )


def test_concurrent_highlighting():
    """Verify concurrent highlighting doesn't corrupt state."""
    import concurrent.futures
    from rosettes import highlight

    def highlight_task(i: int) -> str:
        return highlight(f"x = {i}", "python")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(highlight_task, range(100)))

    # All results should be valid HTML
    assert all("<span" in r for r in results)
    assert len(results) == 100
```

### CI Configuration

```yaml
# .github/workflows/test.yml (excerpt)

jobs:
  test-free-threading:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Python 3.14t (free-threaded)
        uses: actions/setup-python@v5
        with:
          python-version: "3.14t"

      - name: Install dependencies
        run: pip install -e ".[test]"

      - name: Run tests with GIL disabled
        env:
          PYTHON_GIL: "0"
        run: |
          python -c "import sys; print(f'GIL enabled: {sys._is_gil_enabled()}')"
          pytest tests/ -v --tb=short

      - name: Verify no GIL warnings
        env:
          PYTHON_GIL: "0"
        run: |
          python -W error -c "import rosettes; rosettes.highlight('x=1', 'python')" 2>&1 | tee output.txt
          ! grep -q "GIL has been enabled" output.txt
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
    import json
    from datetime import datetime

    print("Warming up...")
    bench_rosettes(10)
    bench_pygments(10)

    print("\nBenchmarking (1000 iterations)...")
    r_time = bench_rosettes()
    p_time = bench_pygments()

    results = {
        "timestamp": datetime.now().isoformat(),
        "iterations": 1000,
        "code_chars": len(CODE),
        "rosettes_ms": r_time * 1000,
        "pygments_ms": p_time * 1000,
        "speedup": p_time / r_time,
        "rosettes_per_call_ms": r_time,
        "pygments_per_call_ms": p_time,
    }

    print(f"\nResults:")
    print(f"  Rosettes: {r_time*1000:.1f}ms total ({r_time:.3f}ms/call)")
    print(f"  Pygments: {p_time*1000:.1f}ms total ({p_time:.3f}ms/call)")
    print(f"  Speedup:  {p_time/r_time:.2f}x")

    # Save baseline for comparison
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to benchmark_results.json")
```

### Baseline Capture (Phase 0)

Run this before starting implementation to establish Pygments baseline:

```bash
# Capture Pygments-only baseline
python -c "
import time
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

CODE = '''
def example():
    x = 42
    return x * 2
'''

lexer = PythonLexer()
formatter = HtmlFormatter()

# Cold start
start = time.perf_counter()
highlight(CODE, lexer, formatter)
cold_start = time.perf_counter() - start

# Warm (1000 iterations)
start = time.perf_counter()
for _ in range(1000):
    highlight(CODE, lexer, formatter)
warm_total = time.perf_counter() - start

print(f'Pygments cold start: {cold_start*1000:.1f}ms')
print(f'Pygments warm (1000x): {warm_total*1000:.1f}ms ({warm_total:.3f}ms/call)')
"
```

---

## Success Criteria

### Must Have (MVP) — Blocks Release

| Criterion | Validation | Owner |
|-----------|------------|-------|
| No GIL re-enablement on Python 3.14t | CI job with `PYTHON_GIL=0` | Automated |
| 10 languages supported | Unit tests for each lexer | Dev |
| HTML formatter with Pygments CSS compatibility | Visual diff test | Dev |
| At least 1x Pygments speed (not slower) | Benchmark suite | Automated |
| Works as Bengal `HighlightBackend` | Integration test | Dev |
| Thread-safe under concurrent load | 8-thread stress test | Automated |

### Should Have — Documented if Missed

| Criterion | Target | Acceptable |
|-----------|--------|------------|
| Cold start improvement | 5x faster | 2x faster |
| Thread scaling (8 cores) | 6x+ | 4x+ |
| Memory per block | <200 bytes | <1KB |
| Bengal site renders correctly | 100% | 95%+ |

### Nice to Have — Post-MVP

- [ ] Terminal formatter (ANSI colors)
- [ ] 20+ languages
- [ ] PyPI publication
- [ ] MkDocs plugin

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance misses targets | Medium | Low | Pygments fallback exists; document trade-offs |
| Regex backtracking on edge cases | Low | Medium | Complexity guards, timeout limits, fallback |
| Language coverage gaps | Low | Low | Pygments fallback handles unsupported languages |
| Thread-safety bugs | Low | High | CI with `PYTHON_GIL=0`, stress tests, immutable design |
| Pygments theme incompatibility | Low | Low | Use identical CSS class names |

**Overall Risk**: **Low** — The fallback strategy and immutable design minimize risk.

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

## Decisions (Resolved)

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Package name** | `rosettes` | Short, memorable, unique on PyPI, no conflicts |
| **PyPI publication** | Internal first, open-source after MVP | Validate design before public commitment |
| **Minimum Python** | 3.12+ | StrEnum, slots, modern typing; works on 3.13t/3.14t |
| **MVP languages** | See priority list below | Based on Bengal docs usage frequency |

### MVP Language Priority (10 languages)

1. **Python** — Most common in Bengal docs
2. **JavaScript** — Web integration examples
3. **TypeScript** — Growing usage
4. **JSON** — Config files, API examples
5. **YAML** — Bengal config, frontmatter
6. **TOML** — pyproject.toml, config
7. **Bash/Shell** — Installation, CLI examples
8. **HTML** — Template examples
9. **CSS** — Styling examples
10. **Diff/Patch** — Changelog, migration guides

**Post-MVP**: Rust, Go, SQL, Markdown, XML

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
