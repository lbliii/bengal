# RFC: Hand-Written State Machine Lexers

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-0006 |
| **Title** | Hand-Written State Machine Lexers for Rosettes |
| **Status** | Draft |
| **Created** | 2025-12-25 |
| **Author** | Bengal Core Team |
| **Depends On** | RFC-0002 (Rosettes Syntax Highlighter) |
| **Supersedes** | RFC-0004 (ReDoS Prevention), RFC-0005 (DFA Lexers) |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Replace regex-based lexers with hand-written character-by-character state machines |
| **Why** | Fastest possible execution, zero ReDoS risk, trivial parallelization |
| **Effort** | ~1 week (AI-assisted generation of 50+ lexers) |
| **Risk** | Low — simpler architecture, no compilation machinery |
| **Constraints** | Must remain pure Python; must be backwards-compatible API |

**Key Insight**: With AI-assisted development, "tedious to write" is no longer a constraint. We can choose the fastest, simplest approach without compromise.

**Key Deliverables:**
1. Base `StateMachineLexer` class with O(n) guaranteed runtime
2. AI-generated lexers for all 50+ supported languages
3. Parallel tokenization for large files (3.14t)
4. Backwards-compatible `PatternLexer` API layer

---

## Motivation

### Why Not DFA Compilation?

RFC-0005 proposed compiling regex patterns to DFA. This requires:

| Component | Complexity | Purpose |
|-----------|------------|---------|
| Regex parser | Medium | Parse pattern strings |
| Thompson NFA builder | Medium | Convert AST to NFA |
| Subset construction | High | Convert NFA to DFA |
| DFA minimization | High | Reduce state count |
| Table generation | Medium | Pack for runtime |

**Total: ~1000+ lines of infrastructure** to avoid writing lexers by hand.

### The Insight: AI Changes the Calculus

| Era | Constraint | Solution |
|-----|------------|----------|
| Pre-AI | Human effort is expensive | Use regex, accept ReDoS risk |
| Pre-AI | Hand-writing is tedious | Build DFA compiler to generate |
| **Post-AI** | AI writes code | Hand-write optimal lexers directly |

**Result**: We can skip all the DFA machinery and just write the fastest possible code.

### Performance Comparison

| Approach | Compile Time | Runtime | Memory | ReDoS Risk |
|----------|-------------|---------|--------|------------|
| Backtracking regex | None | O(2ⁿ) worst | Low | ✅ Yes |
| DFA compilation | O(2^m) states | O(n) | Medium | ❌ No |
| **Hand-written** | None | O(n) optimal | Minimal | ❌ No |

Hand-written state machines are faster than DFA because:
1. **No abstraction overhead** — direct character matching
2. **No table lookups** — inline branching
3. **Perfect cache behavior** — sequential access
4. **Language-specific optimizations** — human/AI knowledge baked in

---

## Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    StateMachineLexer                             │
│  - Character-by-character iteration                              │
│  - Explicit state tracking                                       │
│  - No regex, no backtracking                                     │
│  - O(n) guaranteed                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Language-Specific Lexers                      │
│  - PythonLexer, JavaScriptLexer, RustLexer, etc.                │
│  - Hand-written by AI                                            │
│  - Optimized for each language's syntax                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Parallel Tokenization (3.14t)                 │
│  - Split at safe boundaries                                      │
│  - Tokenize chunks in parallel                                   │
│  - True parallelism on free-threaded Python                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Base Lexer Implementation

```python
# rosettes/lexers/_state_machine.py

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from bengal.rendering.rosettes._types import Token, TokenType

if TYPE_CHECKING:
    pass

__all__ = ["StateMachineLexer"]


class StateMachineLexer:
    """Base class for hand-written state machine lexers.

    Thread-safe: tokenize() uses only local variables.
    O(n) guaranteed: single pass, no backtracking.

    Subclasses implement language-specific tokenization by overriding
    the tokenize() method with character-by-character logic.

    Design Principles:
        1. No regex — character matching only
        2. Explicit state — no hidden backtracking
        3. Local variables only — thread-safe by design
        4. Single pass — O(n) guaranteed
    """

    name: str = "base"
    aliases: tuple[str, ...] = ()
    filenames: tuple[str, ...] = ()
    mimetypes: tuple[str, ...] = ()

    # Shared character class sets (frozen for thread safety)
    DIGITS: frozenset[str] = frozenset("0123456789")
    HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdefABCDEF")
    OCTAL_DIGITS: frozenset[str] = frozenset("01234567")
    BINARY_DIGITS: frozenset[str] = frozenset("01")
    LETTERS: frozenset[str] = frozenset(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )
    IDENT_START: frozenset[str] = frozenset(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
    )
    IDENT_CONT: frozenset[str] = frozenset(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789"
    )
    WHITESPACE: frozenset[str] = frozenset(" \t\n\r\f\v")

    def tokenize(self, code: str) -> Iterator[Token]:
        """Tokenize source code.

        Subclasses override this with language-specific logic.

        Args:
            code: The source code to tokenize.

        Yields:
            Token objects in order of appearance.
        """
        raise NotImplementedError("Subclasses must implement tokenize()")

    def tokenize_fast(self, code: str) -> Iterator[tuple[TokenType, str]]:
        """Fast tokenization without position tracking.

        Default implementation strips position info from tokenize().
        Subclasses may override for further optimization.

        Args:
            code: The source code to tokenize.

        Yields:
            (TokenType, value) tuples.
        """
        for token in self.tokenize(code):
            yield (token.type, token.value)


# Helper functions for common patterns

def scan_while(code: str, pos: int, char_set: frozenset[str]) -> int:
    """Advance position while characters are in char_set.

    Returns the new position (may be unchanged if no match).
    """
    length = len(code)
    while pos < length and code[pos] in char_set:
        pos += 1
    return pos


def scan_until(code: str, pos: int, char_set: frozenset[str]) -> int:
    """Advance position until a character in char_set is found.

    Returns the new position (may be end of string).
    """
    length = len(code)
    while pos < length and code[pos] not in char_set:
        pos += 1
    return pos


def scan_string(
    code: str,
    pos: int,
    quote: str,
    *,
    allow_escape: bool = True,
    allow_multiline: bool = False,
) -> int:
    """Scan a string literal, handling escapes.

    Args:
        code: Source code.
        pos: Position after opening quote.
        quote: The quote character (' or ").
        allow_escape: Whether backslash escapes are allowed.
        allow_multiline: Whether newlines are allowed.

    Returns:
        Position after closing quote (or end of string/line if unterminated).
    """
    length = len(code)

    while pos < length:
        char = code[pos]

        if char == quote:
            return pos + 1  # Include closing quote

        if char == '\\' and allow_escape and pos + 1 < length:
            pos += 2  # Skip escape sequence
            continue

        if char == '\n' and not allow_multiline:
            return pos  # Unterminated string

        pos += 1

    return pos  # End of input (unterminated)


def scan_triple_string(code: str, pos: int, quote: str) -> int:
    """Scan a triple-quoted string.

    Args:
        code: Source code.
        pos: Position after opening triple quote.
        quote: The quote character (' or ").

    Returns:
        Position after closing triple quote (or end of input).
    """
    length = len(code)
    triple = quote * 3

    while pos < length:
        if code[pos:pos + 3] == triple:
            return pos + 3

        if code[pos] == '\\' and pos + 1 < length:
            pos += 2  # Skip escape
            continue

        pos += 1

    return pos  # End of input (unterminated)
```

---

## Python Lexer Prototype

```python
# rosettes/lexers/python_sm.py

"""Hand-written Python lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._state_machine import (
    StateMachineLexer,
    scan_while,
    scan_string,
    scan_triple_string,
)

__all__ = ["PythonStateMachineLexer"]


# Keyword lookup table (frozen for thread safety)
_KEYWORDS: frozenset[str] = frozenset({
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
})

_KEYWORD_CONSTANTS: frozenset[str] = frozenset({"True", "False", "None"})
_KEYWORD_DECLARATIONS: frozenset[str] = frozenset({"def", "class", "lambda"})
_KEYWORD_NAMESPACE: frozenset[str] = frozenset({"import", "from"})

_BUILTINS: frozenset[str] = frozenset({
    "abs", "aiter", "all", "anext", "any", "ascii", "bin", "bool",
    "breakpoint", "bytearray", "bytes", "callable", "chr", "classmethod",
    "compile", "complex", "delattr", "dict", "dir", "divmod", "enumerate",
    "eval", "exec", "filter", "float", "format", "frozenset", "getattr",
    "globals", "hasattr", "hash", "help", "hex", "id", "input", "int",
    "isinstance", "issubclass", "iter", "len", "list", "locals", "map",
    "max", "memoryview", "min", "next", "object", "oct", "open", "ord",
    "pow", "print", "property", "range", "repr", "reversed", "round",
    "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum",
    "super", "tuple", "type", "vars", "zip", "__import__",
})

_PSEUDO_BUILTINS: frozenset[str] = frozenset({
    "self", "cls", "__name__", "__doc__", "__package__", "__loader__",
    "__spec__", "__path__", "__file__", "__cached__", "__builtins__",
})

_EXCEPTIONS: frozenset[str] = frozenset({
    "ArithmeticError", "AssertionError", "AttributeError", "BaseException",
    "BlockingIOError", "BrokenPipeError", "BufferError", "BytesWarning",
    "ChildProcessError", "ConnectionAbortedError", "ConnectionError",
    "ConnectionRefusedError", "ConnectionResetError", "DeprecationWarning",
    "EOFError", "EnvironmentError", "Exception", "FileExistsError",
    "FileNotFoundError", "FloatingPointError", "FutureWarning",
    "GeneratorExit", "IOError", "ImportError", "ImportWarning",
    "IndentationError", "IndexError", "InterruptedError",
    "IsADirectoryError", "KeyError", "KeyboardInterrupt", "LookupError",
    "MemoryError", "ModuleNotFoundError", "NameError", "NotADirectoryError",
    "NotImplemented", "NotImplementedError", "OSError", "OverflowError",
    "PendingDeprecationWarning", "PermissionError", "ProcessLookupError",
    "RecursionError", "ReferenceError", "ResourceWarning", "RuntimeError",
    "RuntimeWarning", "StopAsyncIteration", "StopIteration", "SyntaxError",
    "SyntaxWarning", "SystemError", "SystemExit", "TabError", "TimeoutError",
    "TypeError", "UnboundLocalError", "UnicodeDecodeError",
    "UnicodeEncodeError", "UnicodeError", "UnicodeTranslateError",
    "UnicodeWarning", "UserWarning", "ValueError", "Warning",
    "ZeroDivisionError",
})

# String prefix characters
_STRING_PREFIXES: frozenset[str] = frozenset("fFrRbBuU")


class PythonStateMachineLexer(StateMachineLexer):
    """Hand-written Python 3 lexer.

    O(n) guaranteed, zero regex, thread-safe.
    Handles all Python 3.x syntax including f-strings, type hints, walrus operator.
    """

    name = "python"
    aliases = ("py", "python3", "py3")
    filenames = ("*.py", "*.pyw", "*.pyi")
    mimetypes = ("text/x-python", "application/x-python")

    def tokenize(self, code: str) -> Iterator[Token]:
        """Tokenize Python source code.

        Single-pass, character-by-character. O(n) guaranteed.
        """
        pos = 0
        length = len(code)
        line = 1
        line_start = 0

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace
            if char in self.WHITESPACE:
                start = pos
                while pos < length and code[pos] in self.WHITESPACE:
                    if code[pos] == '\n':
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], line, col)
                continue

            # Comments
            if char == '#':
                start = pos
                while pos < length and code[pos] != '\n':
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                continue

            # String literals (including prefixed)
            if char in _STRING_PREFIXES or char in '"\'':
                start = pos
                token_type, new_pos = self._scan_string_literal(code, pos)

                # Track newlines in multi-line strings
                value = code[start:new_pos]
                newlines = value.count('\n')
                if newlines:
                    line += newlines
                    line_start = start + value.rfind('\n') + 1

                yield Token(token_type, value, line - newlines, col)
                pos = new_pos
                continue

            # Numbers
            if char in self.DIGITS or (char == '.' and pos + 1 < length and code[pos + 1] in self.DIGITS):
                start = pos
                token_type, new_pos = self._scan_number(code, pos)
                yield Token(token_type, code[start:new_pos], line, col)
                pos = new_pos
                continue

            # Identifiers, keywords, builtins
            if char in self.IDENT_START:
                start = pos
                pos = scan_while(code, pos, self.IDENT_CONT)
                word = code[start:pos]
                token_type = self._classify_word(word)
                yield Token(token_type, word, line, col)
                continue

            # Decorators
            if char == '@':
                start = pos
                pos += 1
                if pos < length and code[pos] in self.IDENT_START:
                    pos = scan_while(code, pos, self.IDENT_CONT)
                    # Handle dotted decorators
                    while pos < length and code[pos] == '.':
                        pos += 1
                        pos = scan_while(code, pos, self.IDENT_CONT)
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Multi-character operators
            if pos + 1 < length:
                two_char = code[pos:pos + 2]

                if two_char == ':=':  # Walrus
                    yield Token(TokenType.OPERATOR, two_char, line, col)
                    pos += 2
                    continue

                if two_char == '->':  # Return type hint
                    yield Token(TokenType.OPERATOR, two_char, line, col)
                    pos += 2
                    continue

                if two_char in ('==', '!=', '<=', '>=', '**', '//', '<<', '>>', '+=', '-=', '*=', '/=', '%=', '@=', '&=', '|=', '^='):
                    # Check for 3-char operators
                    if pos + 2 < length:
                        three_char = code[pos:pos + 3]
                        if three_char in ('**=', '//=', '>>=', '<<='):
                            yield Token(TokenType.OPERATOR, three_char, line, col)
                            pos += 3
                            continue

                    yield Token(TokenType.OPERATOR, two_char, line, col)
                    pos += 2
                    continue

            # Single-character operators
            if char in '+-*/%@&|^~<>=!':
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Punctuation
            if char in '()[]{}:;.,':
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            # Unknown character — skip
            pos += 1

    def _scan_string_literal(
        self,
        code: str,
        pos: int,
    ) -> tuple[TokenType, int]:
        """Scan a string literal with optional prefix.

        Returns (token_type, end_position).
        """
        start = pos

        # Handle string prefixes (f, r, b, u, combinations)
        prefix = ""
        while pos < len(code) and code[pos] in _STRING_PREFIXES:
            prefix += code[pos]
            pos += 1

        if pos >= len(code) or code[pos] not in '"\'':
            # Not actually a string, backtrack
            return TokenType.NAME, start + 1

        quote = code[pos]
        pos += 1

        # Check for triple quote
        if pos + 1 < len(code) and code[pos:pos + 2] == quote * 2:
            pos += 2  # Skip the other two quotes
            pos = scan_triple_string(code, pos, quote)
            return TokenType.STRING_DOC, pos

        # Single-quoted string
        pos = scan_string(code, pos, quote, allow_escape=True, allow_multiline=False)
        return TokenType.STRING, pos

    def _scan_number(self, code: str, pos: int) -> tuple[TokenType, int]:
        """Scan a numeric literal.

        Returns (token_type, end_position).
        """
        length = len(code)
        start = pos

        # Leading dot (e.g., .5)
        if code[pos] == '.':
            pos += 1
            pos = self._scan_digits_with_underscore(code, pos)
            pos = self._scan_exponent(code, pos)
            return TokenType.NUMBER_FLOAT, pos

        # 0x, 0o, 0b prefixes
        if code[pos] == '0' and pos + 1 < length:
            next_char = code[pos + 1]

            if next_char in 'xX':
                pos += 2
                pos = self._scan_hex_digits(code, pos)
                return TokenType.NUMBER_HEX, pos

            if next_char in 'oO':
                pos += 2
                pos = self._scan_octal_digits(code, pos)
                return TokenType.NUMBER_OCT, pos

            if next_char in 'bB':
                pos += 2
                pos = self._scan_binary_digits(code, pos)
                return TokenType.NUMBER_BIN, pos

        # Decimal integer or float
        pos = self._scan_digits_with_underscore(code, pos)

        # Decimal point
        if pos < length and code[pos] == '.':
            pos += 1
            pos = self._scan_digits_with_underscore(code, pos)
            pos = self._scan_exponent(code, pos)
            return TokenType.NUMBER_FLOAT, pos

        # Exponent without decimal point
        if pos < length and code[pos] in 'eE':
            pos = self._scan_exponent(code, pos)
            return TokenType.NUMBER_FLOAT, pos

        return TokenType.NUMBER_INTEGER, pos

    def _scan_digits_with_underscore(self, code: str, pos: int) -> int:
        """Scan digits with optional underscores."""
        length = len(code)
        while pos < length and (code[pos] in self.DIGITS or code[pos] == '_'):
            pos += 1
        return pos

    def _scan_hex_digits(self, code: str, pos: int) -> int:
        """Scan hex digits with optional underscores."""
        length = len(code)
        while pos < length and (code[pos] in self.HEX_DIGITS or code[pos] == '_'):
            pos += 1
        return pos

    def _scan_octal_digits(self, code: str, pos: int) -> int:
        """Scan octal digits with optional underscores."""
        length = len(code)
        while pos < length and (code[pos] in self.OCTAL_DIGITS or code[pos] == '_'):
            pos += 1
        return pos

    def _scan_binary_digits(self, code: str, pos: int) -> int:
        """Scan binary digits with optional underscores."""
        length = len(code)
        while pos < length and (code[pos] in self.BINARY_DIGITS or code[pos] == '_'):
            pos += 1
        return pos

    def _scan_exponent(self, code: str, pos: int) -> int:
        """Scan optional exponent part of number."""
        if pos >= len(code) or code[pos] not in 'eE':
            return pos

        pos += 1

        if pos < len(code) and code[pos] in '+-':
            pos += 1

        return self._scan_digits_with_underscore(code, pos)

    def _classify_word(self, word: str) -> TokenType:
        """Classify an identifier into the appropriate token type."""
        if word in _KEYWORDS:
            if word in _KEYWORD_CONSTANTS:
                return TokenType.KEYWORD_CONSTANT
            if word in _KEYWORD_DECLARATIONS:
                return TokenType.KEYWORD_DECLARATION
            if word in _KEYWORD_NAMESPACE:
                return TokenType.KEYWORD_NAMESPACE
            return TokenType.KEYWORD

        if word in _BUILTINS:
            return TokenType.NAME_BUILTIN

        if word in _PSEUDO_BUILTINS:
            return TokenType.NAME_BUILTIN_PSEUDO

        if word in _EXCEPTIONS:
            return TokenType.NAME_EXCEPTION

        return TokenType.NAME
```

---

## Parallel Tokenization (3.14t)

```python
# rosettes/_parallel.py

"""Parallel tokenization for free-threaded Python (3.14t+)."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator

from bengal.rendering.rosettes._types import Token

if TYPE_CHECKING:
    from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["tokenize_parallel", "is_free_threaded"]


def is_free_threaded() -> bool:
    """Check if running on free-threaded Python (3.14t+)."""
    if hasattr(sys, '_is_gil_enabled'):
        return not sys._is_gil_enabled()
    return False


@dataclass(frozen=True, slots=True)
class _Chunk:
    """A chunk of source code with position metadata."""
    text: str
    start_offset: int
    start_line: int


def _find_safe_splits(code: str, target_chunk_size: int) -> list[int]:
    """Find safe split points (newlines) for parallel tokenization."""
    splits: list[int] = []
    pos = target_chunk_size

    while pos < len(code):
        # Find nearest newline before or at target
        newline_pos = code.rfind('\n', max(0, pos - target_chunk_size // 2), pos)

        if newline_pos == -1:
            newline_pos = code.find('\n', pos)
            if newline_pos == -1:
                break

        split_pos = newline_pos + 1  # Split after newline

        if split_pos > (splits[-1] if splits else 0):
            splits.append(split_pos)

        pos = split_pos + target_chunk_size

    return splits


def _make_chunks(code: str, splits: list[int]) -> list[_Chunk]:
    """Split code into chunks at the given positions."""
    chunks: list[_Chunk] = []
    prev = 0
    line = 1

    for split_pos in splits:
        chunk_text = code[prev:split_pos]
        chunks.append(_Chunk(
            text=chunk_text,
            start_offset=prev,
            start_line=line,
        ))
        line += chunk_text.count('\n')
        prev = split_pos

    # Final chunk
    if prev < len(code):
        chunks.append(_Chunk(
            text=code[prev:],
            start_offset=prev,
            start_line=line,
        ))

    return chunks


def tokenize_parallel(
    lexer: StateMachineLexer,
    code: str,
    *,
    chunk_size: int = 64_000,
    max_workers: int | None = None,
) -> Iterator[Token]:
    """Parallel tokenization for large files.

    Only beneficial on free-threaded Python (3.14t+).
    Falls back to sequential on GIL Python.

    Args:
        lexer: The lexer to use.
        code: Source code to tokenize.
        chunk_size: Target chunk size in characters.
        max_workers: Maximum threads. None = CPU count.

    Yields:
        Tokens in order of appearance.
    """
    # Small files or GIL Python: sequential
    if len(code) < chunk_size * 2 or not is_free_threaded():
        yield from lexer.tokenize(code)
        return

    # Split at newlines
    splits = _find_safe_splits(code, chunk_size)

    if not splits:
        yield from lexer.tokenize(code)
        return

    chunks = _make_chunks(code, splits)

    def process_chunk(chunk: _Chunk) -> list[Token]:
        tokens = list(lexer.tokenize(chunk.text))
        # Adjust line numbers
        if chunk.start_line > 1:
            return [
                Token(
                    type=t.type,
                    value=t.value,
                    line=t.line + chunk.start_line - 1,
                    column=t.column,
                )
                for t in tokens
            ]
        return tokens

    # Tokenize in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_chunk, chunks))

    # Yield in order
    for chunk_tokens in results:
        yield from chunk_tokens
```

---

## Backwards Compatibility Layer

```python
# rosettes/lexers/_base.py (updated)

class PatternLexer(StateMachineLexer):
    """Backwards-compatible wrapper.

    Existing regex-based lexers continue to work.
    New lexers should extend StateMachineLexer directly.
    """

    # Existing rules-based implementation for backwards compat
    rules: tuple[Rule, ...] = ()

    # ... existing PatternLexer implementation ...
```

---

## Lexer Generation Strategy

### AI Generation Workflow

1. **Provide language specification** to AI:
   - Token types needed
   - Keyword lists
   - String/comment syntax
   - Number formats
   - Operator precedence (for grouping)

2. **AI generates lexer** following the pattern:
   - Extend `StateMachineLexer`
   - Implement `tokenize()` with character iteration
   - Use helper functions (`scan_while`, `scan_string`, etc.)

3. **Validate output**:
   - Run against test corpus
   - Compare tokens to Pygments reference
   - Benchmark performance

### Example Generation Prompt

```markdown
Generate a hand-written state machine lexer for [LANGUAGE] following
the PythonStateMachineLexer pattern in rosettes.

Language specification:
- Keywords: [list]
- String delimiters: [list]
- Comment syntax: [description]
- Number formats: [description]
- Operators: [list]

Requirements:
- Extend StateMachineLexer
- Single-pass O(n) tokenization
- Use frozenset for keyword/builtin lookups
- Thread-safe (no instance state mutation)
- Match TokenType values from rosettes._types
```

---

## Migration Plan

### Week 1: Core Infrastructure + Python Prototype

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Implement `StateMachineLexer` base | `_state_machine.py` |
| 1 | Implement helper functions | `scan_while`, `scan_string`, etc. |
| 2-3 | Hand-write Python lexer | `python_sm.py` |
| 4 | Unit tests for Python lexer | `tests/lexers/test_python_sm.py` |
| 5 | Benchmark vs regex lexer | Performance report |

### Week 2: Generate All Lexers

| Day | Task | Languages |
|-----|------|-----------|
| 1 | Core languages | JavaScript, TypeScript, JSON, HTML, CSS |
| 2 | Systems languages | C, C++, Rust, Go, Zig |
| 3 | JVM languages | Java, Kotlin, Scala, Groovy |
| 4 | Scripting languages | Ruby, Perl, Lua, PHP, Bash |
| 5 | Other languages | All remaining (~20) |

### Week 3: Validation + Polish

| Task | Priority |
|------|----------|
| Run all lexers against test corpus | P0 |
| Compare tokens to current regex lexers | P0 |
| Fix discrepancies | P0 |
| Add parallel tokenization | P1 |
| Update documentation | P1 |
| Deprecate old regex lexers | P2 |

---

## Performance Expectations

### Tokenization Speed

| Input Size | Regex Lexer | State Machine | Improvement |
|------------|-------------|---------------|-------------|
| 1 KB | ~0.5 ms | ~0.3 ms | 1.7x |
| 10 KB | ~5 ms | ~2.5 ms | 2x |
| 100 KB | ~50 ms | ~20 ms | 2.5x |
| 1 MB | ~500 ms | ~150 ms | 3.3x |

### Parallel Tokenization (3.14t, 4 cores)

| Input Size | Sequential | Parallel | Improvement |
|------------|------------|----------|-------------|
| 100 KB | ~20 ms | ~8 ms | 2.5x |
| 1 MB | ~150 ms | ~50 ms | 3x |
| 10 MB | ~1.5 s | ~400 ms | 3.75x |

### Memory Usage

| Component | Regex Lexer | State Machine |
|-----------|-------------|---------------|
| Compiled patterns | ~50 KB/lexer | 0 |
| Keyword sets | ~5 KB | ~5 KB (frozen) |
| Runtime overhead | Medium | Minimal |

---

## Success Criteria

- [ ] All 50+ lexers converted to state machine
- [ ] Tokens match current regex lexers (validated by diff test)
- [ ] 2x+ speedup on typical inputs
- [ ] Parallel tokenization shows speedup on 3.14t
- [ ] Zero ReDoS vulnerability by construction
- [ ] API backwards-compatible

---

## Appendix: Why This Is Better

### vs RFC-0004 (ReDoS Prevention)

| Aspect | RFC-0004 | RFC-0006 |
|--------|----------|----------|
| Approach | Mitigate regex vulnerabilities | Eliminate regex entirely |
| Guarantee | Heuristic + timeout | O(n) by construction |
| Maintenance | Must validate every pattern | No patterns to validate |

### vs RFC-0005 (DFA Lexers)

| Aspect | RFC-0005 | RFC-0006 |
|--------|----------|----------|
| Infrastructure | ~1000 lines DFA machinery | ~100 lines base class |
| Compile time | O(2^m) for DFA construction | None |
| Runtime | O(n) via table lookup | O(n) via inline code |
| Optimization | Generic | Language-specific |

### The Meta-Insight

Traditional software engineering optimizes for *human effort*:
- Regex: Easy to write, hard to optimize
- DFA compiler: Hard to write once, generates optimal code

AI-assisted development optimizes for *output quality*:
- Hand-written state machines: Hard to write, optimal performance
- AI writes the "hard" part, we get optimal results

**This RFC embraces the new paradigm.**
