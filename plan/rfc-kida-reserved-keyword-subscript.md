# RFC: Kida Reserved Keyword Subscript Access

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-01-01  
**Issue**: Parser fails on reserved keywords inside bracket subscript expressions

---

## Summary

Kida's parser incorrectly interprets reserved Python keywords (`in`, `is`, `for`, `if`, etc.) inside bracket subscript expressions as keywords rather than string literals. This causes valid dict access patterns like `obj['in']` to fail with parse errors.

## Problem Statement

### Current Behavior

```html
{% let value = data['in'] %}
```

**Error:**
```
Parse Error: Expected attribute name after ?.
  --> template.html:1:20
   |
 1 | {% let value = data['in'] %}
   |                    ^
```

The parser sees `in` and interprets it as the keyword `in` (used in `for x in items`), not as a string literal.

### Expected Behavior

The expression `data['in']` should be parsed as subscript access with the string key `'in'`, identical to how Jinja2 and Python handle it.

### Real-World Impact

This issue was discovered in OpenAPI template development where `in` is a common field in security scheme definitions:

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
  {% let location = scheme['in'] %}  {# ❌ FAILS #}
{% end %}
```

**Workaround** (currently required):
```html
{% let location = scheme.get('in', 'header') %}  {# ✅ Works but ugly #}
```

### Affected Keywords

All Python/Kida reserved keywords when used as string literals in subscripts:
- `in`, `is`, `if`, `else`, `for`, `while`, `and`, `or`, `not`
- `def`, `class`, `return`, `yield`, `import`, `from`, `as`
- `try`, `except`, `finally`, `raise`, `with`
- `True`, `False`, `None`
- `match`, `case` (Kida-specific)

## Proposed Solution

### Approach: Lexer Context Awareness

When the lexer encounters `[`, it should enter a "subscript context" where:
1. String literals are parsed normally (including those containing reserved words)
2. The subscript expression is terminated by `]`
3. Within quoted strings (`'...'` or `"..."`), no keyword recognition occurs

### Implementation

**Location**: `bengal/rendering/kida/lexer.py`

**Change**: After tokenizing `[`, switch to a subscript-aware mode that:
1. Continues tokenizing as normal for expressions
2. For string literals, captures the full string including reserved words
3. Returns to normal mode after `]`

**Key insight**: The lexer already correctly handles string literals in most contexts. The issue is specifically with how the parser combines tokens in subscript expressions.

### Alternative: Parser-Level Fix

If lexer changes are too invasive, the parser could be modified:
1. When parsing a subscript expression (after `[`)
2. If the next token is a string literal
3. Accept the string regardless of whether its content matches a keyword

**Location**: `bengal/rendering/kida/parser/expressions.py`

## Test Cases

### Basic Reserved Keyword Access
```html
{% let x = data['in'] %}      {# Should work #}
{% let x = data["in"] %}      {# Should work #}
{% let x = data['for'] %}     {# Should work #}
{% let x = data['if'] %}      {# Should work #}
{% let x = data['is'] %}      {# Should work #}
```

### Nested Access
```html
{% let x = data['items']['in'] %}  {# Should work #}
{% let x = data.items['in'] %}     {# Should work #}
```

### With Optional Chaining
```html
{% let x = data?.['in'] %}         {# Should work #}
{% let x = data?.items?.['in'] %}  {# Should work #}
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

**Backward Compatibility**: This is a pure enhancement. All currently-working templates continue to work. Templates that previously failed will now succeed.

**No breaking changes**.

## Alternatives Considered

### 1. Document `.get()` as the canonical pattern
**Rejected**: Forces awkward workarounds for a common use case. OpenAPI specs, JSON schemas, and many APIs use reserved words as keys.

### 2. Add escape syntax (e.g., `data[\'in\']`)
**Rejected**: Adds complexity. The string literal already clearly indicates it's a string, not a keyword.

### 3. Pre-process templates to rewrite `['keyword']` to `.get('keyword')`
**Rejected**: Lossy transformation (loses KeyError semantics), adds build complexity.

## Implementation Estimate

- **Effort**: Small (2-4 hours)
- **Risk**: Low (isolated lexer/parser change)
- **Testing**: Add test cases above to parser test suite

## Related Issues

- OpenAPI template development blocked on workarounds
- Similar issue in schema-viewer.html, responses.html, etc.

## Decision

Pending review.

---

## Appendix: Parser Flow

Current parsing of `data['in']`:

```
Token Stream:
  NAME(data) -> LBRACKET -> STRING('in') -> RBRACKET

Parser sees:
  1. NAME(data) -> start subscript expression
  2. LBRACKET -> expect subscript key
  3. STRING('in') -> ❌ Parser sees 'in' keyword, not string
  4. Error: unexpected keyword in subscript position
```

Expected parsing:

```
Token Stream:
  NAME(data) -> LBRACKET -> STRING('in') -> RBRACKET

Parser should:
  1. NAME(data) -> start subscript expression
  2. LBRACKET -> enter subscript context
  3. STRING('in') -> ✅ Accept as string literal key
  4. RBRACKET -> complete subscript, return Subscript(data, 'in')
```
