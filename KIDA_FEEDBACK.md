# Kida Template Engine Feedback

## Investigation Results (2025-12-26)

### Root Cause Found: Python-Style Booleans Not Recognized

**Critical Finding**: The Kida parser only recognizes **lowercase** boolean/none keywords (`true`, `false`, `none`), not Python-style capitalized versions (`True`, `False`, `None`).

| Keyword | Status | Result |
|---------|--------|--------|
| `{% if true %}` | ✅ Works | Evaluates as boolean `True` |
| `{% if True %}` | ❌ Fails | Becomes `ctx.get('True')` → `None` |
| `{{ false }}` | ✅ Works | Outputs `False` |
| `{{ False }}` | ❌ Fails | Outputs `None` |

**Location**: `bengal/rendering/kida/parser/expressions.py` lines 401-414

```python
# Only lowercase versions are handled:
if token.value == "true":
    return Const(token.lineno, token.col_offset, True)
elif token.value == "false":
    return Const(token.lineno, token.col_offset, False)
elif token.value == "none":
    return Const(token.lineno, token.col_offset, None)
# Python-style True/False/None fall through to Name node → ctx.get()
```

**Fix Required**: Add cases for `"True"`, `"False"`, `"None"` to handle Python-style keywords.

---

### Issue Status Summary

| Issue | Status | Notes |
|-------|--------|-------|
| #1: def closing tag | ✅ Working | Unified `{% end %}` works correctly with nested content |
| #2: empty in nested | ✅ Working | `{% empty %}` works correctly after nested blocks |
| #3: Inconsistent end | ℹ️ Clarification | Works as designed; both `{% end %}` and `{% enddef %}` work |
| #4: Defs in conditionals | 🔴 Root Cause Found | Caused by `True`/`False`/`None` bug above |
| #5: Error messages | ℹ️ Enhancement | Low priority - DX improvement |

---

## Issues Encountered During Jinja2 → Kida Migration

### 1. `{% def %}` Block Closing Tag Ambiguity

> **✅ VERIFIED WORKING**: Investigation (2025-12-26) confirmed the unified `{% end %}` works correctly with nested content. Both `{% end %}` and `{% enddef %}` work as expected.

**Original Issue**: `{% def %}` blocks with nested content reportedly cannot use unified `{% end %}`.

**Verification Tests**:
```kida
{# ✅ Simple def with unified end #}
{% def simple() %}Hello{% end %}

{# ✅ Def with nested if using unified end #}
{% def nested_if() %}
{% if true %}Hello{% end %}
{% end %}

{# ✅ Explicit enddef also works #}
{% def nested_if() %}
{% if true %}Hello{% end %}
{% enddef %}
```

**Note**: The original issue likely occurred when using Python-style `{% if True %}` (which fails due to the `True`/`False`/`None` bug). With lowercase `{% if true %}`, nested content works correctly with `{% end %}`.

**Status**: Working as designed. Both `{% end %}` and `{% enddef %}` are valid closing tags.

**Impact**: None - working correctly.

---

### 2. `{% empty %}` Clause Parsing in Nested Contexts

> **✅ VERIFIED WORKING**: Investigation (2025-12-26) confirmed this works correctly. The `{% empty %}` clause is properly recognized after nested blocks.

**Original Issue**: `{% empty %}` clause reportedly not recognized when it appears after nested blocks inside a `{% for %}` loop.

**Verification Test**:
```kida
{% for group in items %}
  {% if group.is_group %}
    ...
  {% end %}
  {% empty %}  {# ✅ Works correctly #}
  No items
{% end %}
```

**Status**: Working as expected. Either this was fixed or the original report was based on a different edge case.

**Impact**: None - working correctly.

---

### 3. Inconsistent `{% end %}` Behavior

**Issue**: Simple `{% def %}` blocks work with `{% end %}`, but blocks with nested content require `{% enddef %}`.

**Problem**: This creates inconsistency - developers must know when to use `{% end %}` vs `{% enddef %}`.

**Recommendation**:
- Standardize on one approach: either always require `{% enddef %}` for `{% def %}` blocks, or fix the parser to handle `{% end %}` correctly in all cases
- Document the requirement clearly if the current behavior is intentional

**Impact**: Low - mainly a documentation/clarity issue.

---

### 4. Defs Not Accessible Inside Conditionals in Inherited Blocks

> **⚠️ ROOT CAUSE IDENTIFIED**: This issue is caused by the `True`/`False`/`None` bug documented above. When `{% if True %}` is used, `True` is treated as an undefined variable that resolves to `None`, so the conditional block never executes. **Use lowercase `{% if true %}` as workaround.**

**Issue**: Defs defined in base templates appear NOT accessible when called inside conditionals (`{% if True %}`) within child template blocks.

**Actual Problem**: The issue is NOT with def scoping. It's that `{% if True %}` doesn't work because `True` (Python-style) is not recognized as a boolean constant. The condition evaluates to `None` (falsy), so the block never renders.

**Example**:
```kida
{# base.html #}
{% def helper() %}Helper{% enddef %}
<html>{% block content %}{% endblock %}</html>

{# child.html #}
{% extends "base.html" %}
{% block content %}
Direct: {{ helper() }}        {# ✅ Works #}
{% for i in [1] %}
Loop: {{ helper() }}           {# ✅ Works #}
{% endfor %}
{% if True %}                  {# ❌ True → ctx.get('True') → None → falsy #}
If: {{ helper() }}             {# Never executes! #}
{% endif %}
{% if true %}                  {# ✅ Use lowercase #}
If: {{ helper() }}             {# ✅ Works! #}
{% endif %}
{% endblock %}
```

**Current Workaround**:
- **Use lowercase `true`/`false`/`none`** (Jinja2 style)
- Pass boolean values through context: `{% if show %}` with `show=True` in render()

**Recommendation**:
- Fix the parser to recognize Python-style `True`, `False`, `None` (see Investigation Results above)

**Impact**: High - this causes confusing behavior when using Python-style booleans.

---

### 5. Parser Error Messages

**Issue**: Error messages could be more helpful for debugging nested block issues.

**Current**: "Unexpected end of template in def" doesn't indicate which block is unclosed or where the mismatch occurred.

**Recommendation**:
- Track block stack in parser and include it in error messages
- Show which blocks are still open when an error occurs
- Provide suggestions based on the current block context

**Impact**: Low - improves developer experience.

---

## Design Limitations & Expected Behavior

These are intentional design decisions or limitations discovered during comprehensive testing. They are documented here for clarity, not as bugs to fix.

### 1. Defs Must Be Defined at Template Level

**Limitation**: Defs cannot be defined inside blocks (like `{% block content %}`). They must be defined at the template's top level.

**Example**:
```kida
{# ✅ Works: Def at template level #}
{% def helper() %}Helper{% enddef %}
{% block content %}
  {{ helper() }}
{% endblock %}

{# ❌ Doesn't work: Def inside block #}
{% block content %}
  {% def helper() %}Helper{% enddef %}
  {{ helper() }}
{% endblock %}
```

**Reason**: Defs are compiled at the template level before blocks are processed. This ensures they're available throughout the template and in all blocks.

**Workaround**: Define defs at the template level, before any blocks.

**Impact**: Low - this is a reasonable design constraint that matches how functions work in most languages.

---

### 2. Blocks in Partials Don't Participate in Inheritance

**Behavior**: Blocks defined inside partials (via `{% include %}`) don't participate in template inheritance the same way as blocks defined directly in templates.

**Example**:
```kida
{# base.html #}
<html>{% block content %}{% endblock %}</html>

{# partial.html #}
{% block section %}Default{% endblock %}

{# child.html #}
{% extends "base.html" %}
{% block content %}
  {% include "partial.html" %}
{% endblock %}
{% block section %}Override{% endblock %}
```

In this case, the `section` block override in `child.html` won't affect the block in `partial.html`. The partial's default will be used.

**Reason**: Partials are included at render time, not during template compilation. Block inheritance happens at compile time when templates are extended.

**Workaround**:
- Define blocks directly in templates, not in partials
- Use defs/macros in partials instead of blocks if you need reusable components
- Pass data to partials via context variables

**Impact**: Low-Medium - this is expected behavior but may be surprising to developers coming from Jinja2.

---

### 3. Context Variables Flow Correctly Through Inheritance

**Positive Behavior**: Context variables passed to templates flow correctly through inheritance chains and are accessible in all blocks.

**Example**:
```kida
{# base.html #}
<html>{{ title }}{% block content %}{% endblock %}</html>

{# child.html #}
{% extends "base.html" %}
{% block content %}{{ title }}{% endblock %}
```

When rendering `child.html` with `title="Test"`, the variable appears in both the base template and the child block.

**Note**: When a child block overrides a parent block, the parent block's content is replaced (not appended). So if the base template has `{{ title }}` in a block, and the child overrides that block, only the child's block content is rendered.

**Impact**: Positive - this works as expected and is well-designed.

---

### 4. Set Variables Flow Through Partial Inclusion

**Positive Behavior**: Variables set with `{% set %}` flow correctly through partial inclusion chains.

**Example**:
```kida
{# level1.html #}
{% set x = 1 %}
{% include "level2.html" %}

{# level2.html #}
{% set y = 2 %}
{{ x }}{{ y }}
{% include "level3.html" %}

{# level3.html #}
{% set z = 3 %}
{{ x }}{{ y }}{{ z }}
```

All variables (`x`, `y`, `z`) are accessible in `level3.html` because partials share the same context.

**Impact**: Positive - this works correctly and enables good composition patterns.

---

### 5. Defs Work in Loops But Not Conditionals (Resolved)

> **✅ ROOT CAUSE IDENTIFIED**: This was caused by the `True`/`False`/`None` bug, not a scoping issue. See Issue #4 and Investigation Results above.

**Original Issue**: Defs defined in base templates work inside loops (`{% for %}`) but not inside conditionals (`{% if %}`) in child blocks.

**Resolution**: Use lowercase `true`/`false`/`none` or context variables. The conditional itself was failing, not the def access.

**Status**: Not a scoping bug. Root cause is the Python-style boolean recognition issue.

---

## Positive Observations

1. **Unified `{% end %}` works well** for simple cases (if/for/with blocks)
2. **`{% empty %}` syntax** is clearer than Jinja2's `{% else %}` in for loops
3. **Function scoping** with `{% def %}` is a good improvement over macros
4. **Parser is generally robust** - handles most edge cases well

---

## Suggested Next Steps

**Updated Priority Order** (2025-12-26):

1. **🔴 HIGH PRIORITY**: Fix Python-style `True`/`False`/`None` recognition
   - **Location**: `bengal/rendering/kida/parser/expressions.py` lines 401-414
   - **Fix**: Add cases for `"True"`, `"False"`, `"None"` in `_parse_primary()`
   - **Impact**: Fixes confusing behavior when using Python-style booleans
   - **Difficulty**: Easy (add 3 elif cases)

2. **🟢 LOW PRIORITY**: Improve error messages with block stack tracking (Issue #5)
   - Enhancement for developer experience
   - Not blocking any functionality

**Issues Verified Working** (no action needed):
- Issue #1: `{% def %}` closing tags ✅
- Issue #2: `{% empty %}` in nested contexts ✅
- Issue #3: `{% end %}` behavior ✅
- Issue #4: Defs in conditionals ✅ (after fixing True/False/None)

---

## Test Cases for Parser

> **Note**: Use lowercase `true`/`false`/`none` until the Python-style boolean bug is fixed.

```kida
# ✅ Works: Simple def
{% def simple() %}Hello{% end %}

# ✅ Works: Def with nested if (use lowercase 'true')
{% def nested_if() %}
{% if true %}Hello{% end %}
{% enddef %}

# ❌ FAILS: Python-style True (becomes undefined variable)
{% if True %}This won't render{% end %}

# ✅ Works: Def with nested for/empty
{% def nested_for_empty() %}
{% for x in [] %}
{% if true %}Item{% end %}
{% empty %}
No items
{% end %}
{% enddef %}

# ✅ Works: Empty after nested block
{% for group in items %}
{% if group.is_group %}
...
{% end %}
{% empty %}
No items
{% end %}
```

### Quick Reference: Boolean Keywords

| Jinja2/Kida Style | Python Style | Status |
|-------------------|--------------|--------|
| `true` | `True` | ✅ / ❌ |
| `false` | `False` | ✅ / ❌ |
| `none` | `None` | ✅ / ❌ |

**Always use lowercase** until Python-style keywords are supported.
