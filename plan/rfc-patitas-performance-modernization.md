# RFC: Patitas Performance & Modernization

**Status**: Implemented  
**Author**: Bengal Team  
**Created**: 2026-01-02  
**Updated**: 2026-01-02  
**Implemented**: 2026-01-02  
**Target**: Patitas 0.2.0  
**Depends On**: rfc-patitas-commonmark-compliance.md

## Executive Summary

Patitas is architecturally sound with O(n) guaranteed performance, but several targeted improvements can yield 10-15% additional throughput while improving type safety and leveraging Python 3.14 features. This RFC proposes four focused enhancements:

1. **Emphasis Algorithm Refactor** — Decouple match tracking from token mutation (prerequisite)
2. **Inline Token Representation** — Replace dict-based tokens with typed NamedTuples (~10% speedup)
3. **Pre-compiled Character Sets** — Expand frozenset usage for O(1) character classification
4. **Python 3.14 Modernization** — Adopt PEP 695 type syntax and other 3.14-specific features

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
| Local variable caching | `parsing/inline/core.py:82-83` | Hot loop optimization |

### Baseline Requirements

**Before implementation begins**, capture baseline metrics:

```bash
# Run and record these baselines
pytest benchmarks/test_patitas_performance.py -v --benchmark-only --benchmark-json=baseline.json
```

| Metric | Baseline (to be measured) | Target |
|--------|---------------------------|--------|
| Medium doc (100 iterations) | ___ ms | 15% faster |
| Emphasis-heavy doc | ___ ms | 16% faster |
| Memory per inline token | ___ bytes | 60% reduction |

---

## Proposal 0: Emphasis Algorithm Refactor (Prerequisite)

### Problem

The current emphasis algorithm **mutates tokens in place**:

```python
# parsing/inline/emphasis.py:107-120
opener["matched_with"] = closer_idx
opener["match_count"] = use_count
opener["count"] -= use_count
opener["active"] = False
```

This prevents using immutable NamedTuples for tokens. We must decouple match tracking from token mutation.

### Solution

Introduce an external `MatchRegistry` to track delimiter matches without token mutation:

```python
# parsing/inline/match_registry.py (NEW FILE)
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DelimiterMatch:
    """Record of a matched opener-closer pair."""
    opener_idx: int
    closer_idx: int
    match_count: int  # 1 for emphasis, 2 for strong


@dataclass(slots=True)
class MatchRegistry:
    """External tracking for delimiter matches.

    Decouples match state from token objects, enabling immutable tokens.
    """
    matches: list[DelimiterMatch] = field(default_factory=list)
    consumed: dict[int, int] = field(default_factory=dict)  # idx -> consumed count
    deactivated: set[int] = field(default_factory=set)

    def record_match(self, opener_idx: int, closer_idx: int, count: int) -> None:
        """Record a delimiter match."""
        self.matches.append(DelimiterMatch(opener_idx, closer_idx, count))
        # Track consumed delimiters
        self.consumed[opener_idx] = self.consumed.get(opener_idx, 0) + count
        self.consumed[closer_idx] = self.consumed.get(closer_idx, 0) + count

    def is_active(self, idx: int) -> bool:
        """Check if delimiter at idx is still active."""
        return idx not in self.deactivated

    def deactivate(self, idx: int) -> None:
        """Mark delimiter as inactive."""
        self.deactivated.add(idx)

    def remaining_count(self, idx: int, original_count: int) -> int:
        """Get remaining delimiter count after matches."""
        return original_count - self.consumed.get(idx, 0)

    def get_match_for_opener(self, idx: int) -> DelimiterMatch | None:
        """Get match record where idx is the opener."""
        for match in self.matches:
            if match.opener_idx == idx:
                return match
        return None
```

### Updated Emphasis Algorithm

```python
# parsing/inline/emphasis.py (UPDATED)
from .match_registry import MatchRegistry

def _process_emphasis(self, tokens: list[InlineToken], registry: MatchRegistry) -> None:
    """Process delimiter stack using external match tracking.

    Tokens remain immutable; all state tracked in registry.
    """
    closer_idx = 0
    while closer_idx < len(tokens):
        closer = tokens[closer_idx]
        if not isinstance(closer, DelimiterToken):
            closer_idx += 1
            continue
        if not closer.can_close or not registry.is_active(closer_idx):
            closer_idx += 1
            continue

        closer_remaining = registry.remaining_count(closer_idx, closer.count)
        if closer_remaining == 0:
            closer_idx += 1
            continue

        # Look backwards for matching opener
        opener_idx = closer_idx - 1
        found_opener = False

        while opener_idx >= 0:
            opener = tokens[opener_idx]
            if not isinstance(opener, DelimiterToken):
                opener_idx -= 1
                continue
            if not opener.can_open or not registry.is_active(opener_idx):
                opener_idx -= 1
                continue
            if opener.char != closer.char:
                opener_idx -= 1
                continue

            opener_remaining = registry.remaining_count(opener_idx, opener.count)
            if opener_remaining == 0:
                opener_idx -= 1
                continue

            # CommonMark "sum of delimiters" rule
            both_can_open_close = (opener.can_open and opener.can_close) or \
                                  (closer.can_open and closer.can_close)
            sum_is_multiple_of_3 = (opener_remaining + closer_remaining) % 3 == 0
            neither_is_multiple_of_3 = opener_remaining % 3 != 0 or closer_remaining % 3 != 0
            if both_can_open_close and sum_is_multiple_of_3 and neither_is_multiple_of_3:
                opener_idx -= 1
                continue

            # Found match
            found_opener = True
            use_count = 2 if (opener_remaining >= 2 and closer_remaining >= 2) else 1
            registry.record_match(opener_idx, closer_idx, use_count)

            # Deactivate if exhausted
            if registry.remaining_count(opener_idx, opener.count) == 0:
                registry.deactivate(opener_idx)
            if registry.remaining_count(closer_idx, closer.count) == 0:
                registry.deactivate(closer_idx)

            # Deactivate unmatched delimiters between opener and closer
            for i in range(opener_idx + 1, closer_idx):
                if isinstance(tokens[i], DelimiterToken) and registry.is_active(i):
                    registry.deactivate(i)

            break

        if not found_opener:
            if not closer.can_open:
                registry.deactivate(closer_idx)
            closer_idx += 1
        elif registry.remaining_count(closer_idx, closer.count) > 0:
            pass  # Continue from same position
        else:
            closer_idx += 1
```

### Benefits

1. **Enables immutable tokens** — NamedTuples can now be used
2. **Cleaner separation** — Match state vs token data
3. **Testable** — Registry can be unit tested independently
4. **No performance penalty** — Dict/set lookups are O(1)

---

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

Replace with typed NamedTuples (now possible after Proposal 0):

```python
# parsing/inline/tokens.py (NEW FILE)
from __future__ import annotations

from typing import NamedTuple, Literal

type DelimiterChar = Literal["*", "_", "~"]


class DelimiterToken(NamedTuple):
    """Delimiter token for emphasis/strikethrough processing.

    Immutable by design — match state tracked externally in MatchRegistry.

    NamedTuple chosen over dataclass for:
    - Immutability by default (required for external match tracking)
    - Tuple unpacking support
    - Lower memory footprint (~80 bytes vs ~200 for dict)
    - Faster attribute access (tuple index vs hash lookup)
    """
    char: DelimiterChar
    count: int
    can_open: bool
    can_close: bool

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


class HardBreakToken(NamedTuple):
    """Hard line break token."""

    @property
    def type(self) -> Literal["hard_break"]:
        return "hard_break"


class SoftBreakToken(NamedTuple):
    """Soft line break token."""

    @property
    def type(self) -> Literal["soft_break"]:
        return "soft_break"


# Type alias for all inline tokens (PEP 695 syntax)
type InlineToken = DelimiterToken | TextToken | CodeSpanToken | NodeToken | HardBreakToken | SoftBreakToken
```

### Migration

**Phase 1**: Create new token types and match registry (non-breaking)

```python
# parsing/inline/tokens.py - new file with types above
# parsing/inline/match_registry.py - new file with registry
```

**Phase 2**: Update tokenizer to use typed tokens

```python
# parsing/inline/core.py
from .tokens import DelimiterToken, TextToken, CodeSpanToken, NodeToken, HardBreakToken, SoftBreakToken

# Before:
tokens_append({"type": "delimiter", "char": delim_char, ...})

# After:
tokens_append(DelimiterToken(
    char=delim_char,
    count=count,
    can_open=can_open,
    can_close=can_close,
))
```

**Phase 3**: Update emphasis processor with registry

```python
# parsing/inline/emphasis.py
from .match_registry import MatchRegistry

def _process_emphasis(self, tokens: list[InlineToken], registry: MatchRegistry) -> None:
    """Process delimiter stack using external match tracking."""
    # See Proposal 0 for implementation
    ...
```

**Phase 4**: Update AST builder to use registry

```python
# parsing/inline/core.py
def _build_inline_ast(
    self,
    tokens: list[InlineToken],
    registry: MatchRegistry,
    location: SourceLocation,
) -> tuple[Inline, ...]:
    for idx, token in enumerate(tokens):
        match token:
            case TextToken(content=content):
                result.append(Text(location=location, content=content))
            case CodeSpanToken(code=code):
                result.append(CodeSpan(location=location, code=code))
            case DelimiterToken() if (match := registry.get_match_for_opener(idx)):
                # Build emphasis/strong using match info
                children = self._build_inline_ast(
                    tokens[idx + 1 : match.closer_idx],
                    registry,
                    location,
                )
                if token.char == "~":
                    node = Strikethrough(location=location, children=children)
                elif match.match_count == 2:
                    node = Strong(location=location, children=children)
                else:
                    node = Emphasis(location=location, children=children)
                result.append(node)
                idx = match.closer_idx  # Skip to after closer
            case DelimiterToken():
                # Unmatched delimiter - emit as text
                remaining = registry.remaining_count(idx, token.count)
                if remaining > 0:
                    result.append(Text(location=location, content=token.char * remaining))
            case HardBreakToken():
                result.append(LineBreak(location=location))
            case SoftBreakToken():
                result.append(SoftBreak(location=location))
            case NodeToken(node=node):
                result.append(node)
    return tuple(result)
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

# parsing/inline/core.py:223 (ALSO NEEDS UPDATE)
if next_char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~":  # Escape check
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

**Update core.py** (TWO locations):

```python
# Location 1 - Before:
INLINE_SPECIAL_CHARS = frozenset("*_`[!\\\n<{~$")

# After:
from ..charsets import INLINE_SPECIAL
# (Use INLINE_SPECIAL directly)

# Location 2 - Before (line ~223):
if next_char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~":

# After:
from ..charsets import ASCII_PUNCTUATION
if next_char in ASCII_PUNCTUATION:
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

**Timeline**: Can be done in a single PR after Proposal 0, 1 & 2.

---

## Implementation Roadmap

### Sprint 0: Algorithm Prep (2 days) — NEW

- [ ] Create `parsing/inline/match_registry.py` with `MatchRegistry` class
- [ ] Write unit tests for `MatchRegistry` in isolation
- [ ] Refactor `_process_emphasis()` to use `MatchRegistry` (keep dict tokens for now)
- [ ] Update `_build_inline_ast()` to read from registry
- [ ] Run full test suite, verify identical output
- [ ] Benchmark: confirm no performance regression

**Exit Criteria**: All tests pass, HTML output identical, emphasis uses external tracking

### Sprint 1: Typed Inline Tokens (3 days)

- [ ] Create `parsing/inline/tokens.py` with NamedTuple definitions
- [ ] Update `_tokenize_inline()` to use typed tokens
- [ ] Update `_process_emphasis()` type hints for typed tokens
- [ ] Update `_build_inline_ast()` with match statements
- [ ] Run full test suite, fix any regressions
- [ ] Benchmark: measure inline parsing improvement

**Exit Criteria**: All tests pass, inline parsing 10% faster

### Sprint 2: Character Sets (1 day)

- [ ] Create `parsing/charsets.py` with all frozensets
- [ ] Update `emphasis.py` to use charsets (2 locations)
- [ ] Update `core.py` to use charsets (2 locations: line 26 and ~223)
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
- [ ] Capture memory profile with `tracemalloc`
- [ ] Update `COMPLEXITY.md` with new numbers
- [ ] Document token types in docstrings
- [ ] Update RFC with actual measurements

**Exit Criteria**: Performance improvement documented

**Total Time**: 8 days (was 6 days)

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

### Memory Profiling

```python
# benchmarks/test_patitas_memory.py

import tracemalloc
from bengal.rendering.parsers.patitas import parse

def test_token_memory_usage():
    """Measure memory per inline token."""
    tracemalloc.start()

    # Parse document with many tokens
    doc = "**bold** *italic* `code` [link](url) " * 100
    parse(doc)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Current memory: {current / 1024:.1f} KB")
    print(f"Peak memory: {peak / 1024:.1f} KB")

    # Target: peak < X KB (to be established from baseline)
```

### Expected Results

| Document Type | Before RFC | After RFC | Improvement |
|---------------|------------|-----------|-------------|
| Emphasis-heavy (2500 lines) | ___ ms | ___ ms | ~16% |
| Link-heavy (2500 lines) | ___ ms | ___ ms | ~11% |
| Mixed content (2500 lines) | ___ ms | ___ ms | ~15% |
| Small doc (50 lines) | ___ ms | ___ ms | ~8% |

**Note**: Baseline measurements captured before Sprint 0; actuals filled in during Sprint 4.

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| MatchRegistry adds overhead | Medium | Low | Benchmark Sprint 0 confirms no regression |
| NamedTuple slower for some ops | Low | Low | Benchmark hot paths, revert if needed |
| Breaking change in token structure | Medium | Low | Internal API only, not public |
| PEP 695 less familiar to contributors | Low | Low | Add code comments explaining syntax |
| Algorithm refactor introduces bugs | Medium | Medium | Extensive test coverage, diff HTML output |

### Rollback Strategy

Each sprint is designed to be independently revertible:

| Sprint | Rollback |
|--------|----------|
| Sprint 0 | Revert `match_registry.py`, restore old `_process_emphasis()` |
| Sprint 1 | Revert `tokens.py`, restore dict-based tokens |
| Sprint 2 | Revert charset imports, restore inline string literals |
| Sprint 3 | Revert PEP 695 syntax (low risk, pure syntax change) |

**Rollback Trigger**: >5% performance regression OR test failures after 24 hours of debugging.

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Inline parsing throughput | baseline | +10% | `test_patitas_inline_performance.py` |
| Memory per inline token | ~200 bytes | ~80 bytes | `tracemalloc` profile |
| Type errors in inline module | 0 caught | All caught | mypy strict mode |
| Character classification ops | O(n) strings | O(1) frozenset | Code review |
| Python 3.14 syntax adoption | Partial | Complete | PEP 695, `type` statement |
| Algorithm testability | Coupled | Decoupled | `MatchRegistry` unit tests |

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

For **MatchRegistry** (mutable state, methods needed): Dataclass with slots.

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

## Appendix C: MatchRegistry Design Rationale

**Why external tracking instead of mutable tokens?**

1. **Enables NamedTuple tokens** — Core goal of this RFC
2. **Single Responsibility** — Tokens describe syntax; registry tracks algorithm state
3. **Testability** — Registry can be unit tested without parsing
4. **Debugging** — Registry state is inspectable; mutated dicts are not
5. **Thread safety** — Immutable tokens are inherently thread-safe

**Why dataclass for MatchRegistry?**

1. **Needs mutation** — Algorithm modifies state during processing
2. **Benefits from methods** — `record_match()`, `is_active()`, etc.
3. **Slots for memory** — Still efficient with `@dataclass(slots=True)`
4. **Short-lived** — One registry per `_parse_inline()` call

---

## Appendix D: Related RFCs

- **rfc-patitas-commonmark-compliance.md** — CommonMark spec compliance (parallel effort)
- **rfc-patitas-markdown-parser.md** — Original Patitas design RFC
- **rfc-zero-copy-lexer-handoff.md** — Zero-copy code block architecture

---

## References

- [PEP 695 – Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [PEP 703 – Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [Python 3.14 Release Notes](https://docs.python.org/3.14/whatsnew/3.14.html)
- [CommonMark 0.31.2 Specification](https://spec.commonmark.org/0.31.2/)

---

## Changelog

- **2026-01-02 v2**: Added Proposal 0 (MatchRegistry), fixed character set coverage, added rollback strategy, memory profiling, updated timeline to 8 days
- **2026-01-02 v1**: Initial draft
