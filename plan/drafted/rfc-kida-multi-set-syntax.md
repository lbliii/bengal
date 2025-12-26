# RFC: Kida Multi-Set Syntax

**Status**: Draft  
**Created**: 2025-12-26  
**Priority**: Medium  
**Effort**: ~1 day  
**Impact**: Medium - Developer experience, template readability, minor parse-time improvement  
**Category**: Parser / Syntax / DX  
**Scope**: `bengal/rendering/kida/`

---

## Executive Summary

Bengal's templates contain **602 `{% set %}` statements** across 85 files, with 36+ files having consecutive set statements. This creates visual noise and requires repetitive typing.

This RFC proposes **comma-separated multi-set syntax**, allowing multiple independent variable assignments in a single block:

```jinja
{# Before: 5 lines #}
{% set section_filters = params.sections | default([]) %}
{% set show_recent = params.show_recent | default(3) %}
{% set layout = params.layout | default('grid') %}
{% set show_counts = params.show_counts | default(true) %}
{% set max_items = params.max_items | default(10) %}

{# After: 1 block #}
{% set
    section_filters = params.sections | default([]),
    show_recent = params.show_recent | default(3),
    layout = params.layout | default('grid'),
    show_counts = params.show_counts | default(true),
    max_items = params.max_items | default(10)
%}
```

This syntax is proven in **Volt** (Phalcon) and **Cheetah**, reduces template LOC by ~30%, and provides minor parse-time improvements.

---

## Problem Statement

### Current State

Templates, especially at the top of files, have long chains of consecutive `{% set %}` statements:

```jinja
{# From base.html - 12 consecutive sets #}
{% set _page_title = page.title %}
{% set _page_url = page._path %}
{% set _current_lang = current_lang() %}
{% set _main_menu = get_menu_lang('main', _current_lang) %}
{% set _auto_nav = get_auto_nav() if _main_menu | length == 0 else [] %}
{% set _footer_menu = get_menu_lang('footer', _current_lang) %}
{% set _site_title = config.title %}
{% set _build_badge = site.build_badge %}
{% set _doc_app = site.document_application %}
{% set _view_transitions = _doc_app.enabled and _doc_app.navigation.view_transitions %}
{% set _transition_style = _doc_app.navigation.transition_style %}
{% set _link_previews = site.link_previews %}
```

### Impact

| Issue | Metric | Evidence |
|-------|--------|----------|
| **Repetitive syntax** | 602 set statements | `grep "{% set" themes/` |
| **Consecutive sets** | 36+ files with chains | Multiline pattern match |
| **Visual noise** | ~5% of template LOC | Rough estimate |
| **Parse overhead** | 7 tokens per set | `{% set name = expr %}` |

### Usage Patterns

**Pattern 1: Config/Params Extraction** (most common, ~60%)
```jinja
{% set section_filters = params.sections | default([]) %}
{% set show_recent = params.show_recent | default(3) %}
{% set layout = params.layout | default('grid') %}
```

**Pattern 2: Function Call Caching** (~25%)
```jinja
{% set _current_lang = current_lang() %}
{% set _main_menu = get_menu_lang('main', _current_lang) %}
{% set _footer_menu = get_menu_lang('footer', _current_lang) %}
```

**Pattern 3: Loop Variable Setup** (~15%)
```jinja
{% set member_return = member.metadata.return_type or '' %}
{% set member_params = member.metadata.args or [] %}
{% set param_count = member_params | length %}
```

---

## Research: Other Template Engines

### Syntax Comparison

| Engine | Multi-Assign | Syntax | Notes |
|--------|--------------|--------|-------|
| **Volt (Phalcon)** | ✅ Independent | `{% set a = 1, b = 2, c = 3 %}` | Most popular approach |
| **Cheetah** | ✅ Independent | `#set $a = 1, $b = 2, $c = 3` | Python-based |
| **Jinja2** | ⚠️ Tuple only | `{% set a, b = 1, 2 %}` | Same RHS, not independent |
| **Jinja2 with** | ✅ Scoped block | `{% with a = 1, b = 2 %}...{% endwith %}` | Requires closing tag |
| **Twig** | ⚠️ Tuple only | `{% set a, b = 1, 2 %}` | Same as Jinja2 |
| **Nunjucks** | ⚠️ Broadcast | `{% set x, y, z = 5 %}` | All get same value |
| **Liquid** | ❌ None | Separate `{% assign %}` | No multi-assign |

### Developer Preference

Based on community feedback and adoption:

1. **Volt-style** (comma-separated) is most loved - clean, familiar, no new keywords
2. **Jinja2 `with`** is popular but verbose - requires `{% endwith %}`
3. **Tuple unpacking** is useful but different use case (same RHS)

### Performance Evidence

From Liquid/Jekyll optimization guides:
> "Caching values and minimizing repeated logic evaluations can reduce rendering time by up to 30%"

The gains come from:
- Fewer parse operations
- Reduced token count
- Smaller AST (optional)

---

## Proposed Solution

### Syntax Design

**Primary: Comma-separated independent assignments**

```jinja
{% set name1 = expr1, name2 = expr2, name3 = expr3 %}
```

**With line breaks for readability:**

```jinja
{% set
    name1 = expr1,
    name2 = expr2,
    name3 = expr3
%}
```

**Trailing comma allowed:**

```jinja
{% set
    name1 = expr1,
    name2 = expr2,
    name3 = expr3,  {# trailing comma OK #}
%}
```

### Backward Compatibility

| Existing Syntax | Status |
|-----------------|--------|
| `{% set x = 1 %}` | ✅ Unchanged |
| `{% set a, b = 1, 2 %}` | ✅ Unchanged (tuple unpacking) |
| `{% set x = a, b, c %}` | ✅ Unchanged (tuple value) |

### Disambiguation Rules

The parser distinguishes multi-set from tuple values by lookahead:

| Input | Interpretation | Reason |
|-------|----------------|--------|
| `{% set a = 1, b = 2 %}` | Multi-set (2 vars) | Comma followed by `NAME =` |
| `{% set a = 1, 2, 3 %}` | Single var, tuple value | Comma followed by expression |
| `{% set a = [1, 2], b = 3 %}` | Multi-set (2 vars) | List literal is self-contained |
| `{% set a = func(1, 2), b = 3 %}` | Multi-set (2 vars) | Call parens are self-contained |
| `{% set a, b = 1, 2, c = 3 %}` | ❌ Error | Tuple unpacking + multi-set not allowed |

**Key insight**: Parenthesized expressions (lists, calls, tuples) are self-contained. Only top-level commas followed by `NAME =` trigger multi-set continuation.

### AST Options

**Option A: Emit Multiple Set Nodes** (recommended)

```python
# {% set a = 1, b = 2 %} becomes:
[Set(target=Name('a'), value=Const(1)),
 Set(target=Name('b'), value=Const(2))]
```

Benefits:
- No compiler changes needed
- Existing `_compile_set` works unchanged
- Simpler implementation

**Option B: New MultiSet Node**

```python
@dataclass(frozen=True, slots=True)
class MultiSet(Node):
    """Multiple assignments: {% set a = 1, b = 2 %}"""
    assignments: tuple[tuple[Expr, Expr], ...]  # (target, value) pairs
```

Benefits:
- Preserves source grouping in AST
- Better for tooling/analysis
- Slight compile-time optimization potential

**Recommendation**: Start with Option A for simplicity. Add MultiSet node later if needed for tooling.

---

## Implementation

### Critical Design Decision: Expression Parsing

**Problem**: The current `_parse_set` uses `_parse_tuple_or_expression()` which consumes commas as tuple elements:

```python
# Current implementation (variables.py:37)
value = self._parse_tuple_or_expression()  # Consumes "1, 2" as tuple
```

**Solution**: Multi-set parsing must use `_parse_expression()` (not `_parse_tuple_or_expression()`) for each value. This ensures commas are available for multi-set detection:

```python
# Multi-set implementation
value = self._parse_expression()  # Stops at comma, doesn't consume it
```

The disambiguation happens *after* parsing each expression by checking if the next tokens are `, NAME =`.

### Phase 1: Parser Changes (~0.5 days)

**File**: `bengal/rendering/kida/parser/blocks/variables.py`

```python
def _parse_set(self) -> list[Set]:
    """Parse {% set x = expr %} or {% set x = 1, y = 2, z = 3 %}.

    Multi-set syntax allows comma-separated independent assignments:
        {% set a = 1, b = 2, c = 3 %}

    Tuple unpacking remains unchanged:
        {% set a, b = 1, 2 %}

    IMPORTANT: Uses _parse_expression() (not _parse_tuple_or_expression())
    to prevent commas from being consumed as tuple elements.
    """
    start = self._advance()  # consume 'set'
    sets: list[Set] = []

    while True:
        # Parse target - can be single name or tuple for unpacking
        target = self._parse_tuple_or_name()

        # Check for tuple unpacking (comma before =)
        is_tuple_unpack = hasattr(target, 'items') and len(target.items) > 1

        self._expect(TokenType.ASSIGN)

        if is_tuple_unpack:
            # Tuple unpacking: use _parse_tuple_or_expression for RHS
            # This handles {% set a, b = 1, 2 %}
            value = self._parse_tuple_or_expression()
            sets.append(Set(
                lineno=start.lineno,
                col_offset=start.col_offset,
                target=target,
                value=value,
            ))
            # Tuple unpacking cannot be combined with multi-set
            break
        else:
            # Single target: use _parse_expression to preserve commas
            value = self._parse_expression()

            sets.append(Set(
                lineno=start.lineno,
                col_offset=start.col_offset,
                target=target,
                value=value,
            ))

            # Check for multi-set continuation: , NAME =
            if self._current.type == TokenType.COMMA:
                if self._is_multi_set_continuation():
                    self._advance()  # consume comma
                    continue

            break

    self._expect(TokenType.BLOCK_END)
    return sets


def _is_multi_set_continuation(self) -> bool:
    """Check if comma is followed by 'NAME =' pattern (multi-set).

    Uses 2-token lookahead without consuming tokens.

    Returns True for: a = 1, b = 2
    Returns False for: a = 1, 2, 3 (tuple value)
    Returns False for: a = 1, (would be trailing comma)
    """
    # Peek ahead: COMMA NAME ASSIGN?
    # Current token is COMMA
    next_token = self._peek(1)
    if next_token.type != TokenType.NAME:
        return False

    next_next_token = self._peek(2)
    return next_next_token.type == TokenType.ASSIGN
```

**Note**: The parser already has `_peek()` via `TokenNavigationMixin`. Verify it exists:

```python
# In tokens.py - should already exist
def _peek(self, offset: int = 1) -> Token:
    """Peek at token without consuming."""
    pos = self._pos + offset
    if pos < len(self._tokens):
        return self._tokens[pos]
    return self._tokens[-1]  # EOF
```

### Phase 2: Statement Handler Update (~0.25 days)

**File**: `bengal/rendering/kida/parser/statements.py`

Update type signature and handling:

```python
def _parse_block_content(self) -> Node | list[Node] | None:
    """Parse block content after BLOCK_BEGIN is consumed.

    Returns:
        - Single Node for most blocks
        - list[Node] for multi-set
        - None for end tags
    """
    # ... existing code ...

    if keyword == "set":
        return self._parse_set()  # Returns list[Set]

    # ... rest unchanged ...
```

Update `_parse_body` to flatten lists (already handles single nodes):

```python
def _parse_body(self, stop_on_continuation: bool = False) -> list[Node]:
    """Parse template body until an end tag or EOF."""
    nodes: list[Node] = []

    while self._current.type != TokenType.EOF:
        # ... existing checks ...

        if self._current.type == TokenType.BLOCK_BEGIN:
            # ... existing lookahead ...

            result = self._parse_block()
            if result is not None:
                # Flatten multi-set results
                if isinstance(result, list):
                    nodes.extend(result)
                else:
                    nodes.append(result)
        # ... rest unchanged ...

    return nodes
```

### Phase 3: Tests (~0.25 days)

**File**: `tests/rendering/kida/test_kida_multi_set.py`

```python
"""Tests for multi-set syntax: {% set a = 1, b = 2 %}."""

import pytest
from bengal.rendering.kida import Environment


class TestMultiSetSyntax:
    """Test comma-separated multi-set assignments."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_basic_multi_set(self, env):
        """Two variables in one set block."""
        tmpl = env.from_string("{% set a = 1, b = 2 %}{{ a }}-{{ b }}")
        assert tmpl.render() == "1-2"

    def test_three_variables(self, env):
        """Three variables in one set block."""
        tmpl = env.from_string("{% set x = 'a', y = 'b', z = 'c' %}{{ x }}{{ y }}{{ z }}")
        assert tmpl.render() == "abc"

    def test_with_expressions(self, env):
        """Multi-set with complex expressions."""
        tmpl = env.from_string(
            "{% set items = [1,2,3], count = items|length, first = items[0] %}"
            "{{ count }}-{{ first }}"
        )
        assert tmpl.render() == "3-1"

    def test_with_filters(self, env):
        """Multi-set with filter expressions."""
        tmpl = env.from_string(
            "{% set name = 'HELLO'|lower, length = name|length %}"
            "{{ name }}:{{ length }}"
        )
        assert tmpl.render() == "hello:5"

    def test_multiline_format(self, env):
        """Multi-set with line breaks."""
        tmpl = env.from_string("""{% set
            a = 1,
            b = 2,
            c = 3
        %}{{ a }}{{ b }}{{ c }}""")
        assert tmpl.render() == "123"

    def test_trailing_comma(self, env):
        """Trailing comma is allowed."""
        tmpl = env.from_string("{% set a = 1, b = 2, %}{{ a }}-{{ b }}")
        assert tmpl.render() == "1-2"

    def test_single_set_unchanged(self, env):
        """Single set still works."""
        tmpl = env.from_string("{% set x = 42 %}{{ x }}")
        assert tmpl.render() == "42"

    def test_tuple_unpacking_unchanged(self, env):
        """Tuple unpacking still works."""
        tmpl = env.from_string("{% set a, b = 1, 2 %}{{ a }}-{{ b }}")
        assert tmpl.render() == "1-2"

    def test_tuple_value_unchanged(self, env):
        """Tuple as value still works."""
        tmpl = env.from_string("{% set x = 1, 2, 3 %}{{ x }}")
        assert tmpl.render() == "(1, 2, 3)"

    def test_disambiguation(self, env):
        """Disambiguate multi-set from tuple value."""
        # a = 1, b = 2 → multi-set (two vars)
        tmpl1 = env.from_string("{% set a = 1, b = 2 %}{{ a }}|{{ b }}")
        assert tmpl1.render() == "1|2"

        # a = (1, 2) → single var with tuple value
        tmpl2 = env.from_string("{% set a = (1, 2) %}{{ a }}")
        assert tmpl2.render() == "(1, 2)"

    def test_with_default_filter(self, env):
        """Common pattern: params extraction with defaults."""
        tmpl = env.from_string("""
            {% set
                layout = params.layout | default('grid'),
                count = params.count | default(10),
                show = params.show | default(true)
            %}
            {{ layout }}-{{ count }}-{{ show }}
        """)
        result = tmpl.render(params={}).strip()
        assert result == "grid-10-True"


class TestMultiSetNestedCommas:
    """Test disambiguation with commas inside expressions."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_list_literal_with_commas(self, env):
        """List literal commas don't trigger multi-set."""
        tmpl = env.from_string("{% set items = [1, 2, 3], count = 3 %}{{ items }}|{{ count }}")
        assert tmpl.render() == "[1, 2, 3]|3"

    def test_dict_literal_with_commas(self, env):
        """Dict literal commas don't trigger multi-set."""
        tmpl = env.from_string("{% set d = {'a': 1, 'b': 2}, x = 5 %}{{ d['a'] }}|{{ x }}")
        assert tmpl.render() == "1|5"

    def test_function_call_with_commas(self, env):
        """Function call commas don't trigger multi-set."""
        tmpl = env.from_string("{% set result = range(1, 5) | list, count = 4 %}{{ result }}|{{ count }}")
        assert tmpl.render() == "[1, 2, 3, 4]|4"

    def test_nested_parens_with_commas(self, env):
        """Nested parentheses with commas work correctly."""
        tmpl = env.from_string("{% set a = (1 + 2), b = (3, 4) %}{{ a }}|{{ b }}")
        assert tmpl.render() == "3|(3, 4)"

    def test_filter_with_comma_args(self, env):
        """Filter with comma args doesn't trigger multi-set."""
        tmpl = env.from_string("{% set x = 'hello' | replace('l', 'L'), y = 'world' %}{{ x }}|{{ y }}")
        assert tmpl.render() == "heLLo|world"

    def test_conditional_with_commas(self, env):
        """Ternary with tuples works correctly."""
        tmpl = env.from_string("{% set x = (1, 2) if true else (3, 4), y = 5 %}{{ x }}|{{ y }}")
        assert tmpl.render() == "(1, 2)|5"


class TestMultiSetEdgeCases:
    """Edge cases and error handling."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_empty_not_allowed(self, env):
        """Empty set block is an error."""
        with pytest.raises(Exception):  # TemplateSyntaxError
            env.from_string("{% set %}")

    def test_missing_value(self, env):
        """Missing value after = is an error."""
        with pytest.raises(Exception):
            env.from_string("{% set a = %}")

    def test_missing_equals(self, env):
        """Missing = is an error."""
        with pytest.raises(Exception):
            env.from_string("{% set a 1 %}")

    def test_double_comma(self, env):
        """Double comma is an error."""
        with pytest.raises(Exception):
            env.from_string("{% set a = 1,, b = 2 %}")

    def test_tuple_unpack_no_multiset(self, env):
        """Tuple unpacking cannot be combined with multi-set."""
        # This should be interpreted as tuple unpacking with tuple value
        # {% set a, b = 1, 2 %} is valid (tuple unpack)
        # {% set a, b = 1, 2, c = 3 %} is ambiguous - should error or be tuple unpack
        tmpl = env.from_string("{% set a, b = 1, 2 %}{{ a }}-{{ b }}")
        assert tmpl.render() == "1-2"

    def test_only_trailing_comma(self, env):
        """Just a trailing comma after single assignment."""
        tmpl = env.from_string("{% set a = 1, %}{{ a }}")
        assert tmpl.render() == "1"

    def test_complex_expression_chain(self, env):
        """Complex chained expression with multi-set."""
        tmpl = env.from_string(
            "{% set x = items | first | upper, y = items | last | lower %}"
            "{{ x }}-{{ y }}"
        )
        assert tmpl.render(items=['Hello', 'World']) == "HELLO-world"
```

---

## Performance Analysis

### Token Count Comparison

```
# Current: 5 separate sets = 35 tokens
{% set a = 1 %}   →  7 tokens: {% set a = 1 %}
{% set b = 2 %}   →  7 tokens
{% set c = 3 %}   →  7 tokens
{% set d = 4 %}   →  7 tokens
{% set e = 5 %}   →  7 tokens
                     ─────────
                     35 tokens

# Proposed: 1 multi-set = 17 tokens
{% set a = 1, b = 2, c = 3, d = 4, e = 5 %}

Token breakdown:
  {%          → 1 (BLOCK_BEGIN)
  set         → 1 (NAME)
  a           → 1 (NAME)
  =           → 1 (ASSIGN)
  1           → 1 (INTEGER)
  ,           → 1 (COMMA)
  b           → 1 (NAME)
  =           → 1 (ASSIGN)
  2           → 1 (INTEGER)
  ,           → 1 (COMMA)
  c           → 1 (NAME)
  =           → 1 (ASSIGN)
  3           → 1 (INTEGER)
  ,           → 1 (COMMA)
  d           → 1 (NAME)
  =           → 1 (ASSIGN)
  4           → 1 (INTEGER)
  ,           → 1 (COMMA)  [not present - only 4 commas for 5 vars]
  e           → 1 (NAME)
  =           → 1 (ASSIGN)
  5           → 1 (INTEGER)
  %}          → 1 (BLOCK_END)
              ─────────
              21 tokens (actual)

# Savings: 40% fewer tokens (35 → 21)
```

### Parse Time Impact

| Phase | Current (5 sets) | Proposed (1 multi-set) | Savings |
|-------|------------------|------------------------|---------|
| Lexer | 35 tokens | 21 tokens | 40% |
| Parser | 5 statement dispatches | 1 statement dispatch | 80% |
| AST nodes | 5 Set nodes | 5 Set nodes | 0% |
| Compiler | 5 × _compile_set | 5 × _compile_set | 0% |
| Runtime | 5 assignments | 5 assignments | 0% |

**Net effect**: Minor parse-time improvement (~5-10% for set-heavy templates), zero runtime impact.

---

## Migration Path

### Automated Migration (Optional)

A simple script could identify consecutive sets and suggest consolidation:

```python
# scripts/suggest_multiset.py
import re

def find_consecutive_sets(template: str) -> list[tuple[int, int, int]]:
    """Find line ranges with 3+ consecutive {% set %} statements."""
    lines = template.split('\n')
    ranges = []
    start = None
    count = 0

    for i, line in enumerate(lines):
        if re.match(r'\s*\{% set \w+ =', line):
            if start is None:
                start = i
            count += 1
        else:
            if count >= 3:
                ranges.append((start, i - 1, count))
            start = None
            count = 0

    # Handle end of file
    if count >= 3:
        ranges.append((start, len(lines) - 1, count))

    return ranges
```

### Gradual Adoption

1. **No breaking changes** - existing templates work unchanged
2. **Opt-in** - developers choose when to consolidate
3. **IDE support** - VS Code extension could offer quick-fix

---

## Alternatives Considered

### Alternative 1: `{% with %}` Block (Jinja2 style)

```jinja
{% with a = 1, b = 2, c = 3 %}
    {{ a }} {{ b }} {{ c }}
{% end %}
```

**Rejected because:**
- Requires closing tag
- Creates new scope (may not be desired)
- More verbose than multi-set

### Alternative 2: Object Destructuring (JS style)

```jinja
{% set { sections: section_filters, show_recent, layout } = params %}
```

**Deferred because:**
- Complex parser change
- Unfamiliar to Python users
- Good for extraction, but not for independent assignments

### Alternative 3: Semicolon Separator

```jinja
{% set a = 1; b = 2; c = 3 %}
```

**Rejected because:**
- Semicolons unusual in template syntax
- Comma is more Pythonic
- Less visual separation than comma + newline

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| All existing tests pass | 100% | CI |
| New multi-set tests | 20+ tests | Test count |
| Parse 5-set block | < 1.2× single set time | Benchmark |
| No runtime regression | 0% | Benchmark |
| Nested comma tests pass | All 6 cases | `TestMultiSetNestedCommas` |
| Backward compatibility | 100% | Existing syntax unchanged |

---

## Rollout Plan

1. **Phase 1**: Implement parser changes, add tests
2. **Phase 2**: Update documentation
3. **Phase 3**: Migrate 2-3 template files as examples
4. **Phase 4**: Create migration helper script
5. **Phase 5**: Gradually update remaining templates

---

## Open Questions

1. **Should `{% let %}` also support multi-let?**
   - Probably yes, for consistency
   - Same implementation pattern

2. **Should `{% export %}` support multi-export?**
   - Less clear benefit (export is rare)
   - Defer until requested

3. **Should trailing comma be required or optional?**
   - Recommend: optional (like Python)
   - More forgiving for template authors

4. **How are commas inside expressions handled?**
   - Answer: Parenthesized expressions (lists, dicts, function calls, tuples) are self-contained
   - Only top-level commas followed by `NAME =` trigger multi-set
   - `_parse_expression()` naturally handles this since it respects paren/bracket nesting

5. **Can tuple unpacking be combined with multi-set?**
   - Recommend: No, reject `{% set a, b = 1, 2, c = 3 %}`
   - Too confusing; use separate statements for this case
   - The is_tuple_unpack check prevents this

---

## References

- [Volt Template Engine (Phalcon)](https://docs.phalcon.io/latest/volt/) - Multi-set syntax inspiration
- [Cheetah Template Engine](https://cheetahtemplate.org/) - Python-based multi-set
- [Jinja2 `with` Statement](https://jinja.palletsprojects.com/en/3.1.x/templates/#with-statement) - Scoped multi-assign
- [Liquid Performance Guide](https://shopify.dev/docs/storefronts/themes/best-practices/performance) - Variable caching benefits
