# RFC: Rosettes Language Auto-Detection

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-0003 |
| **Title** | Rosettes Language Auto-Detection |
| **Status** | Draft |
| **Created** | 2025-12-24 |
| **Author** | Bengal Core Team |
| **Depends On** | RFC-0002 (Rosettes Syntax Highlighter) |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Add `guess_lexer()` function to rosettes that infers language from filename/shebang |
| **Why** | DRY — eliminate duplicate extension maps in Bengal and rosettes |
| **Effort** | 1-2 hours |
| **Risk** | None — O(1) dict lookups, no content analysis |
| **Performance** | < 1μs overhead (single dict lookup) |

**Key Insight**: Rosettes lexers already declare `filenames` and `mimetypes` properties. This metadata is unused. Exposing it via a `guess_lexer()` function eliminates Bengal's duplicate 40+ entry extension map.

---

## Motivation

### Problem: Duplicate Extension Maps

Bengal's `literalinclude` directive maintains its own hardcoded map:

```python
# bengal/directives/literalinclude.py:168-215
ext_map = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    # ... 40+ entries
}
```

Meanwhile, rosettes lexers already declare this information:

```python
# rosettes/lexers/yaml.py:32-35
class YamlLexer(PatternLexer):
    name = "yaml"
    aliases = ("yml",)
    filenames = ("*.yaml", "*.yml")
    mimetypes = ("text/yaml", "application/x-yaml")
```

**Two maps doing the same thing**. When a new lexer is added to rosettes, Bengal's map must be manually updated or it drifts.

### Current Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Markdown: ```python                                            │
│            print("hello")                                       │
│            ```                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Mistune Parser                                                 │
│  Extracts: code="print('hello')", info="python"    ✅ FREE     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Bengal Highlighting Plugin                                     │
│  Calls: rosettes.highlight(code, language="python")             │
└─────────────────────────────────────────────────────────────────┘
```

The language hint is already extracted **for free** by the markdown parser. No auto-detection needed for fenced code blocks.

### The Real Use Case: `literalinclude`

```markdown
```{literalinclude} config/settings.yaml
```
```

Here Bengal has the filename but needs to infer "yaml". Currently it uses its own map. Should use rosettes' metadata.

---

## Design

### API

```python
# rosettes/__init__.py
def guess_lexer(
    *,
    filename: str | None = None,
    mimetype: str | None = None,
    code: str | None = None,  # Only for shebang, NOT full content analysis
) -> Lexer:
    """
    Guess lexer from hints. O(1) lookups only.

    Priority:
    1. Filename extension (instant)
    2. MIME type (instant)
    3. Shebang in first line (fast, <100 bytes scanned)

    Does NOT perform full content analysis (too slow for hot path).

    Args:
        filename: File path or name (e.g., "config.yaml")
        mimetype: MIME type (e.g., "text/yaml")
        code: Source code (only first line checked for shebang)

    Returns:
        Lexer instance

    Raises:
        LookupError: Cannot determine language from provided hints

    Example:
        >>> lexer = guess_lexer(filename="config.yaml")
        >>> lexer.name
        'yaml'

        >>> lexer = guess_lexer(code="#!/usr/bin/env python\\nprint('hi')")
        >>> lexer.name
        'python'
    """
```

### Convenience Wrapper

```python
def guess_language(
    *,
    filename: str | None = None,
    mimetype: str | None = None,
    code: str | None = None,
) -> str | None:
    """
    Guess language name from hints. Returns None if unknown.

    Same as guess_lexer() but returns language name string,
    and returns None instead of raising LookupError.

    Example:
        >>> guess_language(filename="config.yaml")
        'yaml'

        >>> guess_language(filename="unknown.xyz")
        None
    """
    try:
        return guess_lexer(filename=filename, mimetype=mimetype, code=code).name
    except LookupError:
        return None
```

### Implementation

```python
# rosettes/_detection.py
from __future__ import annotations

import re
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._protocol import Lexer

from ._registry import _LEXER_SPECS, get_lexer

__all__ = ["guess_lexer", "guess_language"]

# Build extension → language map from lexer specs (computed once at import)
_EXT_TO_LANGUAGE: dict[str, str] = {}
_MIME_TO_LANGUAGE: dict[str, str] = {}

def _build_lookup_tables() -> None:
    """Build lookup tables from lexer specs. Called once at module load."""
    for name, spec in _LEXER_SPECS.items():
        # Get lexer class to read filenames/mimetypes
        # Note: This is lazy - we only import the module, not instantiate
        from importlib import import_module
        module = import_module(spec.module)
        lexer_class = getattr(module, spec.class_name)

        # Extract filenames (e.g., "*.py", "*.yaml")
        for pattern in getattr(lexer_class, "filenames", ()):
            if pattern.startswith("*."):
                ext = pattern[1:]  # "*.py" → ".py"
                _EXT_TO_LANGUAGE[ext.lower()] = name

        # Extract mimetypes
        for mime in getattr(lexer_class, "mimetypes", ()):
            _MIME_TO_LANGUAGE[mime.lower()] = name

# Shebang patterns (order matters - most specific first)
_SHEBANG_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"python3?"), "python"),
    (re.compile(r"node|nodejs"), "javascript"),
    (re.compile(r"ruby"), "ruby"),
    (re.compile(r"perl"), "perl"),
    (re.compile(r"php"), "php"),
    (re.compile(r"bash|sh|zsh|ksh"), "bash"),
    (re.compile(r"fish"), "fish"),
    (re.compile(r"lua"), "lua"),
    (re.compile(r"ruby"), "ruby"),
)


def _detect_from_shebang(first_line: str) -> str | None:
    """Extract language from shebang line."""
    if not first_line.startswith("#!"):
        return None
    # Extract interpreter: "#!/usr/bin/env python3" → "python3"
    parts = first_line[2:].strip().split()
    if not parts:
        return None
    interpreter = Path(parts[-1]).name  # Handle "env python" case
    if parts[0].endswith("env") and len(parts) > 1:
        interpreter = parts[1]

    for pattern, language in _SHEBANG_PATTERNS:
        if pattern.search(interpreter):
            return language
    return None


def guess_lexer(
    *,
    filename: str | None = None,
    mimetype: str | None = None,
    code: str | None = None,
) -> Lexer:
    """Guess lexer from hints. O(1) lookups only."""
    # Ensure lookup tables are built
    if not _EXT_TO_LANGUAGE:
        _build_lookup_tables()

    # Priority 1: Filename extension
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in _EXT_TO_LANGUAGE:
            return get_lexer(_EXT_TO_LANGUAGE[ext])

    # Priority 2: MIME type
    if mimetype:
        mime_lower = mimetype.lower().split(";")[0].strip()
        if mime_lower in _MIME_TO_LANGUAGE:
            return get_lexer(_MIME_TO_LANGUAGE[mime_lower])

    # Priority 3: Shebang (first line only, <128 bytes)
    if code:
        first_line = code[:128].split("\n", 1)[0]
        lang = _detect_from_shebang(first_line)
        if lang:
            return get_lexer(lang)

    raise LookupError(
        f"Cannot guess language. Provide filename, mimetype, or code with shebang. "
        f"filename={filename!r}, mimetype={mimetype!r}, code={'...' if code else None}"
    )


def guess_language(
    *,
    filename: str | None = None,
    mimetype: str | None = None,
    code: str | None = None,
) -> str | None:
    """Guess language name. Returns None if unknown."""
    try:
        return guess_lexer(filename=filename, mimetype=mimetype, code=code).name
    except LookupError:
        return None
```

---

## Performance Analysis

| Operation | Cost | Notes |
|-----------|------|-------|
| Lookup tables built | Once at import | Lazy, ~1ms |
| `guess_language(filename=...)` | O(1) | Single dict lookup |
| `guess_language(mimetype=...)` | O(1) | Single dict lookup |
| `guess_language(code=...)` | O(n) where n≤128 | First line only |

**Comparison to Pygments `guess_lexer()`**:

| Approach | Time | Accuracy |
|----------|------|----------|
| Pygments `guess_lexer()` | 10-100ms | High (tries all lexers) |
| Rosettes `guess_lexer()` | < 1μs | Good (hints only) |

**Trade-off**: Rosettes requires at least one hint (filename, mimetype, or shebang). It will NOT analyze full content to guess language. This is intentional — content analysis is too slow for the hot path (rendering 50+ code blocks per page).

---

## Bengal Integration

### Before (Duplicate Map)

```python
# bengal/directives/literalinclude.py
def _detect_language(self, path: str) -> str | None:
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        # ... 40+ entries maintained separately
    }
    ext = Path(path).suffix.lower()
    return ext_map.get(ext)
```

### After (Use Rosettes)

```python
# bengal/directives/literalinclude.py
from rosettes import guess_language

def _detect_language(self, path: str) -> str | None:
    return guess_language(filename=path)
```

**Benefits**:
- Single source of truth (rosettes lexer metadata)
- Automatic sync when new lexers added
- ~45 lines deleted from Bengal

### Fenced Code Blocks (No Change Needed)

Fenced code blocks already have the language in the info string:

```markdown
```python
print("hello")
```
```

The markdown parser extracts `"python"` for free. Auto-detection is only needed when:
1. User writes bare ` ``` ` without language
2. `literalinclude` directive without `:language:` option

---

## Migration Path

### Phase 1: Add to Rosettes (This RFC)

1. Add `_detection.py` module
2. Export `guess_lexer()` and `guess_language()` from `__init__.py`
3. Add tests

### Phase 2: Update Bengal

1. Replace `literalinclude._detect_language()` with `guess_language()`
2. Delete the 45-line `ext_map` dict
3. Optionally: Add fallback for bare fenced code blocks

### Phase 3: Documentation

1. Document `guess_lexer()` API
2. Add examples to README

---

## Alternatives Considered

### 1. Full Content Analysis (Rejected)

**Approach**: Analyze code content to guess language (like Pygments).

**Rejected because**:
- Too slow for hot path (10-100ms per block)
- Inaccurate for short snippets
- Not needed — hints are almost always available

### 2. ML-Based Detection (Rejected)

**Approach**: Use a trained model to classify code.

**Rejected because**:
- Overkill for this use case
- Adds dependencies
- Latency unacceptable for SSG

### 3. Keep Duplicate Maps (Status Quo)

**Approach**: Maintain separate maps in Bengal and rosettes.

**Rejected because**:
- DRY violation
- Drift risk
- More code to maintain

---

## Testing

```python
# tests/test_detection.py
import pytest
from rosettes import guess_lexer, guess_language

class TestGuessLanguage:
    """Test language detection from hints."""

    @pytest.mark.parametrize("filename,expected", [
        ("config.yaml", "yaml"),
        ("config.yml", "yaml"),
        ("script.py", "python"),
        ("app.js", "javascript"),
        ("main.rs", "rust"),
        ("Dockerfile", None),  # No extension
        ("unknown.xyz", None),  # Unknown extension
    ])
    def test_from_filename(self, filename: str, expected: str | None) -> None:
        assert guess_language(filename=filename) == expected

    @pytest.mark.parametrize("mimetype,expected", [
        ("text/yaml", "yaml"),
        ("application/json", "json"),
        ("text/html", "html"),
        ("text/x-python", "python"),
    ])
    def test_from_mimetype(self, mimetype: str, expected: str) -> None:
        assert guess_language(mimetype=mimetype) == expected

    @pytest.mark.parametrize("code,expected", [
        ("#!/usr/bin/env python\nprint('hi')", "python"),
        ("#!/bin/bash\necho hello", "bash"),
        ("#!/usr/bin/env node\nconsole.log('hi')", "javascript"),
        ("no shebang here", None),
    ])
    def test_from_shebang(self, code: str, expected: str | None) -> None:
        assert guess_language(code=code) == expected

    def test_priority_filename_over_shebang(self) -> None:
        # Filename takes priority
        result = guess_language(
            filename="script.py",
            code="#!/bin/bash\necho hi"
        )
        assert result == "python"

    def test_guess_lexer_raises_on_unknown(self) -> None:
        with pytest.raises(LookupError):
            guess_lexer(filename="unknown.xyz")
```

---

## Success Criteria

- [ ] `guess_language(filename="config.yaml")` returns `"yaml"`
- [ ] `guess_language(code="#!/usr/bin/env python\n...")` returns `"python"`
- [ ] Performance: < 1μs per call (verified by benchmark)
- [ ] Bengal's `literalinclude` uses `guess_language()` instead of local map
- [ ] 45+ lines deleted from Bengal

---

## Open Questions

1. **Should `guess_language()` support filename without extension?**
   - Example: `Dockerfile`, `Makefile`, `.bashrc`
   - Current: No (returns None)
   - Could add special-case handling

2. **Should we detect from file content patterns?**
   - Example: `<?php` at start → PHP
   - Current: No (too slow)
   - Could add opt-in `analyze_content=True` parameter

---

## References

- [RFC-0002: Rosettes Syntax Highlighter](rfc-rosettes-syntax-highlighter.md)
- [Pygments guess_lexer](https://pygments.org/docs/api/#pygments.lexers.guess_lexer)
- [GitHub Linguist](https://github.com/github/linguist) (inspiration for heuristics)
