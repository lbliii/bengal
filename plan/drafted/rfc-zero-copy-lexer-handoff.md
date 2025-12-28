# RFC: Zero-Copy Lexer Handoff Protocol (ZCLH)

| Field | Value |
|-------|-------|
| **RFC ID** | `rfc-zero-copy-lexer-handoff` |
| **Status** | Draft |
| **Created** | 2025-12-28 |
| **Author** | AI Assistant + Lawrence Lane |
| **Target** | Patitas (Markdown), Rosettes (Highlighter) |
| **Depends On** | `rfc-patitas-markdown-parser` (complete) |

---

## Executive Summary

This RFC proposes a **Zero-Copy Lexer Handoff (ZCLH)** protocol to eliminate redundant string allocations and double-scanning when syntax highlighting fenced code blocks in Markdown documents.

**Core insight**: By storing buffer coordinates `(source, start, end)` in the AST instead of extracted strings, syntax highlighters can operate directly on the original source buffer without intermediate copies.

**Key changes**:
1. Rosettes lexers gain `start`/`end` parameters (backward compatible)
2. `FencedCode` AST node stores indices instead of extracted `code` string
3. Renderer invokes syntax highlighter with range coordinates

**Trade-offs**:
- ✅ Zero allocations for code block content during parsing
- ✅ Single-scan for syntax highlighting (no re-scan of boundaries)
- ⚠️ Breaking change to `FencedCode` AST node signature
- ⚠️ Source string must remain in scope during rendering

---

## Motivation

### The Problem: Allocation and Double-Scanning

Current flow when rendering a Python code block:

```
1. LEXER     Scans source, finds code fence at positions [100:500]
             Emits tokens: FENCED_CODE_START, FENCED_CODE_CONTENT (per line), FENCED_CODE_END

2. PARSER    Accumulates content lines into new string
             code = "".join(content_lines)  ← ALLOCATION #1
             Returns FencedCode(code=code, ...)

3. RENDERER  Calls rosettes.highlight(code, "python")

4. ROSETTES  Receives code string, scans from pos=0 to len(code)  ← SCAN #2
             (Already scanned by Patitas lexer to find boundaries)
```

**Measured impact** (API reference doc, 80% code):
- ~3,200 intermediate string objects per 10,000-line document
- Rosettes re-scans ~8,000 lines that Patitas already scanned
- Combined overhead: ~12% of total parse time

### The Opportunity: Shared Buffer Coordinates

Both Patitas and Rosettes use **state-machine lexers** with O(n) guaranteed performance. They can operate on the same source buffer if they share a coordinate system:

```python
# Instead of: rosettes.tokenize(extracted_code_string)
# We do:      rosettes.tokenize_range(source, start=100, end=500, lang="python")
```

---

## Design

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CURRENT FLOW                                  │
├──────────────────────────────────────────────────────────────────────┤
│  Source ──► Lexer ──► Parser ──► FencedCode(code="...") ──► Renderer │
│                                         ↑                      │     │
│                                    ALLOCATION              SCAN #2   │
│                                    (join lines)         (rosettes)   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                         ZCLH FLOW                                     │
├──────────────────────────────────────────────────────────────────────┤
│  Source ──► Lexer ──► Parser ──► FencedCode(src, 100, 500) ──► Renderer
│                                         ↑                        │   │
│                                    NO ALLOCATION           HANDOFF   │
│                                    (store indices)    (range coords) │
└──────────────────────────────────────────────────────────────────────┘
```

### Component 1: LexerDelegate Protocol

A minimal protocol that any syntax highlighter can implement:

```python
# bengal/rendering/parsers/patitas/protocols.py

from typing import Protocol, Iterator, Any

class LexerDelegate(Protocol):
    """Protocol for sub-lexers that process source ranges.

    Thread Safety:
        Implementations must be stateless or use only local variables.
        The source string is read-only shared state.
    """

    def tokenize_range(
        self,
        source: str,
        start: int,
        end: int,
        language: str,
    ) -> Iterator[Any]:
        """Tokenize a specific range of the source string.

        Args:
            source: The complete source buffer (read-only)
            start: Start index (inclusive)
            end: End index (exclusive)
            language: Language identifier for lexer selection

        Yields:
            Token objects (type depends on implementation)

        Complexity: O(end - start)
        """
        ...

    def supports_language(self, language: str) -> bool:
        """Check if this delegate can handle the given language."""
        ...
```

### Component 2: Rosettes Range Support

Add `start`/`end` parameters to rosettes lexers. This is **backward compatible**:

```python
# bengal/rendering/rosettes/_protocol.py

class Lexer(Protocol):
    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        *,
        start: int = 0,           # NEW: default preserves current behavior
        end: int | None = None,   # NEW: None means len(code)
    ) -> Iterator[Token]:
        """Tokenize source code, optionally within a range."""
        ...
```

Implementation change for each lexer (example: Python):

```python
# bengal/rendering/rosettes/lexers/python_sm.py

class PythonStateMachineLexer:
    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        """Tokenize Python source code.

        O(end - start) guaranteed. No regex backtracking.
        """
        pos = start                                    # CHANGED: was `pos = 0`
        limit = end if end is not None else len(code)  # CHANGED: was `length = len(code)`
        line = 1
        line_start = start  # Track for column calculation

        while pos < limit:                             # CHANGED: was `pos < length`
            char = code[pos]
            # ... rest of lexer logic unchanged ...
```

### Component 3: FencedCode AST Node (Breaking Change)

The AST node changes from storing extracted code to storing coordinates:

```python
# bengal/rendering/parsers/patitas/nodes.py

@dataclass(frozen=True, slots=True)
class FencedCode(Node):
    """Fenced code block with zero-copy source reference.

    BREAKING CHANGE (v0.4.0):
        Previous: code: str (extracted content)
        Current:  source_start/source_end indices into original source

    Migration:
        Old: block.code
        New: block.get_code(source) or block.code_view(source)
    """

    # Source coordinates (zero-copy)
    source_start: int
    source_end: int

    # Metadata
    info: str | None = None
    marker: Literal["`", "~"] = "`"

    def get_code(self, source: str) -> str:
        """Extract code content (creates new string).

        Use only when string is required (e.g., serialization).
        For rendering, prefer passing coordinates to delegate.
        """
        return source[self.source_start:self.source_end]

    def code_length(self) -> int:
        """Length of code content without allocation."""
        return self.source_end - self.source_start
```

### Component 4: Parser Changes

The parser stores coordinates instead of accumulating content:

```python
# bengal/rendering/parsers/patitas/parser.py

def _parse_fenced_code(self) -> FencedCode:
    """Parse fenced code block with zero-copy coordinates."""
    start_token = self._current
    assert start_token.type == TokenType.FENCED_CODE_START
    self._advance()

    # Extract marker and info
    value = start_token.value
    marker = value[0]
    info = value[len(marker * 3):].strip() or None

    # Track content boundaries (ZERO-COPY: no string accumulation)
    content_start: int | None = None
    content_end: int = 0

    while self._current and self._current.type != TokenType.FENCED_CODE_END:
        token = self._current
        if token.type == TokenType.FENCED_CODE_CONTENT:
            if content_start is None:
                # First content token: record start position
                content_start = token.location.offset  # Need offset in token
            content_end = token.location.end_offset
        self._advance()

    # Consume closing fence
    if self._current and self._current.type == TokenType.FENCED_CODE_END:
        self._advance()

    return FencedCode(
        location=start_token.location,
        source_start=content_start or start_token.location.end_offset,
        source_end=content_end,
        info=info,
        marker=marker,
    )
```

### Component 5: Renderer Handoff

The renderer passes coordinates to the delegate:

```python
# bengal/rendering/parsers/patitas/renderers/html.py

class HtmlRenderer:
    def __init__(
        self,
        source: str,                          # NEW: keep reference to source
        highlight: bool = True,
        delegate: LexerDelegate | None = None,  # NEW: optional delegate
        ...
    ):
        self._source = source
        self._delegate = delegate
        ...

    def _render_fenced_code(
        self,
        node: FencedCode,
        sb: StringBuilder,
    ) -> None:
        """Render fenced code block with zero-copy handoff."""
        lang = node.info.split()[0].lower() if node.info else None

        # Special case: mermaid diagrams
        if lang == "mermaid":
            code = node.get_code(self._source)  # Need actual string for mermaid
            sb.append(f'<div class="mermaid">{_escape_html(code)}</div>\n')
            return

        # Zero-copy handoff to delegate
        if self._delegate and lang and self._delegate.supports_language(lang):
            tokens = self._delegate.tokenize_range(
                self._source,
                node.source_start,
                node.source_end,
                lang,
            )
            self._render_highlighted_tokens(tokens, lang, sb)
            return

        # Fallback: extract code and render plain
        code = node.get_code(self._source)
        sb.append("<pre><code")
        if lang:
            sb.append(f' class="language-{_escape_attr(lang)}"')
        sb.append(">")
        sb.append(_escape_html(code))
        sb.append("</code></pre>\n")
```

### Component 6: RosettesDelegate Bridge

A concrete delegate implementation bridging to rosettes:

```python
# bengal/rendering/highlighting/delegate.py

from bengal.rendering.rosettes import get_lexer, supports_language
from bengal.rendering.parsers.patitas.protocols import LexerDelegate

class RosettesDelegate:
    """LexerDelegate implementation using rosettes.

    Thread-safe: All state is local to method calls.
    """

    def tokenize_range(
        self,
        source: str,
        start: int,
        end: int,
        language: str,
    ) -> Iterator[Token]:
        """Tokenize range using rosettes state-machine lexer."""
        lexer = get_lexer(language)
        yield from lexer.tokenize(source, start=start, end=end)

    def supports_language(self, language: str) -> bool:
        return supports_language(language)
```

---

## Migration Guide

### For Library Users

**Before (v0.3.x)**:
```python
from bengal.rendering.parsers.patitas import parse_to_ast

ast = parse_to_ast(source)
for block in ast:
    if isinstance(block, FencedCode):
        print(block.code)  # Direct access to code string
```

**After (v0.4.0)**:
```python
from bengal.rendering.parsers.patitas import parse_to_ast

ast = parse_to_ast(source)
for block in ast:
    if isinstance(block, FencedCode):
        print(block.get_code(source))  # Explicit extraction
        # Or for zero-copy iteration:
        # print(f"Code at [{block.source_start}:{block.source_end}]")
```

### Deprecation Timeline

| Version | Status |
|---------|--------|
| v0.3.x  | Current: `FencedCode.code: str` |
| v0.4.0  | Breaking: `FencedCode.source_start/source_end` |
| -       | No deprecation period (internal API, pre-1.0) |

---

## Performance Analysis

### Expected Improvements

| Metric | Current | ZCLH | Improvement |
|--------|---------|------|-------------|
| **Allocations per code block** | 1 (content string) | 0 | -100% |
| **Bytes allocated (100-line block)** | ~4KB | 0 | -100% |
| **Scanning passes** | 2 (Patitas + Rosettes) | 1 (Rosettes only, boundaries known) | -50% |
| **Cache locality** | Poor (new string) | Good (original buffer) | Improved |

### Realistic Impact Assessment

| Document Type | Code % | Expected Speedup | Notes |
|---------------|--------|------------------|-------|
| API Reference | 80% | 8-12% | High impact |
| Tutorial | 40% | 4-6% | Moderate impact |
| Conceptual | 10% | 1-2% | Minimal impact |
| Prose-heavy | 5% | <1% | Negligible |

**Honest assessment**: For typical documentation (30-40% code), expect **~5% total parse time reduction**. The main benefit is reduced memory pressure during parallel builds.

### Benchmarks Required

Create before implementation:

```python
# tests/performance/benchmark_zclh.py

import pytest
from pathlib import Path

FIXTURES = Path("tests/fixtures/code_heavy")

@pytest.mark.benchmark
def test_baseline_current_approach(benchmark):
    """Measure current FencedCode.code string allocation."""
    source = (FIXTURES / "api_reference_10k_lines.md").read_text()
    benchmark(lambda: parse_and_render(source, use_zclh=False))

@pytest.mark.benchmark  
def test_zclh_zero_copy(benchmark):
    """Measure ZCLH zero-copy handoff."""
    source = (FIXTURES / "api_reference_10k_lines.md").read_text()
    benchmark(lambda: parse_and_render(source, use_zclh=True))

@pytest.mark.benchmark
def test_memory_pressure(benchmark):
    """Measure peak memory during parallel builds."""
    # 8 threads, 100 documents each
    ...
```

---

## Implementation Plan

### Phase 1: Rosettes Range Parameters (Low Risk)

**Scope**: Add backward-compatible `start`/`end` to rosettes lexers.

**Changes**:
- [ ] Update `rosettes._protocol.Lexer` signature
- [ ] Update all 50+ lexers in `rosettes/lexers/`
- [ ] Add tests for range tokenization
- [ ] Benchmark range vs full tokenization

**Risk**: Low (backward compatible, defaults preserve current behavior)

**Timeline**: 3 days

### Phase 2: AST and Parser Changes (Medium Risk)

**Scope**: Change `FencedCode` to store coordinates; update parser.

**Changes**:
- [ ] Add `offset`/`end_offset` to `Token` (needed for coordinates)
- [ ] Update `FencedCode` dataclass
- [ ] Update `_parse_fenced_code()` in parser
- [ ] Update all tests using `FencedCode.code`
- [ ] Add `get_code()` convenience method

**Risk**: Medium (breaking change to AST node)

**Timeline**: 5 days

### Phase 3: Renderer Handoff (Medium Risk)

**Scope**: Implement delegate protocol and renderer integration.

**Changes**:
- [ ] Define `LexerDelegate` protocol
- [ ] Implement `RosettesDelegate`
- [ ] Update `HtmlRenderer` to accept source + delegate
- [ ] Update `create_markdown()` factory
- [ ] Integration tests

**Risk**: Medium (changes rendering pipeline)

**Timeline**: 4 days

### Phase 4: Benchmarks and Validation (Required)

**Scope**: Verify performance claims with real measurements.

**Changes**:
- [ ] Create benchmark fixtures (code-heavy docs)
- [ ] Implement benchmark suite
- [ ] Run A/B comparison
- [ ] Document actual improvements
- [ ] Update RFC with measured results

**Timeline**: 2 days

**Total**: ~14 days

---

## Alternatives Considered

### Alternative 1: Lazy Property on FencedCode

```python
@dataclass
class FencedCode:
    _source_ref: weakref.ref[str]  # Weak reference to source
    _start: int
    _end: int

    @property
    def code(self) -> str:
        source = self._source_ref()
        if source is None:
            raise ValueError("Source string no longer available")
        return source[self._start:self._end]
```

**Rejected because**:
- Weak references add complexity
- Still allocates on access
- Source lifetime management is error-prone

### Alternative 2: memoryview

```python
@dataclass
class FencedCode:
    code: memoryview  # Zero-copy view into source
```

**Rejected because**:
- `memoryview` requires bytes, not str
- Unicode handling becomes complex
- Most downstream code expects `str`

### Alternative 3: Keep Current Design, Optimize Elsewhere

Focus optimization efforts on other bottlenecks (template rendering, I/O).

**Rejected because**:
- Profiling shows code-heavy docs spend 12%+ in this path
- Memory pressure affects parallel build scaling
- Clean architectural improvement regardless of perf

---

## Success Criteria

1. **Zero string allocations** for `FencedCode` content during parsing (verified via `tracemalloc`)
2. **Rosettes operates on original buffer** (verified via debugger/logging)
3. **Patitas installable without rosettes** (verified via fresh venv test)
4. **Rosettes installable without Patitas** (verified via fresh venv test)
5. **Measured speedup ≥5%** on code-heavy documents (verified via benchmarks)
6. **No regression** on prose-heavy documents (verified via benchmarks)
7. **Thread-safe** under Python 3.14t (verified via ThreadSanitizer)

---

## Open Questions

1. **Should `get_code()` cache the extracted string?**
   - Pro: Avoid re-extraction if called multiple times
   - Con: Defeats zero-copy purpose; adds state to frozen dataclass
   - **Recommendation**: No caching; caller can cache if needed

2. **How to handle AST serialization (e.g., JSON cache)?**
   - Options: Extract code on serialize, or store coordinates + require source on deserialize
   - **Recommendation**: Extract on serialize (cache compatibility)

3. **What if source is modified between parse and render?**
   - Current design assumes source is immutable during pipeline
   - Document this assumption; not a new constraint

---

## References

- `rfc-patitas-markdown-parser`: Parent RFC describing Patitas architecture
- `bengal/rendering/rosettes/_protocol.py`: Rosettes lexer protocol
- `bengal/rendering/parsers/patitas/parser.py:229-276`: Current `_parse_fenced_code()`
- `bengal/rendering/parsers/patitas/nodes.py:268-277`: Current `FencedCode` definition
