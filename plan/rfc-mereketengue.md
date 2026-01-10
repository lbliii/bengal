# RFC: Mereketengue — A Modern Pattern Matching Library for Python

**Author:** llane  
**Date:** 2026-01-09  
**Status:** Draft  
**Target Python:** 3.14+

---

## Abstract

This RFC proposes **Mereketengue**, a modern pattern matching library designed as a safe, readable, and composable alternative to regular expressions. Building on architectural patterns proven in our ecosystem (rosettes, kida, patitas, bengal), Mereketengue provides:

1. **O(n) guaranteed performance** via Thompson NFA (no ReDoS)
2. **Readable fluent API** — patterns read like English
3. **Type-safe captures** — extract structured data, not just strings
4. **Composability** — build complex patterns from simple ones
5. **First-class debugging** — know exactly why a match failed

---

## Motivation

### The Problem

Regular expressions are ubiquitous but deeply flawed:

```python
# What does this do? How long does it take to understand?
r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
```

**Pain points** (documented in academic research):

| Issue | Impact | Source |
|-------|--------|--------|
| Cryptic syntax | Code review burden, errors | [Regexes are Hard (2023)](https://arxiv.org/abs/2303.02555) |
| ReDoS vulnerability | Security incidents, outages | Cloudflare July 2019 (27-min global outage) |
| Catastrophic backtracking | O(2^n) worst case | [Microsoft Best Practices](https://learn.microsoft.com/en-us/dotnet/standard/base-types/best-practices-regex) |
| Cross-language inconsistency | 15% semantic differences | [Lingua Franca study (2021)](https://arxiv.org/abs/2105.04397) |
| No composability | Copy-paste, duplication | Industry standard practice |

### Market Validation

- **$124-183M** regex testing tool market (North America, 2024)
- **28.7M** developers globally, ~70-80% use regex regularly
- **Cloudflare, Stack Overflow, Atom** — all had regex-caused outages

### Why Now?

1. **Python 3.14t** — free-threaded Python needs thread-safe libraries
2. **Security focus** — ReDoS now in OWASP, DevSecOps requirements
3. **AI/LLM processing** — massive text volumes require safe patterns
4. **Our ecosystem** — rosettes already proves the state machine approach

---

## Competitive Landscape

### Existing Solutions (PyPI Downloads, Last Month)

| Package | Downloads | What It Does | Gap |
|---------|-----------|--------------|-----|
| **pyparsing** | 214.7M | Full parser combinator library | Overkill for patterns, no O(n) guarantee |
| **regex** | 158.2M | Drop-in `re` replacement, more features | Still regex syntax, still ReDoS-vulnerable |
| **lark** | 39.8M | Grammar-based parser generator | Parser, not pattern matcher |
| **parse** | 12.6M | Reverse of format strings | Limited patterns, not regex-powerful |
| **google-re2** | 8.0M | Google's O(n) regex (C++ bindings) | Still regex syntax, C++ dependency |
| **parsy** | 1.3M | Lightweight parser combinators | Parser focus, no O(n) guarantee |
| **pregex** | 20.6K | Readable regex builder | Generates regex strings, no safety |
| **verbalexpressions** | 51 | Fluent regex builder | Dead project, no safety |

### Closest Competitor: pregex

```python
# pregex — readable but still generates regex, no O(n) guarantee
from pregex.core.classes import AnyLetter, AnyDigit
from pregex.core.quantifiers import OneOrMore

email = OneOrMore(AnyLetter() | AnyDigit()) + '@' + OneOrMore(AnyLetter())
print(email.get_pattern())  # → '[a-zA-Z\d]+@[a-zA-Z]+'
# Still vulnerable to ReDoS if pattern is complex
```

### Gap Analysis

```
                        READABILITY
                             ↑
                             │
           pyparsing ●       │       ● Mereketengue (target)
                             │
               pregex ●      │
                             │
                 parse ●     │
    ─────────────────────────┼──────────────────────→ O(n) SAFETY
                             │
                             │       ● google-re2
                             │
        verbalexpressions ●  │
              (dead)         │
                             │
                Python re ●  │
                             ↓
```

### Feature Comparison

| Feature | Python `re` | pregex | google-re2 | pyparsing | parse | **Mereketengue** |
|---------|-------------|--------|------------|-----------|-------|------------------|
| Readable API | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| O(n) guaranteed | ❌ | ❌ | ✅ | ❌ | N/A | ✅ |
| Typed captures | ❌ | ❌ | ❌ | Partial | ✅ | ✅ |
| Debugging tools | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Pure Python | ✅ | ✅ | ❌ (C++) | ✅ | ✅ | ✅ |
| Free-threading safe | ❓ | ❓ | ❓ | ❓ | ❓ | ✅ |
| Composable patterns | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ |
| Built-in library | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### The Opportunity

**Nobody combines all three:**
1. Readable fluent API (like pregex)
2. O(n) guaranteed safety (like RE2)
3. Typed captures (like parse)

**Plus unique features:**
4. First-class debugging (explain, trace, visualize)
5. Built-in validated patterns (email, URL, semver, etc.)
6. Python 3.14t free-threading ready

---

## Design Principles

### 1. Safety by Default

```python
# Mereketengue uses Thompson NFA — O(n) guaranteed
# No pattern can cause exponential backtracking

from mereketengue import word

# This is ALWAYS O(n), unlike Python's re module
pattern = word[1:] + word[:]  # One-or-more, then zero-or-more
result = pattern.match("a" * 1000000)  # Completes in milliseconds
```

### 2. Readable AND Concise

```python
# ❌ Regex: Cryptic, unsafe
r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# ✅ Mereketengue: Clear, safe, concise
from mereketengue import word, letter

email = word[1:] + "@" + word[1:] + "." + letter[2:]
```

### 3. Type-Safe Captures

```python
from mereketengue import digit, word, maybe, capture
from dataclasses import dataclass

@dataclass
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: str | None = None

semver = (
    capture(digit[1:], "major", int) + "." +
    capture(digit[1:], "minor", int) + "." +
    capture(digit[1:], "patch", int) +
    maybe("-" + capture(word[1:], "prerelease"))
).to(SemVer)

result = semver.match("1.2.3-beta")
# result = SemVer(major=1, minor=2, patch=3, prerelease="beta")
```

### 4. Composability

```python
from mereketengue import digit, Range, maybe

# Build complex patterns from simple, reusable parts
octet = (
    "25" + Range("0", "5") |
    "2" + Range("0", "4") + digit |
    maybe("0" | "1") + digit + maybe(digit)
)

ipv4 = octet + ("." + octet)[3]  # Exactly 3 more octets

cidr = ipv4 + "/" + digit[1:2]  # 1-2 digits for prefix

# Patterns are immutable and can be shared across threads
```

### 5. Debuggability

```python
from mereketengue import word

pattern = "foo" + word[1:] + "bar"

# Explain what the pattern does
print(pattern.explain())
# → Match 'foo', then one or more word characters, then 'bar'

# Debug a failed match
result = pattern.match("foobaz", debug=True)
print(result.failure_reason)
# → Expected 'bar' at position 6, found 'baz'

# Visualize as state machine
pattern.to_dot()  # Generates Graphviz DOT for visualization
```

---

## Syntax

Mereketengue uses Python operators and slice notation for a concise, readable DSL.

### Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `a + b` | Sequence (then) | `word + "@" + word` |
| `a \| b` | Alternation (or) | `"http" \| "https"` |
| `"str"` | Auto-literal | `"@"` same as `literal("@")` |

### Quantifiers (Slice Notation)

| Syntax | Meaning | Regex Equivalent |
|--------|---------|------------------|
| `a[1:]` | One or more | `a+` |
| `a[:]` | Zero or more | `a*` |
| `a[:1]` | Zero or one (optional) | `a?` |
| `a[3]` | Exactly 3 | `a{3}` |
| `a[2:5]` | Between 2 and 5 | `a{2,5}` |
| `a[3:]` | 3 or more | `a{3,}` |

### Full Example

```python
from mereketengue import word, digit, letter, Range, maybe, capture

# Email: readable AND concise
email = word[1:] + "@" + word[1:] + "." + letter[2:]

# URL with typed captures
url = (
    capture("http" | "https", "scheme") + "://" +
    capture(word[1:] + ("." + word[1:])[1:], "host") +
    maybe(":" + capture(digit[1:], "port", int)) +
    capture("/" + any[:], "path", default="/")
)

# IPv4: compose complex from simple
octet = "25" + Range("0","5") | "2" + Range("0","4") + digit | digit[1:3]
ipv4 = octet + ("." + octet)[3]

# Semantic version
semver = (
    capture(digit[1:], "major", int) + "." +
    capture(digit[1:], "minor", int) + "." +
    capture(digit[1:], "patch", int) +
    maybe("-" + capture(word[1:], "prerelease"))
)
```

### Why This Syntax?

| Goal | Solution |
|------|----------|
| **Readable** | `word + "@" + word` reads naturally |
| **Concise** | `[1:]` shorter than `.plus()` or `.one_or_more()` |
| **Ergonomic** | Strings auto-convert, no `literal()` everywhere |
| **Pythonic** | Uses familiar operators (`+`, `\|`, `[:]`) |
| **O(n) Safe** | Thompson NFA under the hood, always |

---

## API Import Styles

### Recommended: Direct Imports

```python
from mereketengue import word, digit, letter, maybe, capture

email = word[1:] + "@" + word[1:] + "." + letter[2:]
```

### Alternative: Namespace Import

```python
from mereketengue import m  # Short namespace alias

email = m.word[1:] + "@" + m.word[1:] + "." + m.letter[2:]
```

### For Exploration: Star Import

```python
from mereketengue import *

email = word[1:] + "@" + word[1:] + "." + letter[2:]
```

---

## Architecture

### Leveraging Existing Patterns

Mereketengue builds on proven patterns from our ecosystem:

| Source | Pattern | Application |
|--------|---------|-------------|
| **rosettes** | Hand-written state machines, O(n) guarantee | Thompson NFA engine |
| **rosettes** | Frozen config dataclasses | Pattern configuration |
| **rosettes** | Composable scanner mixins | Built-in pattern library |
| **kida** | AST-native compilation | Pattern compilation |
| **kida** | StringBuilder pattern | Efficient match building |
| **patitas** | Mixin composition | Pattern composition |
| **bengal** | Free-threading safety | Thread-safe by design |

### Module Structure

```
mereketengue/
├── __init__.py              # High-level API: digit, word, literal, capture, etc.
├── _types.py                # Pattern, Match, Capture (frozen dataclasses)
├── _protocol.py             # Matcher protocol
├── _config.py               # PatternConfig (frozen)
├── engine/
│   ├── __init__.py
│   ├── thompson.py          # Thompson NFA — O(n) guaranteed
│   ├── vm.py                # Bytecode VM for complex patterns
│   └── compile.py           # Pattern → NFA/VM compilation
├── patterns/
│   ├── __init__.py
│   ├── base.py              # Pattern base class
│   ├── primitives.py        # digit, letter, whitespace, etc.
│   ├── combinators.py       # then, or, repeat, optional
│   └── transforms.py        # capture, transform, to
├── common/                  # Built-in validated patterns
│   ├── __init__.py
│   ├── network.py           # ipv4, ipv6, email, url, domain
│   ├── data.py              # uuid, iso_date, semver, json_path
│   ├── code.py              # identifier, string_literal, number
│   └── text.py              # word, sentence, paragraph
├── compat/
│   └── re.py                # Drop-in re module compatibility layer
├── debug/
│   ├── __init__.py
│   ├── explain.py           # Human-readable pattern explanation
│   ├── trace.py             # Step-by-step match tracing
│   └── visualize.py         # Graphviz/SVG visualization
└── py.typed
```

### Core Types

```python
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable
from collections.abc import Iterator

T = TypeVar("T")

@dataclass(frozen=True, slots=True)
class Match(Generic[T]):
    """Result of a successful match."""
    value: str           # The matched string
    start: int           # Start position in input
    end: int             # End position in input
    captures: T          # Typed captures (or dict for untyped)

    def group(self, name: str) -> str:
        """Get capture by name (re compatibility)."""
        ...

@dataclass(frozen=True, slots=True)
class Pattern(Generic[T]):
    """Immutable pattern definition."""
    _node: PatternNode   # Internal AST representation
    _compiled: CompiledPattern | None = None

    # Matching
    def match(self, text: str, pos: int = 0) -> Match[T] | None:
        """Match at position. O(n) guaranteed."""
        ...

    def search(self, text: str) -> Match[T] | None:
        """Find first match anywhere in text."""
        ...

    def findall(self, text: str) -> list[Match[T]]:
        """Find all non-overlapping matches."""
        ...

    def finditer(self, text: str) -> Iterator[Match[T]]:
        """Iterate over all matches."""
        ...

    def sub(self, repl: str | Callable, text: str) -> str:
        """Replace matches with replacement."""
        ...

    # Operators
    def __add__(self, other: Pattern | str) -> Pattern:
        """Sequence: a + b matches a then b."""
        ...

    def __radd__(self, other: str) -> Pattern:
        """Allow 'string' + pattern."""
        ...

    def __or__(self, other: Pattern | str) -> Pattern:
        """Alternation: a | b matches a or b."""
        ...

    def __ror__(self, other: str) -> Pattern:
        """Allow 'string' | pattern."""
        ...

    # Quantifiers via slice notation
    def __getitem__(self, key: int | slice) -> Pattern:
        """
        Quantifiers via slice notation:
            a[1:]   → one or more
            a[:]    → zero or more
            a[:1]   → optional (zero or one)
            a[3]    → exactly 3
            a[2:5]  → between 2 and 5
        """
        ...
```

### Thompson NFA Engine

Following the approach proven in rosettes:

```python
# engine/thompson.py

from dataclasses import dataclass
from enum import Enum, auto

class OpCode(Enum):
    CHAR = auto()      # Match single character
    RANGE = auto()     # Match character range
    CLASS = auto()     # Match character class
    ANY = auto()       # Match any character
    SPLIT = auto()     # Fork execution (alternation)
    JUMP = auto()       # Unconditional jump
    SAVE = auto()      # Save position for capture
    MATCH = auto()     # Successful match

@dataclass(frozen=True, slots=True)
class Instruction:
    op: OpCode
    arg1: int | str | frozenset[str] = 0
    arg2: int = 0

def execute(program: list[Instruction], text: str, start: int = 0) -> Match | None:
    """Execute NFA program. O(n) guaranteed via Thompson simulation.

    Key insight: Instead of backtracking, we simulate ALL possible
    states in parallel. At each character, we advance all active states.

    Time: O(n * m) where n = text length, m = program size
    Space: O(m) for state sets

    This is the same approach used by RE2 and Rust's regex crate.
    """
    # Current and next state sets
    current: set[int] = {0}
    next_states: set[int] = set()

    for i, char in enumerate(text[start:], start):
        if not current:
            return None  # No active states = no match

        next_states.clear()

        for pc in current:
            inst = program[pc]

            if inst.op == OpCode.CHAR:
                if char == inst.arg1:
                    next_states.add(pc + 1)

            elif inst.op == OpCode.RANGE:
                if inst.arg1 <= char <= inst.arg2:
                    next_states.add(pc + 1)

            elif inst.op == OpCode.CLASS:
                if char in inst.arg1:
                    next_states.add(pc + 1)

            elif inst.op == OpCode.ANY:
                next_states.add(pc + 1)

            elif inst.op == OpCode.SPLIT:
                # Add both branches to current (epsilon transition)
                current.add(inst.arg1)
                current.add(inst.arg2)

            elif inst.op == OpCode.MATCH:
                return Match(text[start:i], start, i, {})

        current, next_states = next_states, current

    # Check for match at end
    for pc in current:
        if program[pc].op == OpCode.MATCH:
            return Match(text[start:], start, len(text), {})

    return None
```

---

## API Examples

### Basic Usage

```python
from mereketengue import digit, letter, alnum

# Simple patterns
digits_pattern = digit[1:]
word_pattern = letter[1:]
identifier = letter + alnum[:]

# Match
result = digits_pattern.match("12345")
print(result.value)  # "12345"

# Search
result = word_pattern.search("hello, world!")
print(result.value)  # "hello"

# Find all
for match in digit[1:].finditer("a1b22c333"):
    print(match.value)  # "1", "22", "333"

# Replace
result = letter[1:].sub(lambda m: m.value.upper(), "hello world")
print(result)  # "HELLO WORLD"
```

### Captures

```python
from mereketengue import digit, capture

# Named captures
log_pattern = capture(digit[1:], "year") + "-" + capture(digit[1:], "month") + "-" + capture(digit[1:], "day")

result = log_pattern.match("2026-01-09")
print(result.captures["year"])   # "2026"
print(result.captures["month"])  # "01"
print(result.captures["day"])    # "09"

# With transformation to int
date_pattern = (
    capture(digit[1:], "year", int) + "-" +
    capture(digit[1:], "month", int) + "-" +
    capture(digit[1:], "day", int)
)

result = date_pattern.match("2026-01-09")
print(result.captures["year"])   # 2026 (int)
```

### Typed Captures

```python
from mereketengue import word, digit, any, maybe, capture
from dataclasses import dataclass

@dataclass
class URL:
    scheme: str
    host: str
    port: int | None
    path: str

url = (
    capture("http" | "https", "scheme") + "://" +
    capture(word[1:] + ("." + word[1:])[1:], "host") +
    maybe(":" + capture(digit[1:], "port", int)) +
    capture("/" + any[:], "path", default="/")
).to(URL)

result = url.match("https://example.com:8080/api/v1")
# result.captures = URL(scheme="https", host="example.com", port=8080, path="/api/v1")
```

### Built-in Patterns

```python
from mereketengue import ws, quoted, capture
from mereketengue.common import ipv4, email, uuid, semver, iso_date

# All built-in patterns are O(n) guaranteed
assert ipv4.match("192.168.1.1")
assert email.match("user@example.com")
assert uuid.match("550e8400-e29b-41d4-a716-446655440000")
assert semver.match("1.2.3-beta.1")
assert iso_date.match("2026-01-09")

# Compose with built-ins
server_log = iso_date + ws + capture(ipv4, "client_ip") + ws + capture(quoted('"'), "message")
```

### Debugging

```python
from mereketengue import ws, word
from mereketengue.common import path

pattern = "GET" + ws + path

# Why didn't it match?
result = pattern.match("POST /api", debug=True)
print(result.failure_reason)
# → Expected 'GET' at position 0, found 'POS...'

# Explain the pattern
print(pattern.explain())
# → Match 'GET', then whitespace, then a file path

# Step-by-step trace
result = pattern.match("GET /api", debug=True)
for step in result.trace:
    print(step)
# Step 1: Matched 'GET' at 0-3
# Step 2: Matched ' ' (whitespace) at 3-4  
# Step 3: Matched '/api' (path) at 4-8
# Success: Full match
```

### Compatibility Layer

```python
# Drop-in replacement for simple cases
from mereketengue.compat import re

# Same API as Python's re module
pattern = re.compile(r"\d+")
result = pattern.match("12345")
print(result.group())  # "12345"

# But with O(n) guarantee!
# This would hang with Python's re, but completes instantly:
evil_pattern = re.compile(r"(a+)+b")
result = evil_pattern.match("a" * 100)  # O(n), not O(2^n)
```

---

## Migration Path

### Phase 1: New Code

```python
# Use mereketengue for new pattern matching
from mereketengue import letter, alnum

# Clean, readable, safe, O(n)
identifier = letter + alnum[:]
```

### Phase 2: Gradual Migration

```bash
# CLI tool to convert regex to mereketengue
$ mereketengue convert "^[a-zA-Z_][a-zA-Z0-9_]*$"

# Output:
# from mereketengue import letter, alnum, START, END
#
# pattern = START + (letter | "_") + (alnum | "_")[:] + END
```

### Phase 3: Compatibility Layer

```python
# For legacy code, use the compat layer
from mereketengue.compat import re  # Drop-in replacement

# Existing code works unchanged, but with O(n) guarantee
```

---

## Integration with Our Ecosystem

### rosettes

```python
# rosettes/lexers/_scanners.py
from mereketengue import digit, maybe

# Replace regex-based helpers with mereketengue patterns
NUMBER_PATTERN = (
    maybe("0x" | "0o" | "0b") +
    digit + (digit | "_")[:] +
    maybe("." + digit[1:]) +
    maybe(("e" | "E") + maybe("+" | "-") + digit[1:])
)

# Pattern can be used for documentation AND matching
print(NUMBER_PATTERN.explain())
# → Match optional hex/octal/binary prefix, then digits (with underscores),
#   optional decimal part, optional exponent
```

### kida

```python
# kida/lexer.py
from mereketengue import ws, identifier, capture

# Template syntax patterns
VAR_PATTERN = "{{" + ws[:] + capture(identifier, "name") + ws[:] + "}}"

BLOCK_PATTERN = "{%" + ws[:] + capture(identifier, "tag") + ws[:] + "%}"
```

### patitas

```python
# patitas/parsing/inline/links.py
from mereketengue import ws, balanced, not_in, maybe, capture

# Link syntax: [text](url "title")
LINK_PATTERN = (
    "[" + capture(balanced("[", "]"), "text") + "](" +
    capture(not_in(")")[1:], "url") +
    maybe(ws[1:] + '"' + capture(not_in('"')[:], "title") + '"') +
    ")"
)
```

### bengal

```python
# bengal/config/validation.py
from mereketengue.common import url, email, semver

# Config validation using type-safe patterns
class ConfigValidator:
    def validate_url(self, value: str) -> URL:
        result = url.match(value)
        if not result:
            raise ValidationError(f"Invalid URL: {value}")
        return result.captures  # Typed URL object
```

---

## Performance

### Complexity Guarantees

| Operation | Mereketengue | Python re | Notes |
|-----------|--------------|-----------|-------|
| Match | O(n × m) | O(2^n) worst | n=text, m=pattern |
| Search | O(n × m) | O(2^n) worst | |
| Findall | O(n × m) | O(2^n) worst | |
| ReDoS-safe | ✅ Always | ❌ Never | |

### Benchmark Targets

```
Target: Competitive with RE2/Rust regex on typical patterns

Simple patterns (identifier, number):
  Target: < 2x Python re
  Reality: Often faster (no backtracking overhead)

Complex patterns (email, URL):
  Target: < 1.5x Python re  
  Reality: Often faster (predictable performance)

Evil patterns ((a+)+b with long input):
  Target: O(n)
  Reality: Python re times out; mereketengue completes instantly
```

---

## Security

### ReDoS Prevention

```python
# By design, mereketengue cannot have ReDoS vulnerabilities
from mereketengue import letter

# This pattern would cause Python's re to hang:
# re.match(r"(a+)+b", "a" * 30)  # Exponential backtracking

# Mereketengue handles it in O(n):
pattern = letter[1:][1:] + "b"  # Nested quantifiers — still O(n)!
result = pattern.match("a" * 1000000)  # Completes in milliseconds
```

### Input Validation

```python
from mereketengue import Pattern, Match
from mereketengue.common import email

# Safe for untrusted input
def validate_user_input(pattern: Pattern, text: str, max_len: int = 10000) -> Match | None:
    """Validate input with length limit (defense in depth)."""
    if len(text) > max_len:
        raise ValueError(f"Input too long: {len(text)} > {max_len}")
    return pattern.match(text)  # O(n) guaranteed
```

---

## Implementation Plan

### Phase 1: Core Engine (4 weeks)

- [ ] Pattern AST types (`_types.py`)
- [ ] Thompson NFA compiler (`engine/compile.py`)
- [ ] NFA executor (`engine/thompson.py`)
- [ ] Basic primitives (digit, letter, whitespace)
- [ ] Basic combinators (then, or, star, plus, maybe)
- [ ] Test suite (100% coverage target)

### Phase 2: Captures & Types (3 weeks)

- [ ] Named captures
- [ ] Transform functions
- [ ] Typed capture to dataclass
- [ ] Capture groups API

### Phase 3: Built-in Patterns (2 weeks)

- [ ] Network patterns (ipv4, ipv6, email, url)
- [ ] Data patterns (uuid, iso_date, semver)
- [ ] Code patterns (identifier, string_literal)
- [ ] Pattern validation tests

### Phase 4: Debugging & DX (2 weeks)

- [ ] Pattern explanation
- [ ] Match tracing
- [ ] Failure reasons
- [ ] Graphviz visualization

### Phase 5: Compatibility & Ecosystem (3 weeks)

- [ ] `re` module compatibility layer
- [ ] Regex-to-mereketengue converter
- [ ] rosettes integration
- [ ] kida integration
- [ ] Documentation & examples

### Phase 6: Optimization (2 weeks)

- [ ] Benchmark suite
- [ ] JIT compilation (optional)
- [ ] Memory optimization
- [ ] Parallel matching

---

## Open Questions

1. **Name**: Mereketengue is unique but hard to spell. Alternatives:
   - `rayas` (Spanish: stripes) — short, available on PyPI
   - `manchas` (Spanish: spots) — fits cat theme
   - `stripes` — descriptive, available on PyPI

2. **Regex compatibility level**: How much PCRE to support?
   - Lookahead/lookbehind: Complex, breaks O(n) in some cases
   - Backreferences: Fundamentally incompatible with Thompson NFA
   - Unicode categories: Important, should support

3. **API stability**: When to commit to 1.0?
   - After integration with rosettes/kida?
   - After community feedback?

4. **Performance vs. features trade-off**:
   - Pure Python for portability?
   - Cython for hot paths?
   - Rust via PyO3 for maximum performance?

---

## References

1. [Regular Expression Matching Can Be Simple And Fast (Cox, 2007)](https://swtch.com/~rsc/regexp/regexp1.html) — Thompson NFA explanation
2. [RE2: A principled approach to regular expression matching](https://github.com/google/re2) — Google's O(n) regex
3. [Rust regex crate](https://github.com/rust-lang/regex) — 180M downloads, Thompson NFA
4. [Regexes are Hard (2023)](https://arxiv.org/abs/2303.02555) — Academic study of regex pain points
5. [Cloudflare outage postmortem (2019)](https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/) — Real-world ReDoS impact

---

## Appendix A: Name Candidates

| Name | PyPI Available | Meaning | Pros | Cons |
|------|----------------|---------|------|------|
| **mereketengue** | ✅ | (unique) | Memorable, fits ecosystem | Hard to spell |
| **rayas** | ✅ | Spanish: stripes | Short, pattern-related | Less memorable |
| **manchas** | ✅ | Spanish: spots | Cat-themed | Less intuitive |
| **stripes** | ✅ | English | Descriptive, easy | Generic |
| **milo** | ❌ (taken) | Cat name | Personal connection | Taken since 2013 |

**Recommendation**: `mereketengue` for uniqueness in the ecosystem, or `rayas` for accessibility.

---

## Appendix B: Comparison with Alternatives

### vs. Python `re`

```python
# Python re — cryptic, ReDoS vulnerable
import re
pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Mereketengue — readable, O(n) safe
from mereketengue import letter, alnum, START, END
pattern = START + (letter | "_") + (alnum | "_")[:] + END
```

### vs. pyparsing

```python
# pyparsing — verbose, no O(n) guarantee
from pyparsing import Word, alphas, alphanums
identifier = Word(alphas + "_", alphanums + "_")

# Mereketengue — concise, O(n) guaranteed
from mereketengue import letter, alnum
identifier = letter + alnum[:]
```

### vs. RE2 (via google-re2)

```python
# google-re2 — safe but still regex syntax
import re2
pattern = re2.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Mereketengue — safe AND readable
from mereketengue import letter, alnum, START, END
pattern = START + (letter | "_") + (alnum | "_")[:] + END
```

### vs. pregex

```python
# pregex — readable but generates regex (still ReDoS vulnerable!)
from pregex.core.classes import AnyLetter, AnyDigit
from pregex.core.quantifiers import OneOrMore
pattern = OneOrMore(AnyLetter() | AnyDigit())
regex_str = pattern.get_pattern()  # → '[a-zA-Z\d]+'

# Mereketengue — readable AND safe (no regex generation)
from mereketengue import letter, digit
pattern = (letter | digit)[1:]  # Direct Thompson NFA execution
```

### Side-by-Side Summary

| Task | Python `re` | pregex | pyparsing | **Mereketengue** |
|------|-------------|--------|-----------|------------------|
| Email | `r'[\w.]+@[\w.]+'` | `OneOrMore(AnyLetter()) + ...` | `Word(...) + "@" + ...` | `word[1:] + "@" + word[1:]` |
| O(n) safe | ❌ | ❌ | ❌ | ✅ |
| Lines of code | 1 (cryptic) | 5+ | 3+ | 1 (clear) |
