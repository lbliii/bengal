# RFC: Kida Parser Hardening & Compile-Time Validation

**Status**: ✅ Completed  
**Created**: 2025-12-26  
**Updated**: 2025-12-26  
**Effort**: Phase 2: ~2 days | Phase 3: ~1.5 days  
**Impact**: High - Prevents runtime crashes, improves developer DX  
**Category**: Compiler / Type Safety / Error Handling  
**Scope**: `bengal/rendering/kida/`

---

## Executive Summary

Kida now has robust **Block Stack Validation** (P0), ensuring that unmatched or mismatched tags are caught during parsing. However, the compiler remains "lazy" regarding external dependencies like filters and tests, and macro recursion with arithmetic fails due to type coercion issues with `Markup` objects.

**The Goal**: Move error detection from "Render-Time" to "Compile-Time" and ensure that macro-driven arithmetic correctly coerces string results to numbers.

**Key Changes**:
1. Validate filter/test names against `Environment._filters`/`_tests` during compilation
2. Add "Did you mean?" suggestions using `difflib.get_close_matches()`
3. Wrap arithmetic operands from macro calls in `_coerce_numeric()` helper

---

## Problems & Opportunities

### P1: Unknown Filters/Tests Caught Too Late (Render-Time)

Currently, Kida compiles filter and test calls into dynamic dictionary lookups without validating that the filter/test exists. This results in a `KeyError` only when the template is rendered.

```python
# ❌ Current: Compiles successfully, fails during render
tmpl = env.from_string("{{ x|unknown_filter }}")  # No error
tmpl.render(x=5)  # KeyError: 'unknown_filter'
```

**Evidence**:

Filter compilation at `expressions.py:204-214`:
```python
# Current: No validation against _filters registry
return ast.Call(
    func=ast.Subscript(
        value=ast.Name(id="_filters", ctx=ast.Load()),
        slice=ast.Constant(value=node.name),  # node.name not validated!
        ctx=ast.Load(),
    ),
    ...
)
```

Test compilation at `expressions.py:148-164`:
```python
# Current: No validation against _tests registry
test_call = ast.Call(
    func=ast.Subscript(
        value=ast.Name(id="_tests", ctx=ast.Load()),
        slice=ast.Constant(value=node.name),  # node.name not validated!
        ...
    ),
    ...
)
```

**Opportunity**: Validate filter and test names against `Environment._filters`/`_tests` during compilation. The compiler already has access to `self._env` (see `expressions.py:47`).

### P2: Macro Recursion Arithmetic Failure (String Multiplication)

Macros return `Markup` objects (a string subclass). When arithmetic operators like `*` are used with macro results, Python performs **string multiplication** instead of numeric multiplication.

```jinja
{% macro factorial(n) %}
  {% if n <= 1 %}1{% else %}{{ n * factorial(n - 1)|int }}{% endif %}
{% endmacro %}
{{ factorial(5) }}

{# ❌ Actual output: "111111111111111111111111111111..." #}
{# 5 * Markup('1') → '11111' (string repeated 5 times, NOT 5 * 1 = 5) #}
```

**Root Cause** (verified in `functions.py:99-119`):

```python
# Macro body is compiled to return Markup-wrapped string
func_body.append(
    ast.Return(
        value=ast.Call(
            func=ast.Name(id="_Markup", ctx=ast.Load()),  # Always Markup!
            args=[
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Constant(value=""),
                        attr="join",
                        ...
                    ),
                    args=[ast.Name(id="buf", ctx=ast.Load())],
                    ...
                ),
            ],
            ...
        ),
    )
)
```

**Failure Chain**:
1. `factorial(1)` returns `Markup('1')` (string, not int)
2. Expression `n * factorial(n-1)` evaluates as `5 * Markup('1')`
3. Python's `str.__rmul__`: `'1' * 5` → `'11111'`
4. The `|int` filter converts `'11111'` → `11111` (wrong!)

**Existing Test** (marked xfail at `test_kida_macros.py:137-147`):

```python
@pytest.mark.xfail(reason="BUG: Recursive macro multiplication not working correctly")
def test_simple_recursion(self, env):
    tmpl = env.from_string(
        "{% macro factorial(n) %}"
        "{% if n <= 1 %}1{% else %}{{ n * factorial(n - 1)|int }}{% endif %}"
        "{% endmacro %}"
        "{{ factorial(5) }}"
    )
    result = tmpl.render().strip()
    # Expected: 120 (5!)
```

**Note**: The `int` filter handles whitespace correctly: `int("  24  ")` → `24`. The issue is operator precedence—arithmetic happens before the filter is applied.

### P3: Missing "Did You Mean?" Suggestions for Filters/Tests

While we detect structural errors, filter/test typos produce generic errors without suggestions.

**Opportunity**: Bengal already has a suggestions framework at `bengal/errors/suggestions.py` with:
- `ActionableSuggestion` dataclass for structured suggestions
- `search_suggestions()` for keyword-based search
- Pattern matching for common errors

For compile-time filter/test suggestions, we can use Python's `difflib.get_close_matches()` for simple Levenshtein-distance matching against the filter/test registry.

---

## Proposed Solution

### Phase 2: Compile-Time Validation (~2 days)

**Goal**: Raise `TemplateSyntaxError` during `env.from_string()` if a filter or test is missing.

#### 2.1 Validate Filters in Compiler

Modify `bengal/rendering/kida/compiler/expressions.py` to check the environment registry before generating filter calls. Insert validation before the existing code at line 203.

```python
# bengal/rendering/kida/compiler/expressions.py (in _compile_expr, Filter case)

if node_type == "Filter":
    # === NEW: Compile-time filter validation ===
    # Skip validation for 'default' and 'd' which have special handling
    if node.name not in ("default", "d") and node.name not in self._env._filters:
        suggestion = self._get_filter_suggestion(node.name)
        msg = f"Unknown filter '{node.name}'"
        if suggestion:
            msg += f". Did you mean '{suggestion}'?"
        raise TemplateSyntaxError(msg, lineno=getattr(node, 'lineno', None))

    # ... existing special handling for 'default' filter ...
    # ... existing compilation logic at lines 203-214 ...
```

#### 2.2 Validate Tests in Compiler

Insert validation at the start of the Test handling block (line 118):

```python
# bengal/rendering/kida/compiler/expressions.py (in _compile_expr, Test case)

if node_type == "Test":
    # === NEW: Compile-time test validation ===
    # Skip validation for 'defined' and 'undefined' which have special handling
    if node.name not in ("defined", "undefined") and node.name not in self._env._tests:
        suggestion = self._get_test_suggestion(node.name)
        msg = f"Unknown test '{node.name}'"
        if suggestion:
            msg += f". Did you mean '{suggestion}'?"
        raise TemplateSyntaxError(msg, lineno=getattr(node, 'lineno', None))

    # ... existing special handling for 'defined'/'undefined' ...
    # ... existing compilation logic at lines 148-164 ...
```

#### 2.3 Suggestion Helpers

Add to `ExpressionCompilationMixin` class:

```python
def _get_filter_suggestion(self, name: str) -> str | None:
    """Find closest matching filter name for typo suggestions."""
    from difflib import get_close_matches
    matches = get_close_matches(name, self._env._filters.keys(), n=1, cutoff=0.6)
    return matches[0] if matches else None

def _get_test_suggestion(self, name: str) -> str | None:
    """Find closest matching test name for typo suggestions."""
    from difflib import get_close_matches
    matches = get_close_matches(name, self._env._tests.keys(), n=1, cutoff=0.6)
    return matches[0] if matches else None
```

#### 2.4 Add TemplateSyntaxError Import

Ensure `TemplateSyntaxError` is imported in `expressions.py`:

```python
from bengal.rendering.kida.environment.exceptions import TemplateSyntaxError
```

---

### Phase 3: Macro Arithmetic Coercion (~1.5 days)

**Goal**: Ensure arithmetic operations on macro results use numeric values, not string multiplication.

#### 3.1 Compiler-Level Numeric Coercion (Recommended)

Modify the existing `BinOp` handling in `expressions.py` (starting at line 216). Currently it only handles `~` (string concatenation) specially. Add coercion for arithmetic operators.

```python
# bengal/rendering/kida/compiler/expressions.py (modify BinOp case)

if node_type == "BinOp":
    # Special handling for ~ (string concatenation) - EXISTING
    if node.op == "~":
        return ast.BinOp(
            left=ast.Call(
                func=ast.Name(id="_str", ctx=ast.Load()),
                args=[self._compile_expr(node.left)],
                keywords=[],
            ),
            op=ast.Add(),
            right=ast.Call(
                func=ast.Name(id="_str", ctx=ast.Load()),
                args=[self._compile_expr(node.right)],
                keywords=[],
            ),
        )

    # === NEW: Numeric coercion for arithmetic operators ===
    left = self._compile_expr(node.left)
    right = self._compile_expr(node.right)

    if node.op in ('*', '/', '-', '+', '**', '//', '%'):
        # Wrap FuncCall/Filter results in numeric coercion
        if self._is_potentially_string(node.left):
            left = self._wrap_coerce_numeric(left)
        if self._is_potentially_string(node.right):
            right = self._wrap_coerce_numeric(right)

    return ast.BinOp(left=left, op=self._get_binop(node.op), right=right)
```

Add helper methods to `ExpressionCompilationMixin`:

```python
def _is_potentially_string(self, node) -> bool:
    """Check if node could produce a string (macro call, filter chain)."""
    node_type = type(node).__name__
    return node_type in ('FuncCall', 'Filter')

def _wrap_coerce_numeric(self, expr: ast.expr) -> ast.expr:
    """Wrap expression in _coerce_numeric() call."""
    return ast.Call(
        func=ast.Name(id='_coerce_numeric', ctx=ast.Load()),
        args=[expr],
        keywords=[],
    )
```

#### 3.2 Runtime Coercion Helper

Add to the template runtime namespace in `bengal/rendering/kida/template.py`:

```python
def _coerce_numeric(value: Any) -> int | float:
    """Coerce value to numeric type for arithmetic operations.

    Handles Markup objects and strings that represent numbers.
    Strips whitespace which is common in macro output.

    Args:
        value: Any value (typically Markup from macro, or numeric)

    Returns:
        int or float, or 0 if conversion fails
    """
    # Fast path: already numeric (but not bool, which is a subclass of int)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value

    # Convert to string, strip whitespace (macros often have trailing newlines)
    s = str(value).strip()

    # Empty string → 0
    if not s:
        return 0

    # Try int first (more common in templates), then float
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return 0  # Default for non-numeric strings
```

Register in template namespace (where `_Markup`, `_str`, etc. are registered):

```python
namespace["_coerce_numeric"] = _coerce_numeric
```

#### 3.3 Alternative: Explicit Coercion Filter (Lower Priority)

If compiler-level coercion is too invasive, add a `|num` filter for explicit use:

```jinja
{{ n * factorial(n - 1)|num }}  {# Explicit numeric coercion #}
```

This is less ideal because it requires template authors to remember to use it.

---

## Testing Strategy

### Phase 2: Compile-Time Validation Tests

```python
# tests/rendering/kida/test_kida_compile_validation.py

import pytest
from bengal.rendering.kida import Environment
from bengal.rendering.kida.environment.exceptions import TemplateSyntaxError


class TestCompileTimeFilterValidation:
    """Filter validation during compilation."""

    def test_unknown_filter_raises_at_compile_time(self, env):
        """Unknown filter should raise TemplateSyntaxError during compilation."""
        with pytest.raises(TemplateSyntaxError, match="Unknown filter 'typo'"):
            env.from_string("{{ x|typo }}")

    def test_unknown_filter_suggests_similar(self, env):
        """Typo in filter name should suggest similar filter."""
        with pytest.raises(TemplateSyntaxError, match="Did you mean 'upper'"):
            env.from_string("{{ x|uper }}")

    def test_unknown_filter_no_suggestion_for_random(self, env):
        """Random string should not produce a suggestion."""
        with pytest.raises(TemplateSyntaxError) as exc:
            env.from_string("{{ x|xyzzy123 }}")
        assert "Did you mean" not in str(exc.value)

    def test_valid_filter_compiles(self, env):
        """Known filters should compile successfully."""
        tmpl = env.from_string("{{ x|upper }}")
        assert tmpl.render(x="hello") == "HELLO"


class TestCompileTimeTestValidation:
    """Test validation during compilation."""

    def test_unknown_test_raises_at_compile_time(self, env):
        """Unknown test should raise TemplateSyntaxError during compilation."""
        with pytest.raises(TemplateSyntaxError, match="Unknown test 'typo'"):
            env.from_string("{% if x is typo %}yes{% endif %}")

    def test_unknown_test_suggests_similar(self, env):
        """Typo in test name should suggest similar test."""
        with pytest.raises(TemplateSyntaxError, match="Did you mean 'defined'"):
            env.from_string("{% if x is defned %}yes{% endif %}")

    def test_defined_test_still_works(self, env):
        """Built-in 'defined' test should still work."""
        tmpl = env.from_string("{% if x is defined %}yes{% else %}no{% endif %}")
        assert tmpl.render(x=1).strip() == "yes"
        assert tmpl.render().strip() == "no"
```

### Phase 3: Macro Arithmetic Tests

```python
# tests/rendering/kida/test_kida_macro_arithmetic.py

import pytest


class TestMacroArithmetic:
    """Macro return values in arithmetic operations."""

    def test_recursive_factorial(self, env):
        """Recursive macro with arithmetic should produce correct numeric result."""
        tmpl = env.from_string(
            "{% macro factorial(n) %}"
            "{% if n <= 1 %}1{% else %}{{ n * factorial(n - 1) }}{% endif %}"
            "{% endmacro %}"
            "{{ factorial(5) }}"
        )
        result = tmpl.render().strip()
        assert "120" in result  # 5! = 120

    def test_macro_arithmetic_with_whitespace(self, env):
        """Macro with internal whitespace should still compute correctly."""
        tmpl = env.from_string(
            "{% macro double(n) %}\n"
            "  {{ n * 2 }}\n"
            "{% endmacro %}"
            "{{ double(5) * 2 }}"
        )
        result = tmpl.render().strip()
        assert "20" in result  # (5*2) * 2 = 20

    def test_macro_in_division(self, env):
        """Macro result in division should coerce correctly."""
        tmpl = env.from_string(
            "{% macro ten() %}10{% endmacro %}"
            "{{ ten() / 2 }}"
        )
        result = tmpl.render().strip()
        assert result in ("5", "5.0")

    def test_macro_in_addition(self, env):
        """Macro result in addition should coerce correctly."""
        tmpl = env.from_string(
            "{% macro five() %}5{% endmacro %}"
            "{{ five() + 3 }}"
        )
        result = tmpl.render().strip()
        assert result == "8"

    def test_coerce_numeric_preserves_real_numbers(self, env):
        """Real numeric values should pass through unchanged."""
        tmpl = env.from_string("{{ 5 * 3 }}")
        assert tmpl.render().strip() == "15"


class TestCoerceNumericHelper:
    """Unit tests for _coerce_numeric runtime helper."""

    def test_int_passthrough(self):
        from bengal.rendering.kida.template import _coerce_numeric
        assert _coerce_numeric(42) == 42

    def test_float_passthrough(self):
        from bengal.rendering.kida.template import _coerce_numeric
        assert _coerce_numeric(3.14) == 3.14

    def test_string_to_int(self):
        from bengal.rendering.kida.template import _coerce_numeric
        assert _coerce_numeric("42") == 42

    def test_string_with_whitespace(self):
        from bengal.rendering.kida.template import _coerce_numeric
        assert _coerce_numeric("  42  \n") == 42

    def test_markup_to_int(self):
        from bengal.rendering.kida.template import _coerce_numeric
        from markupsafe import Markup
        assert _coerce_numeric(Markup("42")) == 42

    def test_non_numeric_returns_zero(self):
        from bengal.rendering.kida.template import _coerce_numeric
        assert _coerce_numeric("hello") == 0
```

---

## Implementation Priority

| Task | Effort | Impact | Priority | Dependencies |
|------|--------|--------|----------|--------------|
| **1. Block Validation** | - | High | **Done** ✅ | - |
| **2.1 Filter Validation** | 3h | High | P1 | - |
| **2.2 Test Validation** | 2h | High | P1 | 2.1 |
| **2.3 Suggestion Helpers** | 1h | Medium | P1 | 2.1 |
| **2.4 Add Exception Import** | 0.5h | Low | P1 | 2.1 |
| **3.1 Numeric Coercion (Compiler)** | 4h | High | P1 | - |
| **3.2 Runtime Helper** | 1h | High | P1 | 3.1 |
| **3.3 Register in Namespace** | 0.5h | High | P1 | 3.2 |
| **Testing** | 4h | High | P1 | All above |

**Total Estimate**: ~2 days (Phase 2) + ~1.5 days (Phase 3) = **~3.5 days**

---

## Success Criteria

- [ ] **Zero unknown filters** pass compilation—`TemplateSyntaxError` raised at compile time
- [ ] **Zero unknown tests** pass compilation—`TemplateSyntaxError` raised at compile time
- [ ] **Helpful suggestions**: Typos like `|uper` suggest `|upper`
- [ ] **Recursive arithmetic macros** produce correct numeric results (`factorial(5)` = 120)
- [ ] **xfail test passes**: Remove xfail marker from `test_kida_macros.py:137`
- [ ] **No breaking changes**: Existing templates continue to work
- [ ] **All new tests pass**: Full test suite green

---

## Appendix: Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `bengal/rendering/kida/compiler/expressions.py` | Add filter/test validation before compilation, add suggestion helpers, modify BinOp for numeric coercion | ~118, ~175, ~216 |
| `bengal/rendering/kida/template.py` | Add `_coerce_numeric()` helper, register in namespace | ~TBD |
| `tests/rendering/kida/test_kida_compile_validation.py` | **New file**: compile-time validation tests | - |
| `tests/rendering/kida/test_kida_macro_arithmetic.py` | **New file**: macro arithmetic tests | - |
| `tests/rendering/kida/test_kida_macros.py` | Remove xfail marker from `test_simple_recursion` | 137 |

---

## Related Work

| Item | Location | Notes |
|------|----------|-------|
| Suggestions Framework | `bengal/errors/suggestions.py` | `ActionableSuggestion`, `search_suggestions()` - not directly usable for compile-time errors but shows pattern |
| xfail Factorial Test | `tests/rendering/kida/test_kida_macros.py:137-148` | Will be unmarked when P3 complete |
| Environment Registries | `bengal/rendering/kida/environment/core.py:150-178` | `_filters`, `_tests` dicts accessible via properties |
| ExpressionCompilationMixin | `bengal/rendering/kida/compiler/expressions.py:15-268` | Has `self._env` access for validation |
| BinOp Handling | `bengal/rendering/kida/compiler/expressions.py:216-268` | Currently only handles `~` specially |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Compile-time validation rejects templates with dynamic filters | Low | Medium | Only validate against registered filters; document opt-out via `env.add_filter()` before compilation |
| Numeric coercion changes intentional string multiplication | Low | Low | Only coerce `FuncCall` and `Filter` results, not literals or variables |
| Suggestion generation slow for large filter sets | Very Low | Low | `difflib.get_close_matches()` is O(n) but n is small (~50 filters); cutoff=0.6 limits comparisons |
| Breaking backward compatibility | Medium | High | Run full test suite; maintain Jinja2 compatibility semantics |

---

## References

| Reference | Link/Location |
|-----------|---------------|
| Jinja2 Filter Validation | [jinja2/compiler.py](https://github.com/pallets/jinja/blob/main/src/jinja2/compiler.py) - validates at compile time |
| Macro Return Type | `bengal/rendering/kida/compiler/statements/functions.py:99-119` |
| Filter Compilation | `bengal/rendering/kida/compiler/expressions.py:175-214` |
| Test Compilation | `bengal/rendering/kida/compiler/expressions.py:118-164` |
| Environment Core | `bengal/rendering/kida/environment/core.py:31-200` |
| difflib.get_close_matches | [Python docs](https://docs.python.org/3/library/difflib.html#difflib.get_close_matches) |

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-26 | Initial draft |
| 2025-12-26 | Enhanced with verified evidence, accurate line references, comprehensive test strategy |
