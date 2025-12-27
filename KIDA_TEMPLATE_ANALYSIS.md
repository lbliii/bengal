# Kida Template Engine Analysis: Public Output Issues

**Date**: 2025-01-27  
**Scope**: Analysis of public HTML output to identify Kida parser or template conversion issues  
**Status**: Analysis Complete

---

## Executive Summary

Analysis of the site's public output (`site/public/`) reveals **template rendering failures** affecting multiple pages. The primary issue is that templates using Kida syntax are failing to render, causing fallback HTML to be generated. Key findings:

1. **Fallback mode detected**: `/docs/index.html` and release pages show fallback notices
2. **Template syntax issues**: Templates use Jinja2 patterns that may not be fully compatible with Kida
3. **Method call mutations**: Templates use `{% set _ = list.append(item) %}` pattern which may not work correctly

---

## Issues Found

### 1. Template Rendering Failures

**Location**: `site/public/docs/index.html`

**Evidence**:
```html
<div class="fallback-notice">
  <strong>⚠️ Notice:</strong> This page is displayed in fallback mode due to a template error.
  Some features (navigation, sidebars, etc.) may be missing.
</div>
```

**Affected Pages**:
- `/docs/index.html` (main documentation home)
- `/releases/*/index.html` (multiple release pages)

**Root Cause**: Template `doc/home.html` fails to render with Kida engine, triggering fallback rendering.

---

### 2. Template Syntax: List Mutation Pattern

**Location**: `bengal/themes/default/templates/doc/home.html:40-43`

**Problematic Code**:
```kida
{% set doc_sections = [] %}
{% for section in site.sections %}
{% if section.metadata.type == 'doc' or section.metadata.content_type == 'doc' %}
{% set _ = doc_sections.append(section) %}
```

**Issue**: The pattern `{% set _ = list.append(item) %}` is a Jinja2 idiom for mutating lists. While Kida's expression parser supports method calls (`FuncCall` nodes), the `{% set %}` statement may not properly handle:
1. Method calls that mutate objects (like `list.append()`)
2. Assignment to `_` (discard pattern)

**Kida Support**:
- ✅ Expression parser supports method calls (`FuncCall` node)
- ✅ Expression parser supports attribute access (`Getattr` node)
- ❓ `{% set %}` statement may not handle mutation side effects correctly

**Evidence from Code**:
- `bengal/rendering/kida/parser/expressions.py:291-301` - Supports `FuncCall` parsing
- `bengal/rendering/kida/compiler/statements/variables.py:23-89` - `_compile_set()` only handles assignment, not mutation side effects

---

### 3. Template Conversion Status

**Current State**: Templates use **mixed syntax**:
- ✅ Unified `{% end %}` tags (Kida-native)
- ✅ `{% extends %}`, `{% block %}` (compatible)
- ⚠️ `{% set %}` with list mutations (Jinja2 pattern, may not work)

**Template Engine Config**: `site/config/_default/site.yaml:13`
```yaml
template_engine: kida
```

**Templates Analyzed**:
- `doc/home.html` - Uses `{% set _ = list.append() %}` pattern ❌
- `base.html` - Uses standard Kida syntax ✅
- **71 instances** of `{% set _ = list.append() %}` pattern found across templates ❌
- **6 instances** of `{% do list.append() %}` pattern found (correct usage) ✅

**Affected Templates** (using incorrect pattern):
- `doc/home.html` (2 instances)
- `partials/content-components.html` (6 instances)
- `autodoc/openapi/section-index.html` (1 instance)
- `autodoc/cli/section-index.html` (1 instance)
- `autodoc/python/section-index.html` (1 instance)
- `autodoc/partials/header.html` (15 instances)
- `autodoc/partials/members.html` (12 instances)
- `author/list.html` (2 instances)
- `blog/home.html` (1 instance)
- `author/single.html` (1 instance)
- `changelog/list.html` (6 instances)
- `home.html` (2 instances)
- And more...

---

## Technical Analysis

### Kida Expression Parser Capabilities

**Supported** (from `bengal/rendering/kida/parser/expressions.py`):
- ✅ Attribute access: `obj.attr`
- ✅ Method calls: `obj.method(args)`
- ✅ Subscript access: `obj[key]`
- ✅ Filter chains: `x | filter1 | filter2`
- ✅ Complex expressions: `x if y else z`

**Unclear**:
- ❓ Method calls that mutate objects: `list.append(item)`
- ❓ Side effects in `{% set %}` statements

### Kida Set Statement Compilation

**From** `bengal/rendering/kida/compiler/statements/variables.py:23-89`:

```python
def _compile_set(self, node: Any) -> list[ast.stmt]:
    """Compile {% set %}."""
    value = self._compile_expr(node.value)  # Compiles expression
    # ... assigns to ctx['name']
```

**Analysis**: The `_compile_set()` method:
1. Compiles the expression (including method calls)
2. Assigns the **return value** to the context variable
3. Does **not** handle mutation side effects explicitly

**Issue**: When `{% set _ = doc_sections.append(section) %}`, the expression `doc_sections.append(section)`:
- ✅ Compiles correctly (returns `None`)
- ✅ Assigns `None` to `_` (discarded)
- ❓ **May not execute the mutation** if the expression is optimized away or if `doc_sections` is not properly resolved

---

## Root Cause Hypothesis

### Hypothesis 1: Context Variable Resolution

**Problem**: `doc_sections` is created with `{% set doc_sections = [] %}`, but when accessed in `doc_sections.append(section)`, Kida may:
- Not resolve `doc_sections` from context correctly
- Create a new local variable instead of mutating the context variable

**Evidence Needed**: Check if `doc_sections` is properly stored/retrieved from context.

### Hypothesis 2: Expression Evaluation Order

**Problem**: The `{% set _ = expr %}` pattern may not evaluate `expr` if the result is discarded.

**Evidence Needed**: Check if Kida optimizes away expressions assigned to `_`.

### Hypothesis 3: Method Call Execution

**Problem**: Method calls like `list.append()` may not execute correctly in Kida's expression evaluation.

**Evidence Needed**: Test if `{% set _ = ctx['list'].append(item) %}` works.

---

## Recommended Fixes

### Fix 1: Replace List Mutation Pattern

**Current** (Jinja2 pattern):
```kida
{% set doc_sections = [] %}
{% for section in site.sections %}
{% if section.metadata.type == 'doc' %}
{% set _ = doc_sections.append(section) %}
```

**Recommended** (Kida-compatible):
```kida
{% set doc_sections = [] %}
{% for section in site.sections %}
{% if section.metadata.type == 'doc' or section.metadata.content_type == 'doc' %}
{% set doc_sections = doc_sections + [section] %}
```

**Alternative** (using filter):
```kida
{% set doc_sections = site.sections | selectattr('metadata.type', 'equalto', 'doc') | list %}
```

### Fix 2: Use `{% do %}` Statement ✅ **RECOMMENDED**

**Kida DOES support `{% do %}`** (statement expressions):
```kida
{% set doc_sections = [] %}
{% for section in site.sections %}
{% if section.metadata.type == 'doc' %}
{% do doc_sections.append(section) %}
```

**Evidence**: Found `{% do %}` usage in existing templates:
- `partials/archive-sidebar.html:97` - `{% do post_counts.append(...) %}`
- `category-browser.html:74,79,108,183,197` - Multiple `{% do %}` usages

**This is the correct Kida pattern for side effects!**

### Fix 3: Use List Comprehension Pattern

**Most Kida-native**:
```kida
{% set doc_sections = [] %}
{% for section in site.sections %}
{% if section.metadata.type == 'doc' or section.metadata.content_type == 'doc' %}
{% set doc_sections = doc_sections | list + [section] %}
```

---

## Testing Strategy

### Test 1: Verify Method Calls Work

```python
# Test if method calls execute in {% set %}
tmpl = env.from_string("""
{% set items = [] %}
{% set _ = items.append(1) %}
{{ items | length }}
""")
assert tmpl.render() == "1"  # Should be 1 if mutation works
```

### Test 2: Verify Context Variable Mutation

```python
# Test if context variables can be mutated
tmpl = env.from_string("""
{% set x = [] %}
{% set _ = x.append('a') %}
{% set _ = x.append('b') %}
{{ x | join(',') }}
""")
assert tmpl.render() == "a,b"  # Should work if mutations persist
```

### Test 3: Verify Discard Pattern

```python
# Test if `_` assignment executes expression
tmpl = env.from_string("""
{% set x = [] %}
{% set _ = x.append(1) %}
{{ x | length }}
""")
assert tmpl.render() == "1"  # Should execute even if result discarded
```

---

## Next Steps

1. ✅ **COMPLETED**: Fixed all `{% set _ = list.append() %}` patterns → `{% do list.append() %}`
   - **Result**: 58 replacements across 18 template files
   - **Script**: `scripts/fix_kida_mutation_patterns.py`
2. **Immediate**: Rebuild site to verify templates render correctly
3. **Short-term**: Add linting rule to catch this pattern in future templates
4. **Long-term**: Document Kida-compatible patterns vs Jinja2 patterns

---

## Files to Review

### Templates
- `bengal/themes/default/templates/doc/home.html` - **Primary issue**
- `bengal/themes/default/templates/base.html` - Check for similar patterns
- All templates in `bengal/themes/default/templates/` - Full scan needed

### Kida Parser/Compiler
- `bengal/rendering/kida/parser/expressions.py` - Expression parsing
- `bengal/rendering/kida/compiler/statements/variables.py` - Set statement compilation
- `bengal/rendering/kida/compiler/expressions.py` - Expression compilation

### Tests
- `tests/rendering/kida/test_kida_statements.py` - Add tests for mutation patterns
- `tests/rendering/kida/test_kida_expressions.py` - Add tests for method calls

---

## Related Issues

- `KIDA_FEEDBACK.md` - Documents known Kida parser issues
- `plan/drafted/rfc-default-theme-kida-migration.md` - Migration plan for templates

---

## Conclusion

The primary issue is **template syntax incompatibility** between Jinja2 patterns (list mutations) and Kida's execution model. The `{% set _ = list.append() %}` pattern does not work correctly in Kida, causing template rendering failures.

**Root Cause**: 71 templates use the incorrect `{% set _ = list.append() %}` pattern instead of the correct `{% do list.append() %}` pattern.

**Recommended Action**:
1. **Immediate**: Replace all `{% set _ = list.append() %}` with `{% do list.append() %}`
2. **Verify**: Test that `{% do %}` works correctly for all mutation patterns
3. **Document**: Add linting rule to catch this pattern in future templates

**Files Requiring Fixes**: 20+ template files with 71 instances total.
