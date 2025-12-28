# RFC: Patitas Structural Validation — Unified Error Handling for Markdown Syntax

| Field | Value |
|-------|-------|
| **RFC ID** | `rfc-patitas-structural-validation` |
| **Status** | Draft |
| **Created** | 2025-12-28 |
| **Updated** | 2025-12-28 |
| **Depends On** | `rfc-patitas-markdown-parser` |
| **Supersedes** | H201 (syntax errors), H202 (fence nesting) in Bengal health checks |

---

## Executive Summary

Patitas should emit structural validation errors (unclosed directives, mismatched fences) as part of its lexer/parser, eliminating the need for Bengal's duplicate validation logic. This provides:

1. **Single source of truth** — One lexer, one set of rules
2. **Better errors** — Patitas has precise source locations
3. **Standalone value** — Any tool using patitas gets validation for free
4. **Fewer false positives** — Current Bengal validators have bugs due to reimplementing fence logic

---

## Problem Statement

### Current Architecture (Redundant)

```
┌─────────────────────────────────────────────────────────────────┐
│  DUPLICATE VALIDATION LOGIC                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  patitas/lexer.py              health/validators/directives/   │
│  ┌─────────────────┐           ┌─────────────────────────────┐ │
│  │ Stack-based     │           │ Regex-based fence scanner   │ │
│  │ directive_stack │           │ _check_code_block_nesting() │ │
│  │ mode switching  │           │ validate_nested_fences()    │ │
│  │                 │           │                             │ │
│  │ CORRECT         │           │ BUGGY (false positives)     │ │
│  └─────────────────┘           └─────────────────────────────┘ │
│           │                              │                      │
│           ▼                              ▼                      │
│    Silent on errors              H201/H202 warnings             │
│    (best-effort parse)           (often wrong)                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Observed False Positives

From `bengal validate` on the Bengal documentation site:

```
! Directives (2 warning(s))
  • [H202] 5 directive(s) have fence nesting issues
    docs/reference/directives/admonitions.md:99 - Inner code block conflicts
    with outer directive at line 84. Fix: Change outer to 4+ backticks.
```

**Analysis:** Lines 84-92 contain a properly closed 5-backtick code block. Line 99 starts a *new* 5-backtick block. The health validator's stack logic fails to pop at line 92, incorrectly flagging line 99 as nested.

**Root cause:** The health validator reimplements fence detection with different (buggy) logic instead of using patitas's battle-tested lexer.

### The Gap in Patitas

Currently, patitas does best-effort parsing:

```python
# lexer.py:127-140
def tokenize(self) -> Iterator[Token]:
    while self._pos < source_len:
        yield from self._dispatch_mode()

    # Just emits EOF — doesn't check for unclosed structures!
    yield Token(TokenType.EOF, "", self._location())
```

If a directive is never closed, patitas silently treats all remaining content as part of that directive. No error is raised.

---

## Proposed Solution

### 1. Add ERROR Token Type

```python
# tokens.py
class TokenType(Enum):
    # ... existing types ...

    # Structural errors (emitted by lexer)
    ERROR = auto()  # Syntax/structural error with message
```

### 2. Emit Errors at EOF for Unclosed Structures

```python
# lexer.py
def tokenize(self) -> Iterator[Token]:
    while self._pos < source_len:
        yield from self._dispatch_mode()

    # NEW: Check for unclosed directives
    for line_num, colon_count, name in self._directive_stack:
        yield Token(
            TokenType.ERROR,
            f"Directive '{name}' opened at line {line_num} but never closed. "
            f"Add closing {':::'  if colon_count == 3 else ':' * colon_count} fence.",
            SourceLocation(line_num, 1, self._source_file),
        )

    # NEW: Check for unclosed code fence
    if self._mode == LexerMode.CODE_FENCE:
        yield Token(
            TokenType.ERROR,
            f"Code block opened at line {self._fence_start_line} but never closed. "
            f"Add closing {self._fence_char * self._fence_count} fence.",
            SourceLocation(self._fence_start_line, 1, self._source_file),
        )

    yield Token(TokenType.EOF, "", self._location())
```

### 3. Add Convenience Validation Method

```python
# __init__.py or wrapper.py
@dataclass(frozen=True, slots=True)
class ValidationError:
    """Structural validation error from patitas."""
    message: str
    line: int
    column: int
    file: str | None = None

    def __str__(self) -> str:
        loc = f"{self.file}:" if self.file else ""
        return f"{loc}{self.line}:{self.column}: {self.message}"


def validate(
    source: str,
    source_file: str | None = None,
) -> list[ValidationError]:
    """Validate Markdown structural syntax without full parse.

    Returns list of validation errors. Empty list = valid.

    Checks:
    - Unclosed directives (:::{name} without closing :::)
    - Unclosed code fences (``` without closing ```)
    - Mismatched fence lengths
    - Orphaned closing fences

    Example:
        >>> errors = patitas.validate(":::{note}\\nNo closing fence")
        >>> print(errors[0])
        1:1: Directive 'note' opened at line 1 but never closed.
    """
    lexer = Lexer(source, source_file=source_file)
    errors = []

    for token in lexer.tokenize():
        if token.type == TokenType.ERROR:
            errors.append(ValidationError(
                message=token.value,
                line=token.location.line,
                column=token.location.column,
                file=token.location.file,
            ))

    return errors
```

### 4. Bengal Integration

```python
# bengal/health/validators/directives/analysis.py

from bengal.rendering.parsers.patitas import validate as patitas_validate

class DirectiveAnalyzer:
    def analyze(self, site: Site, build_context: BuildContext | None = None) -> dict:
        data = {
            "syntax_errors": [],  # Now from patitas
            # ... other fields ...
        }

        for page in site.pages:
            content = self._get_content(page, build_context)

            # NEW: Use patitas for structural validation
            errors = patitas_validate(content, source_file=str(page.source_path))
            for error in errors:
                data["syntax_errors"].append({
                    "page": page.source_path,
                    "line": error.line,
                    "type": "structural",
                    "error": error.message,
                })

            # Keep semantic validation (completeness, performance, etc.)
            self._check_directive_completeness(content, page, data)
            self._check_directive_performance(content, page, data)
```

---

## Code to Remove from Bengal

Once patitas handles structural validation, delete:

| File | Function/Code | Lines | Reason |
|------|---------------|-------|--------|
| `health/validators/directives/analysis.py` | `_check_code_block_nesting()` | ~80 | Patitas handles this |
| `health/validators/directives/analysis.py` | `_build_code_block_index()` | ~70 | No longer needed |
| `health/validators/directives/analysis.py` | `_build_colon_directive_index()` | ~50 | No longer needed |
| `health/validators/directives/analysis.py` | `_is_line_inside_ranges()` | ~10 | No longer needed |
| `directives/validator.py` | `validate_nested_fences()` | ~160 | Patitas handles this |
| `health/validators/directives/checkers.py` | H201 syntax error reporting | ~20 | Use patitas errors |
| `health/validators/directives/checkers.py` | H202 fence nesting reporting | ~60 | Use patitas errors |

**Estimated removal:** ~450 lines of duplicate/buggy code

---

## Health Check Code Mapping

| Old Code | New Source | Notes |
|----------|------------|-------|
| H201 (syntax errors) | `patitas.validate()` | Unified structural errors |
| H202 (fence nesting) | `patitas.validate()` | No more false positives |
| H203 (completeness) | Keep in Bengal | Semantic check |
| H204 (improvements) | Keep in Bengal | Semantic check |
| H205 (performance) | Keep in Bengal | Bengal-specific |
| H206 (too many tabs) | Keep in Bengal | Bengal-specific |

---

## Error Message Quality

Patitas errors should be actionable:

```
# Bad (vague)
Line 45: Syntax error

# Good (actionable)
Line 45: Directive 'tab-set' opened with :::: but never closed.
Add closing :::: fence, or use named closer ::::{/tab-set}.
```

### Error Templates

```python
ERRORS = {
    "unclosed_directive": (
        "Directive '{name}' opened at line {line} but never closed. "
        "Add closing {fence} fence."
    ),
    "unclosed_code_fence": (
        "Code block opened at line {line} but never closed. "
        "Add closing {fence} fence."
    ),
    "orphaned_closer": (
        "Closing fence {fence} at line {line} has no matching opener."
    ),
    "mismatched_fence": (
        "Closing fence {close_fence} at line {line} doesn't match "
        "opener {open_fence} at line {open_line}. Use {expected} to close."
    ),
}
```

---

## Testing Strategy

### Unit Tests for Patitas Validation

```python
# tests/unit/patitas/test_validation.py

class TestValidation:
    def test_unclosed_directive(self):
        errors = patitas.validate(":::{note}\nContent without close")
        assert len(errors) == 1
        assert "never closed" in errors[0].message
        assert errors[0].line == 1

    def test_unclosed_code_fence(self):
        errors = patitas.validate("```python\ncode without close")
        assert len(errors) == 1
        assert "never closed" in errors[0].message

    def test_valid_nested_directives(self):
        content = """\
::::{tab-set}
:::{tab} One
Content
:::
::::
"""
        errors = patitas.validate(content)
        assert errors == []

    def test_named_closer(self):
        content = """\
:::{note}
Content
:::{/note}
"""
        errors = patitas.validate(content)
        assert errors == []

    def test_code_block_inside_directive(self):
        # This was a false positive in the old validator
        content = """\
:::{tab-item} Example
```python
code here
```
:::
"""
        errors = patitas.validate(content)
        assert errors == []  # Should NOT flag as nesting issue
```

### Integration Tests

```python
# tests/integration/test_health_patitas.py

def test_health_check_uses_patitas():
    """Verify health check delegates to patitas for structural validation."""
    # Create page with unclosed directive
    page = create_test_page(":::{note}\nNo close")

    # Run health check
    results = run_health_check([page])

    # Should report error from patitas, not old validator
    assert any("never closed" in r.message for r in results)
    assert not any("H202" in r.code for r in results)  # Old code gone
```

---

## Migration Plan

### Phase 1: Add Patitas Validation (Non-Breaking)

1. Add `TokenType.ERROR` to patitas
2. Add EOF checks in lexer for unclosed structures
3. Add `patitas.validate()` convenience function
4. Add comprehensive tests

### Phase 2: Bengal Integration

1. Update `DirectiveAnalyzer` to use `patitas.validate()`
2. Update `check_directive_syntax()` to format patitas errors
3. Keep H201/H202 codes for backwards compatibility (map from patitas errors)

### Phase 3: Remove Dead Code

1. Delete `_check_code_block_nesting()` and related functions
2. Delete `validate_nested_fences()` from directive validator
3. Remove `CodeBlockRange` and `ColonDirectiveRange` dataclasses
4. Update tests to remove old validator tests

### Phase 4: Documentation

1. Update health check documentation
2. Document `patitas.validate()` for standalone users
3. Add examples to patitas README

---

## Standalone Patitas Value

This enhancement makes patitas more valuable as a standalone library:

```python
# Any Python project can use patitas for Markdown validation
import patitas

def lint_markdown(path: str) -> list[str]:
    """Lint a Markdown file for structural issues."""
    content = Path(path).read_text()
    errors = patitas.validate(content, source_file=path)
    return [str(e) for e in errors]

# CLI tool
if __name__ == "__main__":
    for path in sys.argv[1:]:
        for error in lint_markdown(path):
            print(error)
```

---

## Success Criteria

1. **Zero false positives** on Bengal documentation site
2. **~450 lines removed** from Bengal codebase
3. **Patitas standalone validation** works without Bengal
4. **Actionable error messages** with line numbers and fix suggestions
5. **All existing tests pass** (or are updated for new behavior)

---

## Open Questions

1. **Should patitas collect all errors or fail-fast?**
   - Recommendation: Collect all (better UX for linting)

2. **Should ERROR tokens halt parsing or allow continuation?**
   - Recommendation: Continue parsing for maximum error reporting

3. **Should we add a `strict` mode that raises exceptions?**
   - Recommendation: No, keep it simple. Users can check `len(errors) > 0`

---

## References

- `rfc-patitas-markdown-parser.md` — Patitas architecture
- `bengal/health/validators/directives/analysis.py` — Current buggy validator
- `bengal/directives/validator.py:240-401` — `validate_nested_fences()` to remove
