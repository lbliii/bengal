# RFC: Kida Optional Subscript Sugar (`?.[key]`)

**Status**: Closed (Documentation)  
**Author**: AI Assistant  
**Created**: 2025-01-01  
**Resolved**: 2025-01-01  
**Issue**: `?.[key]` is currently a parse error; users expect it to behave like optional subscript (`?[key]`)

---

## Summary

Kida supports optional attribute access (`obj?.attr`) and optional subscript access (`obj?[key]`). Today, `obj?.[key]` fails because `?.` is parsed as optional *dot* access and requires a following attribute name.

This RFC proposes a parser-only enhancement: treat `obj?.[key]` as syntactic sugar for `obj?[key]` to reduce confusion (especially when users come from JavaScript/TypeScript, where `obj?.[key]` is common).

## Problem Statement

### Current Behavior

```html
{% let value = data?.["in"] %}
```

**Error:**
```
Parse Error: Expected attribute name after ?.
  --> template.html:1:20
   |
 1 | {% let value = data?.["in"] %}
   |                    ^
```

This error is expected given the current grammar: after `?.` the parser requires a `NAME` token (an attribute).

### Expected Behavior

`data?.["in"]` should parse and behave like optional subscript access: `data?["in"]`.

Non-goal: change how *strings* are tokenized. Quoted strings inside subscripts already work (for example, `data["in"]` parses correctly today).

### Real-World Impact

This came up in OpenAPI template development where `in` is a common field in security scheme definitions:

```yaml
# OpenAPI spec
securitySchemes:
  apiKey:
    type: apiKey
    in: header        # <-- 'in' is a standard OpenAPI field
    name: X-API-Key
```

```html
{# Template trying to access this data #}
{% for name, scheme in security_schemes |> items %}
  {% let location = scheme?.["in"] %}  {# currently fails; users expect it to work #}
{% end %}
```

**Workaround** (today):
```html
{% let location = scheme?["in"] ?? "header" %}
```

## Proposed Solution

### Approach: Parser-Level Sugar

Interpret the token sequence `OPTIONAL_DOT` (`?.`) followed immediately by `LBRACKET` (`[`) as optional subscript access.

This keeps the lexer unchanged and makes the parser accept both spellings:
- Canonical: `obj?[key]`
- Sugar: `obj?.[key]`

### Implementation

**Location**: `bengal/rendering/kida/parser/expressions.py`

**Change**: In the `OPTIONAL_DOT` postfix branch, if the next token is `LBRACKET`, parse a subscript and emit an `OptionalGetitem` node instead of raising “Expected attribute name after ?.”.

## Test Cases

### Optional Subscript Sugar
```html
{% let x = data?.["in"] %}             {# Should work (sugar) #}
{% let x = data?.['in'] %}             {# Should work (sugar) #}
{% let x = data?.items?.["in"] %}      {# Should work (sugar chained) #}
```

### Canonical Optional Subscript
```html
{% let x = data?["in"] %}          {# Should work (canonical) #}
{% let x = data?.items?["in"] %}   {# Should work (mixing ?. and ?[) #}
```

### Non-goal: reserved words inside quoted strings
```html
{% let x = data["in"] %}           {# Already works today #}
{% let x = data['for'] %}          {# Already works today #}
```

### Mixed Expressions
```html
{% let x = data['prefix_' ~ key ~ '_in'] %}  {# String concat, should work #}
{% let x = data[key] %}                       {# Variable key, already works #}
```

### Negative Cases (Should Still Fail)
```html
{% let x = data[in] %}    {# ❌ Bare keyword, should fail #}
{% for x in data %}       {# ✅ 'in' as keyword, should work #}
{% if x in items %}       {# ✅ 'in' as operator, should work #}
```

## Migration

**Backward Compatibility**: Additive enhancement. Existing templates keep working. Templates using `?.[key]` (currently failing) will start working.

**No breaking changes**.

## Alternatives Considered

### 1. Document `?[key]` as the only supported syntax ✅ CHOSEN
Kida's `?[key]` is the better design. It's more concise, follows a consistent prefix pattern, and avoids JavaScript's historical baggage. Documentation was updated to make this convention clear.

### 2. Add parser sugar for `?.[key]`
**Not implemented**: While this would reduce friction for JavaScript developers, it adds complexity for marginal benefit. The documentation approach is sufficient—users learn the pattern once.

### 3. Lexer context mode for subscripts
**Not needed**: Quoted strings already lex as `STRING` in all contexts. The original RFC misdiagnosed the issue.

### 4. Pre-process templates to rewrite `?.[key]` to `?[key]`
**Rejected**: Adds build complexity and makes errors harder to map back to source.

## Implementation Estimate

Removed. This RFC does not estimate implementation work.

## Related Issues

- OpenAPI templates sometimes use `?.[key]` patterns and get “Expected attribute name after ?.”

## Decision

**Resolved via documentation.**

After analysis, we decided that Kida's `?[key]` syntax is the correct design choice:

1. **Already working**: `data?['in']` works today
2. **More concise**: Avoids the redundant dot in `?.[]`
3. **Consistent pattern**: `?` prefix makes any accessor optional (`?.` for attribute, `?[` for subscript)
4. **No historical baggage**: JavaScript uses `?.[]` due to backwards compatibility constraints that don't apply to Kida

**Actions taken**:
- Updated [Kida Syntax Reference](/docs/reference/kida-syntax/) with comprehensive optional chaining documentation
- Added tip explaining the `?[` vs `?.[]` difference for users coming from JavaScript
- Documented common use cases (reserved word keys, safe array access, nested structures)

**No parser changes required.** Users should use `data?['key']` (canonical Kida syntax).
