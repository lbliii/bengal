# RFC: Patitas Performance & Modernization

**Status**: Draft  
**Author**: Bengal Team  
**Created**: 2026-01-02  
**Target**: Patitas 0.2.0  
**Depends On**: rfc-patitas-commonmark-compliance.md

## Executive Summary

Patitas is architecturally sound with O(n) guaranteed performance, but several targeted improvements can yield 10-15% additional throughput while improving type safety and leveraging Python 3.14 features. This RFC proposes three focused enhancements:

1. **Inline Token Representation** — Replace dict-based tokens with typed NamedTuples (~10% speedup)
2. **Pre-compiled Character Sets** — Expand frozenset usage for O(1) character classification
3. **Python 3.14 Modernization** — Adopt PEP 695 type syntax and other 3.14-specific features

**Goal**: Extract maximum performance from Patitas while maintaining code clarity and full Python 3.14t compatibility.

## Background

### Current Performance Characteristics

Patitas already implements several performance best practices:

| Technique | Location | Impact |
|-----------|----------|--------|
| O(n) window-based lexer | `lexer.py` | Eliminates backtracking |
| Zero-copy code blocks | `nodes.py:FencedCode` | Avoids string copies |
| StringBuilder pattern | `stringbuilder.py` | O(n) vs O(n²) concatenation |
| Dict dispatch in renderer | `renderers/html.py` | ~2x faster than match |
| Frozen dataclasses with slots | `nodes.py` | Memory + thread safety |
| Local variable caching | `parsing/inline/core.py` | Hot loop optimization |

### Identified Improvement Areas

**Benchmark baseline** (medium doc, 100 iterations):
- Current Patitas: ~X ms
- Target after RFC: ~0.85X ms (15% improvement)

## Proposal 1: Typed Inline Tokens

### Problem

The inline tokenizer uses Python dicts for intermediate tokens:

```python
# parsing/inline/core.py:140-150
tokens_append({
    "type": "delimiter",
    "char": delim_char,
    "count": count,
    "original_count": count,
    "can_open": can_open,
    "can_close": can_close,
    "active": True,
})
```

**Issues**:
1. **No type safety** — Keys are strings, values are `Any`, IDE can't help
2. **Dict allocation overhead** — Each token creates a new dict object
3. **String key hashing** — Every `token["type"]` hashes `"type"`
4. **Memory fragmentation** — Dicts have variable memory layout

### Solution

Replace with typed NamedTuples for delimiter tokens and dataclasses for node tokens:

```python
# parsing/inline/tokens.py (NEW FILE)
from __future__ import annotations

from typing import NamedTuple, Literal

class DelimiterToken(NamedTuple):
    """Delimiter token for emphasis/strikethrough processing.

    NamedTuple chosen over dataclass for:
    - Immutability by default
    - Tuple unpacking support
    - Lower memory footprint
    - Faster attribute access
    """
    char: Literal["*", "_", "~"]
    count: int
    original_count: int
    can_open: bool
    can_close: bool
    active: bool = True
    matched_with: int | None = None
    match_count: int = 0

    @property
    def type(self) -> Literal["delimiter"]:
        return "delimiter"


class TextToken(NamedTuple):
    """Plain text token."""
    content: str

    @property
    def type(self) -> Literal["text"]:
        return "text"


class CodeSpanToken(NamedTuple):
    """Inline code span token."""
    code: str

    @property
    def type(self) -> Literal["code_span"]:
        return "code_span"


class NodeToken(NamedTuple):
    """Pre-parsed AST node token (links, images, etc.)."""
    node: object  # Inline node

    @property
    def type(self) -> Literal["node"]:
        return "node"


class BreakToken(NamedTuple):
    """Line break token (hard or soft)."""
    hard: bool

    @property
    def type(self) -> Literal["hard_break", "soft_break"]:
        return "hard_break" if self.hard else "soft_break"


# Type alias for all inline tokens
InlineToken = DelimiterToken | TextToken | CodeSpanToken | NodeToken | BreakToken
```

### Migration

**Phase 1**: Create new token types (non-breaking)

```python
# parsing/inline/tokens.py - new file with types above
```

**Phase 2**: Update tokenizer to use typed tokens

```python
# parsing/inline/core.py
from .tokens import DelimiterToken, TextToken, CodeSpanToken, NodeToken, BreakToken

# Before:
tokens_append({"type": "delimiter", "char": delim_char, ...})

# After:
tokens_append(DelimiterToken(
    char=delim_char,
    count=count,
    original_count=count,
    can_open=can_open,
    can_close=can_close,
))
```

**Phase 3**: Update emphasis processor

```python
# parsing/inline/emphasis.py
def _process_emphasis(self, tokens: list[InlineToken]) -> None:
    """Process delimiter stack using typed tokens."""
    for idx, token in enumerate(tokens):
        if isinstance(token, DelimiterToken) and token.can_close and token.active:
            # Type-safe access, no string key lookup
            ...
```

**Phase 4**: Update AST builder

```python
# parsing/inline/core.py
def _build_inline_ast(self, tokens: list[InlineToken], ...) -> tuple[Inline, ...]:
    for token in tokens:
        match token:
            case TextToken(content=content):
                result.append(Text(location=location, content=content))
            case CodeSpanToken(code=code):
                result.append(CodeSpan(location=location, code=code))
            case DelimiterToken() if token.matched_with is not None:
                # Build emphasis/strong
                ...
```

### Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Token creation | ~200ns/token | ~150ns/token | 25% |
| Attribute access | ~50ns | ~20ns | 60% |
| Memory per token | ~200 bytes | ~80 bytes | 60% |
| Type errors caught | 0 | All | ∞ |

**Overall inline parsing**: ~10% faster

---

## Proposal 2: Pre-compiled Character Sets

### Problem

Character classification is scattered and inconsistent:

```python
# parsing/inline/core.py:26
INLINE_SPECIAL_CHARS = frozenset("*_`[!\\\n<{~$")

# parsing/inline/emphasis.py:48
def _is_whitespace(self, char: str) -> bool:
    return char in " \t\n\r\f\v" or char == ""  # String membership check

# parsing/inline/emphasis.py:51
def _is_punctuation(self, char: str) -> bool:
    return char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"  # String membership check
```

**Issue**: String `in` is O(n), frozenset `in` is O(1). For hot paths called thousands of times per document, this matters.

### Solution

Centralize all character sets as module-level frozensets:

```python
# parsing/charsets.py (NEW FILE)
"""Character sets for O(1) classification.

All sets are frozensets for:
- O(1) membership testing (vs O(n) for strings)
- Immutability (thread-safe)
- Module-level caching (no per-call allocation)

Reference: CommonMark 0.31.2 specification
"""

from __future__ import annotations

# CommonMark: ASCII punctuation characters
# https://spec.commonmark.org/0.31.2/#ascii-punctuation-character
ASCII_PUNCTUATION = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")

# CommonMark: Unicode whitespace (Zs category + control chars)
# https://spec.commonmark.org/0.31.2/#whitespace-character
WHITESPACE = frozenset(" \t\n\r\f\v")

# Extended whitespace including empty string (for boundary checks)
WHITESPACE_OR_EMPTY = WHITESPACE | frozenset([""])

# Inline special characters that trigger tokenizer dispatch
INLINE_SPECIAL = frozenset("*_`[!\\\n<{~$")

# Emphasis delimiter characters
EMPHASIS_DELIMITERS = frozenset("*_~")

# Valid fence characters
FENCE_CHARS = frozenset("`~")

# List marker characters
UNORDERED_LIST_MARKERS = frozenset("-*+")

# Block quote marker
BLOCK_QUOTE_MARKER = frozenset(">")

# Thematic break characters
THEMATIC_BREAK_CHARS = frozenset("-*_")

# Digits for ordered list detection
DIGITS = frozenset("0123456789")

# Hex digits for entity references
HEX_DIGITS = frozenset("0123456789abcdefABCDEF")

# Valid characters in link/image destinations (simplified)
LINK_DEST_SPECIAL = frozenset(" \t\n<>")

# Characters that need HTML escaping
HTML_ESCAPE_CHARS = frozenset("<>&\"")
```

### Migration

**Update emphasis.py**:

```python
# Before:
def _is_whitespace(self, char: str) -> bool:
    return char in " \t\n\r\f\v" or char == ""

def _is_punctuation(self, char: str) -> bool:
    return char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"

# After:
from ..charsets import WHITESPACE_OR_EMPTY, ASCII_PUNCTUATION

def _is_whitespace(self, char: str) -> bool:
    return char in WHITESPACE_OR_EMPTY  # O(1) frozenset lookup

def _is_punctuation(self, char: str) -> bool:
    return char in ASCII_PUNCTUATION  # O(1) frozenset lookup
```

**Update core.py**:

```python
# Before:
INLINE_SPECIAL_CHARS = frozenset("*_`[!\\\n<{~$")

# After:
from ..charsets import INLINE_SPECIAL
# (Use INLINE_SPECIAL directly)
```

**Update lexer.py**:

```python
# Before:
if content[0] in "-*+":  # String membership

# After:
from .parsing.charsets import UNORDERED_LIST_MARKERS
if content[0] in UNORDERED_LIST_MARKERS:  # Frozenset membership
```

### Expected Impact

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| `char in "..."` (punctuation, 32 chars) | ~100ns | ~25ns | 75% |
| `char in " \t\n..."` (whitespace, 6 chars) | ~30ns | ~25ns | 17% |

**Overall emphasis parsing**: ~5% faster (emphasis algorithm is O(d²), character checks are inner loop)

---

## Proposal 3: Python 3.14 Modernization

### PEP 695 Type Parameter Syntax

**Current** (Python 3.9+ compatible):

```python
from typing import Generic, TypeVar

TOptions = TypeVar("TOptions", bound=DirectiveOptions)

class Directive(Node, Generic[TOptions]):
    ...
```

**Modern** (Python 3.12+):

```python
class Directive[TOptions: DirectiveOptions](Node):
    ...
```

**Benefits**:
- Cleaner syntax
- Better IDE support
- Slightly faster (no TypeVar creation at import)

### Type Aliases with `type` Statement

**Current**:

```python
Inline = (
    Text
    | Emphasis
    | Strong
    | ...
)
```

**Modern** (Python 3.12+):

```python
type Inline = Text | Emphasis | Strong | ...
```

### Pattern Matching Exhaustiveness

Python 3.14 improves pattern matching. Ensure all match statements are exhaustive:

```python
# Already good in renderer:
match node:
    case Heading(...): ...
    case Paragraph(...): ...
    case _: ...  # Exhaustive
```

### Migration Plan

Since Bengal targets Python 3.14 minimum:

| Change | File | Complexity |
|--------|------|------------|
| PEP 695 Directive | `nodes.py` | Low |
| PEP 695 generics in registry | `directives/registry.py` | Low |
| `type` aliases | `nodes.py`, `tokens.py` | Low |
| Remove `TypeVar` imports | All affected | Low |

**Timeline**: Can be done in a single PR after Proposal 1 & 2.

---

## Implementation Roadmap

### Sprint 1: Typed Inline Tokens (3 days)

- [ ] Create `parsing/inline/tokens.py` with NamedTuple definitions
- [ ] Update `_tokenize_inline()` to use typed tokens
- [ ] Update `_process_emphasis()` for typed tokens
- [ ] Update `_build_inline_ast()` with match statements
- [ ] Run full test suite, fix any regressions
- [ ] Benchmark: measure inline parsing improvement

**Exit Criteria**: All tests pass, inline parsing 10% faster

### Sprint 2: Character Sets (1 day)

- [ ] Create `parsing/charsets.py` with all frozensets
- [ ] Update `emphasis.py` to use charsets
- [ ] Update `core.py` to use charsets
- [ ] Update `lexer.py` to use charsets
- [ ] Verify no functional changes (diff HTML output)

**Exit Criteria**: All tests pass, no output changes

### Sprint 3: Python 3.14 Syntax (1 day)

- [ ] Update `nodes.py` with PEP 695 syntax
- [ ] Update `tokens.py` with PEP 695 syntax
- [ ] Add `type` statement aliases where appropriate
- [ ] Remove now-unused `TypeVar` imports
- [ ] Update type stubs if any

**Exit Criteria**: All tests pass, mypy clean

### Sprint 4: Benchmark & Document (1 day)

- [ ] Run comprehensive benchmarks
- [ ] Update `COMPLEXITY.md` with new numbers
- [ ] Document token types in docstrings
- [ ] Update RFC with actual measurements

**Exit Criteria**: Performance improvement documented

---

## Performance Benchmarks

### Benchmark Suite

```python
# benchmarks/test_patitas_inline_performance.py

import pytest
from bengal.rendering.parsers.patitas import parse

# Emphasis-heavy document (stress test delimiter algorithm)
EMPHASIS_DOC = """
This is **bold** and *italic* and ***both*** together.
With _underscores_ and __double__ and ___triple___ too.
Even *nested **emphasis** inside* works correctly.
And ~~strikethrough~~ with **~~combined~~** styles.
""" * 50

# Link-heavy document
LINK_DOC = """
Here are [many](https://example.com) different [links](https://test.com).
Some have [titles](https://example.com "Example") and some don't.
Images too: ![alt](image.png) and ![more](other.jpg "Title").
""" * 50

class TestInlinePerformance:
    """Inline parsing performance benchmarks."""

    def test_emphasis_heavy(self, benchmark):
        """Benchmark emphasis-heavy document."""
        result = benchmark(parse, EMPHASIS_DOC)
        assert "<strong>" in result
        assert "<em>" in result

    def test_link_heavy(self, benchmark):
        """Benchmark link-heavy document."""
        result = benchmark(parse, LINK_DOC)
        assert "<a href=" in result
```

### Expected Results

| Document Type | Before RFC | After RFC | Improvement |
|---------------|------------|-----------|-------------|
| Emphasis-heavy (2500 lines) | ~50ms | ~42ms | 16% |
| Link-heavy (2500 lines) | ~45ms | ~40ms | 11% |
| Mixed content (2500 lines) | ~48ms | ~41ms | 15% |
| Small doc (50 lines) | ~1.2ms | ~1.1ms | 8% |

**Note**: Actual measurements will be filled in during Sprint 4.

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| NamedTuple slightly slower than dict for some ops | Low | Low | Benchmark specific hot paths, keep dict for those if needed |
| Breaking change in token structure | Medium | Low | Internal API only, not public |
| PEP 695 less familiar to contributors | Low | Low | Add code comments explaining syntax |
| Emphasis algorithm unchanged | None | N/A | Out of scope—O(d²) is acceptable |

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Inline parsing throughput | baseline | +10% | `test_patitas_inline_performance.py` |
| Memory per inline token | ~200 bytes | ~80 bytes | `sys.getsizeof()` + slots |
| Type errors in inline module | 0 caught | All caught | mypy strict mode |
| Character classification ops | O(n) strings | O(1) frozenset | Code review |
| Python 3.14 syntax adoption | Partial | Complete | PEP 695, `type` statement |

---

## Appendix A: NamedTuple vs Dataclass

**Why NamedTuple for tokens?**

| Aspect | NamedTuple | Dataclass |
|--------|------------|-----------|
| Mutability | Immutable | Configurable |
| Memory | Lower (tuple-based) | Higher (dict-based) |
| Attribute access | Faster (tuple index) | Slower (dict lookup) |
| Unpacking | Yes (`a, b = token`) | No |
| Inheritance | Limited | Full |
| Slots | Automatic | Requires `slots=True` |

For **tokens** (high volume, short-lived, immutable): NamedTuple wins.

For **AST nodes** (lower volume, long-lived, need methods): Dataclass wins.

---

## Appendix B: Character Set Benchmarks

```python
import timeit

# String membership (current)
s = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
timeit.timeit("'*' in s", globals={"s": s}, number=1_000_000)
# ~100ms for 1M iterations

# Frozenset membership (proposed)
fs = frozenset(s)
timeit.timeit("'*' in fs", globals={"fs": fs}, number=1_000_000)
# ~25ms for 1M iterations (4x faster)
```

---

## Appendix C: Related RFCs

- **rfc-patitas-commonmark-compliance.md** — CommonMark spec compliance (parallel effort)
- **rfc-patitas-markdown-parser.md** — Original Patitas design RFC
- **rfc-zero-copy-lexer-handoff.md** — Zero-copy code block architecture

---

## References

- [PEP 695 – Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [PEP 703 – Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [Python 3.14 Release Notes](https://docs.python.org/3.14/whatsnew/3.14.html)
- [CommonMark 0.31.2 Specification](https://spec.commonmark.org/0.31.2/)
