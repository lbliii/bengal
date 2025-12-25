# RFC: DFA-Based Lexers for Rosettes

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-0005 |
| **Title** | DFA-Based Lexers with Parallel Tokenization |
| **Status** | Draft |
| **Created** | 2025-12-25 |
| **Author** | Bengal Core Team |
| **Depends On** | RFC-0002 (Rosettes Syntax Highlighter) |
| **Supersedes** | RFC-0004 (ReDoS Prevention) — provides stronger guarantees |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Replace backtracking regex with DFA-compiled lexers; add parallel tokenization for 3.14t |
| **Why** | Eliminate ReDoS by construction; leverage free-threading for performance |
| **Effort** | 3-4 weeks |
| **Risk** | Medium — requires rewriting lexer infrastructure |
| **Constraints** | Must remain pure Python; must be backwards-compatible API |

**Key Deliverables:**
1. Thompson NFA construction from regex patterns
2. NFA→DFA conversion with subset construction
3. DFA minimization and table generation
4. Parallel chunked tokenization for large files (3.14t)
5. Backwards-compatible `PatternLexer` API

---

## Motivation

### Why Not Just Fix the Regex Patterns?

RFC-0004 proposes mitigating ReDoS through:
- Static pattern analysis (heuristic)
- Pattern rewriting guidelines
- Fuzz testing
- Runtime timeouts

**Problem**: These are *mitigations*, not *solutions*. The vulnerability remains in the architecture.

| RFC-0004 Approach | Limitation |
|-------------------|------------|
| Static analysis | Heuristic — can miss patterns, flag safe ones |
| Pattern guidelines | Requires eternal vigilance from contributors |
| Fuzz testing | Can't prove absence of vulnerability |
| Runtime timeout | Admits the problem exists; just limits damage |

### The Right Solution: Eliminate Backtracking

The fundamental issue: Python's `re` module uses a **backtracking** algorithm that can exhibit exponential time complexity.

**Alternative**: Compile regex to DFA (Deterministic Finite Automaton). DFAs:
- Match in O(n) time — always, regardless of pattern
- Cannot backtrack — the algorithm doesn't support it
- Are the "textbook correct" approach to lexing

### Why Now? Python 3.14t

Python 3.14t (free-threaded) removes the GIL, enabling true parallelism. This creates an opportunity:

| Capability | GIL Python | Free-threaded 3.14t |
|------------|------------|---------------------|
| Parallel tokenization | No benefit (serialized) | True parallelism |
| Large file performance | Single-threaded | Multi-threaded speedup |
| Thread-safe lexers | Require locks | Immutable data = free |

**Positioning**: Rosettes can be the first syntax highlighter designed for free-threaded Python.

---

## Design Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Definition Time (once)                        │
├─────────────────────────────────────────────────────────────────┤
│  1. Parse regex patterns                                         │
│  2. Build NFA (Thompson construction)                            │
│  3. Convert NFA → DFA (subset construction)                      │
│  4. Minimize DFA (Hopcroft's algorithm)                          │
│  5. Generate immutable transition tables                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Runtime (per tokenize call)                   │
├─────────────────────────────────────────────────────────────────┤
│  1. Detect if parallel beneficial (file size + 3.14t check)     │
│  2. If parallel: split at safe boundaries, tokenize chunks      │
│  3. If sequential: single-pass DFA execution                     │
│  4. O(n) guaranteed — just table lookups                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Regex Parser

Parse regex patterns into an AST for NFA construction.

### Supported Regex Features

| Feature | Syntax | Supported | Notes |
|---------|--------|-----------|-------|
| Literal | `a` | ✅ | Direct character match |
| Concatenation | `ab` | ✅ | Sequence |
| Alternation | `a\|b` | ✅ | Choice |
| Kleene star | `a*` | ✅ | Zero or more |
| Plus | `a+` | ✅ | Rewrite as `aa*` |
| Optional | `a?` | ✅ | Rewrite as `(a\|ε)` |
| Character class | `[a-z]` | ✅ | Expanded to alternation |
| Negated class | `[^a-z]` | ✅ | Complement of class |
| Dot | `.` | ✅ | Any char except newline |
| Anchors | `^$` | ⚠️ | Limited support |
| Groups | `(...)` | ✅ | Non-capturing only |
| Backrefs | `\1` | ❌ | Not regular — cannot DFA |
| Lookahead | `(?=...)` | ❌ | Not regular — cannot DFA |
| Lookbehind | `(?<=...)` | ❌ | Not regular — cannot DFA |

**Note**: Backreferences and lookaround are not "regular" — they cannot be compiled to DFA. Lexers requiring these features fall back to the guarded regex path (RFC-0004).

### Implementation

```python
# rosettes/lexers/_regex_parser.py

from dataclasses import dataclass
from typing import Union

@dataclass(frozen=True, slots=True)
class Literal:
    char: str

@dataclass(frozen=True, slots=True)
class CharClass:
    chars: frozenset[str]
    negated: bool = False

@dataclass(frozen=True, slots=True)
class Concat:
    left: 'RegexAST'
    right: 'RegexAST'

@dataclass(frozen=True, slots=True)
class Alternation:
    left: 'RegexAST'
    right: 'RegexAST'

@dataclass(frozen=True, slots=True)
class Star:
    child: 'RegexAST'

@dataclass(frozen=True, slots=True)
class Epsilon:
    """Empty string match."""
    pass

RegexAST = Union[Literal, CharClass, Concat, Alternation, Star, Epsilon]


def parse_regex(pattern: str) -> RegexAST:
    """Parse regex pattern string into AST.

    Raises:
        ValueError: If pattern uses unsupported features (backrefs, lookaround).
    """
    # Recursive descent parser for regex grammar
    # ...implementation...
```

---

## Layer 2: Thompson NFA Construction

Convert regex AST to NFA using Thompson's construction algorithm.

### NFA Representation

```python
# rosettes/lexers/_nfa.py

from dataclasses import dataclass
from typing import FrozenSet

@dataclass(frozen=True, slots=True)
class NFAState:
    """Immutable NFA state."""
    id: int
    is_accepting: bool
    token_type: TokenType | None = None

@dataclass(frozen=True, slots=True)
class NFATransition:
    """NFA transition (including epsilon)."""
    from_state: int
    to_state: int
    on_char: str | None  # None = epsilon transition

@dataclass(frozen=True, slots=True)
class NFA:
    """Complete NFA with immutable structure."""
    states: tuple[NFAState, ...]
    transitions: tuple[NFATransition, ...]
    start_state: int
    accept_states: frozenset[int]
```

### Thompson Construction Rules

```
Literal 'a':
    ┌───┐  a   ┌───┐
    │ s │─────▶│ e │
    └───┘      └───┘

Concatenation (A followed by B):
    ┌─────┐      ┌─────┐
    │  A  │─────▶│  B  │
    └─────┘      └─────┘

Alternation (A | B):
           ┌─────┐
        ε ─▶│  A  │─ε─┐
    ┌───┐  └─────┘    ▼  ┌───┐
    │ s │              ──▶│ e │
    └───┘  ┌─────┐    ▲  └───┘
        ε ─▶│  B  │─ε─┘
           └─────┘

Kleene Star (A*):
              ε
           ┌──────┐
           ▼      │
    ┌───┐  ε  ┌─────┐  ε  ┌───┐
    │ s │────▶│  A  │────▶│ e │
    └───┘     └─────┘     └───┘
      │                     ▲
      └─────────ε───────────┘
```

### Implementation

```python
# rosettes/lexers/_nfa.py (continued)

class NFABuilder:
    """Build NFA from regex AST using Thompson's construction."""

    def __init__(self) -> None:
        self._next_state_id = 0
        self._states: list[NFAState] = []
        self._transitions: list[NFATransition] = []

    def build(self, ast: RegexAST, token_type: TokenType) -> NFA:
        """Build NFA from regex AST."""
        start, end = self._build_fragment(ast)

        # Mark end state as accepting
        self._states[end] = NFAState(
            id=end,
            is_accepting=True,
            token_type=token_type,
        )

        return NFA(
            states=tuple(self._states),
            transitions=tuple(self._transitions),
            start_state=start,
            accept_states=frozenset([end]),
        )

    def _build_fragment(self, ast: RegexAST) -> tuple[int, int]:
        """Build NFA fragment, return (start, end) state IDs."""
        match ast:
            case Literal(char):
                return self._literal(char)
            case CharClass(chars, negated):
                return self._char_class(chars, negated)
            case Concat(left, right):
                return self._concat(left, right)
            case Alternation(left, right):
                return self._alternation(left, right)
            case Star(child):
                return self._star(child)
            case Epsilon():
                return self._epsilon()

    def _literal(self, char: str) -> tuple[int, int]:
        start = self._new_state()
        end = self._new_state()
        self._add_transition(start, end, char)
        return start, end

    def _concat(self, left: RegexAST, right: RegexAST) -> tuple[int, int]:
        left_start, left_end = self._build_fragment(left)
        right_start, right_end = self._build_fragment(right)
        # Connect left end to right start with epsilon
        self._add_transition(left_end, right_start, None)
        return left_start, right_end

    def _alternation(self, left: RegexAST, right: RegexAST) -> tuple[int, int]:
        start = self._new_state()
        end = self._new_state()

        left_start, left_end = self._build_fragment(left)
        right_start, right_end = self._build_fragment(right)

        # Epsilon transitions from start to both branches
        self._add_transition(start, left_start, None)
        self._add_transition(start, right_start, None)

        # Epsilon transitions from both branches to end
        self._add_transition(left_end, end, None)
        self._add_transition(right_end, end, None)

        return start, end

    def _star(self, child: RegexAST) -> tuple[int, int]:
        start = self._new_state()
        end = self._new_state()

        child_start, child_end = self._build_fragment(child)

        # Epsilon from start to child and to end (skip)
        self._add_transition(start, child_start, None)
        self._add_transition(start, end, None)

        # Epsilon from child end to child start (repeat)
        self._add_transition(child_end, child_start, None)

        # Epsilon from child end to end (exit)
        self._add_transition(child_end, end, None)

        return start, end
```

---

## Layer 3: NFA to DFA Conversion

Convert NFA to DFA using the subset construction algorithm.

### Subset Construction

The key insight: a DFA state represents a *set* of NFA states. We track which NFA states are "active" simultaneously.

```python
# rosettes/lexers/_dfa.py

from dataclasses import dataclass
from typing import Final

@dataclass(frozen=True, slots=True)
class DFAState:
    """Immutable DFA state — thread-safe by design."""
    id: int
    nfa_states: frozenset[int]  # Which NFA states this represents
    is_accepting: bool
    token_type: TokenType | None  # Highest-priority accepting token

@dataclass(frozen=True, slots=True)
class DFA:
    """Complete DFA with immutable transition tables."""
    states: tuple[DFAState, ...]
    transitions: dict[tuple[int, str], int]  # (state_id, char) → next_state_id
    start_state: int
    alphabet: frozenset[str]


def epsilon_closure(nfa: NFA, states: frozenset[int]) -> frozenset[int]:
    """Compute epsilon closure of a set of NFA states.

    Returns all states reachable via epsilon transitions.
    """
    closure = set(states)
    worklist = list(states)

    while worklist:
        state = worklist.pop()
        for trans in nfa.transitions:
            if trans.from_state == state and trans.on_char is None:
                if trans.to_state not in closure:
                    closure.add(trans.to_state)
                    worklist.append(trans.to_state)

    return frozenset(closure)


def move(nfa: NFA, states: frozenset[int], char: str) -> frozenset[int]:
    """Compute states reachable from `states` on input `char`."""
    result = set()
    for trans in nfa.transitions:
        if trans.from_state in states and trans.on_char == char:
            result.add(trans.to_state)
    return frozenset(result)


def nfa_to_dfa(nfa: NFA, token_priorities: dict[TokenType, int]) -> DFA:
    """Convert NFA to DFA using subset construction.

    Args:
        nfa: The NFA to convert.
        token_priorities: Priority ordering for token types (lower = higher priority).

    Returns:
        Equivalent DFA with immutable structure.
    """
    # Compute alphabet from NFA transitions
    alphabet = frozenset(
        t.on_char for t in nfa.transitions if t.on_char is not None
    )

    # Start state is epsilon closure of NFA start
    start_nfa_states = epsilon_closure(nfa, frozenset([nfa.start_state]))

    dfa_states: list[DFAState] = []
    state_map: dict[frozenset[int], int] = {}  # NFA state set → DFA state ID
    transitions: dict[tuple[int, str], int] = {}
    worklist: list[frozenset[int]] = [start_nfa_states]

    def get_or_create_state(nfa_states: frozenset[int]) -> int:
        if nfa_states in state_map:
            return state_map[nfa_states]

        state_id = len(dfa_states)
        state_map[nfa_states] = state_id

        # Determine if accepting and which token type
        accepting_tokens = [
            nfa.states[s].token_type
            for s in nfa_states
            if nfa.states[s].is_accepting
        ]

        is_accepting = bool(accepting_tokens)
        token_type = None
        if accepting_tokens:
            # Use highest priority (lowest number) token
            token_type = min(accepting_tokens, key=lambda t: token_priorities.get(t, 999))

        dfa_states.append(DFAState(
            id=state_id,
            nfa_states=nfa_states,
            is_accepting=is_accepting,
            token_type=token_type,
        ))

        return state_id

    get_or_create_state(start_nfa_states)

    while worklist:
        current_nfa_states = worklist.pop()
        current_dfa_id = state_map[current_nfa_states]

        for char in alphabet:
            # Compute next state
            next_nfa_states = epsilon_closure(
                nfa,
                move(nfa, current_nfa_states, char)
            )

            if not next_nfa_states:
                continue  # Dead state, no transition

            if next_nfa_states not in state_map:
                worklist.append(next_nfa_states)

            next_dfa_id = get_or_create_state(next_nfa_states)
            transitions[(current_dfa_id, char)] = next_dfa_id

    return DFA(
        states=tuple(dfa_states),
        transitions=transitions,
        start_state=0,
        alphabet=alphabet,
    )
```

---

## Layer 4: DFA Minimization

Reduce DFA size using Hopcroft's algorithm for faster runtime.

```python
# rosettes/lexers/_dfa.py (continued)

def minimize_dfa(dfa: DFA) -> DFA:
    """Minimize DFA using Hopcroft's algorithm.

    Reduces state count by merging equivalent states.
    Smaller DFA = faster runtime + less memory.
    """
    # Partition states by (is_accepting, token_type)
    # Then iteratively refine based on transitions
    # ...implementation of Hopcroft's algorithm...

    # Return minimized DFA with renumbered states
    pass
```

---

## Layer 5: Transition Table Generation

Convert DFA to compact transition tables for fast runtime.

```python
# rosettes/lexers/_tables.py

from dataclasses import dataclass
from typing import Final
import array

@dataclass(frozen=True, slots=True)
class TransitionTables:
    """Compact, immutable transition tables for DFA execution.

    Design for cache efficiency:
    - Character classes reduce alphabet size
    - Contiguous arrays for spatial locality
    - Immutable = thread-safe
    """

    # Character → character class mapping
    # Uses array for O(1) lookup by ordinal
    char_to_class: Final[array.array]  # 'H' (unsigned short)

    # Transition table: transitions[state * num_classes + class] = next_state
    # -1 = no transition (dead)
    transitions: Final[array.array]  # 'i' (signed int)

    # Accepting state info
    is_accepting: Final[tuple[bool, ...]]
    token_types: Final[tuple[TokenType | None, ...]]

    # Dimensions
    num_states: Final[int]
    num_classes: Final[int]


def generate_tables(dfa: DFA) -> TransitionTables:
    """Generate compact transition tables from DFA.

    Optimizations:
    1. Compute character classes (chars with identical transitions)
    2. Pack transitions into contiguous array
    3. Use array.array for memory efficiency
    """
    # Compute character equivalence classes
    char_classes = _compute_char_classes(dfa)
    num_classes = len(set(char_classes.values()))

    # Build char → class lookup (0-65535 for Unicode BMP)
    char_to_class = array.array('H', [0] * 65536)
    for char, cls in char_classes.items():
        if ord(char) < 65536:
            char_to_class[ord(char)] = cls

    # Build transition table
    num_states = len(dfa.states)
    transitions = array.array('i', [-1] * (num_states * num_classes))

    for (state_id, char), next_state in dfa.transitions.items():
        cls = char_classes[char]
        transitions[state_id * num_classes + cls] = next_state

    return TransitionTables(
        char_to_class=char_to_class,
        transitions=transitions,
        is_accepting=tuple(s.is_accepting for s in dfa.states),
        token_types=tuple(s.token_type for s in dfa.states),
        num_states=num_states,
        num_classes=num_classes,
    )
```

---

## Layer 6: DFA Lexer Runtime

Execute DFA for tokenization — O(n) guaranteed.

```python
# rosettes/lexers/_dfa_lexer.py

from collections.abc import Iterator
from typing import Final

from rosettes._types import Token, TokenType
from rosettes.lexers._tables import TransitionTables

class DFALexer:
    """DFA-based lexer with O(n) guaranteed runtime.

    Thread-safe: all state is immutable.
    No backtracking: DFA execution is forward-only.
    """

    name: str = "base"
    aliases: tuple[str, ...] = ()
    rules: tuple[Rule, ...] = ()

    # Compiled at definition time (immutable)
    _tables: TransitionTables | None = None

    def __init_subclass__(cls, **kwargs) -> None:
        """Compile regex patterns to DFA at class definition time."""
        super().__init_subclass__(**kwargs)

        if not cls.rules:
            return

        # 1. Parse each pattern
        asts = []
        for rule in cls.rules:
            try:
                ast = parse_regex(rule.pattern.pattern)
                asts.append((ast, rule.token_type))
            except ValueError as e:
                # Pattern uses unsupported features — fall back to guarded regex
                cls._tables = None
                cls._use_fallback = True
                return

        # 2. Build combined NFA (alternation of all patterns)
        builder = NFABuilder()
        combined_nfa = builder.build_combined(asts)

        # 3. Convert to DFA
        priorities = {rule.token_type: i for i, rule in enumerate(cls.rules)}
        dfa = nfa_to_dfa(combined_nfa, priorities)

        # 4. Minimize
        dfa = minimize_dfa(dfa)

        # 5. Generate tables
        cls._tables = generate_tables(dfa)

    def tokenize(self, code: str) -> Iterator[Token]:
        """Tokenize source code. O(n) guaranteed.

        Uses longest-match semantics: at each position, find the
        longest match, emit token, advance.
        """
        if self._tables is None:
            # Fallback to guarded regex (for patterns with backrefs, etc.)
            yield from self._tokenize_fallback(code)
            return

        tables = self._tables
        char_to_class = tables.char_to_class
        transitions = tables.transitions
        is_accepting = tables.is_accepting
        token_types = tables.token_types
        num_classes = tables.num_classes

        pos = 0
        line = 1
        line_start = 0
        length = len(code)

        while pos < length:
            # Find longest match from current position
            state = 0  # Start state
            match_end = -1
            match_token = None
            scan_pos = pos

            while scan_pos < length:
                char = code[scan_pos]
                char_ord = ord(char)

                # O(1) character class lookup
                if char_ord < 65536:
                    char_class = char_to_class[char_ord]
                else:
                    char_class = 0  # Default class for chars outside BMP

                # O(1) transition lookup
                next_state = transitions[state * num_classes + char_class]

                if next_state == -1:
                    break  # No transition — stop scanning

                state = next_state
                scan_pos += 1

                # Track longest accepting match
                if is_accepting[state]:
                    match_end = scan_pos
                    match_token = token_types[state]

            if match_token is not None and match_end > pos:
                # Emit token
                value = code[pos:match_end]
                yield Token(
                    type=match_token,
                    value=value,
                    line=line,
                    column=pos - line_start + 1,
                )

                # Update line tracking
                newlines = value.count('\n')
                if newlines:
                    line += newlines
                    line_start = pos + value.rfind('\n') + 1

                pos = match_end
            else:
                # No match — skip character (or emit error token)
                pos += 1
```

---

## Layer 7: Parallel Tokenization (3.14t)

Leverage free-threading for large files.

```python
# rosettes/_parallel.py

import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Iterator

@dataclass(frozen=True, slots=True)
class Chunk:
    """A chunk of source code with position metadata."""
    text: str
    start_offset: int
    start_line: int

def is_free_threaded() -> bool:
    """Check if running on free-threaded Python (3.14t+)."""
    # Python 3.13+ has sys._is_gil_enabled()
    if hasattr(sys, '_is_gil_enabled'):
        return not sys._is_gil_enabled()
    return False


def find_safe_splits(code: str, target_chunk_size: int) -> list[int]:
    """Find safe split points for parallel tokenization.

    Safe splits are at line boundaries outside strings/comments.
    This is a heuristic — we scan backwards from target positions
    to find newlines.
    """
    splits = []
    pos = target_chunk_size

    while pos < len(code):
        # Find nearest newline before target
        newline_pos = code.rfind('\n', pos - target_chunk_size // 2, pos)
        if newline_pos == -1:
            newline_pos = pos  # No newline found, split here anyway
        else:
            newline_pos += 1  # Include the newline in previous chunk

        if newline_pos > splits[-1] if splits else 0:
            splits.append(newline_pos)

        pos = newline_pos + target_chunk_size

    return splits


def split_into_chunks(code: str, splits: list[int]) -> list[Chunk]:
    """Split code at the given positions."""
    chunks = []
    prev = 0
    line = 1

    for split_pos in splits:
        chunk_text = code[prev:split_pos]
        chunks.append(Chunk(
            text=chunk_text,
            start_offset=prev,
            start_line=line,
        ))
        line += chunk_text.count('\n')
        prev = split_pos

    # Final chunk
    if prev < len(code):
        chunks.append(Chunk(
            text=code[prev:],
            start_offset=prev,
            start_line=line,
        ))

    return chunks


def tokenize_parallel(
    lexer: 'DFALexer',
    code: str,
    *,
    chunk_size: int = 64_000,
    max_workers: int | None = None,
) -> Iterator[Token]:
    """Parallel tokenization for large files.

    Only beneficial on free-threaded Python (3.14t+).
    Falls back to sequential on GIL Python.

    Args:
        lexer: The DFA lexer to use.
        code: Source code to tokenize.
        chunk_size: Target chunk size in characters.
        max_workers: Maximum threads. None = CPU count.

    Yields:
        Tokens in order of appearance.
    """
    # Small files or GIL Python: sequential
    if len(code) < chunk_size or not is_free_threaded():
        yield from lexer.tokenize(code)
        return

    # Split at safe boundaries
    splits = find_safe_splits(code, chunk_size)
    chunks = split_into_chunks(code, splits)

    # Tokenize chunks in parallel
    def process_chunk(chunk: Chunk) -> list[Token]:
        tokens = list(lexer.tokenize(chunk.text))
        # Adjust positions for chunk offset
        return [
            Token(
                type=t.type,
                value=t.value,
                line=t.line + chunk.start_line - 1,
                column=t.column if t.line > 1 else t.column + chunk.start_offset,
            )
            for t in tokens
        ]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_chunk, chunks))

    # Yield tokens in order
    for chunk_tokens in results:
        yield from chunk_tokens
```

---

## Layer 8: Backwards-Compatible PatternLexer API

Maintain API compatibility with existing lexers.

```python
# rosettes/lexers/_base.py (updated)

class PatternLexer(DFALexer):
    """Pattern-based lexer with automatic DFA compilation.

    API-compatible with existing lexers. Patterns are compiled
    to DFA at class definition time when possible.

    If patterns use unsupported regex features (backrefs, lookaround),
    falls back to guarded regex execution with timeout protection.
    """

    # Parallel tokenization configuration
    PARALLEL_THRESHOLD: int = 100_000  # Bytes
    PARALLEL_CHUNK_SIZE: int = 64_000

    def tokenize(
        self,
        code: str,
        *,
        parallel: bool | None = None,
    ) -> Iterator[Token]:
        """Tokenize source code.

        Args:
            code: Source code to tokenize.
            parallel: Force parallel mode. None = auto-detect.

        Yields:
            Tokens in order of appearance.
        """
        # Auto-detect parallel mode
        if parallel is None:
            parallel = (
                len(code) >= self.PARALLEL_THRESHOLD
                and is_free_threaded()
                and self._tables is not None
            )

        if parallel:
            yield from tokenize_parallel(
                self,
                code,
                chunk_size=self.PARALLEL_CHUNK_SIZE,
            )
        else:
            yield from super().tokenize(code)
```

---

## Migration Plan

### Phase 1: Core Infrastructure (Week 1)

| Task | Priority | Deliverable |
|------|----------|-------------|
| Regex parser | P0 | `_regex_parser.py` |
| Thompson NFA builder | P0 | `_nfa.py` |
| Subset construction | P0 | `_dfa.py` |
| Unit tests for each | P0 | `tests/unit/` |

### Phase 2: Optimization (Week 2)

| Task | Priority | Deliverable |
|------|----------|-------------|
| DFA minimization | P1 | Hopcroft's algorithm |
| Transition tables | P0 | `_tables.py` |
| DFA lexer runtime | P0 | `_dfa_lexer.py` |
| Benchmark suite | P1 | `benchmarks/` |

### Phase 3: Integration (Week 3)

| Task | Priority | Deliverable |
|------|----------|-------------|
| PatternLexer migration | P0 | Updated `_base.py` |
| Fallback path for unsupported patterns | P0 | Guarded regex with timeout |
| Parallel tokenization | P1 | `_parallel.py` |
| 3.14t detection | P1 | Runtime check |

### Phase 4: Validation (Week 4)

| Task | Priority | Deliverable |
|------|----------|-------------|
| Audit all lexers for compatibility | P0 | Migration report |
| Rewrite patterns using unsupported features | P1 | Updated lexers |
| Performance benchmarks vs Pygments | P0 | Benchmark report |
| Documentation | P1 | Updated docs |

---

## Performance Expectations

### Compile Time (once per lexer class)

| Lexer Size | Expected Time |
|------------|---------------|
| Small (10 rules) | <10ms |
| Medium (30 rules) | <50ms |
| Large (50 rules) | <200ms |

### Runtime (per tokenize call)

| Approach | Time Complexity | Expected Performance |
|----------|----------------|---------------------|
| Current regex | O(2ⁿ) worst | Vulnerable to ReDoS |
| DFA | O(n) always | ~same speed, no ReDoS |
| DFA + parallel (3.14t) | O(n/cores) | 2-4x faster on large files |

### Memory

| Component | Size |
|-----------|------|
| Character class table | ~128KB (64K × 2 bytes) |
| Transition table | ~(states × classes × 4) bytes |
| Typical Python lexer | ~50KB total |

---

## Fallback Strategy

Some regex features cannot be compiled to DFA:

| Feature | Example | Fallback Behavior |
|---------|---------|-------------------|
| Backreferences | `(.)\\1` | Guarded regex with timeout |
| Positive lookahead | `(?=...)` | Guarded regex with timeout |
| Negative lookahead | `(?!...)` | Guarded regex with timeout |
| Lookbehind | `(?<=...)` | Guarded regex with timeout |

**Guarded Regex**: Falls back to RFC-0004 approach (timeout + pattern validation).

---

## Success Criteria

- [ ] All lexers compile to DFA (or have documented fallback reason)
- [ ] O(n) runtime verified via benchmark suite
- [ ] No performance regression vs current regex approach
- [ ] Parallel tokenization shows speedup on 3.14t with large files
- [ ] API backwards-compatible — existing code works unchanged
- [ ] Fuzz tests pass with 10,000+ random inputs per lexer

---

## Comparison: RFC-0004 vs RFC-0005

| Aspect | RFC-0004 (ReDoS Prevention) | RFC-0005 (DFA Lexers) |
|--------|---------------------------|----------------------|
| **Approach** | Mitigate vulnerabilities | Eliminate by construction |
| **Guarantees** | Heuristic + defense-in-depth | Mathematical (DFA = O(n)) |
| **Effort** | 1-2 weeks | 3-4 weeks |
| **3.14t Benefits** | None | Parallel tokenization |
| **Contributor burden** | Must follow pattern guidelines | Patterns auto-validated |
| **CVE risk** | Reduced | Eliminated (for DFA-compatible patterns) |

**Recommendation**: Implement RFC-0005 if targeting standalone PyPI release. The stronger guarantees justify the extra effort.

---

## References

- [Thompson's Construction](https://en.wikipedia.org/wiki/Thompson%27s_construction) — NFA from regex
- [Subset Construction](https://en.wikipedia.org/wiki/Powerset_construction) — NFA to DFA
- [Hopcroft's Algorithm](https://en.wikipedia.org/wiki/DFA_minimization) — DFA minimization
- [Regular Expression Matching Can Be Simple And Fast](https://swtch.com/~rsc/regexp/regexp1.html) — Russ Cox's classic article
- [Python 3.14 Free-Threading](https://docs.python.org/3.14/whatsnew/3.14.html) — GIL removal
- [PEP 703](https://peps.python.org/pep-0703/) — Making the GIL Optional

---

## Appendix: Why This Is Novel

Most syntax highlighters (Pygments, Prism, etc.) use backtracking regex because:
1. It's easy to write patterns
2. Performance is "usually fine"
3. DFA compilation adds complexity

Rosettes with RFC-0005 would be **unique** in offering:
1. **CVE-proof by construction** — not by policy or testing
2. **Designed for free-threading** — parallel tokenization
3. **Pure Python** — no C dependencies (unlike tree-sitter bindings)
4. **Backwards-compatible** — existing patterns still work

This positions Rosettes as the **modern, secure, performant** choice for Python syntax highlighting.
