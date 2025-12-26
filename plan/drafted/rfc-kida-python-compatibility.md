# RFC: Kida Python Compatibility & Name Resolution

**Status**: Draft  
**Created**: 2025-12-26  
**Updated**: 2025-12-26  
**Author**: AI Assistant  
**Effort**: Low-Medium (~1-2 weeks)  
**Impact**: High - Fixes confusing behavior, improves Python compatibility  
**Category**: Rendering / Parser / Compiler

---

## Executive Summary

Investigation of reported Kida template issues revealed a **single root cause**: Python-style boolean/none keywords (`True`, `False`, `None`) are not recognized by the parser. They're treated as undefined variables that resolve to `None` via `ctx.get()`, causing silent failures.

This RFC proposes:

1. **Immediate Fix**: Add Python-style keyword recognition in the parser
2. **Design Enhancement**: Strict mode with undefined variable errors
3. **Long-term Architecture**: Unified name resolution with configurable behavior

**Key Finding**: Most reported "bugs" (defs not working in conditionals, nested block issues) were actually symptoms of `{% if True %}` silently failing because `True` → `ctx.get('True')` → `None` → falsy.

---

## Problem Statement

### Root Cause Analysis

| Symptom Reported | Actual Cause | Evidence |
|------------------|--------------|----------|
| Defs don't work inside `{% if %}` | `{% if True %}` evaluates to `None` | `True` not in parser keywords |
| Inconsistent `{% end %}` behavior | Same - tests used `{% if True %}` | Works with `{% if true %}` |
| "Compiler scoping bug" | Same - conditional never executed | Verified with context variables |

### Technical Evidence

**Parser code** (`parser/expressions.py:401-414`):

```python
if token.value == "true":
    return Const(token.lineno, token.col_offset, True)
elif token.value == "false":
    return Const(token.lineno, token.col_offset, False)
elif token.value == "none":
    return Const(token.lineno, token.col_offset, None)
# Python-style True/False/None fall through to Name node
return Name(...)  # → ctx.get('True') → None
```

**Compiler code** (`compiler/expressions.py:37-55`):

```python
if node_type == "Name":
    # ...
    # All unknown names become ctx.get(name) → silent None
    return ast.Call(
        func=ast.Attribute(
            value=ast.Name(id="ctx", ctx=ast.Load()),
            attr="get",
            ...
        ),
        args=[ast.Constant(value=node.name)],
        ...
    )
```

### Verified Test Results

```python
env = Environment()

# ✅ Works: Jinja2-style lowercase
env.from_string("{% if true %}yes{% endif %}").render()  # → 'yes'

# ❌ Fails: Python-style uppercase
env.from_string("{% if True %}yes{% endif %}").render()  # → ''

# ❌ Silent failure: True becomes undefined variable
env.from_string("{{ True }}").render()  # → 'None'
```

---

## Design Gaps Identified

### 1. Silent Undefined Variable Resolution

**Current Behavior**: All undefined names resolve to `None` via `ctx.get(name)`.

**Problems**:
- No distinction between "intentionally None" and "undefined"
- Typos in variable names produce silent failures
- Template debugging is difficult
- Python-style keywords accidentally undefined

**Example**:
```kida
{{ user_nmae }}  {# Typo: silently becomes None #}
{{ Undefined }}  {# Silently becomes None #}
{% if Flase %}   {# Typo: silently becomes None (falsy) #}
```

### 2. Jinja2 vs Python Keyword Conflict

**Design Decision Not Made Explicit**:
- Jinja2 uses `true`, `false`, `none` (lowercase)
- Python uses `True`, `False`, `None` (capitalized)
- Kida only supports Jinja2-style

**User Expectation Mismatch**:
- Users familiar with Python expect `True` to work
- No error message explaining the difference
- Silent failure is the worst UX outcome

### 3. Reserved Words Not Enforced

**Current State**: No reserved words (except `and`, `or`, `not`, `in`, `is` in lexer).

**Risk**: Users could define variables named `true`, `True`, `len`, etc., causing unexpected behavior.

### 4. No Strict Mode for Development

**Missing Feature**: Option to error on undefined variables during development, while gracefully handling them in production.

---

## Proposed Solution

### Phase 1: Immediate Fix (Low Effort, High Impact)

**Goal**: Support Python-style `True`, `False`, `None`.

**Location**: `bengal/rendering/kida/parser/expressions.py`

**Change**:

```python
# Before (lines 401-414)
if token.value == "true":
    return Const(token.lineno, token.col_offset, True)
elif token.value == "false":
    return Const(token.lineno, token.col_offset, False)
elif token.value == "none":
    return Const(token.lineno, token.col_offset, None)

# After
if token.value in ("true", "True"):
    return Const(token.lineno, token.col_offset, True)
elif token.value in ("false", "False"):
    return Const(token.lineno, token.col_offset, False)
elif token.value in ("none", "None"):
    return Const(token.lineno, token.col_offset, None)
```

**Complexity**: O(1) - constant-time string comparison  
**Breaking Change**: No - purely additive  
**Test Coverage**: Add tests for Python-style keywords

---

### Phase 2: Undefined Variable Warnings (Medium Effort)

**Goal**: Warn (don't crash) when undefined variables are accessed.

**Approach**: Track defined variables during compilation, emit warnings at runtime.

**Implementation Options**:

#### Option A: Compile-Time Analysis (Recommended)

Track variable definitions during compilation:

```python
class Compiler:
    def __init__(self, env):
        self._defined_vars: set[str] = set()
        self._warn_undefined: bool = env.warn_undefined

    def _compile_expr(self, node):
        if node_type == "Name":
            if self._warn_undefined and node.name not in self._defined_vars:
                # Emit warning at compile time
                self._emit_warning(
                    f"Undefined variable '{node.name}' at line {node.lineno}. "
                    f"Did you mean 'true' (lowercase) instead of 'True'?"
                )
```

**Pros**:
- Zero runtime overhead
- Catches issues during site build
- Can suggest corrections (True → true)

**Cons**:
- Cannot track dynamic context variables
- May false-positive on intended context lookups

#### Option B: Runtime Check (Alternative)

Wrap `ctx.get()` with warning:

```python
def _safe_get(ctx, name, template_info):
    value = ctx.get(name)
    if value is None and name not in ctx:
        warnings.warn(
            f"Undefined variable '{name}' in {template_info.name}:{template_info.line}"
        )
    return value
```

**Pros**:
- Accurate (checks actual context)
- No false positives

**Cons**:
- Runtime overhead (~5-10%)
- Warning per access, not per definition

---

### Phase 3: Strict Mode (Medium Effort)

**Goal**: Optional strict mode that errors on undefined variables.

**Configuration**:

```python
env = Environment(
    undefined="strict"  # Options: "silent" (default), "warn", "strict"
)
```

**Behavior by Mode**:

| Mode | Undefined Variable | Python-style Keywords |
|------|-------------------|-----------------------|
| `silent` | Returns `None` | Recognized (Phase 1) |
| `warn` | Returns `None` + warning | Recognized (Phase 1) |
| `strict` | Raises `UndefinedError` | Recognized (Phase 1) |

**Implementation**:

```python
class UndefinedBehavior(Enum):
    SILENT = "silent"
    WARN = "warn"
    STRICT = "strict"

class Environment:
    def __init__(self, undefined: str = "silent"):
        self._undefined = UndefinedBehavior(undefined)
```

In compiler:

```python
if self._env._undefined == UndefinedBehavior.STRICT:
    # Generate: raise UndefinedError(name) if name not in ctx
    return ast.IfExp(
        test=ast.Compare(
            left=ast.Constant(value=node.name),
            ops=[ast.In()],
            comparators=[ast.Name(id="ctx", ctx=ast.Load())],
        ),
        body=ast.Subscript(
            value=ast.Name(id="ctx", ctx=ast.Load()),
            slice=ast.Constant(value=node.name),
        ),
        orelse=ast.Call(
            func=ast.Name(id="_raise_undefined", ctx=ast.Load()),
            args=[ast.Constant(value=node.name)],
            ...
        ),
    )
```

---

### Phase 4: Reserved Words & Builtins (Low Effort)

**Goal**: Define reserved words and Python builtins for consistency.

**Reserved Words** (parser should recognize):

```python
BOOLEAN_KEYWORDS = frozenset({
    "true", "True",
    "false", "False",
    "none", "None",
})

LOGIC_KEYWORDS = frozenset({
    "and", "or", "not", "in", "is",
})

RESERVED_WORDS = BOOLEAN_KEYWORDS | LOGIC_KEYWORDS
```

**Python Builtins** (optional, for strict mode):

```python
PYTHON_BUILTINS = frozenset({
    "len", "str", "int", "float", "list", "dict", "set",
    "range", "enumerate", "zip", "map", "filter",
    "min", "max", "sum", "abs", "round",
    "sorted", "reversed",
})
```

In strict mode, these could be auto-imported from Python:

```python
if self._env.import_builtins:
    ctx.update({
        "len": len,
        "str": str,
        # ...
    })
```

---

## Performance Analysis

### Phase 1: Zero Overhead

- String comparison `in ("true", "True")` is O(1)
- Tuple membership is optimized by Python
- No runtime impact

### Phase 2-3: Configurable Overhead

| Mode | Parse Time | Compile Time | Runtime |
|------|-----------|--------------|---------|
| Silent | 0% | 0% | 0% |
| Warn | 0% | +5% (tracking) | +5% (check) |
| Strict | 0% | +10% (extra AST) | +10% (check) |

**Optimization**: Checks can be compiled out for production:

```python
env = Environment(
    undefined="warn" if DEBUG else "silent"
)
```

---

## Migration Path

### Phase 1 (Immediate)

1. Add Python-style keyword support
2. Update tests
3. Document: "Both `true` and `True` are valid"
4. **No breaking changes**

### Phase 2-3 (Optional Opt-in)

1. Add `undefined` parameter to Environment
2. Default to `"silent"` (current behavior)
3. Recommend `"warn"` for development
4. Document strict mode for new projects

### Phase 4 (Long-term)

1. Define reserved words
2. Consider Python builtin imports
3. Potentially make `"warn"` the default in v2.0

---

## Test Plan

### Phase 1 Tests

```python
class TestPythonKeywords:
    """Test Python-style True/False/None recognition."""

    def test_true_uppercase(self):
        env = Environment()
        result = env.from_string("{% if True %}yes{% endif %}").render()
        assert result == "yes"

    def test_false_uppercase(self):
        env = Environment()
        result = env.from_string("{% if False %}yes{% else %}no{% endif %}").render()
        assert result == "no"

    def test_none_uppercase(self):
        env = Environment()
        result = env.from_string("{{ None }}").render()
        assert result == "None"  # or "" depending on design

    def test_def_in_if_true(self):
        """Regression test for Issue #4."""
        loader = DictLoader({
            "base.html": "{% def helper() %}Helper{% enddef %}{% block c %}{% endblock %}",
            "child.html": '{% extends "base.html" %}{% block c %}{% if True %}{{ helper() }}{% endif %}{% endblock %}',
        })
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "Helper" in result
```

### Phase 2-3 Tests

```python
class TestUndefinedModes:
    """Test undefined variable handling modes."""

    def test_silent_mode(self):
        env = Environment(undefined="silent")
        result = env.from_string("{{ undefined_var }}").render()
        assert result == "None"  # No error

    def test_warn_mode(self):
        env = Environment(undefined="warn")
        with pytest.warns(UserWarning, match="Undefined variable 'undefined_var'"):
            env.from_string("{{ undefined_var }}").render()

    def test_strict_mode(self):
        env = Environment(undefined="strict")
        with pytest.raises(UndefinedError, match="undefined_var"):
            env.from_string("{{ undefined_var }}").render()
```

---

## Alternatives Considered

### 1. Only Support Jinja2-style (lowercase)

**Rejected**: Too surprising for Python users. Violates principle of least astonishment.

### 2. Make True/False/None Compile-Time Errors

**Rejected**: Would break existing templates using context variables named `True`.

### 3. Auto-Correct with Warning

**Considered**: `True` → `true` with deprecation warning.

**Decision**: Too magical. Better to support both explicitly.

### 4. Different Syntax Entirely

**Rejected**: `@true`, `$true` etc. would be too different from Jinja2/Python.

---

## Success Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| Python keywords work | All tests pass | 100% |
| No performance regression | Benchmark | < 5% overhead |
| Backward compatible | Existing templates | 100% work |
| DX improvement | Error clarity | Reduced debugging time |

---

## Implementation Order

1. **Week 1**: Phase 1 (Python keywords) - Ship immediately
2. **Week 2**: Phase 2 (warnings) - Optional feature
3. **Future**: Phase 3-4 (strict mode, builtins) - Based on feedback

---

## Related RFCs

- `rfc-kida-resilient-error-handling.md` - Complements with `None` handling
- `rfc-template-context-redesign.md` - Context variable architecture
- `rfc-kida-template-engine.md` - Original Kida design

---

## Appendix: Full Investigation Log

### Symptoms Investigated

1. `{% def %}` blocks not closing correctly → **Working**
2. `{% empty %}` not recognized in nested contexts → **Working**
3. `{% end %}` behavior inconsistent → **Working as designed**
4. Defs not accessible in conditionals → **Root cause: True/False/None bug**
5. Parser error messages → **Enhancement, not bug**

### Verification Commands

```bash
python -c '
from bengal.rendering.kida import Environment
env = Environment()
print(env.from_string("{% if true %}yes{% endif %}").render())   # yes
print(env.from_string("{% if True %}yes{% endif %}").render())   # (empty)
'
```

### Files Modified

| File | Change |
|------|--------|
| `parser/expressions.py` | Add `"True"`, `"False"`, `"None"` cases |
| `environment/core.py` | Add `undefined` parameter |
| `compiler/expressions.py` | Add undefined checking logic |
| `tests/test_kida_*.py` | Add test coverage |
