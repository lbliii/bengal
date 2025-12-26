# RFC: Null Coalescing and Filter Ergonomics

**Status**: Drafted  
**Created**: 2025-12-26  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P3 (Low - mostly documentation/guidance)  
**Related**: `bengal/rendering/kida/_types.py`, `rfc-kida-modern-syntax-features.md`  
**Confidence**: 85% 🟢

---

## Executive Summary

The `??` operator has lower precedence than `|` (pipe), causing `x ?? [] | length` to parse as `x ?? ([] | length)` instead of the expected `(x ?? []) | length`. This RFC proposes a documentation-first approach: **recommend `| default()` for filter chains** while keeping `??` for simple fallbacks.

**Key finding**: Kida already has the solution — the `default` filter works correctly in pipelines. This is a guidance/docs issue, not a code change.

---

## Problem Statement

### The Precedence Gotcha

```jinja
{# User expects: get items or empty list, then get length #}
{{ items ?? [] | length }}

{# Actually parses as: get items, or if null get length of empty list (0) #}
{{ items ?? ([] | length) }}

{# Result: When items is [1,2,3], outputs "[1, 2, 3]" not "3" #}
```

### Impact Assessment

| Severity | Count | Notes |
|----------|-------|-------|
| Templates fixed | 9 | Found and fixed in this session |
| Pattern frequency | Low | Most templates use simpler patterns |
| User confusion | Medium | JavaScript users expect different behavior |

---

## Solution Analysis

### The `|>` Pipeline Doesn't Help

Pipeline has the **same precedence** as pipe (both = 6):

```python
# From _types.py
PRECEDENCE = {
    TokenType.PIPE: 6,
    TokenType.PIPELINE: 6,  # Same precedence as PIPE
    TokenType.NULLISH_COALESCE: 0,  # Lowest
}
```

So `x ?? [] |> length` has the same problem.

### The `default` Filter IS the Solution

Kida already has a `default` filter that works correctly:

```jinja
{# These all work correctly #}
{{ items | default([]) | length }}
{{ items |> default([]) |> length }}
```

The filter is evaluated left-to-right as part of the chain, no precedence issues.

---

## Proposed Solution: Documentation + Guidance

### 1. Document the Two Patterns

| Pattern | Use When | Example |
|---------|----------|---------|
| `??` | Simple fallback, no further filtering | `{{ user?.name ?? 'Anonymous' }}` |
| `\| default()` | Fallback followed by filters | `{{ items \| default([]) \| length }}` |

### 2. Update Kida Documentation

Add to syntax reference and migration guide:

```markdown
## Providing Fallback Values

### Simple Fallbacks: Use `??`

For direct output without further processing:

{{ user.name ?? 'Anonymous' }}
{{ config.timeout ?? 30 }}

### Filter Chains: Use `| default()`

When you need to apply filters after the fallback:

{{ items | default([]) | length }}           {# ✅ Correct #}
{{ description | default('') | truncate(100) }}  {# ✅ Correct #}

⚠️ Don't mix `??` with filters:

{{ items ?? [] | length }}                  {# ❌ Precedence gotcha #}
{{ (items ?? []) | length }}                {# ⚠️ Works but verbose #}
```

### 3. (Optional) Add Linter Warning

Could add a warning for the pattern `?? ... |` to catch this at build time:

```
Warning: Possible precedence issue in template.html:45
  {{ items ?? [] | length }}
         ^^^^^^^^^^^^^^^^
  The `??` operator has lower precedence than `|`.
  This parses as: items ?? ([] | length)

  Consider using: {{ items | default([]) | length }}
```

### 4. Update Template Best Practices

Recommend in coding guidelines:

```markdown
## Template Best Practices

### Prefer `| default()` over `??` for filter chains

✅ Good:
{{ items | default([]) | length }}
{{ name | default('') | upper }}

⚠️ Avoid (precedence gotcha):
{{ items ?? [] | length }}
{{ name ?? '' | upper }}

✅ OK for simple fallbacks:
{{ title ?? 'Untitled' }}
{{ count ?? 0 }}
```

---

## Implementation Plan

### Phase 1: Documentation (This PR)
- [ ] Update `site/content/docs/reference/kida-syntax.md` with fallback patterns
- [ ] Update `site/content/docs/theming/templating/kida/migrate-jinja-to-kida.md`
- [ ] Add section to Kida comparison docs

### Phase 2: Template Updates (Optional)
- [ ] Audit remaining templates for `?? ... |` pattern
- [ ] Convert to `| default()` pattern where applicable
- [ ] The 9 templates fixed today used parentheses; could convert to `| default()`

### Phase 3: Tooling (Future)
- [ ] Add optional linter warning for `?? ... |` pattern
- [ ] Consider IDE extension hints

---

## Alternatives Considered

### A. Change `??` Precedence (Rejected)

```python
PRECEDENCE = {
    TokenType.NULLISH_COALESCE: 7,  # Higher than PIPE
}
```

**Pros**: `x ?? [] | length` would just work  
**Cons**:
- Breaks `a or b ?? 'fallback'` → now parses as `a or (b ?? 'fallback')`
- Diverges from JavaScript semantics
- Breaking change with unclear migration path

### B. Introduce `??|` Compound Operator (Rejected)

```jinja
{{ items ??| [] | length }}
```

**Pros**: Clear intent, no precedence confusion  
**Cons**: Novel syntax, learning curve, implementation complexity

### C. Documentation + `default` Filter (Selected)

**Pros**:
- No code changes needed (filter already exists)
- Matches Jinja2/Twig/Liquid patterns
- Familiar to template developers
- Left-to-right readability

**Cons**: Requires users to know the pattern

---

## Test Coverage

Already added tests documenting the behavior:

```python
def test_pipe_has_higher_precedence_than_null_coalesce(self, env):
    """Documents the precedence gotcha."""
    tmpl_wrong = env.from_string("{{ x ?? [] | length }}")
    assert tmpl_wrong.render(x=[1, 2, 3]) == "[1, 2, 3]"  # Gets list, not length!

    tmpl_correct = env.from_string("{{ (x ?? []) | length }}")
    assert tmpl_correct.render(x=[1, 2, 3]) == "3"

def test_null_coalesce_with_filter_requires_parens(self, env):
    """Shows correct patterns."""
    # The default filter is the ergonomic solution
    tmpl = env.from_string("{{ x | default([]) | length }}")
    assert tmpl.render(x=[1, 2]) == "2"
```

---

## Migration Guide Snippet

For docs:

```markdown
## Migrating from `??` to `| default()` for Filter Chains

If you have templates using `??` with filters:

### Before (Precedence Issue)
{{ items ?? [] | length }}      ❌ Returns list, not length

### After (Two Options)

Option 1: Use `| default()` (Recommended)
{{ items | default([]) | length }}  ✅ Returns length

Option 2: Add parentheses
{{ (items ?? []) | length }}        ⚠️ Works but verbose

### When to Use Each

| Syntax | Best For |
|--------|----------|
| `x ?? fallback` | Simple output: `{{ name ?? 'Anonymous' }}` |
| `x \| default(fallback)` | Filter chains: `{{ items \| default([]) \| sort }}` |
```

---

## Success Criteria

- [ ] Documentation clearly explains when to use `??` vs `| default()`
- [ ] Migration guide includes common patterns
- [ ] Tests document the precedence behavior
- [ ] No new templates use the `?? ... |` anti-pattern

---

## Summary

**The solution already exists** — Kida's `default` filter provides the ergonomic pattern that matches Jinja2/Twig/Liquid. This RFC is primarily about:

1. **Documenting** the precedence behavior
2. **Guiding** users toward `| default()` for filter chains
3. **Optionally** adding tooling to catch the anti-pattern

No breaking changes. No new syntax. Just better guidance.
