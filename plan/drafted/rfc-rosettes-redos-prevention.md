# RFC: Rosettes ReDoS Prevention

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-0004 |
| **Title** | ReDoS Prevention for Rosettes Lexers |
| **Status** | Draft |
| **Created** | 2025-12-25 |
| **Author** | Bengal Core Team |
| **Depends On** | RFC-0002 (Rosettes Syntax Highlighter) |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Prevent Regular Expression Denial of Service (ReDoS) in Rosettes lexers |
| **Why** | Regex-based tokenizers are inherently vulnerable to catastrophic backtracking |
| **Effort** | 1-2 weeks |
| **Risk** | Medium — requires auditing all existing lexers |
| **Constraints** | Must remain pure Python; tree-sitter is not free-threading compatible |

**Key Deliverables:**
1. Static pattern analyzer that rejects ReDoS-vulnerable patterns at lexer definition time
2. Pattern rewriting guide for safe regex construction
3. Fuzz testing infrastructure for lexer validation
4. Runtime timeout safeguard as defense-in-depth

---

## Motivation

### The Problem

Pygments has had multiple CVEs for ReDoS vulnerabilities:

| CVE | Component | Impact |
|-----|-----------|--------|
| CVE-2022-40896 | SmithyLexer | DoS via crafted input |
| CVE-2021-27291 | Multiple lexers | Infinite loop |
| CVE-2021-20270 | SMLLexer | DoS via crafted input |

The root cause: **regex patterns with nested quantifiers** that exhibit exponential backtracking on adversarial input.

### Why Rosettes Is Currently Vulnerable

Rosettes uses regex-based tokenization (see `_base.py:PatternLexer`). Current safeguards:

```python
# Complexity guards (necessary but insufficient)
MAX_RULES = 50           # Prevents alternation explosion
MAX_PATTERN_LENGTH = 10000  # Caps combined pattern size
```

These prevent *accidental* complexity but don't detect *pathological* patterns.

**Example vulnerable pattern in Python lexer:**

```python
# Nested quantifiers — classic ReDoS shape
r'[fF]"[^"\\]*(?:\\.[^"\\]*)*"'
#              ↑______________↑ outer *
#                    ↑______↑   inner *
```

With input like `f"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"x`, the regex engine backtracks exponentially.

### Why Not Tree-Sitter?

Tree-sitter provides proper parsing that doesn't suffer from ReDoS. However:

| Constraint | Issue |
|------------|-------|
| **Not free-threaded** | Tree-sitter's Python bindings use the GIL; incompatible with Python 3.14t goals |
| **C dependency** | Rosettes is pure Python by design |
| **Grammar complexity** | Requires maintaining separate grammar files |

**Decision**: Stay with regex-based approach but make it safe.

---

## Design

### Defense Layers

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: Static Analysis (compile-time rejection)   │
├─────────────────────────────────────────────────────┤
│ Layer 2: Pattern Guidelines (safe construction)     │
├─────────────────────────────────────────────────────┤
│ Layer 3: Fuzz Testing (CI validation)               │
├─────────────────────────────────────────────────────┤
│ Layer 4: Runtime Timeout (defense-in-depth)         │
└─────────────────────────────────────────────────────┘
```

---

## Layer 1: Static Pattern Analysis

### Implementation

Add a `validate_pattern()` function called during `PatternLexer.__init_subclass__`:

```python
# rosettes/lexers/_safety.py

import re
from typing import NamedTuple

class PatternRisk(NamedTuple):
    """Result of pattern safety analysis."""
    is_safe: bool
    risk_level: str  # "safe", "warning", "dangerous"
    reason: str
    suggestion: str | None


# Known dangerous pattern shapes
_DANGEROUS_PATTERNS = [
    # Nested quantifiers: (a+)+ or (a*)*
    (r'\([^)]*[+*][^)]*\)[+*]', 'nested quantifiers'),
    # Overlapping alternation: (a|a)+
    (r'\([^)]*\|[^)]*\)[+*]', 'overlapping alternation with quantifier'),
    # Greedy followed by same class: .*x.*
    (r'\.\*[^*]*\.\*', 'multiple greedy wildcards'),
    # Quantifier on group with quantifier inside: (x+y+)+
    (r'\([^)]*[+*][^)]*[+*][^)]*\)[+*]', 'multiple quantifiers in repeated group'),
]

_WARNING_PATTERNS = [
    # Non-greedy on large classes: [\s\S]*?
    (r'\[\\s\\S\]\*\?', 'non-greedy on universal class'),
    # Backtracking anchor: ^.*x
    (r'\^\.\*', 'greedy wildcard after anchor'),
]


def validate_pattern(pattern: re.Pattern[str], lexer_name: str) -> PatternRisk:
    """Analyze a regex pattern for ReDoS vulnerability.

    Returns:
        PatternRisk with safety assessment.

    Note:
        This is heuristic-based, not a formal proof.
        Some safe patterns may be flagged; some unsafe patterns may pass.
        Use in combination with fuzz testing.
    """
    source = pattern.pattern

    # Check dangerous patterns
    for shape, reason in _DANGEROUS_PATTERNS:
        if re.search(shape, source):
            return PatternRisk(
                is_safe=False,
                risk_level="dangerous",
                reason=f"Pattern contains {reason}",
                suggestion=_suggest_fix(reason),
            )

    # Check warning patterns
    for shape, reason in _WARNING_PATTERNS:
        if re.search(shape, source):
            return PatternRisk(
                is_safe=True,  # Allow but warn
                risk_level="warning",
                reason=f"Pattern contains {reason}",
                suggestion=_suggest_fix(reason),
            )

    return PatternRisk(
        is_safe=True,
        risk_level="safe",
        reason="No known dangerous patterns detected",
        suggestion=None,
    )


def _suggest_fix(reason: str) -> str:
    """Suggest a fix for the identified pattern issue."""
    suggestions = {
        'nested quantifiers': 'Use atomic group (?>...) or possessive quantifier *+',
        'overlapping alternation with quantifier': 'Make alternation mutually exclusive',
        'multiple greedy wildcards': 'Use non-greedy .*? or anchor the match',
        'multiple quantifiers in repeated group': 'Flatten the pattern or use atomic groups',
        'non-greedy on universal class': 'Consider using negated class [^x]* instead',
        'greedy wildcard after anchor': 'Use [^\\n]* for line-bounded match',
    }
    return suggestions.get(reason, 'Review pattern for backtracking potential')
```

### Integration with PatternLexer

```python
# rosettes/lexers/_base.py

from rosettes.lexers._safety import validate_pattern, PatternRisk

class PatternLexer:
    # ... existing code ...

    # Safety configuration
    REJECT_DANGEROUS: bool = True  # Fail on dangerous patterns
    WARN_RISKY: bool = True        # Log warnings for risky patterns

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Pre-compile combined regex pattern for the lexer."""
        super().__init_subclass__(**kwargs)

        if not cls.rules:
            return

        # Existing complexity checks...
        if len(cls.rules) > cls.MAX_RULES:
            raise ValueError(...)

        # NEW: Validate each pattern for ReDoS
        for i, rule in enumerate(cls.rules):
            risk = validate_pattern(rule.pattern, cls.name)

            if risk.risk_level == "dangerous" and cls.REJECT_DANGEROUS:
                raise ValueError(
                    f"Lexer {cls.name!r} rule {i} has dangerous pattern: "
                    f"{risk.reason}. {risk.suggestion}"
                )

            if risk.risk_level == "warning" and cls.WARN_RISKY:
                import warnings
                warnings.warn(
                    f"Lexer {cls.name!r} rule {i}: {risk.reason}. "
                    f"{risk.suggestion}",
                    stacklevel=2,
                )

        # ... rest of existing code ...
```

---

## Layer 2: Pattern Guidelines

### Safe Pattern Construction

| Instead Of | Use | Why |
|------------|-----|-----|
| `(a+)+` | `a+` or `(?>a+)+` | Avoid nested quantifiers |
| `.*x.*` | `[^x]*x.*` | Anchor the first wildcard |
| `"[^"\\]*(?:\\.[^"\\]*)*"` | `"(?:[^"\\]|\\.)*"` | Simpler alternation |
| `[\s\S]*?x` | `[^x]*x` | Negated class is linear |
| `(a\|ab)+` | `a+b?` or `ab?\|a` | No overlapping alternation |

### Atomic Groups and Possessive Quantifiers

Python 3.11+ supports atomic groups via `(?>...)`:

```python
# Before: vulnerable to backtracking
r'"[^"\\]*(?:\\.[^"\\]*)*"'

# After: atomic group prevents backtracking
r'"(?>(?:[^"\\]|\\.)*)"'
```

Possessive quantifiers (`*+`, `++`, `?+`) are NOT supported in Python's `re` module. Alternative: use `regex` module or atomic groups.

### String Matching Best Practices

For string literals (common ReDoS vector):

```python
# SAFE: Character-by-character with no nesting
STRING_DOUBLE = re.compile(r'"(?:[^"\\]|\\.)*"')
STRING_SINGLE = re.compile(r"'(?:[^'\\]|\\.)*'")

# SAFE: Use non-capturing atomic-style pattern
# The alternation is mutually exclusive (can't match both sides)
STRING_ESCAPE = re.compile(r'"(?:[^"\\]|\\[nrtfvae0"\\]|\\x[0-9a-fA-F]{2})*"')
```

### Triple-Quoted Strings

```python
# DANGEROUS: non-greedy on universal class
r'"""[\s\S]*?"""'

# SAFER: Explicit negation with lookahead
r'"""(?:(?!""")[^\\]|\\.)*"""'

# SAFEST: Two-phase approach (find delimiters, validate content separately)
# This avoids regex complexity entirely for content matching
```

---

## Layer 3: Fuzz Testing

### Infrastructure

```python
# tests/fuzz/test_lexer_redos.py

import time
import pytest
from hypothesis import given, strategies as st, settings

from rosettes import list_languages, get_lexer

# ReDoS payloads that have caused issues in other highlighters
REDOS_PAYLOADS = [
    # Nested quotes
    '"' + '\\"' * 100 + 'x',
    "'" + "\\'" * 100 + 'x',
    # Repetitive escape sequences  
    '"""' + '\\n' * 1000 + 'x',
    # Malformed strings
    'f"' + '\\' * 100,
    # Deep nesting
    '(' * 100 + 'x' + ')' * 100,
    # Comment-like patterns
    '#' + 'a' * 10000,
    '/*' + '*' * 10000 + 'x',
]

TIMEOUT_SECONDS = 0.5  # Any lexer should tokenize test payloads in <500ms


@pytest.mark.parametrize("language", list_languages())
@pytest.mark.parametrize("payload", REDOS_PAYLOADS)
def test_lexer_no_redos(language: str, payload: str) -> None:
    """Ensure lexers don't hang on adversarial input."""
    lexer = get_lexer(language)

    start = time.perf_counter()
    # Consume all tokens (force evaluation of generator)
    list(lexer.tokenize(payload))
    elapsed = time.perf_counter() - start

    assert elapsed < TIMEOUT_SECONDS, (
        f"Lexer {language!r} took {elapsed:.2f}s on payload, "
        f"possible ReDoS vulnerability"
    )


@given(st.text(min_size=1, max_size=10000))
@settings(max_examples=1000, deadline=500)  # 500ms deadline
def test_lexer_random_input(text: str) -> None:
    """Fuzz test with random input."""
    for language in ["python", "javascript", "json"]:  # Core languages
        lexer = get_lexer(language)
        # Should complete without hanging
        list(lexer.tokenize(text))
```

### CI Integration

```yaml
# .github/workflows/security.yml
name: Security - ReDoS Testing

on:
  push:
    paths:
      - 'rosettes/lexers/**'
  pull_request:
    paths:
      - 'rosettes/lexers/**'

jobs:
  redos-fuzz:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -e ".[test]" hypothesis

      - name: Run ReDoS fuzz tests
        run: pytest tests/fuzz/test_lexer_redos.py -v --timeout=60
```

---

## Layer 4: Runtime Timeout

### Defense-in-Depth

Even with static analysis and fuzz testing, add a runtime safeguard:

```python
# rosettes/_timeout.py

import signal
import sys
from contextlib import contextmanager
from typing import Iterator

class TokenizationTimeout(Exception):
    """Raised when tokenization exceeds time limit."""
    pass


@contextmanager
def tokenize_timeout(seconds: float = 5.0) -> Iterator[None]:
    """Context manager that limits tokenization time.

    Note:
        Only works on Unix (uses SIGALRM).
        On Windows, this is a no-op.

    Args:
        seconds: Maximum time allowed for tokenization.

    Raises:
        TokenizationTimeout: If tokenization exceeds time limit.
    """
    if sys.platform == "win32":
        yield  # No timeout support on Windows
        return

    def handler(signum, frame):
        raise TokenizationTimeout(
            f"Tokenization exceeded {seconds}s limit. "
            "This may indicate a ReDoS vulnerability or extremely large input."
        )

    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
```

### Usage in Highlight API

```python
# rosettes/__init__.py

from rosettes._timeout import tokenize_timeout, TokenizationTimeout

def highlight(
    code: str,
    language: str,
    *,
    timeout: float | None = 5.0,  # Default 5 second timeout
    **kwargs,
) -> str:
    """Highlight source code.

    Args:
        code: Source code to highlight.
        language: Language name or alias.
        timeout: Maximum seconds for tokenization. None to disable.

    Raises:
        TokenizationTimeout: If tokenization exceeds timeout.
    """
    lexer = get_lexer(language)
    formatter = get_formatter(**kwargs)

    if timeout is not None:
        with tokenize_timeout(timeout):
            tokens = list(lexer.tokenize(code))
    else:
        tokens = list(lexer.tokenize(code))

    return formatter.format(tokens)
```

---

## Migration Plan

### Phase 1: Add Safety Infrastructure (Week 1)

| Task | Priority |
|------|----------|
| Implement `_safety.py` with pattern validator | P0 |
| Add validation to `PatternLexer.__init_subclass__` | P0 |
| Create fuzz test suite | P0 |
| Add runtime timeout | P1 |

### Phase 2: Audit Existing Lexers (Week 1-2)

| Task | Priority |
|------|----------|
| Run validator on all lexers, collect warnings | P0 |
| Rewrite dangerous patterns in Python lexer | P0 |
| Rewrite dangerous patterns in JavaScript lexer | P0 |
| Rewrite dangerous patterns in all other lexers | P1 |
| Add lexer-specific fuzz payloads | P1 |

### Phase 3: CI Integration (Week 2)

| Task | Priority |
|------|----------|
| Add ReDoS fuzz tests to CI | P0 |
| Add pattern validation to pre-commit | P1 |
| Document pattern guidelines in CONTRIBUTING.md | P1 |

---

## Known Limitations

| Limitation | Mitigation |
|------------|------------|
| Static analysis is heuristic, not formal | Combine with fuzz testing |
| Timeout only works on Unix | Document Windows limitation |
| Some safe patterns may be flagged | Allow `# safety: ignore` annotation |
| Python `re` lacks possessive quantifiers | Use atomic groups or `regex` module |

---

## Success Criteria

- [ ] All existing lexers pass static pattern validation
- [ ] All existing lexers pass fuzz testing with 1000+ random inputs
- [ ] No lexer takes >500ms on any adversarial payload
- [ ] CI blocks PRs that introduce dangerous patterns
- [ ] Pattern guidelines documented for contributors

---

## Appendix: Audited Patterns

### Python Lexer (Current State)

| Pattern | Risk | Action |
|---------|------|--------|
| `r'"""[\s\S]*?"""'` | Warning | Rewrite with negation |
| `r'[fF]"[^"\\]*(?:\\.[^"\\]*)*"'` | Dangerous | Use atomic alternation |
| `r'"[^"\\]*(?:\\.[^"\\]*)*"'` | Dangerous | Use atomic alternation |

### JavaScript Lexer (Current State)

| Pattern | Risk | Action |
|---------|------|--------|
| Template literals | Warning | Review for backtracking |
| Regex literals | Dangerous | Needs careful rewrite |

*(Full audit to be completed in Phase 2)*

---

## References

- [ReDoS - Wikipedia](https://en.wikipedia.org/wiki/ReDoS)
- [CVE-2022-40896 - Pygments SmithyLexer](https://nvd.nist.gov/vuln/detail/CVE-2022-40896)
- [Atomic Grouping - Python 3.11+](https://docs.python.org/3/library/re.html#index-24)
- [regex module (third-party)](https://github.com/mrabarnett/mrab-regex) - Supports possessive quantifiers
