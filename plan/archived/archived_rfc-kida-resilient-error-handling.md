# RFC: Kida Resilient Error Handling & Rich Error Messages

**Status**: Implemented  
**Created**: 2025-01-27  
**Updated**: 2025-01-26  
**Implemented**: 2025-01-26  
**Author**: AI Assistant  
**Effort**: Medium (~3-4 weeks)  
**Impact**: High - Eliminates template crashes, improves DX, reduces defensive coding  
**Category**: Rendering / Core

---

## Executive Summary

Kida templates crash with unhelpful error messages when encountering `None` values in comparisons or sorting operations. While the sort filter already provides some context (affected items, suggestions), **template name and line numbers are missing**, making debugging difficult. This RFC proposes:

1. **Resilient `None` handling**: `None` access returns empty string (like Hugo), comparisons handle `None` gracefully
2. **Line-aware error context**: Errors include template name, source line number, expression, and actionable suggestions
3. **Execution context tracking**: Thread-local context propagates template/line info to runtime errors
4. **Performance preserved**: All changes maintain O(1) performance characteristics

**Key Insight**: Line numbers are already tracked in the AST (`nodes.py:42`) and throughout parsing. The infrastructure exists—it just needs to be passed through compilation to runtime errors.

---

## Problem Statement

### Current State

**Verified Evidence**:

| Component | Location | Current State |
|-----------|----------|---------------|
| Sort filter error handling | `filters.py:196-228` | ✅ Good: Shows affected items, suggestions |
| Template name in errors | `filters.py:223-227` | ❌ Missing: No template context |
| Line number in errors | All runtime errors | ❌ Missing: No source line info |
| `_safe_getattr` behavior | `template.py:376-382` | Returns `None` (not `""`) |
| Defensive coding required | `content-components.html:152-166` | Templates use `is not none` checks |
| Line tracking in AST | `nodes.py:42` | ✅ Available: All nodes have `lineno` |

**Current Error Experience**:

```
Runtime Error: Cannot compare NoneType with NoneType when sorting by 'weight'
  Expression: | sort(attribute='weight')
  Values:
    left = None (NoneType)
    right = None (NoneType)

  Suggestion: Ensure all items have 'weight' set, or filter out items with None values
```

**What's Good** (existing):
- ✅ Shows the attribute being sorted
- ✅ Lists items with None values (up to 10)
- ✅ Provides actionable suggestion

**What's Missing** (this RFC addresses):
- ❌ Template name (e.g., `index.html`)
- ❌ Source line number (e.g., line 42)
- ❌ Prevention of the crash (resilient `None` handling)
- ❌ Consistent experience across all runtime errors

### Pain Points

**From Real Issues**:
- Developers cannot locate which template or line caused the error
- One `None` value crashes entire page render
- Templates require defensive `| default()` checks everywhere
- No way to know which template in an inheritance chain failed

**Impact**:
- **Developer Experience**: Moderate - good error detail but poor locatability
- **Template Maintainability**: Low - defensive code clutters templates
- **Build Reliability**: Brittle - one bad value crashes entire page

---

## Goals and Non-Goals

### Goals

1. **Resilient `None` Handling**
   - `None` access returns empty string (like Hugo/Go templates)
   - Comparisons handle `None` gracefully (sort `None` last)
   - No crashes on `None` values in common operations

2. **Line-Aware Error Messages**
   - Include template name and source line number
   - Show the expression that failed
   - Display actual values involved (with types)
   - Provide actionable suggestions

3. **Performance Preservation**
   - No performance regression (< 5% overhead)
   - Maintain O(1) attribute access
   - Keep fast-path optimizations

4. **Ergonomic Templates**
   - Reduce defensive coding by 80%+
   - Templates work with real-world data (missing fields, `None` values)
   - Follow principle of least surprise

### Non-Goals

1. **Not changing core architecture**: Keep AST-native compilation, StringBuilder pattern
2. **Not adding runtime type checking**: Performance-critical paths stay fast
3. **Not breaking existing templates**: Backward compatible changes only
4. **Not adding try/catch to templates**: Errors still propagate, just with better context
5. **Not source maps**: Line tracking via compiled code metadata, not separate map files

---

## Design Options

### Option A: Enhanced Error Messages Only (No Resilience)

**Approach**: Add template/line context to existing errors without changing `None` behavior.

**Implementation**:
- Inject `_template_name` and `_current_line` into compiled render function
- Update error handlers to read execution context
- No change to `_safe_getattr`

**Pros**:
- ✅ Minimal behavior change
- ✅ Fast to implement (~1 week)
- ✅ No breaking changes

**Cons**:
- ❌ Templates still crash on `None`
- ❌ Defensive coding still required
- ❌ Line tracking in compiled code adds complexity

**Estimated Effort**: 1-2 weeks

---

### Option B: Resilient Core Only (No Line Tracking)

**Approach**: Make `_safe_getattr` return `""` for `None`, handle `None` in sort. No line numbers.

**Implementation**:
```python
@staticmethod
def _safe_getattr(obj: Any, name: str) -> Any:
    if obj is None:
        return ""
    try:
        val = getattr(obj, name)
        return "" if val is None else val
    except AttributeError:
        try:
            val = obj[name]
            return "" if val is None else val
        except (KeyError, TypeError):
            return ""
```

**Pros**:
- ✅ Eliminates crashes
- ✅ Reduces defensive coding
- ✅ Simple implementation

**Cons**:
- ❌ Errors still lack template/line context
- ❌ Breaking change (`None` → `""`)
- ❌ Debugging still difficult when errors do occur

**Estimated Effort**: 1 week

---

### Option C: Resilient Core + Line-Aware Errors (Recommended)

**Approach**: Combine resilient `None` handling with AST-derived line tracking.

**Key Insight**: Kida AST already tracks line numbers (`node.lineno`). The compiler can inject line markers into generated code.

**Implementation**:

**1. Resilient Attribute Access** (`template.py`):
```python
@staticmethod
def _safe_getattr(obj: Any, name: str) -> Any:
    """Get attribute with None-safe handling (like Hugo)."""
    if obj is None:
        return ""  # None access returns empty string
    try:
        val = getattr(obj, name)
        return "" if val is None else val
    except AttributeError:
        try:
            val = obj[name]
            return "" if val is None else val
        except (KeyError, TypeError):
            return ""
```

**2. Line Tracking via Compiled Code** (`compiler/core.py`):
```python
def _compile_node(self, node: Any) -> list[ast.stmt]:
    """Compile node with line tracking."""
    stmts = []

    # Inject line marker for nodes that can fail
    if hasattr(node, 'lineno') and self._should_track_line(node):
        # ctx['_line'] = 42
        stmts.append(ast.Assign(
            targets=[ast.Subscript(
                value=ast.Name(id='ctx', ctx=ast.Load()),
                slice=ast.Constant(value='_line'),
                ctx=ast.Store(),
            )],
            value=ast.Constant(value=node.lineno),
        ))

    # Compile the node
    stmts.extend(self._dispatch_node(node))
    return stmts

def _should_track_line(self, node: Any) -> bool:
    """Track lines for nodes that can cause runtime errors."""
    return type(node).__name__ in {
        'Output', 'For', 'If', 'Set', 'Let', 'CallBlock'
    }
```

**3. Execution Context in Template** (`template.py`):
```python
class Template:
    def render(self, ctx: dict) -> str:
        # Inject template metadata into context
        ctx['_template'] = self._name
        ctx['_line'] = 0

        try:
            return self._render_func(ctx)
        except Exception as e:
            # Enhance error with context
            if not isinstance(e, TemplateRuntimeError):
                e = self._enhance_error(e, ctx)
            raise

    def _enhance_error(self, error: Exception, ctx: dict) -> TemplateRuntimeError:
        """Convert generic exception to rich template error."""
        template_name = ctx.get('_template')
        lineno = ctx.get('_line')

        if isinstance(error, TypeError) and "NoneType" in str(error):
            return NoneComparisonError(
                None, None,
                template_name=template_name,
                lineno=lineno,
                expression="<see stack trace>",
                suggestion="Check for None values in comparisons or sorting",
            )

        return TemplateRuntimeError(
            str(error),
            template_name=template_name,
            lineno=lineno,
        )
```

**4. Enhanced Sort Filter** (`filters.py`):
```python
def _filter_sort(value, attribute=None, ...):
    # Get execution context (if available)
    # Note: ctx is passed via closure in filter registration
    template_name = _get_template_name()  # From thread-local or ctx
    lineno = _get_current_line()

    try:
        return sorted(items, reverse=reverse, key=key_func)
    except TypeError as e:
        if "NoneType" in str(e):
            # Existing logic to find problematic items...
            raise NoneComparisonError(
                None, None,
                attribute=attribute,
                template_name=template_name,  # NEW
                lineno=lineno,  # NEW
                expression=f"| sort(attribute='{attribute}')" if attribute else "| sort",
                values={'problematic_items': problematic[:5]},
            ) from e
        raise
```

**Pros**:
- ✅ Resilient to `None` (like Hugo) - no crashes
- ✅ Rich error messages with template name and line number
- ✅ Reduces defensive coding in templates by 80%+
- ✅ Uses existing AST line tracking infrastructure
- ✅ Performance preserved (line markers only for nodes that can fail)

**Cons**:
- ⚠️ Behavior change: `None` access returns `""` instead of `None`
- ⚠️ Slight code size increase (line markers in compiled code)
- ⚠️ More complex implementation

**Estimated Effort**: 3-4 weeks

---

## Recommended Approach

**Recommendation**: **Option C - Resilient Core + Line-Aware Errors**

### Reasoning

1. **Industry Standard**: Hugo/Go templates handle `nil` gracefully
   - Hugo returns empty string for `nil` access
   - Jekyll/Liquid handles `nil` without crashing

2. **Infrastructure Exists**: Line numbers are already tracked
   - `nodes.py:42`: All AST nodes have `lineno: int`
   - Parser preserves line info through all 157+ locations
   - Compiler already has access to source positions

3. **Developer Experience**: Line-aware errors dramatically improve debugging
   - **Before**: `Cannot compare NoneType...` (where??)
   - **After**: `index.html:42 - Cannot compare NoneType when sorting by 'weight'`

4. **Ergonomics**: Eliminates 80%+ of defensive coding
   - Current templates have 5+ defensive checks per sort operation
   - Other SSGs don't require this level of defensive coding

### Trade-offs Accepted

1. **Behavior Change**: `None` access returns `""` instead of `None`
   - **Mitigation**: Document clearly, provide migration guide, opt-in period
   - **Benefit**: Matches industry standard (Hugo), prevents crashes

2. **Compiled Code Size**: Line markers add ~10-20 bytes per tracked node
   - **Mitigation**: Only track nodes that can fail at runtime
   - **Benefit**: Accurate line numbers in errors

3. **Implementation Complexity**: More code to maintain
   - **Mitigation**: Well-tested, isolated to error handling layer
   - **Benefit**: Better DX, fewer support issues

---

## Behavior Change Matrix

### `_safe_getattr` Behavior: `None` → `""`

| Expression | Current | Proposed | Impact |
|------------|---------|----------|--------|
| `{{ obj.attr }}` (attr is None) | Renders `None` | Renders empty | ✅ Better |
| `{{ obj.attr }}` (obj is None) | Crashes | Renders empty | ✅ Better |
| `{% if obj.attr %}` | False for None | False for "" | ✅ Same (both falsy) |
| `{% if obj.attr is none %}` | True | False | ⚠️ **Breaking** |
| `{% if obj.attr == none %}` | True | False | ⚠️ **Breaking** |
| `{% if not obj.attr %}` | True | True | ✅ Same |
| `{{ obj.attr | default('x') }}` | Uses 'x' | Uses "" | 🟡 Different but OK |

### Migration Path

**Templates using `is none` checks**:
```jinja
{# Before #}
{% if item.weight is none %}
  {% set weight = 999999 %}
{% else %}
  {% set weight = item.weight %}
{% end %}

{# After - simpler! #}
{% set weight = item.weight or 999999 %}
```

**Opt-in period** (optional):
```python
# Environment configuration
env = Environment(
    strict_none=True,  # Default: False (new behavior)
)
```

---

## Implementation Plan

### Phase 1: Resilient Core (Week 1)

**1.1 Update `_safe_getattr`** to return `""` for `None`
- File: `bengal/rendering/kida/template.py:367-382`
- Change: Normalize `None` to `""` in all return paths
- Tests: Add comprehensive tests for None handling

**1.2 Enhance sort filter** to handle `None` gracefully
- File: `bengal/rendering/kida/environment/filters.py:127-228`
- Change: Ensure `None` values are handled in key function without crash
- Tests: Add tests for sorting with `None` values

### Phase 2a: Template Context Tracking (Week 2)

**2.1 Add template name to execution context**
- File: `bengal/rendering/kida/template.py`
- Change: Inject `_template` into ctx on render entry
- Tests: Verify template name appears in errors

**2.2 Update error handlers** to include template name
- File: `bengal/rendering/kida/environment/exceptions.py`
- File: `bengal/rendering/kida/environment/filters.py`
- Change: Read `_template` from context in error constructors

### Phase 2b: Line Number Tracking (Week 3)

**2.3 Add line markers to compiler output**
- File: `bengal/rendering/kida/compiler/core.py`
- File: `bengal/rendering/kida/compiler/statements.py`
- Change: Inject `ctx['_line'] = N` before risky nodes
- Tests: Verify line numbers in compiled code

**2.4 Update error handlers** to include line number
- File: `bengal/rendering/kida/template.py`
- Change: Read `_line` from ctx in error enhancement
- Tests: Verify line numbers appear in errors

### Phase 3: Template Cleanup & Documentation (Week 4)

**3.1 Remove defensive coding** from default templates
- File: `bengal/themes/default/templates/partials/content-components.html`
- Change: Remove unnecessary `| default()` and `is not none` checks
- Tests: Verify templates work with missing/None values

**3.2 Documentation and migration guide**
- File: `docs/rendering/kida/error-handling.md` (new)
- File: `docs/rendering/kida/migration-v2.md` (new)
- Change: Document new behavior, migration guide, examples

---

## Architecture Impact

### Files Modified

| File | Changes | Risk | Phase |
|------|---------|------|-------|
| `bengal/rendering/kida/template.py` | `_safe_getattr` normalization, context injection, error enhancement | Medium | 1, 2a, 2b |
| `bengal/rendering/kida/environment/filters.py` | Context reading in errors | Low | 2a |
| `bengal/rendering/kida/environment/exceptions.py` | Already supports template_name/lineno | None | - |
| `bengal/rendering/kida/compiler/core.py` | Line marker injection | Medium | 2b |
| `bengal/rendering/kida/compiler/statements.py` | Line tracking for specific nodes | Medium | 2b |
| `bengal/themes/default/templates/**` | Remove defensive code | Low | 3 |

### Performance Impact

| Operation | Current | Proposed | Impact |
|-----------|---------|----------|--------|
| Attribute access | O(1) | O(1) | None |
| Context line update | N/A | O(1) dict assignment | Minimal |
| Error construction | O(n) item scan | O(n) item scan + context read | Minimal |
| Template render (error-free) | Baseline | +1-2% (line markers) | Acceptable |

**Benchmark Target**: < 5% overhead for normal renders, 0% overhead for simple templates without risky nodes.

### Backward Compatibility

| Change | Type | Impact | Migration |
|--------|------|--------|-----------|
| `None` → `""` for attribute access | Behavior | Medium | Replace `is none` with `not x` |
| Line markers in compiled code | Internal | None | Transparent |
| Enhanced error messages | Additive | None | Better DX |

---

## Test Coverage Plan

### Existing Test Gaps

| Area | Current Coverage | Gap |
|------|------------------|-----|
| Sort with None values | ❌ Not tested | Add comprehensive tests |
| `_safe_getattr` with None | ❌ Implicit | Add explicit tests |
| Error message content | ❌ Not verified | Add assertion tests |
| Line number accuracy | ❌ N/A | Add new tests |

### New Test Cases

```python
# tests/rendering/kida/test_none_handling.py

class TestResilientNoneHandling:
    """Test None → '' behavior."""

    def test_none_access_returns_empty(self, env):
        """Accessing None attribute returns empty string."""
        tmpl = env.from_string('{{ obj.missing }}')
        assert tmpl.render(obj={'present': 'value'}) == ''

    def test_none_object_access_returns_empty(self, env):
        """Accessing attribute on None returns empty string."""
        tmpl = env.from_string('{{ obj.attr }}')
        assert tmpl.render(obj=None) == ''

    def test_none_chain_returns_empty(self, env):
        """Chained access through None returns empty string."""
        tmpl = env.from_string('{{ obj.a.b.c }}')
        assert tmpl.render(obj={'a': None}) == ''


class TestSortWithNone:
    """Test sort filter handles None gracefully."""

    def test_sort_with_none_values(self, env):
        """Sort places None values last."""
        tmpl = env.from_string('{{ items|sort(attribute="weight")|map(attribute="name")|join(",") }}')
        items = [
            {'name': 'b', 'weight': 2},
            {'name': 'a', 'weight': None},
            {'name': 'c', 'weight': 1},
        ]
        assert tmpl.render(items=items) == 'c,b,a'  # None last

    def test_sort_all_none_values(self, env):
        """Sort with all None values doesn't crash."""
        tmpl = env.from_string('{{ items|sort(attribute="weight")|length }}')
        items = [
            {'name': 'a', 'weight': None},
            {'name': 'b', 'weight': None},
        ]
        assert tmpl.render(items=items) == '2'


class TestErrorLineNumbers:
    """Test error messages include line numbers."""

    def test_error_includes_template_name(self, env):
        """Errors include template name."""
        tmpl = env.from_string('{{ 1 / 0 }}', name='test.html')
        with pytest.raises(TemplateRuntimeError) as exc:
            tmpl.render()
        assert 'test.html' in str(exc.value)

    def test_error_includes_line_number(self, env):
        """Errors include line number."""
        template_src = '''Line 1
{{ items | sort(attribute="missing") }}
Line 3'''
        tmpl = env.from_string(template_src, name='test.html')
        with pytest.raises(NoneComparisonError) as exc:
            tmpl.render(items=[{'a': 1}, {'a': None}])
        assert ':2' in str(exc.value) or 'line 2' in str(exc.value).lower()
```

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Behavior change breaks `is none` checks | High | Medium | Migration guide, opt-in period, search-and-replace pattern |
| Line tracking adds overhead | Medium | Low | Only track risky nodes, benchmark before/after |
| Line numbers inaccurate for complex expressions | Low | Medium | Document limitations, improve over time |
| Rich errors expose sensitive data | Low | Low | Truncate values, mask secrets in error output |

---

## Success Metrics

1. **Error Message Quality**:
   - ✅ All errors include template name
   - ✅ Errors from tracked nodes include line number
   - ✅ Errors provide actionable suggestions

2. **Resilience**:
   - ✅ `None` access doesn't crash (returns `""`)
   - ✅ `None` comparisons don't crash (sort `None` last)
   - ✅ Templates work with real-world data (missing fields)

3. **Performance**:
   - ✅ < 5% overhead for templates with risky nodes
   - ✅ 0% overhead for simple templates
   - ✅ Error-free renders have minimal overhead

4. **Ergonomics**:
   - ✅ 80%+ reduction in defensive template code
   - ✅ Templates work without `| default()` everywhere

---

## Open Questions

1. **Should the opt-in period be mandatory?**
   - **Recommendation**: No - default to new behavior with clear migration docs
   - **Rationale**: The new behavior is strictly better for most use cases

2. **Should we track line numbers for all nodes or just risky ones?**
   - **Recommendation**: Only risky nodes (`Output`, `For`, `If`, `Set`, etc.)
   - **Rationale**: Minimizes overhead while covering 95% of error cases

3. **How to handle line numbers in included templates?**
   - **Recommendation**: Reset line counter on include, show `included.html:N (from base.html:M)`
   - **Alternative**: Keep single line counter (simpler but less accurate)

4. **Should `None` in conditionals warn?**
   - **Recommendation**: No warnings in v1; consider linter rule for v2
   - **Rationale**: Warnings add noise; linter can catch `is none` patterns

---

## References

- Hugo Error Handling: https://gohugo.io/functions/go-template/try/
- Jinja2 Error Handling: https://jinja.palletsprojects.com/en/3.1.x/templates/#error-handling
- Current Kida AST line tracking: `bengal/rendering/kida/nodes.py:42`
- Current error infrastructure: `bengal/rendering/kida/environment/exceptions.py`
- Sort filter implementation: `bengal/rendering/kida/environment/filters.py:127-228`

---

## Appendix A: Example Error Messages

### Current State

```
Runtime Error: Cannot compare NoneType with NoneType when sorting by 'weight'
  Expression: | sort(attribute='weight')
  Values:
    left = None (NoneType)
    right = None (NoneType)

  Suggestion: Ensure all items have 'weight' set, or filter out items with None values
```

### After Phase 2a (Template Name)

```
Runtime Error: Cannot compare NoneType with NoneType when sorting by 'weight'
  Location: index.html
  Expression: | sort(attribute='weight')

  Items with None values:
    - Getting Started: weight = None
    - Advanced Guide: weight = None

  Suggestion: Use | default(999999) on 'weight' attribute before sorting
```

### After Phase 2b (Line Number)

```
Runtime Error: Cannot compare NoneType with NoneType when sorting by 'weight'
  Location: index.html:42
  Expression: | sort(attribute='weight,title')

  Items with None values:
    - Getting Started: weight = None
    - Advanced Guide: weight = None

  Total Items: 15
  Items with None values: 2

  Suggestion: Use | default(999999) on 'weight' attribute, or filter out items with None values before sorting.

  Example Fix:
    {% set sorted_items = items | selectattr('weight') | sort(attribute='weight,title') %}
```

---

## Appendix B: Compiler Line Injection Example

**Input Template** (`index.html`):
```jinja
{% for item in items %}
  {{ item.title }}
{% endfor %}
```

**Current Compiled Output** (simplified):
```python
def render(ctx, _blocks=None):
    buf = []
    _append = buf.append
    for item in ctx.get('items', []):
        _append(_e(item.title))
    return ''.join(buf)
```

**Proposed Compiled Output** (with line tracking):
```python
def render(ctx, _blocks=None):
    buf = []
    _append = buf.append
    ctx['_line'] = 1  # For loop starts at line 1
    for item in ctx.get('items', []):
        ctx['_line'] = 2  # Output at line 2
        _append(_e(item.title))
    return ''.join(buf)
```

**Performance Note**: The `ctx['_line'] = N` assignment is O(1) dict mutation. For a template with 100 tracked nodes, this adds ~100 dict assignments per render—negligible compared to actual template work.

---

## Appendix C: Migration Checklist

### For Template Authors

- [ ] Search for `is none` patterns → replace with `not x` or `| default()`
- [ ] Search for `== none` patterns → replace with `not x`
- [ ] Test templates with realistic data (some fields missing)
- [ ] Remove excessive `| default()` usage (no longer needed)

### For Bengal Maintainers

- [ ] Update all default theme templates
- [ ] Add deprecation notice for `strict_none` option (if implemented)
- [ ] Update documentation examples
- [ ] Add migration guide to docs

---

## Changelog

- **2025-01-27**: Initial draft
- **2025-01-27**: Updated with accurate evidence, expanded line tracking design, added test plan, behavior matrix, and appendices
- **2025-01-26**: **Implemented** - Core implementation complete:
  - `_safe_getattr` now returns `""` for None (like Hugo)
  - Template name and line number context in all errors
  - Line markers injected by compiler for risky nodes
  - Error enhancement in render() catches and enriches exceptions
  - 29 new tests in `test_resilient_none_handling.py`
  - Simplified defensive coding in `content-components.html`

## Implementation Summary

### Files Modified

| File | Changes |
|------|---------|
| `bengal/rendering/kida/template.py` | `_safe_getattr` → returns `""` for None; `render()` wraps in try/except and enhances errors with template name and line; added `_enhance_error()` method |
| `bengal/rendering/kida/compiler/core.py` | Added `_LINE_TRACKED_NODES` set and `_make_line_marker()` to inject `ctx['_line'] = N` for risky nodes |
| `bengal/themes/default/templates/partials/content-components.html` | Simplified defensive coding patterns using `or` fallback instead of `is not none` checks |
| `tests/rendering/kida/test_resilient_none_handling.py` | **New file** - 30 comprehensive tests for None handling, sort resilience, error context, and migration patterns |

### Test Results

- **29 passed**, 1 skipped (NoneComparisonError test skipped since sort is now resilient)
- All None-related tests pass
- Error messages include template name and line numbers
