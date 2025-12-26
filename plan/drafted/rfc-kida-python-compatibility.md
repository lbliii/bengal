# RFC: Kida Python-Native Keywords & Strict Mode

**Status**: Draft  
**Created**: 2025-12-26  
**Updated**: 2025-12-26  
**Author**: AI Assistant  
**Effort**: Phase 1: ~1 day | Phase 2: ~1 week  
**Impact**: High - Aligns Kida with Python conventions, improves DX  
**Category**: Rendering / Parser / Compiler

---

## Executive Summary

Kida is a **Python-native template engine** built for Python 3.13+ and free-threaded Python. Unlike legacy template engines, Kida should embrace Python conventions, not fight them.

**The Bug**: Python-style keywords (`True`, `False`, `None`) are not recognized. They silently resolve to `None`, causing confusing failures.

**The Fix**: Recognize Python keywords as the primary style. This is a one-line fix with zero performance cost.

**The Opportunity**: Introduce strict mode as the modern default — undefined variables should error, not silently become `None`.

---

## Design Philosophy

### Kida is Python-Native, Not Jinja-Compatible

| Principle | Kida (2025) | Legacy Engines |
|-----------|-------------|----------------|
| **Keywords** | Python-style: `True`, `False`, `None` | Lowercase: `true`, `false`, `none` |
| **Undefined vars** | Error by default (strict mode) | Silent `None` |
| **Threading** | Free-threaded safe | GIL-dependent |
| **Compilation** | AST-to-AST | String manipulation |
| **Performance** | StringBuilder, zero-copy | Generator yields |

**We support lowercase for convenience, but Python-style is canonical.**

---

## Problem Statement

### The Bug

```python
env = Environment()

# ❌ Fails silently - True becomes undefined → None → falsy
env.from_string("{% if True %}yes{% endif %}").render()  # → ''

# ✅ Works - lowercase recognized
env.from_string("{% if true %}yes{% endif %}").render()  # → 'yes'
```

**Root Cause**: Parser only handles lowercase keywords:

```python
# parser/expressions.py:404-414
if token.value == "true":    # Missing "True"
    return Const(..., True)
elif token.value == "false":  # Missing "False"
    return Const(..., False)
elif token.value == "none":   # Missing "None"
    return Const(..., None)
return Name(...)  # True/False/None fall through → ctx.get('True') → None
```

### The Inconsistency

The parser already recognizes Python-style keywords in `_can_start_test_arg()` (line 206):

```python
return self._current.value in ("true", "false", "none", "True", "False", "None")
```

But `_parse_primary()` only handles lowercase. This is an oversight, not a design choice.

---

## Proposed Solution

### Phase 1: Python Keyword Recognition (~1 day)

**Goal**: Recognize `True`, `False`, `None` as the canonical Python style.

**Implementation**:

```python
# parser/expressions.py - module level
BOOL_TRUE = frozenset({"True", "true"})
BOOL_FALSE = frozenset({"False", "false"})
BOOL_NONE = frozenset({"None", "none"})
BOOL_KEYWORDS = BOOL_TRUE | BOOL_FALSE | BOOL_NONE

# In _parse_primary(), lines 404-414
if token.value in BOOL_TRUE:
    return Const(token.lineno, token.col_offset, True)
elif token.value in BOOL_FALSE:
    return Const(token.lineno, token.col_offset, False)
elif token.value in BOOL_NONE:
    return Const(token.lineno, token.col_offset, None)
```

**Performance**: Zero overhead. `frozenset` lookup is O(1). This runs at parse time, not render time.

---

### Phase 2: Strict Mode as Default (~1 week)

**Goal**: Undefined variables should error, not silently become `None`.

**Rationale**: Silent `None` is a legacy pattern that causes debugging nightmares. Modern Python uses type hints and explicit errors. Kida should too.

**Configuration**:

```python
# Modern (recommended)
env = Environment()  # strict=True by default

# Legacy compatibility
env = Environment(strict=False)
```

**Behavior**:

| Mode | Undefined Variable | Typo in Variable Name |
|------|-------------------|-----------------------|
| `strict=True` (default) | `UndefinedError` | `UndefinedError` |
| `strict=False` | `None` | `None` (silent bug) |

**Implementation**:

```python
class Environment:
    def __init__(self, strict: bool = True):
        self._strict = strict
```

In compiler, for undefined variables:

```python
if self._env._strict:
    # Generate: ctx[name] (raises KeyError → UndefinedError)
    return ast.Subscript(
        value=ast.Name(id="ctx", ctx=ast.Load()),
        slice=ast.Constant(value=node.name),
        ctx=ast.Load(),
    )
else:
    # Legacy: ctx.get(name) → None
    return ast.Call(
        func=ast.Attribute(
            value=ast.Name(id="ctx", ctx=ast.Load()),
            attr="get",
            ctx=ast.Load(),
        ),
        args=[ast.Constant(value=node.name)],
        keywords=[],
    )
```

**Exception Design**:

```python
class UndefinedError(TemplateError):
    """Raised when accessing an undefined variable in strict mode."""

    def __init__(self, name: str, template: str, lineno: int):
        self.name = name
        self.template = template
        self.lineno = lineno
        super().__init__(
            f"Undefined variable '{name}' in {template}:{lineno}"
        )
```

---

### Phase 3: Optional Warning Mode (Future)

For gradual migration, add a warning mode:

```python
env = Environment(strict="warn")  # Logs warning, returns None
```

This is lower priority than getting strict mode right.

---

## Performance Analysis

### Phase 1: Zero Cost

- `frozenset` membership is O(1)
- Runs once at parse time, not per-render
- Compiled bytecode is identical

### Phase 2: Strict Mode is Faster

| Mode | Operation | Performance |
|------|-----------|-------------|
| `strict=True` | `ctx[name]` | O(1) dict lookup |
| `strict=False` | `ctx.get(name)` | O(1) + function call overhead |

Strict mode is actually **faster** because `ctx[name]` is a direct subscript vs `ctx.get(name)` which has method call overhead.

---

## Migration Path

### Phase 1 (Immediate)

1. Add Python keyword support
2. Document: "`True`, `False`, `None` are the standard Python keywords. Lowercase `true`, `false`, `none` also work."
3. **No breaking changes**

### Phase 2 (Strict Mode)

**Option A: Strict by Default (Recommended)**

New projects get strict mode. Existing code adds `strict=False` if needed.

```python
# bengal.yaml or config
kida:
  strict: false  # Opt-out for legacy templates
```

**Option B: Opt-in Strict Mode**

Default remains lenient. Users opt into strict mode.

```python
env = Environment(strict=True)
```

**Recommendation**: Option A. Modern defaults should be safe defaults.

---

## Test Plan

### Phase 1: Python Keywords

```python
class TestPythonKeywords:
    """Python-style True/False/None are canonical."""

    @pytest.fixture
    def env(self):
        return Environment(strict=False)  # Test keyword parsing, not strict mode

    def test_True_in_conditional(self, env):
        assert env.from_string("{% if True %}yes{% endif %}").render() == "yes"

    def test_False_in_conditional(self, env):
        assert env.from_string("{% if False %}no{% else %}yes{% endif %}").render() == "yes"

    def test_None_renders_empty(self, env):
        assert env.from_string("{{ None }}").render() == ""

    def test_True_equals_true(self, env):
        assert env.from_string("{% if True == true %}yes{% endif %}").render() == "yes"

    def test_ternary_with_True(self, env):
        assert env.from_string("{{ 'yes' if True else 'no' }}").render() == "yes"

    def test_def_inside_if_True(self, env):
        """Regression test: def blocks inside {% if True %} work."""
        tmpl = env.from_string("""
{% def greet() %}Hello{% enddef %}
{% if True %}{{ greet() }}{% endif %}
""")
        assert "Hello" in tmpl.render()
```

### Phase 2: Strict Mode

```python
class TestStrictMode:
    """Strict mode errors on undefined variables."""

    def test_strict_is_default(self):
        env = Environment()
        assert env._strict is True

    def test_undefined_raises(self):
        env = Environment()
        with pytest.raises(UndefinedError, match="undefined_var"):
            env.from_string("{{ undefined_var }}").render()

    def test_defined_works(self):
        env = Environment()
        result = env.from_string("{{ name }}").render(name="World")
        assert result == "World"

    def test_strict_false_returns_none(self):
        env = Environment(strict=False)
        result = env.from_string("{{ undefined_var }}").render()
        assert result == ""  # None → empty

    def test_error_includes_location(self):
        env = Environment()
        try:
            env.from_string("line1\n{{ bad }}").render()
        except UndefinedError as e:
            assert e.name == "bad"
            assert e.lineno == 2
```

---

## Documentation

### Keyword Documentation

```markdown
## Boolean and None Values

Kida uses Python-style keywords:

- `True` - Boolean true
- `False` - Boolean false  
- `None` - Null value (renders as empty string)

```kida
{% if True %}
  This always renders.
{% endif %}

{% if user is None %}
  No user provided.
{% endif %}
```

Lowercase `true`, `false`, `none` are also accepted for convenience.
```

### Strict Mode Documentation

```markdown
## Strict Mode (Default)

Kida uses strict mode by default. Undefined variables raise an error:

```python
env = Environment()
env.from_string("{{ typo_var }}").render()
# Raises: UndefinedError: Undefined variable 'typo_var'
```

This catches bugs early instead of silently rendering empty strings.

### Disabling Strict Mode

For legacy templates or optional variables:

```python
env = Environment(strict=False)
```

Or use the `default` filter:

```kida
{{ optional_var | default("fallback") }}
```
```

---

## Alternatives Considered

### 1. Only Support Lowercase (Jinja2-style)

**Rejected**: We're not Jinja2. Python developers expect `True` to work. Silent failure is unacceptable.

### 2. Warning Instead of Error

**Deferred**: Warning mode (`strict="warn"`) can be added later. Errors are the right default for catching bugs.

### 3. Lenient by Default

**Rejected**: Silent `None` is a legacy anti-pattern. Modern Python uses explicit errors. Kida should lead, not follow.

---

## Success Criteria

| Criterion | Target |
|-----------|--------|
| `True`/`False`/`None` work | 100% of tests pass |
| Zero performance regression | Phase 1 has no runtime cost |
| Strict mode catches typos | `{{ typo }}` raises `UndefinedError` |
| Clear error messages | Error shows variable name and line number |
| Backward compatibility | `strict=False` restores legacy behavior |

---

## Implementation Checklist

### Phase 1 (~1 day)

- [ ] Add `BOOL_TRUE`, `BOOL_FALSE`, `BOOL_NONE` constants to `parser/expressions.py`
- [ ] Update `_parse_primary()` to use constants
- [ ] Update `_can_start_test_arg()` to use same constants
- [ ] Add `tests/rendering/kida/test_python_keywords.py`
- [ ] Run full test suite
- [ ] Update syntax documentation

### Phase 2 (~1 week)

- [ ] Add `strict` parameter to `Environment`
- [ ] Add `UndefinedError` exception class
- [ ] Update compiler to use `ctx[name]` in strict mode
- [ ] Update existing tests to use `strict=False` where needed
- [ ] Add strict mode tests
- [ ] Document strict mode
- [ ] Update bengal config to support `kida.strict` setting

---

## Files Modified

| File | Change |
|------|--------|
| `parser/expressions.py` | Add `BOOL_*` constants, update `_parse_primary()`, `_can_start_test_arg()` |
| `environment/core.py` | Add `strict` parameter |
| `compiler/expressions.py` | Conditional `ctx[name]` vs `ctx.get(name)` |
| `errors/__init__.py` | Add `UndefinedError` |
| `tests/rendering/kida/test_python_keywords.py` | New test file |
| `tests/rendering/kida/test_strict_mode.py` | New test file |

---

## Related RFCs

- `rfc-kida-resilient-error-handling.md` - Complements with attribute access on `None`
- `rfc-kida-template-engine.md` - Original Kida design and philosophy

---

## Appendix: Investigation Log

### Verification

```bash
python -c '
from bengal.rendering.kida import Environment
env = Environment()

# Bug demonstration:
print("{% if True %}:", repr(env.from_string("{% if True %}yes{% endif %}").render()))
print("{% if true %}:", repr(env.from_string("{% if true %}yes{% endif %}").render()))
print("{{ True }}:", repr(env.from_string("{{ True }}").render()))
'

# Current output (BUG):
# {% if True %}: ''
# {% if true %}: 'yes'
# {{ True }}: 'None'

# Expected after fix:
# {% if True %}: 'yes'
# {% if true %}: 'yes'
# {{ True }}: 'True'
```

---

## Changelog

- **2025-12-26**: Initial draft
- **2025-12-26**: Reframed as Python-native, not Jinja-compatible. Added strict mode as default. Simplified scope.
