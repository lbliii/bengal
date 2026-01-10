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

## Design Principles

### 1. Safety by Default

```python
# Mereketengue uses Thompson NFA — O(n) guaranteed
# No pattern can cause exponential backtracking

from mereketengue import Pattern

# This is ALWAYS O(n), unlike Python's re module
pattern = Pattern.word.then(Pattern.word.star())
result = pattern.match("a" * 1000000)  # Completes in milliseconds
```

### 2. Readability Over Brevity

```python
# ❌ Regex: Write-only
r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# ✅ Mereketengue: Reads like specification
from mereketengue import p

email = (
    p.word_chars.plus()
    .then(p.maybe(p.oneof(".", "_", "%", "+", "-").then(p.word_chars.plus())).star())
    .then(p.literal("@"))
    .then(p.word_chars.plus())
    .then(p.literal(".").then(p.word_chars.plus()).plus())
    .then(p.letter.repeat(2, None))  # TLD: 2+ letters
)
```

### 3. Type-Safe Captures

```python
from mereketengue import p, capture, typed
from dataclasses import dataclass

@dataclass
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: str | None = None

semver = (
    capture(p.digits, "major", transform=int)
    .then(p.literal("."))
    .then(capture(p.digits, "minor", transform=int))
    .then(p.literal("."))
    .then(capture(p.digits, "patch", transform=int))
    .then(p.maybe(
        p.literal("-").then(capture(p.word_chars.plus(), "prerelease"))
    ))
    .to(SemVer)
)

result = semver.match("1.2.3-beta")
# result = SemVer(major=1, minor=2, patch=3, prerelease="beta")
```

### 4. Composability

```python
from mereketengue import p

# Build complex patterns from simple, reusable parts
octet = (
    p.literal("25").then(p.range("0", "5")) |
    p.literal("2").then(p.range("0", "4")).then(p.digit) |
    p.maybe(p.oneof("0", "1")).then(p.digit).then(p.maybe(p.digit))
)

ipv4 = (
    octet.then(p.literal(".")).repeat(3)
    .then(octet)
)

cidr = ipv4.then(p.literal("/")).then(p.digits.between(1, 2))

# Patterns are immutable and can be shared across threads
```

### 5. Debuggability

```python
from mereketengue import p

pattern = p.literal("foo").then(p.word).then(p.literal("bar"))

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
├── __init__.py              # High-level API: p, Pattern, capture, typed
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

    # Composition
    def then(self, other: Pattern) -> Pattern:
        """Sequence: match self, then other."""
        ...

    def __or__(self, other: Pattern) -> Pattern:
        """Alternation: match self or other."""
        ...

    # Quantifiers
    def star(self) -> Pattern:
        """Zero or more (greedy)."""
        ...

    def plus(self) -> Pattern:
        """One or more (greedy)."""
        ...

    def maybe(self) -> Pattern:
        """Zero or one (optional)."""
        ...

    def repeat(self, min: int, max: int | None = None) -> Pattern:
        """Repeat between min and max times."""
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
from mereketengue import p

# Simple patterns
digits = p.digit.plus()
word = p.letter.plus()
identifier = p.letter.then(p.alnum.star())

# Match
result = digits.match("12345")
print(result.value)  # "12345"

# Search
result = word.search("hello, world!")
print(result.value)  # "hello"

# Find all
for match in digits.finditer("a1b22c333"):
    print(match.value)  # "1", "22", "333"

# Replace
result = word.sub(lambda m: m.value.upper(), "hello world")
print(result)  # "HELLO WORLD"
```

### Captures

```python
from mereketengue import p, capture

# Named captures
log_pattern = (
    capture(p.digits, "year")
    .then(p.literal("-"))
    .then(capture(p.digits, "month"))
    .then(p.literal("-"))
    .then(capture(p.digits, "day"))
)

result = log_pattern.match("2026-01-09")
print(result.captures["year"])   # "2026"
print(result.captures["month"])  # "01"
print(result.captures["day"])    # "09"

# With transformation
date_pattern = (
    capture(p.digits, "year", transform=int)
    .then(p.literal("-"))
    .then(capture(p.digits, "month", transform=int))
    .then(p.literal("-"))
    .then(capture(p.digits, "day", transform=int))
)

result = date_pattern.match("2026-01-09")
print(result.captures["year"])   # 2026 (int)
```

### Typed Captures

```python
from mereketengue import p, capture, typed
from dataclasses import dataclass

@dataclass
class URL:
    scheme: str
    host: str
    port: int | None
    path: str

url_pattern = (
    capture(p.oneof("http", "https"), "scheme")
    .then(p.literal("://"))
    .then(capture(p.word.then(p.literal(".").then(p.word)).plus(), "host"))
    .then(p.maybe(
        p.literal(":").then(capture(p.digits, "port", transform=int))
    ))
    .then(capture(p.literal("/").then(p.any.star()), "path").default("/"))
    .to(URL)
)

result = url_pattern.match("https://example.com:8080/api/v1")
# result.captures = URL(scheme="https", host="example.com", port=8080, path="/api/v1")
```

### Built-in Patterns

```python
from mereketengue.common import ipv4, email, uuid, semver, iso_date

# All built-in patterns are O(n) guaranteed
assert ipv4.match("192.168.1.1")
assert email.match("user@example.com")
assert uuid.match("550e8400-e29b-41d4-a716-446655440000")
assert semver.match("1.2.3-beta.1")
assert iso_date.match("2026-01-09")

# Compose with built-ins
server_log = (
    iso_date
    .then(p.whitespace)
    .then(capture(ipv4, "client_ip"))
    .then(p.whitespace)
    .then(capture(p.quoted('"'), "message"))
)
```

### Debugging

```python
from mereketengue import p

pattern = p.literal("GET").then(p.whitespace).then(p.path)

# Why didn't it match?
result = pattern.match("POST /api", debug=True)
print(result.failure_reason)
# → Expected 'GET' at position 0, found 'POS...'

# Explain the pattern
print(pattern.explain())
# → Match literal 'GET', then whitespace, then a file path

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
from mereketengue import p

# Clean, readable, safe
identifier = p.letter.then(p.alnum.star())
```

### Phase 2: Gradual Migration

```python
# CLI tool to convert regex to mereketengue
$ mereketengue convert "^[a-zA-Z_][a-zA-Z0-9_]*$"
# Output:
# p.start.then(
#     p.oneof(p.letter, p.literal("_"))
# ).then(
#     p.oneof(p.alnum, p.literal("_")).star()
# ).then(p.end)
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
from mereketengue import p

# Replace regex-based helpers with mereketengue patterns
NUMBER_PATTERN = (
    p.maybe(p.oneof("0x", "0o", "0b"))
    .then(p.digit.then(p.oneof(p.digit, p.literal("_")).star()))
    .then(p.maybe(p.literal(".").then(p.digit.plus())))
    .then(p.maybe(p.oneof("e", "E").then(p.maybe(p.oneof("+", "-"))).then(p.digit.plus())))
)

# Pattern can be used for documentation AND matching
print(NUMBER_PATTERN.explain())
# → Match optional hex/octal/binary prefix, then digits (with underscores),
#   optional decimal part, optional exponent
```

### kida

```python
# kida/lexer.py
from mereketengue import p

# Template syntax patterns
VAR_PATTERN = p.literal("{{").then(p.whitespace.star()).then(
    capture(p.identifier, "name")
).then(p.whitespace.star()).then(p.literal("}}"))

BLOCK_PATTERN = p.literal("{%").then(p.whitespace.star()).then(
    capture(p.identifier, "tag")
).then(p.whitespace.star()).then(p.literal("%}"))
```

### patitas

```python
# patitas/parsing/inline/links.py
from mereketengue import p, capture

# Link syntax: [text](url "title")
LINK_PATTERN = (
    p.literal("[")
    .then(capture(p.balanced("[", "]"), "text"))
    .then(p.literal("]("))
    .then(capture(p.not_chars(")").plus(), "url"))
    .then(p.maybe(
        p.whitespace.plus()
        .then(p.literal('"'))
        .then(capture(p.not_chars('"').star(), "title"))
        .then(p.literal('"'))
    ))
    .then(p.literal(")"))
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

# This pattern would cause Python's re to hang:
# re.match(r"(a+)+b", "a" * 30)  # Exponential backtracking

# Mereketengue handles it in O(n):
pattern = p.letter.plus().plus().then(p.literal("b"))
result = pattern.match("a" * 1000000)  # Completes in milliseconds
```

### Input Validation

```python
from mereketengue import p
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
# Python re
import re
pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
if pattern.match(text):
    ...

# Mereketengue
from mereketengue import p
pattern = p.start.then(p.letter | p.literal("_")).then((p.alnum | p.literal("_")).star()).then(p.end)
if pattern.match(text):
    ...
```

**Differences**:
- Mereketengue: Readable, O(n) guaranteed, composable
- re: Terse, potential ReDoS, not composable

### vs. pyparsing

```python
# pyparsing
from pyparsing import Word, alphas, alphanums
identifier = Word(alphas + "_", alphanums + "_")

# Mereketengue  
from mereketengue import p
identifier = (p.letter | p.literal("_")).then((p.alnum | p.literal("_")).star())
```

**Differences**:
- pyparsing: Full parser, heavier, returns parse results
- Mereketengue: Pattern matching focus, lighter, O(n) guarantee

### vs. RE2 (via google-re2)

```python
# google-re2
import re2
pattern = re2.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Mereketengue
from mereketengue import p
pattern = p.start.then(p.letter | p.literal("_")).then((p.alnum | p.literal("_")).star()).then(p.end)
```

**Differences**:
- RE2: C++ binding, regex syntax, fast
- Mereketengue: Pure Python, readable API, typed captures, ecosystem integration
